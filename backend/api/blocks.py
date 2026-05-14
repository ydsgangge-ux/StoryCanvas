import uuid
import json
from fastapi import APIRouter, HTTPException, Query
from backend.core.database import get_connection
from backend.core.models import BlockCreate, BlockUpdate
from backend.narrative.progress import calculate_completeness

router = APIRouter()


@router.get("/api/projects/{project_id}/blocks")
def list_blocks(project_id: str, type: str = None, timeline_id: str = None, on_canvas: str = None):
    """获取块列表。on_canvas=1仅画布上, on_canvas=0仅池中, 不传=全部"""
    conn = get_connection()
    query = "SELECT * FROM blocks WHERE project_id = ?"
    params = [project_id]
    if type:
        query += " AND type = ?"
        params.append(type)
    if timeline_id:
        query += " AND timeline_id = ?"
        params.append(timeline_id)
    if on_canvas is not None:
        query += " AND on_canvas = ?"
        params.append(on_canvas)
    query += " ORDER BY created_at ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return _serialize_blocks(rows)


def _serialize_blocks(rows):
    result = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d.get("tags") or "[]")
        d["content"] = json.loads(d.get("content") or "{}")
        d["collapsed"] = bool(d["collapsed"])
        d["is_draft"] = bool(d["is_draft"])
        d["on_canvas"] = bool(d.get("on_canvas", True))
        result.append(d)
    return result


@router.post("/api/projects/{project_id}/blocks")
def create_block(project_id: str, req: BlockCreate):
    conn = get_connection()
    existing = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not existing:
        raise HTTPException(404, "项目不存在")

    block_id = str(uuid.uuid4())
    content_json = json.dumps(req.content, ensure_ascii=False)
    tags_json = json.dumps(req.tags, ensure_ascii=False)

    completeness = calculate_completeness(req.type, req.content)

    conn.execute(
        """INSERT INTO blocks (id, project_id, type, canvas_x, canvas_y, canvas_w, collapsed,
           color, timeline_id, chapter_pos, tags, notes, content, is_draft, completeness)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (block_id, project_id, req.type, req.canvas_x, req.canvas_y, req.canvas_w,
         int(req.collapsed), req.color, req.timeline_id, req.chapter_pos,
         tags_json, req.notes, content_json, int(req.is_draft), completeness)
    )
    conn.commit()
    conn.close()
    # 触发经验标记检查
    from backend.core.experience import auto_check
    try:
        auto_check(project_id)
    except Exception:
        pass  # 非关键操作
    return {"id": block_id, "message": "块创建成功"}


@router.get("/api/projects/{project_id}/blocks/{block_id}")
def get_block(project_id: str, block_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM blocks WHERE id = ? AND project_id = ?",
                        (block_id, project_id)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "块不存在")
    return _serialize_blocks([row])[0]


@router.put("/api/projects/{project_id}/blocks/{block_id}")
def update_block(project_id: str, block_id: str, req: BlockUpdate):
    conn = get_connection()
    existing = conn.execute("SELECT * FROM blocks WHERE id = ? AND project_id = ?",
                             (block_id, project_id)).fetchone()
    if not existing:
        raise HTTPException(404, "块不存在")

    updates = {}
    if req.canvas_x is not None: updates["canvas_x"] = req.canvas_x
    if req.canvas_y is not None: updates["canvas_y"] = req.canvas_y
    if req.canvas_w is not None: updates["canvas_w"] = req.canvas_w
    if req.collapsed is not None: updates["collapsed"] = int(req.collapsed)
    if req.color is not None: updates["color"] = req.color
    if req.timeline_id is not None: updates["timeline_id"] = req.timeline_id
    if req.chapter_pos is not None: updates["chapter_pos"] = req.chapter_pos
    if req.tags is not None: updates["tags"] = json.dumps(req.tags, ensure_ascii=False)
    if req.notes is not None: updates["notes"] = req.notes
    if req.is_draft is not None: updates["is_draft"] = int(req.is_draft)
    if req.on_canvas is not None: updates["on_canvas"] = int(req.on_canvas)
    if req.content is not None:
        updates["content"] = json.dumps(req.content, ensure_ascii=False)
        content_data = req.content
    else:
        content_data = json.loads(existing["content"] or "{}")

    if req.content is not None or req.tags is not None:
        updates["completeness"] = calculate_completeness(
            existing["type"],
            req.content if req.content is not None else content_data
        )

    if updates:
        updates["updated_at"] = "datetime('now')"
        set_clause = ", ".join(f"{k} = ?" for k in updates if k != "updated_at")
        set_clause += ", updated_at = datetime('now')"
        values = [v for k, v in updates.items() if k != "updated_at"]
        values.append(block_id)
        try:
            conn.execute(f"UPDATE blocks SET {set_clause} WHERE id = ?", values)
        except Exception as e:
            conn.close()
            raise HTTPException(500, f"数据库错误: {str(e)}")
        conn.commit()

    conn.close()
    return {"message": "更新成功"}


@router.delete("/api/projects/{project_id}/blocks/{block_id}")
def delete_block(project_id: str, block_id: str):
    conn = get_connection()
    # 先删连线（外键依赖 blocks），再删块本身
    conn.execute("DELETE FROM connections WHERE project_id = ? AND (from_block = ? OR to_block = ?)",
                 (project_id, block_id, block_id))
    conn.execute("DELETE FROM blocks WHERE id = ? AND project_id = ?", (block_id, project_id))
    conn.commit()
    conn.close()
    return {"message": "块已删除"}


@router.post("/api/projects/{project_id}/blocks/batch")
def batch_create_blocks(project_id: str, blocks: list[BlockCreate]):
    conn = get_connection()
    created = []
    for req in blocks:
        block_id = str(uuid.uuid4())
        content_json = json.dumps(req.content, ensure_ascii=False)
        tags_json = json.dumps(req.tags, ensure_ascii=False)
        completeness = calculate_completeness(req.type, req.content)
        conn.execute(
            """INSERT INTO blocks (id, project_id, type, canvas_x, canvas_y, canvas_w, collapsed,
               color, timeline_id, chapter_pos, tags, notes, content, is_draft, completeness)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (block_id, project_id, req.type, req.canvas_x, req.canvas_y, req.canvas_w,
             int(req.collapsed), req.color, req.timeline_id, req.chapter_pos,
             tags_json, req.notes, content_json, int(req.is_draft), completeness)
        )
        created.append({"id": block_id, "type": req.type})
    conn.commit()
    conn.close()
    return {"blocks": created, "message": f"已创建 {len(created)} 个块"}


@router.put("/api/projects/{project_id}/blocks/batch-move")
def batch_move_blocks(project_id: str, moves: list[dict]):
    conn = get_connection()
    for move in moves:
        bid = move.get("id")
        x = move.get("canvas_x")
        y = move.get("canvas_y")
        if bid and x is not None and y is not None:
            conn.execute("UPDATE blocks SET canvas_x = ?, canvas_y = ?, updated_at = datetime('now') WHERE id = ? AND project_id = ?",
                         (x, y, bid, project_id))
    conn.commit()
    conn.close()
    return {"message": "批量移动成功"}


# ─── 块池管理 ────────────────────────────────────────────


@router.get("/api/projects/{project_id}/pool-blocks")
def list_pool_blocks(project_id: str, type: str = None):
    """获取块池中的块（不在画布上的块）"""
    conn = get_connection()
    query = "SELECT * FROM blocks WHERE project_id = ? AND COALESCE(on_canvas, 1) = 0"
    params = [project_id]
    if type:
        query += " AND type = ?"
        params.append(type)
    query += " ORDER BY updated_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return _serialize_blocks(rows)


@router.post("/api/projects/{project_id}/blocks/{block_id}/move-to-canvas")
def move_block_to_canvas(project_id: str, block_id: str):
    """将块从池移到画布"""
    conn = get_connection()
    existing = conn.execute("SELECT id FROM blocks WHERE id = ? AND project_id = ?", (block_id, project_id)).fetchone()
    if not existing:
        raise HTTPException(404, "块不存在")
    conn.execute("UPDATE blocks SET on_canvas = 1, updated_at = datetime('now') WHERE id = ?", (block_id,))
    conn.commit()
    conn.close()
    return {"message": "块已放到画布"}


@router.post("/api/projects/{project_id}/blocks/{block_id}/move-to-pool")
def move_block_to_pool(project_id: str, block_id: str):
    """将块从画布移到池"""
    conn = get_connection()
    existing = conn.execute("SELECT id FROM blocks WHERE id = ? AND project_id = ?", (block_id, project_id)).fetchone()
    if not existing:
        raise HTTPException(404, "块不存在")
    conn.execute("UPDATE blocks SET on_canvas = 0, updated_at = datetime('now') WHERE id = ?", (block_id,))
    conn.commit()
    conn.close()
    return {"message": "块已移回块池"}
