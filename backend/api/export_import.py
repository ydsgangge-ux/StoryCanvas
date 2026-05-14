"""导出/导入 API - .storycanvas / canvas-json / Markdown / PNG"""
import uuid
import json
import io
import zipfile
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from backend.core.database import get_connection
from backend.core.snapshot import get_snapshots

router = APIRouter()


# ─── 补充导出端点（占位，实际实现延后） ──────────────────────

@router.get("/api/projects/{project_id}/export/canvas-png")
def export_canvas_png(project_id: str):
    """导出画布截图PNG（含工作流元数据）- 需要截图渲染支持"""
    raise HTTPException(501, "Canvas PNG导出需要截图渲染支持，将在后续版本实现")


@router.get("/api/projects/{project_id}/export/screenplay")
def export_screenplay(project_id: str):
    """导出剧本PDF"""
    raise HTTPException(501, "剧本PDF导出将在后续版本实现")


@router.get("/api/projects/{project_id}/export/characters")
def export_characters(project_id: str):
    """导出角色手册"""
    conn = get_connection()
    chars = conn.execute(
        "SELECT id, content FROM blocks WHERE project_id = ? AND type = 'CHARACTER'", (project_id,)
    ).fetchall()
    conn.close()
    lines = ["# 角色手册\n"]
    for c in chars:
        cc = json.loads(c["content"] or "{}")
        lines.append(f"\n## {cc.get('name', '未命名角色')}\n")
        lines.append(f"- 年龄: {cc.get('age', '?')}\n")
        lines.append(f"- 外貌: {cc.get('appearance', '?')}\n")
        lines.append(f"- 想要: {cc.get('want', '?')}\n")
        lines.append(f"- 需要: {cc.get('need', '?')}\n")
        lines.append(f"- 致命缺陷: {cc.get('fatal_flaw', '?')}\n")
        lines.append(f"- 能力: {cc.get('superpower', '?')}\n")
        lines.append(f"- 说话风格: {cc.get('voice_style', '?')}\n")
    content = "".join(lines)
    from urllib.parse import quote
    filename = quote("角色手册.md")
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )


@router.get("/api/projects/{project_id}/export/worldbuilding")
def export_worldbuilding(project_id: str):
    """导出世界设定集"""
    conn = get_connection()
    world = conn.execute(
        "SELECT id, content FROM blocks WHERE project_id = ? AND type IN ('WORLDVIEW', 'FACTION', 'RULE_CONSTRAINT')",
        (project_id,)
    ).fetchall()
    conn.close()
    lines = ["# 世界设定集\n"]
    for w in world:
        wc = json.loads(w["content"] or "{}")
        lines.append(f"\n## {wc.get('world_name') or wc.get('name') or wc.get('rule_name', '未命名')}\n")
        if wc.get("fundamental_rules"):
            lines.append(f"规则: {', '.join(wc['fundamental_rules'])}\n")
        if wc.get("ideology"):
            lines.append(f"意识形态: {wc['ideology']}\n")
        if wc.get("goal"):
            lines.append(f"目标: {wc['goal']}\n")
        if wc.get("mechanism"):
            lines.append(f"机制: {wc['mechanism']}\n")
    content = "".join(lines)
    from urllib.parse import quote
    filename = quote("世界设定集.md")
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )


# ─── 导出 ─────────────────────────────────────────────────────

@router.get("/api/projects/{project_id}/export/full")
def export_full(project_id: str, include_drafts: bool = Query(False)):
    """导出完整 .storycanvas 文件"""
    conn = get_connection()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        conn.close()
        raise HTTPException(404, "项目不存在")

    blocks = conn.execute(
        "SELECT * FROM blocks WHERE project_id = ?" + ("" if include_drafts else " AND is_draft = 0"),
        (project_id,)
    ).fetchall()
    connections = conn.execute("SELECT * FROM connections WHERE project_id = ?", (project_id,)).fetchall()
    layout = conn.execute("SELECT * FROM canvas_layout WHERE project_id = ?", (project_id,)).fetchone()
    chapters = conn.execute("SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_num ASC", (project_id,)).fetchall()

    # 构建 canvas.json
    canvas = {
        "viewport": {"x": layout["viewport_x"] if layout else 0, "y": layout["viewport_y"] if layout else 0, "zoom": layout["zoom"] if layout else 1.0},
        "timeline_layout": json.loads(layout["timeline_y"]) if layout and layout["timeline_y"] else {},
        "blocks": [dict(b) for b in blocks],
        "connections": [dict(c) for c in connections],
    }

    # 构建 metadata
    stats = {
        "total_blocks": len(blocks),
        "total_chapters": len([c for c in chapters if c["content"]]),
        "total_words": sum(c["word_count"] or 0 for c in chapters),
        "story_cards": json.loads(project["story_cards"] or "[]"),
    }
    meta = {
        "storycanvas_version": "1.0",
        "project_id": project_id,
        "title": project["title"],
        "created_at": project["created_at"],
        "exported_at": __import__("datetime").datetime.now().isoformat(),
        "stats": stats,
        "app_info": {"platform": "StoryCanvas", "version": "1.0.0"},
    }

    # 打包 ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("metadata.json", json.dumps(meta, ensure_ascii=False, indent=2))
        zf.writestr("canvas.json", json.dumps(canvas, ensure_ascii=False, indent=2))
        zf.writestr("style_signature.json", json.dumps(json.loads(project["style_sig"] or "{}"), ensure_ascii=False, indent=2))
        zf.writestr("story_cards.json", json.dumps(json.loads(project["story_cards"] or "[]"), ensure_ascii=False, indent=2))
        zf.writestr("omniscient.json", json.dumps(json.loads(project["omniscient"] or "{}"), ensure_ascii=False, indent=2))

        # 检查点快照
        checkpoints = conn.execute(
            "SELECT * FROM snapshots WHERE project_id = ? AND snapshot_type = 'checkpoint' ORDER BY created_at ASC",
            (project_id,)
        ).fetchall()
        for i, cp in enumerate(checkpoints):
            cp_dict = dict(cp)
            cp_dict.pop("project_id", None)
            zf.writestr(f"snapshots/checkpoint_{i+1:03d}.json", json.dumps(cp_dict, ensure_ascii=False, indent=2))

        # 章节正文
        for ch in chapters:
            if ch["content"]:
                filename = f"chapters/chapter_{ch['chapter_num']:03d}.md"
                zf.writestr(filename, ch["content"])

    conn.close()
    zip_buffer.seek(0)

    from urllib.parse import quote
    filename = quote(f"{project['title']}.storycanvas")
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )


@router.get("/api/projects/{project_id}/export/canvas-json")
def export_canvas_json(project_id: str, include_drafts: bool = Query(False)):
    """只导出 canvas.json"""
    conn = get_connection()
    blocks = conn.execute(
        "SELECT * FROM blocks WHERE project_id = ?" + ("" if include_drafts else " AND is_draft = 0"),
        (project_id,)
    ).fetchall()
    connections = conn.execute("SELECT * FROM connections WHERE project_id = ?", (project_id,)).fetchall()
    layout = conn.execute("SELECT * FROM canvas_layout WHERE project_id = ?", (project_id,)).fetchone()
    conn.close()

    canvas = {
        "viewport": {"x": layout["viewport_x"] if layout else 0, "y": layout["viewport_y"] if layout else 0, "zoom": layout["zoom"] if layout else 1.0},
        "timeline_layout": json.loads(layout["timeline_y"]) if layout and layout["timeline_y"] else {},
        "blocks": [dict(b) for b in blocks],
        "connections": [dict(c) for c in connections],
    }
    return canvas


@router.get("/api/projects/{project_id}/export/markdown")
def export_markdown(project_id: str):
    """导出全书为 Markdown"""
    conn = get_connection()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    chapters = conn.execute(
        "SELECT * FROM chapters WHERE project_id = ? AND status != 'planned' ORDER BY chapter_num ASC",
        (project_id,)
    ).fetchall()
    conn.close()

    if not project:
        raise HTTPException(404, "项目不存在")

    lines = [f"# {project['title']}\n"]
    for ch in chapters:
        title = ch.get("title") or ""
        lines.append(f"\n## 第{ch['chapter_num']}章 {title}\n")
        if ch["content"]:
            lines.append(ch["content"] + "\n")

    content = "".join(lines)
    from urllib.parse import quote
    filename = quote(f"{project['title']}.md")
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )


# ─── 导入 ─────────────────────────────────────────────────────

@router.post("/api/projects/import/preview")
async def import_preview(file: UploadFile = File(...)):
    """导入预览（不写库）"""
    content = await file.read()
    filename = file.filename or ""
    info = {"filename": filename}

    if filename.endswith(".storycanvas"):
        meta = _read_storycanvas_meta(content)
        info.update(meta)
    elif filename.endswith(".json"):
        try:
            canvas = json.loads(content)
            info["format"] = "canvas.json"
            info["title"] = "导入的画布"
            info["total_blocks"] = len(canvas.get("blocks", []))
            info["total_connections"] = len(canvas.get("connections", []))
            info["total_chapters"] = 0
            info["total_words"] = 0
            info["exported_at"] = None
        except json.JSONDecodeError:
            raise HTTPException(400, "无效的 JSON 文件")
    else:
        raise HTTPException(400, f"不支持的文件格式: {filename}")

    return info


@router.post("/api/projects/import")
async def import_project(file: UploadFile = File(...), as_new: bool = Query(True)):
    """通用导入入口（.storycanvas / .json / .png）"""
    content = await file.read()
    filename = file.filename or ""

    if filename.endswith(".storycanvas"):
        return _import_storycanvas(content)
    elif filename.endswith(".json"):
        return _import_canvas_json(content)
    elif filename.endswith(".png"):
        return _import_from_png(content)
    else:
        raise HTTPException(400, f"不支持的文件格式: {filename}")


def _import_from_png(content: bytes) -> dict:
    """从PNG元数据提取canvas.json并还原"""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(content))
        workflow_str = img.info.get("storycanvas_workflow")
        if not workflow_str:
            raise HTTPException(400, "此PNG不包含 StoryCanvas 工作流信息")
        canvas = json.loads(workflow_str)
        return _import_canvas_json(json.dumps(canvas).encode())
    except ImportError:
        raise HTTPException(501, "PIL/Pillow 未安装，无法处理PNG文件")
    except Exception as e:
        raise HTTPException(400, f"PNG导入失败: {str(e)}")


@router.post("/api/projects/{project_id}/import/markdown")
async def import_markdown(project_id: str, chapter_num: int = Query(...), content: str = Query(...)):
    """从Markdown文本导入章节"""
    from backend.core.database import get_connection
    import uuid
    conn = get_connection()
    existing = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not existing:
        raise HTTPException(404, "项目不存在")
    ch_id = str(uuid.uuid4())
    conn.execute(
        "INSERT OR REPLACE INTO chapters (id, project_id, chapter_num, content, word_count, status) VALUES (?, ?, ?, ?, ?, 'imported')",
        (ch_id, project_id, chapter_num, content, len(content))
    )
    conn.commit()
    conn.close()
    return {"message": f"第{chapter_num}章已导入", "chapter_id": ch_id, "word_count": len(content)}


def _read_storycanvas_meta(content: bytes) -> dict:
    """从 .storycanvas 读取元数据（不写库）"""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = zf.namelist()
        if "metadata.json" not in names:
            raise HTTPException(400, "无效的 .storycanvas 文件：缺少 metadata.json")

        meta = json.loads(zf.read("metadata.json"))
        return {
            "format": ".storycanvas",
            "title": meta.get("title", "未命名项目"),
            "storycanvas_version": meta.get("storycanvas_version", "1.0"),
            "total_blocks": meta.get("stats", {}).get("total_blocks", 0),
            "total_chapters": meta.get("stats", {}).get("total_chapters", 0),
            "total_words": meta.get("stats", {}).get("total_words", 0),
            "story_cards": meta.get("stats", {}).get("story_cards", []),
            "exported_at": meta.get("exported_at"),
        }


def _import_storycanvas(content: bytes) -> dict:
    """导入 .storycanvas 文件，还原完整项目"""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = zf.namelist()
        if "metadata.json" not in names:
            raise HTTPException(400, "无效的 .storycanvas 文件")

        meta = json.loads(zf.read("metadata.json"))
        new_id = str(uuid.uuid4())

        conn = get_connection()
        # 创建项目
        conn.execute(
            """INSERT INTO projects (id, title, genre, story_cards, style_sig, omniscient, experience_flags, import_source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_id, (meta.get("title", "导入项目")),
             "", json.dumps(meta.get("stats", {}).get("story_cards", [])),
             "{}", "{}",
             json.dumps({"has_applied_story_card": False, "has_added_custom_blocks": False,
                         "has_generated_chapter": False, "has_created_second_project": False,
                         "expert_mode_enabled": False}),
             meta.get("title", "未命名"))
        )
        conn.execute("INSERT INTO canvas_layout (project_id) VALUES (?)", (new_id,))

        # 还原画布
        if "canvas.json" in names:
            canvas = json.loads(zf.read("canvas.json"))
            _restore_canvas(conn, new_id, canvas)

        # 还原风格签名
        if "style_signature.json" in names:
            style = json.loads(zf.read("style_signature.json"))
            conn.execute("UPDATE projects SET style_sig = ? WHERE id = ?",
                         (json.dumps(style, ensure_ascii=False), new_id))

        # 还原章节正文
        chapter_files = sorted([n for n in names if n.startswith("chapters/")])
        for cf in chapter_files:
            try:
                parts = cf.split("_")
                chapter_num = int(parts[1].split(".")[0]) if len(parts) >= 2 else 0
                content_md = zf.read(cf).decode("utf-8")
                ch_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO chapters (id, project_id, chapter_num, content, word_count, status) VALUES (?, ?, ?, ?, ?, 'imported')",
                    (ch_id, new_id, chapter_num, content_md, len(content_md))
                )
            except (ValueError, IndexError):
                continue

        conn.commit()
        conn.close()

        return {
            "project_id": new_id,
            "title": meta.get("title", "导入项目"),
            "stats": {
                "blocks": meta.get("stats", {}).get("total_blocks", 0),
                "chapters": meta.get("stats", {}).get("total_chapters", 0),
                "words": meta.get("stats", {}).get("total_words", 0),
            }
        }


def _import_canvas_json(content: bytes) -> dict:
    """从 canvas.json 导入"""
    try:
        canvas = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "无效的 JSON 文件")

    new_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO projects (id, title, import_source) VALUES (?, ?, ?)",
        (new_id, "导入的画布", "canvas.json")
    )
    conn.execute("INSERT INTO canvas_layout (project_id) VALUES (?)", (new_id,))
    _restore_canvas(conn, new_id, canvas)
    conn.commit()
    conn.close()

    return {
        "project_id": new_id,
        "title": "导入的画布",
        "stats": {
            "blocks": len(canvas.get("blocks", [])),
            "chapters": 0,
            "words": 0,
        }
    }


def _restore_canvas(conn, project_id: str, canvas: dict):
    """将 canvas.json 的块和连线写入数据库（保留原始ID）"""
    viewport = canvas.get("viewport", {})
    conn.execute(
        "UPDATE canvas_layout SET viewport_x = ?, viewport_y = ?, zoom = ? WHERE project_id = ?",
        (viewport.get("x", 0), viewport.get("y", 0), viewport.get("zoom", 1.0), project_id)
    )

    # ID 冲突映射
    id_map = {}
    for block in canvas.get("blocks", []):
        old_id = block.get("id")
        if not old_id:
            continue
        # Check for ID conflict
        existing = conn.execute("SELECT id FROM blocks WHERE id = ?", (old_id,)).fetchone()
        if existing:
            new_id = str(uuid.uuid4())
            id_map[old_id] = new_id
        else:
            id_map[old_id] = old_id

    for block in canvas.get("blocks", []):
        bid = block.get("id", str(uuid.uuid4()))
        actual_id = id_map.get(bid, bid)
        conn.execute(
            """INSERT OR REPLACE INTO blocks (id, project_id, type, canvas_x, canvas_y, canvas_w, collapsed,
               color, timeline_id, chapter_pos, tags, notes, content, is_draft)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (actual_id, project_id, block.get("type", "SCENE"), block.get("canvas_x", 0),
             block.get("canvas_y", 0), block.get("canvas_w", 280),
             block.get("collapsed", 0), block.get("color"), block.get("timeline_id"),
             block.get("chapter_pos"), block.get("tags", "[]"), block.get("notes", ""),
             json.dumps(block.get("content", {}), ensure_ascii=False),
             block.get("is_draft", 0))
        )

    for conn_data in canvas.get("connections", []):
        old_from = conn_data.get("from_block", "")
        old_to = conn_data.get("to_block", "")
        actual_from = id_map.get(old_from, old_from)
        actual_to = id_map.get(old_to, old_to)
        conn.execute(
            "INSERT INTO connections (id, project_id, from_block, to_block, conn_type, label, chapter_hint) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (conn_data.get("id", str(uuid.uuid4())), project_id, actual_from, actual_to,
             conn_data.get("conn_type", "follows"), conn_data.get("label"), conn_data.get("chapter_hint"))
        )


# ─── 通用手稿导入（三路径） ──────────────────────────────
from pydantic import BaseModel
from typing import Optional


@router.post("/api/projects/{project_id}/extract-from-text")
async def extract_from_text(project_id: str, req: dict):
    """从纯文本中用LLM提取结构化数据（不写库，只预览）"""
    text = req.get("text", "")
    if len(text) < 50:
        raise HTTPException(400, "文本太短，至少50字")

    from backend.llm.base import create_llm
    llm = create_llm()
    import re

    # 分章
    chapters = []
    raw_chapters = re.split(r'(?:^|\n)(?:第\s*\d+\s*[章节部]|Chapter\s*\d+|#{1,3}\s*\d+)', text, flags=re.I | re.M)
    for i, ch in enumerate(raw_chapters):
        ch = ch.strip()
        if len(ch) < 20:
            continue
        chapters.append({"number": i + 1, "preview": ch[:300], "word_count": len(ch)})

    chapter_previews = "\n".join(f"第{c['number']}章({c['word_count']}字): {c['preview']}" for c in chapters[:20])

    system_prompt = """你是一位资深叙事分析师。根据小说各章摘要，提取结构化信息。
只输出JSON，不要任何说明。JSON格式：
{
  "title": "小说标题",
  "logline": "一句话概括",
  "characters": [{"name":"角色名", "role":"主角/反派/配角", "want":"想要什么", "need":"需要什么", "description":"简要描述"}],
  "world": {"name":"世界观名称", "rules":["规则1"], "factions":[{"name":"势力名","ideology":"理念"}]},
  "events": [{"title":"事件名", "chapter":所属章节号, "description":"简要描述"}]
}"""

    user_prompt = f"以下是小说各章摘要（共{len(chapters)}章，{len(text)}字）：\n\n{chapter_previews[:4000]}"

    result = await llm.chat(system_prompt, user_prompt, temperature=0.3)
    result = result.strip()
    if result.startswith("```"):
        result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(result)
    except json.JSONDecodeError:
        import re as regex
        match = regex.search(r'\{.*\}', result, regex.DOTALL)
        parsed = json.loads(match.group()) if match else {"error": "解析失败"}

    return {
        "extraction": parsed,
        "chapters_detected": len(chapters),
        "characters_extracted": len(parsed.get("characters", [])),
    }


@router.post("/api/projects/{project_id}/import/structured")
def import_structured(project_id: str, req: dict):
    """导入结构化JSON（无LLM，直接写库）"""
    conn = get_connection()
    existing = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not existing:
        raise HTTPException(404, "项目不存在")

    created = {"blocks": [], "on_canvas": 0, "in_pool": 0}

    for char in req.get("characters", []):
        bid = str(uuid.uuid4())
        content = {
            "name": char.get("name", "未命名"),
            "want": char.get("want", ""),
            "need": char.get("need", ""),
            "role_archetype": char.get("role", "配角"),
            "surface_personality": char.get("description", ""),
        }
        is_main = char.get("role") in ("主角", "protagonist")
        conn.execute(
            "INSERT INTO blocks (id, project_id, type, canvas_x, canvas_y, on_canvas, content) VALUES (?, ?, 'CHARACTER', ?, ?, ?, ?)",
            (bid, project_id, 100 + len(created["blocks"]) * 30, 200 + (0 if is_main else 400),
             1 if is_main else 0, json.dumps(content, ensure_ascii=False))
        )
        created["blocks"].append(bid)
        if is_main:
            created["on_canvas"] += 1
        else:
            created["in_pool"] += 1

    world = req.get("world", {})
    if world.get("name"):
        bid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO blocks (id, project_id, type, canvas_x, canvas_y, on_canvas, content) VALUES (?, ?, 'WORLDVIEW', ?, ?, 1, ?)",
            (bid, project_id, 600, 100, json.dumps({
                "world_name": world.get("name", ""), "fundamental_rules": world.get("rules", [])
            }, ensure_ascii=False))
        )
        created["blocks"].append(bid)
        created["on_canvas"] += 1

    for faction in world.get("factions", []):
        bid = str(uuid.uuid4())
        on_c = 1 if len(world.get("factions", [])) <= 5 else 0
        conn.execute(
            "INSERT INTO blocks (id, project_id, type, canvas_x, canvas_y, on_canvas, content) VALUES (?, ?, 'FACTION', ?, ?, ?, ?)",
            (bid, project_id, 600, 200 + len(world.get("factions", [])) * 80, on_c,
             json.dumps({"name": faction.get("name", ""), "ideology": faction.get("ideology", "")}, ensure_ascii=False))
        )
        created["blocks"].append(bid)
        if on_c: created["on_canvas"] += 1
        else: created["in_pool"] += 1

    for evt in req.get("events", []):
        bid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO blocks (id, project_id, type, canvas_x, canvas_y, on_canvas, content) VALUES (?, ?, 'EVENT', ?, ?, 0, ?)",
            (bid, project_id, 300 + len(req.get("events", [])) * 20, 100,
             json.dumps({"title": evt.get("title", "未命名事件"), "what_happens": evt.get("description", "")}, ensure_ascii=False))
        )
        created["blocks"].append(bid)
        created["in_pool"] += 1

    conn.commit()
    conn.close()
    return {"message": "结构化导入完成", "blocks_created": len(created["blocks"]), "on_canvas": created["on_canvas"], "in_pool": created["in_pool"]}


@router.post("/api/import/dramatica-flow")
async def import_dramatica_flow(file: UploadFile = File(...)):
    """导入 Dramatica-Flow 项目（上传 zip）"""
    import zipfile

    content = await file.read()
    project_id = str(uuid.uuid4())

    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
        names = zf.namelist()

        def read_json(path):
            return json.loads(zf.read(path).decode("utf-8")) if path in names else {}

        characters = read_json("setup/characters.json")
        if not characters:
            for n in names:
                if "characters.json" in n:
                    characters = json.loads(zf.read(n).decode("utf-8"))
                    break

        world = read_json("setup/world.json")
        events = read_json("setup/events.json")
        outline = read_json("outline.json")
    except Exception as e:
        raise HTTPException(400, f"Dramatica-Flow 项目解析失败: {str(e)}")

    structured = {"characters": [], "world": {"name": "", "rules": [], "factions": []}, "events": []}

    if isinstance(characters, dict):
        for cid, cdata in characters.items():
            structured["characters"].append({
                "name": cdata.get("name", cid), "want": cdata.get("want", ""),
                "need": cdata.get("need", ""), "role": cdata.get("role", "配角"),
                "description": cdata.get("appearance", "") or cdata.get("personality", ""),
            })

    if world:
        w = world if isinstance(world, dict) else {}
        structured["world"]["name"] = w.get("name", "")
        structured["world"]["rules"] = w.get("rules", []) or []
        factions = w.get("factions", {})
        if isinstance(factions, dict):
            structured["world"]["factions"] = [
                {"name": f.get("name", fid), "ideology": f.get("ideology", "")}
                for fid, f in factions.items()
            ]

    if isinstance(events, dict):
        for eid, edata in events.items():
            structured["events"].append({
                "title": edata.get("title", eid), "description": edata.get("description", ""),
                "chapter": edata.get("chapter", 1),
            })

    # 创建项目
    title = outline.get("title") or structured["world"].get("name") or "Dramatica-Flow 项目"
    conn = get_connection()
    conn.execute("INSERT INTO projects (id, title, story_cards, experience_flags) VALUES (?, ?, '[]', ?)",
                 (project_id, title, json.dumps({"has_applied_story_card": False})))
    conn.execute("INSERT INTO canvas_layout (project_id) VALUES (?)", (project_id,))
    conn.commit()
    conn.close()

    import_result = import_structured(project_id, structured)

    # 导入已有章节
    try:
        chapter_files = sorted([n for n in zf.namelist() if n.startswith("chapters/")])
        imported_chs = []
        for cf in chapter_files:
            import re as regex
            m = regex.search(r'(\d+)', cf)
            if m:
                ch_num = int(m.group(1))
                ch_text = zf.read(cf).decode("utf-8")
                imported_chs.append((ch_num, len(ch_text), ch_text))
        if imported_chs:
            conn2 = get_connection()
            for ch_num, wc, text in imported_chs:
                conn2.execute(
                    "INSERT INTO chapters (id, project_id, chapter_num, content, word_count, status) VALUES (?, ?, ?, ?, ?, 'imported')",
                    (str(uuid.uuid4()), project_id, ch_num, text, wc))
            conn2.commit()
            conn2.close()
    except Exception:
        pass
    finally:
        zf.close()

    return {"project_id": project_id, "title": title, **import_result,
            "chapters_imported": len(imported_chs) if 'imported_chs' in dir() else 0}
