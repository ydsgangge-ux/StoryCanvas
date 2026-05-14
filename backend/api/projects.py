import uuid
import json
from fastapi import APIRouter, HTTPException
from backend.core.database import get_connection
from backend.core.models import ProjectCreate, ProjectUpdate, ApplyStoryCardsRequest
from backend.narrative.progress import calculate_project_progress
from backend.api.blocks import _serialize_blocks
from backend.core.experience import (
    EXPERIENCE_FLAGS_RULES, get_experience_flags, update_flag, auto_check, get_next_steps
)

router = APIRouter()


@router.get("/api/projects/{project_id}/onboarding-status")
def get_onboarding_status(project_id: str):
    """获取引导状态 + 经验标记 + 解锁项"""
    flags = get_experience_flags(project_id)
    unlocked_features = []
    for flag_name, rule in EXPERIENCE_FLAGS_RULES.items():
        if flags.get(flag_name):
            unlocked_features.extend(rule["unlocks"])
    return {
        "flags": flags,
        "unlocked_features": unlocked_features,
        "next_steps": get_next_steps(flags),
    }


@router.post("/api/projects/{project_id}/toggle-expert-mode")
def toggle_expert_mode(project_id: str):
    """切换专家模式"""
    conn = get_connection()
    existing = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not existing:
        raise HTTPException(404, "项目不存在")
    flags = get_experience_flags(project_id)
    is_expert = not flags.get("expert_mode_enabled", False)
    update_flag(project_id, "expert_mode_enabled", is_expert)
    return {"expert_mode_enabled": is_expert, "message": "专家模式已开启" if is_expert else "专家模式已关闭"}


@router.get("/api/projects")
def list_projects():
    conn = get_connection()
    rows = conn.execute("SELECT id, title, genre, story_cards, chapter_count, created_at, updated_at FROM projects ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/api/projects")
def create_project(req: ProjectCreate):
    project_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        """INSERT INTO projects (id, title, genre, story_cards, style_sig, omniscient, chapter_count, experience_flags)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (project_id, req.title, req.genre, req.story_cards or "[]",
         req.style_sig or "{}", req.omniscient or "{}",
         req.chapter_count or 30,
         json.dumps({"has_applied_story_card": False, "has_added_custom_blocks": False,
                      "has_generated_chapter": False, "has_created_second_project": False,
                      "expert_mode_enabled": False}))
    )
    # Create default canvas layout
    conn.execute("INSERT INTO canvas_layout (project_id) VALUES (?)", (project_id,))
    conn.commit()
    conn.close()
    return {"id": project_id, "title": req.title, "message": "项目创建成功"}


@router.get("/api/projects/{project_id}")
def get_project(project_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        raise HTTPException(404, "项目不存在")
    project = dict(row)

    # Get blocks on canvas (COALESCE handles NULL from migration)
    blocks = conn.execute("SELECT * FROM blocks WHERE project_id = ? AND COALESCE(on_canvas, 1) = 1", (project_id,)).fetchall()
    project["blocks"] = _serialize_blocks(blocks)

    # Get all connections
    conns = conn.execute("SELECT * FROM connections WHERE project_id = ?", (project_id,)).fetchall()
    project["connections"] = [dict(c) for c in conns]

    conn.close()
    return project


@router.put("/api/projects/{project_id}")
def update_project(project_id: str, req: ProjectUpdate):
    conn = get_connection()
    existing = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not existing:
        raise HTTPException(404, "项目不存在")

    updates = {}
    if req.title is not None: updates["title"] = req.title
    if req.genre is not None: updates["genre"] = req.genre
    if req.style_sig is not None: updates["style_sig"] = req.style_sig
    if req.omniscient is not None: updates["omniscient"] = req.omniscient
    if req.chapter_count is not None: updates["chapter_count"] = req.chapter_count

    if updates:
        updates["updated_at"] = "datetime('now')"
        set_clause = ", ".join(f"{k} = ?" for k in updates if k != "updated_at")
        set_clause += ", updated_at = datetime('now')"
        values = [v for k, v in updates.items() if k != "updated_at"]
        values.append(project_id)
        conn.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
        conn.commit()

    conn.close()
    return {"message": "更新成功"}


@router.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM canvas_layout WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM chapters WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM connections WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM snapshots WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM blocks WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return {"message": "项目已删除"}


@router.get("/api/projects/{project_id}/progress")
def get_project_progress(project_id: str):
    conn = get_connection()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        raise HTTPException(404, "项目不存在")
    blocks = conn.execute("SELECT * FROM blocks WHERE project_id = ? AND is_draft = 0",
                           (project_id,)).fetchall()
    conn.close()
    return calculate_project_progress(dict(project), [dict(b) for b in blocks])


@router.post("/api/projects/{project_id}/apply-story-cards")
def apply_story_cards(project_id: str, req: ApplyStoryCardsRequest):
    import json
    from backend.core.database import get_connection
    from backend.story_cards.cards import get_card

    conn = get_connection()
    project = conn.execute("SELECT id, story_cards FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        raise HTTPException(404, "项目不存在")

    primary_card = get_card(req.primary)
    if not primary_card:
        raise HTTPException(400, f"故事卡 {req.primary} 不存在")

    all_cards = [(req.primary, primary_card)]
    for sid in req.secondary:
        card = get_card(sid)
        if card:
            all_cards.append((sid, card))

    created_blocks = []
    created_connections = []

    # 创建故事卡框架块（STORY_CARD类型，放在画布右上区域）
    story_card_block_id = str(uuid.uuid4())
    sc_content = {
        "card_id": req.primary,
        "card_name": primary_card.get("name", ""),
        "genre": primary_card.get("category", ""),
        "writing_modifier": primary_card.get("writing_prompt_modifier", ""),
        "reference_works": ", ".join(primary_card.get("reference_works", [])),
    }
    conn.execute(
        """INSERT INTO blocks (id, project_id, type, canvas_x, canvas_y, canvas_w, content)
           VALUES (?, ?, 'STORY_CARD', ?, ?, ?, ?)""",
        (story_card_block_id, project_id, 800, 50, 300, json.dumps(sc_content, ensure_ascii=False))
    )
    created_blocks.append({"id": story_card_block_id, "type": "STORY_CARD"})

    # Create blocks from all cards
    seen_types = set()
    for cid, card in all_cards:
        auto_blocks = card.get("auto_blocks", {})
        for block_def in auto_blocks.get("required", []):
            btype = block_def["type"]
            key = f"{btype}_{cid}"
            if key in seen_types:
                continue
            seen_types.add(key)
            bid = str(uuid.uuid4())
            defaults = block_def.get("content_defaults", {})
            content = json.dumps(defaults) if defaults else "{}"
            conn.execute(
                """INSERT INTO blocks (id, project_id, type, canvas_x, canvas_y, content)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (bid, project_id, btype, block_def["canvas"]["x"], block_def["canvas"]["y"], content)
            )
            created_blocks.append({"id": bid, "type": btype})

        for block_def in auto_blocks.get("recommended", []):
            bid = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO blocks (id, project_id, type, canvas_x, canvas_y, content)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (bid, project_id, block_def["type"],
                 block_def["canvas"]["x"], block_def["canvas"]["y"], "{}")
            )
            created_blocks.append({"id": bid, "type": block_def["type"]})

        for conn_def in card.get("auto_connections", []):
            # Find blocks by type
            from_blocks = conn.execute(
                "SELECT id FROM blocks WHERE project_id = ? AND type = ?", (project_id, conn_def["from_type"])
            ).fetchall()
            to_blocks = conn.execute(
                "SELECT id FROM blocks WHERE project_id = ? AND type = ?", (project_id, conn_def["to_type"])
            ).fetchall()
            if from_blocks and to_blocks:
                cid = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO connections (id, project_id, from_block, to_block, conn_type, label)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (cid, project_id, from_blocks[0]["id"], to_blocks[0]["id"],
                     conn_def["conn_type"], conn_def.get("label", ""))
                )
                created_connections.append({"id": cid})

    # Update experience flags
    flags = json.loads(project["story_cards"] or "[]")
    if req.primary not in flags:
        flags.append(req.primary)
    conn.execute("UPDATE projects SET story_cards = ?, updated_at = datetime('now') WHERE id = ?",
                 (json.dumps(flags), project_id))
    conn.commit()
    conn.close()

    return {"blocks": created_blocks, "connections": created_connections}
