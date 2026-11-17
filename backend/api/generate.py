import json
import re
import uuid
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from backend.core.database import get_connection
from backend.core.models import GenerateOutlineRequest, GenerateContentRequest, GenerateBlockContentRequest, RewriteContentRequest, SaveOutlineRequest
from backend.narrative.aggregator import ContextAggregator
from backend.pipeline.architect import run as architect_run
from backend.pipeline.writer import stream as writer_stream
from backend.pipeline.auditor import run as auditor_run
from backend.pipeline.revisor import run as revisor_run
from backend.pipeline.writeback import WritebackService
from backend.llm.base import create_llm
from backend.core.config import settings

router = APIRouter()
aggregator = ContextAggregator()


def _with_output_language(system_prompt: str, language: str) -> str:
    """按输出语言附加说明。仅当 language='en' 时追加英文输出要求，中文保持原样。"""
    if language == "en":
        return system_prompt + "\n请始终使用英文输出全部内容。\nAlways respond entirely in English."
    return system_prompt


def _clean_trailing_commas(s: str) -> str:
    """移除 JSON 字符串中逗号后面紧跟 } 或 ] 的尾部逗号（脏 JSON 常见错误）。
    例如 {"a": "1",} -> {"a": "1"}。"""
    return re.sub(r',\s*([}\]])', r'\1', s)


def _parse_llm_json(result: str, fields: dict) -> dict:
    """健壮地解析 LLM 输出的 JSON。逐级降级，最后一定返回 dict 而非抛异常。"""
    candidates = []
    if result:
        candidates.append(result)
    match = re.search(r'\{.*\}', result, re.DOTALL)
    if match:
        candidates.append(match.group())
    # 去掉首尾括号分别尝试（防止开头有多余说明文字）
    for cand in list(candidates):
        cand = cand.strip()
        if cand.startswith("{"):
            candidates.append(cand.split("}", 1)[0] + "}")
        if cand.endswith("}"):
            candidates.append("{" + cand.rsplit("{", 1)[1])
    for cand in candidates:
        for variant in (cand, _clean_trailing_commas(cand)):
            variant = variant.strip()
            if not variant:
                continue
            try:
                parsed = json.loads(variant)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
    # 全部失败：把整段文字塞给第一个字段，保证接口不崩溃
    first = list(fields.keys())[0] if fields else "content"
    return {first: (result or "")[:200]}


@router.get("/api/projects/{project_id}/debug/context/{chapter_num}")
def debug_context(project_id: str, chapter_num: int):
    """诊断：查看聚合器产出的上下文，检查哪些数据传进去了"""
    conn = get_connection()
    project = conn.execute("SELECT id, title FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    if not project:
        raise HTTPException(404, "项目不存在")

    ctx = aggregator.aggregate(project_id, chapter_num)

    # 提取关键信息，展示哪些字段有数据、哪些是空的
    summary = {}
    for key in ["story_card_framework", "scene_instructions", "expression_instructions",
                 "active_characters", "pending_hooks", "revealed_truths",
                 "world_background", "timeline_context", "special_links",
                 "chapter_history", "style_signature"]:
        val = ctx.get(key)
        if isinstance(val, list):
            summary[key] = {"type": "list", "count": len(val), "non_empty": len(val) > 0}
        elif isinstance(val, dict):
            summary[key] = {"type": "dict", "keys": list(val.keys()), "non_empty": len(val) > 0}
        elif isinstance(val, str):
            summary[key] = {"type": "text", "length": len(val), "non_empty": len(val) > 0}
        else:
            summary[key] = {"type": type(val).__name__, "value": str(val)[:100], "non_empty": val is not None}

    # 旧key别名也检查
    old_keys_summary = {}
    for key in ["characters", "world", "expression", "history", "timeline", "structure"]:
        val = ctx.get(key)
        if isinstance(val, list):
            old_keys_summary[key] = {"type": "list", "count": len(val), "non_empty": len(val) > 0}
        elif isinstance(val, dict):
            old_keys_summary[key] = {"type": "dict", "keys": list(val.keys()), "non_empty": len(val) > 0}
        elif isinstance(val, str):
            old_keys_summary[key] = {"type": "text", "length": len(val), "non_empty": len(val) > 0}
        else:
            old_keys_summary[key] = {"type": type(val).__name__, "value": str(val)[:100], "non_empty": val is not None}

    # 角色列表预览
    characters_preview = []
    for c in ctx.get("characters", [])[:5]:
        characters_preview.append({"name": c.get("name", "?"), "want": c.get("want", "")[:30]})

    return {
        "project_title": project["title"],
        "chapter_num": chapter_num,
        "total_blocks": ctx.get("total_blocks", 0),
        "total_connections": ctx.get("total_connections", 0),
        "new_keys": summary,
        "old_keys": old_keys_summary,
        "characters_preview": characters_preview,
        "style": ctx.get("style_signature", "")[:200],
        "has_issue": any(
            not v.get("non_empty") for k, v in summary.items()
            if k not in ("special_links", "story_card_framework")
        ),
    }

OUTLINE_PROMPT_TEMPLATE = """你是一个资深叙事策划师。根据以下画布结构，生成第{chapter_num}章的详细章节细纲。

## 世界背景
{world_context}

## 故事大纲与主题
{story_outline}

## 故事框架
{story_framework}

## 关键事件
{key_events}

## 本章时间线
{timeline_info}

## 本章登场角色
{characters_with_boundaries}

## 人物关系
{relationships}

## 本章场景规划
{scene_blocks}

## 已有章节大纲
{chapter_outline}

## 结构要求
- 核心冲突：{conflicts}
- 待触发的转折点：{turning_points}
- 待回收的伏笔：{hooks_to_resolve}
- 待埋设的铺垫：{foreshadows_to_plant}

## 情绪目标
{emotion_target}

## 特殊关联线
{special_links}

## 风格签名
{style_signature}

## 最近章节摘要
{recent_summaries}

请生成章节细纲，格式如下：
1. 章节标题
2. 本章叙事目标（1-2句）
3. 场景序列（每个场景：开场/核心冲突/结尾）
4. 角色行为逻辑确认（每个角色的行动是否符合其信息边界）
5. 伏笔操作清单（埋设/回收/触发）
6. 章末钩子
"""


@router.post("/api/projects/{project_id}/generate/chapter-outline")
async def generate_outline(project_id: str, req: GenerateOutlineRequest):
    """生成章节细纲（SSE流式返回）"""
    conn = get_connection()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        raise HTTPException(404, "项目不存在")
    conn.close()

    ctx = aggregator.aggregate(project_id, req.chapter_num)

    prompt = OUTLINE_PROMPT_TEMPLATE.format(
        chapter_num=req.chapter_num,
        world_context=ctx.get("world") or "无",
        story_outline=_format_story_outline(ctx.get("story_structure", {})),
        story_framework=_format_story_card(ctx.get("story_card_framework", {})),
        key_events=_format_events(ctx.get("story_structure", {}).get("events", [])),
        timeline_info=_format_timelines(ctx.get("timeline", [])),
        characters_with_boundaries=_format_characters(ctx.get("characters", [])),
        relationships=_format_relationships(ctx.get("relationships", [])),
        scene_blocks=_format_scene_blocks(ctx.get("structure", {}).get("scenes", [])),
        chapter_outline=_format_chapter_outline(ctx.get("structure", {}).get("chapter_outline", {})),
        conflicts=_format_conflicts(ctx.get("structure", {}).get("conflicts", [])),
        turning_points=_format_turning_points(ctx.get("structure", {}).get("turning_points", [])),
        hooks_to_resolve=_format_hooks(ctx.get("structure", {}).get("hooks_to_resolve", [])),
        foreshadows_to_plant=_format_hooks(ctx.get("structure", {}).get("foreshadows_to_plant", [])),
        emotion_target=_format_expression(ctx.get("expression", [])),
        special_links=_format_links(ctx.get("special_links", [])),
        style_signature=ctx.get("style_signature") or "无标准风格",
        recent_summaries=ctx.get("history") or "无",
    )

    if req.additional_instructions:
        prompt += f"\n\n## 用户额外指令\n{req.additional_instructions}"

    async def event_stream():
        yield {"data": json.dumps({"event": "stage", "data": {"stage": "outlining", "msg": "正在生成章节细纲..."}})}
        llm = create_llm()
        outline_text = ""
        try:
            async for chunk in llm.chat_stream(
                _with_output_language("你是一个专业的叙事策划师，擅长生成详细的章节细纲。", req.language),
                prompt,
                temperature=0.7
            ):
                outline_text += chunk
                yield {"data": json.dumps({"event": "chunk", "data": {"text": chunk}})}
        except Exception as e:
            yield {"data": json.dumps({"event": "error", "data": {"msg": f"细纲生成失败: {str(e)}"}})}
            return

        # 细纲写回 chapters.outline，否则「细纲 → 正文」链路断裂
        save_chapter_outline_text(project_id, req.chapter_num, outline_text)

        yield {"data": json.dumps({"event": "done", "data": {"outline": outline_text, "chapter_num": req.chapter_num}})}

    return EventSourceResponse(event_stream())


def save_chapter_outline_text(project_id: str, chapter_num: int, outline: str) -> None:
    """保存章节细纲到 chapters.outline（不存在则创建记录）"""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM chapters WHERE project_id = ? AND chapter_num = ?",
            (project_id, chapter_num)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE chapters SET outline = ?, updated_at = datetime('now') WHERE id = ?",
                (outline, existing["id"])
            )
        else:
            conn.execute(
                "INSERT INTO chapters (id, project_id, chapter_num, outline, status) VALUES (?, ?, ?, ?, 'planned')",
                (str(uuid.uuid4()), project_id, chapter_num, outline)
            )
        conn.commit()
    finally:
        conn.close()


@router.post("/api/projects/{project_id}/chapters/{chapter_num}/outline")
def save_chapter_outline(project_id: str, chapter_num: int, req: SaveOutlineRequest):
    """保存用户编辑后的章节细纲"""
    conn = get_connection()
    project = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    if not project:
        raise HTTPException(404, "项目不存在")
    save_chapter_outline_text(project_id, chapter_num, req.outline)
    return {"message": "细纲已保存", "chapter_num": chapter_num}


@router.get("/api/projects/{project_id}/chapters/{chapter_num}")
def get_chapter_content(project_id: str, chapter_num: int):
    """获取单章正文"""
    conn = get_connection()
    chapter = conn.execute(
        "SELECT chapter_num, title, content, word_count, status, outline, created_at, updated_at FROM chapters WHERE project_id = ? AND chapter_num = ?",
        (project_id, chapter_num)
    ).fetchone()
    conn.close()
    if not chapter:
        return {"chapter_num": chapter_num, "content": "", "exists": False}
    return {
        "chapter_num": chapter["chapter_num"],
        "title": chapter["title"],
        "content": chapter["content"] or "",
        "word_count": chapter["word_count"] or 0,
        "status": chapter["status"] or "planned",
        "outline": chapter["outline"] or "",
        "exists": True,
    }


@router.post("/api/projects/{project_id}/generate/chapter-content")
async def generate_chapter_content(project_id: str, req: GenerateContentRequest):
    """生成章节正文（SSE流式返回，五层Agent管线）

    支持通过 block_id 指定使用 CHAPTER_DETAIL 块内容作为写作来源。
    支持 save_only 模式直接保存已编辑的正文。
    """
    # save_only 模式：直接保存正文，不运行管线
    if req.save_only and req.content is not None:
        conn = get_connection()
        existing = conn.execute(
            "SELECT id FROM chapters WHERE project_id = ? AND chapter_num = ?",
            (project_id, req.chapter_num)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE chapters SET content = ?, word_count = ?, status = 'generated', updated_at = datetime('now') WHERE id = ?",
                (req.content, len(req.content), existing["id"])
            )
        else:
            conn.execute(
                "INSERT INTO chapters (id, project_id, chapter_num, content, word_count, status) VALUES (?, ?, ?, ?, ?, 'generated')",
                (str(uuid.uuid4()), project_id, req.chapter_num, req.content, len(req.content))
            )
        conn.commit()
        conn.close()
        return {"message": "正文已保存", "chapter_num": req.chapter_num, "word_count": len(req.content)}

    conn = get_connection()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        raise HTTPException(404, "项目不存在")

    # 优先使用传入的 CHAPTER_DETAIL 块内容作为细纲来源
    outline = None
    if req.block_id:
        detail_block = conn.execute(
            "SELECT * FROM blocks WHERE id = ? AND project_id = ?",
            (req.block_id, project_id)
        ).fetchone()
        if detail_block and detail_block["type"] == "CHAPTER_DETAIL":
            try:
                content = json.loads(detail_block["content"] or "{}")
            except json.JSONDecodeError:
                content = {}
            if not isinstance(content, dict):
                content = {}
            scenes = []
            for i in range(1, 4):
                heading = content.get(f"scene{i}_heading", "")
                body = content.get(f"scene{i}_content", "")
                if heading or body:
                    scenes.append(f"【场景{i}】{heading}\n{body}")
            # 细纲里的冲突/角色目标/写作提示也一并交给建筑师，避免信息丢失
            for key, label in (
                ("key_conflicts", "关键冲突"),
                ("character_goals", "角色目标"),
                ("writing_notes", "写作提示"),
            ):
                value = content.get(key)
                if value:
                    scenes.append(f"【{label}】{value}")
            outline = "\n\n".join(scenes) if scenes else None

    # 如果没有 CHAPTER_DETAIL 块内容，回退到 chapters.outline
    if not outline:
        chapter = conn.execute(
            "SELECT * FROM chapters WHERE project_id = ? AND chapter_num = ?",
            (project_id, req.chapter_num)
        ).fetchone()
        outline = chapter["outline"] if chapter and chapter["outline"] else None

    # 最后回退到画布上的本章章节大纲块（CHAPTER_OUTLINE）
    if not outline:
        outline_blocks = conn.execute(
            """SELECT content FROM blocks
               WHERE project_id = ? AND type = 'CHAPTER_OUTLINE' AND is_draft = 0
               ORDER BY created_at""",
            (project_id,)
        ).fetchall()
        for row in outline_blocks:
            try:
                o_content = json.loads(row["content"] or "{}")
            except json.JSONDecodeError:
                continue
            if not isinstance(o_content, dict):
                continue
            try:
                number = int(o_content.get("chapter_number", 0))
            except (ValueError, TypeError):
                continue
            if number != req.chapter_num:
                continue
            parts = []
            for key, label in (
                ("summary", "概要"),
                ("narrative_goal", "叙事目标"),
                ("dramatic_function", "戏剧功能"),
                ("emotional_arc", "情感曲线"),
            ):
                if o_content.get(key):
                    parts.append(f"【{label}】{o_content[key]}")
            for i in range(1, 4):
                if o_content.get(f"beat{i}_desc"):
                    parts.append(f"【节拍{i}】{o_content[f'beat{i}_desc']}")
            if parts:
                outline = "\n\n".join(parts)
                break

    if not outline:
        outline = "(无细纲，直接生成)"

    conn.close()

    ctx = aggregator.aggregate(project_id, req.chapter_num)

    async def event_stream():
        # ① 建筑师
        yield {"data": json.dumps({"event": "stage", "data": {"stage": "architect", "msg": "建筑师分析蓝图..."}})}
        try:
            blueprint = await architect_run(ctx, outline)
            yield {"data": json.dumps({"event": "stage", "data": {"stage": "writing", "msg": "写手开始创作..."}})}
        except Exception as e:
            yield {"data": json.dumps({"event": "error", "data": {"msg": f"建筑师阶段失败: {str(e)}"}})}
            return

        # ② 写手
        chapter_content = ""
        try:
            async for chunk in writer_stream(blueprint, ctx, language=req.language):
                chapter_content += chunk
                yield {"data": json.dumps({"event": "chunk", "data": {"stage": "writing", "text": chunk}})}
        except Exception as e:
            yield {"data": json.dumps({"event": "error", "data": {"msg": f"写作阶段失败: {str(e)}"}})}
            return

        # Extract content (remove settlement table)
        content_only = extract_content(chapter_content)

        # ③ 验证器（零LLM）
        yield {"data": json.dumps({"event": "stage", "data": {"stage": "validating", "msg": "验证器检查中..."}})}
        from backend.narrative.validator import InformationValidator
        validator = InformationValidator()
        char_boundaries = {}
        for c in ctx.get("characters", []):
            boundary = c.get("knowledge_boundary") or {}
            doesnt_know = []
            for item in boundary.get("wrongly_believes") or []:
                if isinstance(item, dict):
                    doesnt_know.append(item.get("belief") or item.get("info") or "")
                elif isinstance(item, str) and item:
                    doesnt_know.append(item)
            char_boundaries[c.get("id", "")] = {
                "doesnt_know": [x for x in doesnt_know if x],
                "name": c.get("name", ""),
            }
        violations = validator.validate(content_only, char_boundaries)
        for v in violations:
            v["character_name"] = char_boundaries.get(v.get("character", ""), {}).get("name", "")
        if violations:
            yield {"data": json.dumps({"event": "warning", "data": {"violations": violations}})}

        # ④ 审计员
        yield {"data": json.dumps({"event": "stage", "data": {"stage": "auditing", "msg": "审计员检查中..."}})}
        try:
            audit = await auditor_run(content_only, ctx)
            yield {"data": json.dumps({"event": "audit", "data": audit})}
        except Exception as e:
            audit = {"passed": True, "has_critical_issues": False, "result": f"审计跳过: {str(e)}"}
            yield {"data": json.dumps({"event": "audit", "data": audit})}

        # ⑤ 修订（如有严重问题，最多2轮）
        final_content = content_only
        revised_raw = ""
        if not audit.get("passed", True) and audit.get("has_critical_issues", False):
            yield {"data": json.dumps({"event": "stage", "data": {"stage": "revising", "msg": "修订者修复中..."}})}
            for attempt in range(settings.max_retries):
                try:
                    revised = await revisor_run(final_content, audit.get("result", ""), ctx, language=req.language)
                    revised_raw = revised
                    final_content = extract_content(revised)
                    re_audit = await auditor_run(final_content, ctx)
                    if re_audit.get("passed", True):
                        break
                except Exception:
                    break

        # Save chapter
        word_count = len(final_content)
        conn2 = get_connection()
        existing = conn2.execute(
            "SELECT id FROM chapters WHERE project_id = ? AND chapter_num = ?",
            (project_id, req.chapter_num)
        ).fetchone()
        if existing:
            conn2.execute(
                "UPDATE chapters SET content = ?, word_count = ?, status = 'generated', updated_at = datetime('now') WHERE id = ?",
                (final_content, word_count, existing["id"])
            )
        else:
            chapter_id = str(uuid.uuid4())
            conn2.execute(
                "INSERT INTO chapters (id, project_id, chapter_num, content, word_count, status) VALUES (?, ?, ?, ?, ?, 'generated')",
                (chapter_id, project_id, req.chapter_num, final_content, word_count)
            )

        # 同步章节大纲块状态，保持「大纲 → 细纲 → 正文」可追踪
        outline_blocks = conn2.execute(
            "SELECT id, content FROM blocks WHERE project_id = ? AND type = 'CHAPTER_OUTLINE' AND is_draft = 0",
            (project_id,)
        ).fetchall()
        for row in outline_blocks:
            try:
                o_content = json.loads(row["content"] or "{}")
            except json.JSONDecodeError:
                continue
            if not isinstance(o_content, dict):
                continue
            if str(o_content.get("chapter_number", "")) == str(req.chapter_num):
                o_content["status"] = "written"
                conn2.execute(
                    "UPDATE blocks SET content = ?, updated_at = datetime('now') WHERE id = ?",
                    (json.dumps(o_content, ensure_ascii=False), row["id"])
                )

        conn2.commit()

        # 触发经验标记：has_generated_chapter
        from backend.core.experience import auto_check
        try:
            auto_check(project_id)
        except Exception:
            pass

        # ⑤ 回写器（用含结算表的原始文本，正文本身已剥离结算表）
        writeback = WritebackService()
        wb_result = writeback.writeback(project_id, req.chapter_num, revised_raw or chapter_content)
        conn2.close()

        yield {"data": json.dumps({"event": "done", "data": {"chapter_num": req.chapter_num, "word_count": word_count, "writeback": wb_result, "chapter_content": final_content}})}

    return EventSourceResponse(event_stream())


@router.post("/api/projects/{project_id}/generate/rewrite")
async def rewrite_content(project_id: str, req: RewriteContentRequest):
    """AI改写/修复章节正文

    - 有 selected_text：LLM 只输出改写后的段落，前端做字符串替换
    - 无 selected_text：LLM 输出全文，前端直接替换
    """
    conn = get_connection()
    chapter = conn.execute(
        "SELECT content FROM chapters WHERE project_id = ? AND chapter_num = ?",
        (project_id, req.chapter_num)
    ).fetchone()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()

    if not chapter or not chapter["content"]:
        raise HTTPException(404, "章节不存在或尚无正文")

    full_text = chapter["content"]
    style_sig = json.loads(project["style_sig"] or "{}")

    is_segment = bool(req.selected_text)

    prompt_parts = []

    if is_segment:
        system_prompt = "你是一位专业的小说修订者。根据用户要求修改指定的文本段落。"
        if req.context_before or req.context_after:
            ctx = []
            if req.context_before:
                ctx.append(f"选中文本前的上下文：\n{req.context_before}")
            if req.context_after:
                ctx.append(f"选中文本后的上下文：\n{req.context_after}")
            prompt_parts.append("\n".join(ctx))
        prompt_parts.append(f"## 需要修改的原文\n{req.selected_text}")
    else:
        system_prompt = "你是一位专业的小说修订者。根据用户要求修改章节正文。"
        prompt_parts.append(f"## 当前正文（第{req.chapter_num}章）\n{full_text}")

    if req.issue:
        prompt_parts.append(f"## 需要修复的问题\n{req.issue}")
    if req.instruction:
        prompt_parts.append(f"## 用户要求\n{req.instruction}")

    from backend.narrative.translator import style_to_prompt
    style = style_to_prompt(style_sig)
    if style:
        prompt_parts.append(f"## 风格要求\n{style}")

    if is_segment:
        prompt_parts.append("请仅输出修改后的段落文本，不要包含原文中未选中的内容，不要加任何解释或标记。保持与上下文的连贯性。")
    else:
        prompt_parts.append("请直接输出修改后的完整正文内容，不要加解释或标记。只修改需要修改的部分，保持其余内容不变。")

    system_prompt = _with_output_language(system_prompt, req.language)

    llm = create_llm()
    result = await llm.chat(system_prompt, "\n\n".join(prompt_parts), temperature=0.6)

    return {"revised_content": result, "is_segment": is_segment}


@router.post("/api/projects/{project_id}/generate/block-content")
async def generate_block_content(project_id: str, req: GenerateBlockContentRequest):
    """AI辅助填充块内容 - 感知连线上下文

    如果块有连线关系，会自动读取关联块的内容作为上下文。
    例如：CHARACTER块连了CONFLICT块 → 生成角色信息时会参考冲突内容。
    """
    conn = get_connection()
    block = conn.execute("SELECT * FROM blocks WHERE id = ? AND project_id = ?",
                         (req.block_id, project_id)).fetchone()
    if not block:
        raise HTTPException(404, "块不存在")

    block_type = block["type"]
    try:
        existing_content = json.loads(block["content"] or "{}")
    except json.JSONDecodeError:
        existing_content = {}
    if not isinstance(existing_content, dict):
        existing_content = {"value": existing_content}

    roster_rows = conn.execute(
        "SELECT id, type, content FROM blocks WHERE project_id = ? AND type IN ('CHARACTER', 'FACTION') ORDER BY created_at, id",
        (project_id,)
    ).fetchall()

    # 查询连出/连入的块
    connected_blocks = _get_connected_blocks(conn, req.block_id, project_id)
    conn.close()

    # 构建连线上下文
    conn_context = ""
    if connected_blocks:
        conn_parts = []
        for cb in connected_blocks:
            direction = "本块 → 该块" if cb.get("direction") == "out" else "该块 → 本块"
            conn_parts.append(
                f"[{cb['conn_type']} / {direction}] {cb['type']}块「{cb['title']}」:\n{cb['content_summary']}"
            )
        conn_context = "## 连线关联的块\n" + "\n\n".join(conn_parts)

    # 需要填写角色/势力ID的块，提供真实ID清单，避免生成无效关联
    roster_context = ""
    ID_REFERENCE_BLOCKS = {
        "INFORMATION_BOUNDARY", "RELATIONSHIP", "ACTION_LINE", "DIALOGUE",
        "CURRENT_STATE", "GROWTH", "FACTION_RELATION", "ATTITUDE",
    }
    if block_type in ID_REFERENCE_BLOCKS and roster_rows:
        roster_lines = []
        for row in roster_rows:
            try:
                roster_content = json.loads(row["content"] or "{}")
            except json.JSONDecodeError:
                roster_content = {}
            if not isinstance(roster_content, dict):
                roster_content = {}
            name = roster_content.get("name") or roster_content.get("world_name") or "未命名"
            roster_lines.append(f"- {row['type']}「{name}」 id: {row['id']}")
        roster_context = (
            "## 可引用的角色/势力ID（character_id / party_a_id / party_b_id 等字段必须使用这里的ID）\n"
            + "\n".join(roster_lines)
        )

    # 构建各个字段的生成提示
    from backend.narrative.progress import (
        COMPLETENESS_RULES, EXTRA_AI_FIELDS, AI_FILL_EXCLUDED_FIELDS, STRUCTURED_FIELD_HINTS,
    )
    rules = dict(COMPLETENESS_RULES.get(block_type, {}))
    # 编辑器可填但未计入完整度权重的字段也要一并补全
    for extra_field in EXTRA_AI_FIELDS.get(block_type, []):
        rules.setdefault(extra_field, 0.0)
    excluded_fields = AI_FILL_EXCLUDED_FIELDS.get(block_type, set())

    # 确定要生成的字段（已填的跳过；指定 field 时只补该字段）
    if req.field and req.field != "all":
        fields_to_generate = {} if existing_content.get(req.field) else {req.field: rules.get(req.field, 0.0)}
    else:
        fields_to_generate = {
            k: v for k, v in rules.items()
            if k not in excluded_fields and not existing_content.get(k)
        }

    if not fields_to_generate:
        return {
            "block_id": req.block_id,
            "block_type": block_type,
            "generated_fields": {},
            "merged_content": existing_content,
            "connections_used": len(connected_blocks),
            "message": "该块已填充完整，无需生成",
        }

    llm = create_llm()
    system_prompt = _with_output_language(f"""你是一位资深叙事设计师。根据已有信息和关联块，为{block_type}类型块生成内容。
直接输出JSON对象，不要解释，不要加markdown标记。JSON键名必须严格匹配指定字段。""", req.language)

    hint_lines = [
        f"- {field_name}: {STRUCTURED_FIELD_HINTS[field_name]}"
        for field_name in fields_to_generate
        if field_name in STRUCTURED_FIELD_HINTS
    ]

    user_prompt_parts = [
        f"## 目标块类型: {block_type}",
        f"## 已有内容: {json.dumps(existing_content, ensure_ascii=False, indent=2)}" if existing_content else "",
        conn_context,
        roster_context,
        f"## 需要填充的字段及其权重(越高越重要)",
        *[
            f"- {field_name}" + (f" (权重{weight:.0%})" if weight else "")
            for field_name, weight in fields_to_generate.items()
        ],
    ]
    if hint_lines:
        user_prompt_parts.append("## 字段格式要求\n" + "\n".join(hint_lines))
    if req.hint:
        user_prompt_parts.append(f"## 用户提示: {req.hint}")

    field_template = ", ".join(f'"{k}": "..."' for k in fields_to_generate)
    user_prompt_parts.append(f"\n请生成包含以下字段的JSON: {{{field_template}}}")
    user_prompt = "\n".join(p for p in user_prompt_parts if p)

    result = await llm.chat(system_prompt, user_prompt, temperature=0.7)

    # 解析JSON结果
    generated = _parse_block_content_result(result, list(fields_to_generate.keys()))

    # 只接受本次要补的字段，避免覆盖用户已填内容
    merged = {**existing_content, **generated}

    return {
        "block_id": req.block_id,
        "block_type": block_type,
        "generated_fields": generated,
        "merged_content": merged,
        "connections_used": len(connected_blocks),
    }


def _parse_block_content_result(result: str, target_fields: list) -> dict:
    """解析块内容生成结果，并把结构化字段规范化为预期结构"""
    result = (result or "").strip()
    if result.startswith("```"):
        result = result.split("\n", 1)[1] if "\n" in result else ""
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()
        if result.startswith("json"):
            result = result[4:].strip()

    parsed = None
    try:
        parsed = json.loads(result)
    except json.JSONDecodeError:
        parsed = _parse_llm_json(result, {k: None for k in target_fields})

    if not isinstance(parsed, dict):
        parsed = {}

    generated = {}
    for key in target_fields:
        if key not in parsed:
            continue
        value = parsed[key]
        if value in (None, "", [], {}):
            continue
        generated[key] = _normalize_block_field(key, value)
    return generated


# 需要数组结构的关键字段（LLM 有时返回扁平字符串，直接存会破坏后续聚合）
LIST_TEXT_FIELDS = {
    "fundamental_rules", "confirmed_knowledge", "wrongly_believes",
    "pov_characters", "peak_points", "valley_points",
}
DICT_LIST_FIELDS = {
    "true_facts": "content",
    "reader_reveal_plan": "reveal",
}


def _normalize_block_field(field: str, value):
    """把字符串形式的数组字段转换为数组，保证结构正确"""
    if field in LIST_TEXT_FIELDS:
        if isinstance(value, list):
            return [v if isinstance(v, str) else json.dumps(v, ensure_ascii=False) for v in value]
        if isinstance(value, str):
            text = value.strip()
            parsed = None
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = None
            if isinstance(parsed, list):
                return [v if isinstance(v, str) else json.dumps(v, ensure_ascii=False) for v in parsed]
            parts = [p.strip(" -•\t") for p in re.split(r"[\n；;、]+", text) if p.strip(" -•\t")]
            return parts
        return value

    if field in DICT_LIST_FIELDS:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            text = value.strip()
            parsed = None
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = None
            if isinstance(parsed, list):
                return parsed
            parts = [p.strip(" -•\t") for p in re.split(r"[\n；;]+", text) if p.strip(" -•\t")]
            return [{DICT_LIST_FIELDS[field]: p} for p in parts]
        return value

    return value


def _get_connected_blocks(conn, block_id: str, project_id: str) -> list:
    """获取与指定块有连线关系的所有块及其连线类型"""
    rows = conn.execute(
        """SELECT c.conn_type, c.from_block, c.to_block, b.type, b.content, b.id as other_id
           FROM connections c
           JOIN blocks b ON (b.id = CASE WHEN c.from_block = ? THEN c.to_block ELSE c.from_block END)
           WHERE c.project_id = ? AND (c.from_block = ? OR c.to_block = ?)
           AND b.id != ?
           ORDER BY c.created_at""",
        (block_id, project_id, block_id, block_id, block_id)
    ).fetchall()

    from backend.narrative.translator import block_to_context

    result = []
    seen = set()
    for r in rows:
        # 同一对块可能有多条不同类型的连线，按「对方块 + 连线类型」去重
        key = (r["other_id"], r["conn_type"])
        if key in seen:
            continue
        seen.add(key)
        if len(result) >= 12:  # 避免上下文过长挤占正文生成
            break

        try:
            content = json.loads(r["content"] or "{}")
        except (json.JSONDecodeError, TypeError):
            content = {}
        if not isinstance(content, dict):
            content = {"value": content}

        # 优先用统一的块转文本逻辑，避免 json.dumps 截断出半截 JSON
        try:
            summary = block_to_context({"type": r["type"], "content": content})
        except Exception:
            summary = json.dumps(content, ensure_ascii=False)
        summary = (summary or "").strip()
        if len(summary) > 400:
            summary = summary[:400] + "…"

        result.append({
            "conn_type": r["conn_type"],
            "type": r["type"],
            "title": _block_title(r["type"], content),
            "direction": "out" if r["from_block"] == block_id else "in",
            "content_summary": summary,
        })
    return result


def _block_title(block_type: str, content: dict) -> str:
    """提取不同类型块的标题"""
    if block_type == "CHARACTER":
        return content.get("name", "未命名角色")
    if block_type == "SCENE":
        return content.get("title", "未命名场景")
    if block_type in ("EVENT", "HOOK", "CONFLICT", "TURNING_POINT", "FORESHADOW", "SURPRISE"):
        return content.get("title", "")
    if block_type == "WORLDVIEW":
        return content.get("world_name", "")
    if block_type == "FACTION":
        return content.get("name", "")
    if block_type == "GOAL":
        return content.get("surface_goal", "")
    if block_type == "STORYBOARD":
        return content.get("title", "分镜头脚本")
    return block_type


@router.post("/api/projects/{project_id}/generate/suggest-blocks")
async def suggest_blocks(project_id: str, req: dict):
    """基于故事卡和现有块，建议要创建的块"""
    conn = get_connection()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        raise HTTPException(404, "项目不存在")

    story_cards = req.get("story_cards", [])
    if not story_cards:
        # Infer from project
        cards_used = json.loads(project["story_cards"] or "[]")
        story_cards = cards_used if cards_used else ["A1"]

    existing_types = set(b["type"] for b in conn.execute(
        "SELECT DISTINCT type FROM blocks WHERE project_id = ?", (project_id,)
    ).fetchall())
    conn.close()

    # Card-specific block recommendations
    card_suggestions = {
        "A1": [("GOAL", "设定英雄目标"), ("CONFLICT", "定义冲突对手"), ("TURNING_POINT", "标记转折时刻")],
        "A2": [("GOAL", "复仇计划目标"), ("TURNING_POINT", "复仇转折点")],
        "A3": [("FACTION_RELATION", "梳理势力关系"), ("TURNING_POINT", "权力转折点")],
        "A4": [("GOAL", "救援目标"), ("CONFLICT", "救援路上的阻碍")],
        "A5": [("GROWTH", "设定成长弧线"), ("CONFLICT", "成长路上的对手")],
        "B1": [("RELATIONSHIP", "定义双人关系"), ("GROWTH", "彼此成长弧线")],
        "B2": [("RELATIONSHIP", "三角关系定义"), ("CONFLICT", "关系冲突")],
        "B3": [("RELATIONSHIP", "家族关系网络"), ("TIMELINE", "家族时间线")],
        "B4": [("RELATIONSHIP", "群像关系网络"), ("SCENE", "群像场景规划")],
        "B5": [("FACTION_RELATION", "文明间关系"), ("CONFLICT", "文明冲突")],
        "C1": [("FORESHADOW", "埋设线索"), ("SURPRISE", "真相揭露时刻")],
        "C2": [("FORESHADOW", "身份线索铺垫"), ("SURPRISE", "身份揭露时刻")],
        "C3": [("FORESHADOW", "历史线索"), ("TIMELINE", "历史时间线")],
        "C4": [("INFORMATION_BOUNDARY", "角色信息边界"), ("FORESHADOW", "世界谎言线索")],
        "C5": [("FORESHADOW", "考古线索"), ("HOOK", "未解之谜")],
        "D1": [("GOAL", "生存目标"), ("CONFLICT", "生存威胁")],
        "D2": [("FACTION", "压迫势力"), ("CONFLICT", "系统性冲突")],
        "D3": [("RULE_CONSTRAINT", "异世界规则"), ("GOAL", "适应目标")],
        "D4": [("RULE_CONSTRAINT", "游戏规则定义"), ("GOAL", "通关目标")],
        "D5": [("FACTION_RELATION", "种族关系"), ("CONFLICT", "种族冲突")],
        "E1": [("GROWTH", "成长弧线"), ("CONFLICT", "逆袭对手")],
        "E2": [("GROWTH", "认知转变弧线"), ("TURNING_POINT", "认知转折点")],
        "E3": [("GROWTH", "救赎弧线"), ("TURNING_POINT", "救赎转折点")],
        "E4": [("GROWTH", "代价成长弧线"), ("CONFLICT", "代价冲突")],
        "E5": [("GROWTH", "堕落弧线"), ("CONFLICT", "道德冲突")],
        "F1": [("FACTION_RELATION", "文明关系"), ("CONFLICT", "核心冲突")],
        "F2": [("FACTION", "时代势力"), ("TURNING_POINT", "时代转折")],
        "F3": [("FACTION", "神系势力"), ("RULE_CONSTRAINT", "神话规则")],
        "F4": [("INFORMATION_BOUNDARY", "信息边界"), ("HOOK", "跨线悬念")],
        "F5": [("EVENT", "历史大事件"), ("TIMESTAMP", "时间锚点")],
        "F6": [("RULE_CONSTRAINT", "神系规则"), ("CONFLICT", "神战冲突")],
        "G1": [("TIMELINE", "套层时间线"), ("THEME_STATEMENT", "主题呼应")],
        "G2": [("INFORMATION_BOUNDARY", "信息操控"), ("HOOK", "不可靠悬念")],
        "G3": [("TIMELINE", "平行时间线"), ("EVENT", "跨线关键事件")],
        "G4": [("TIMELINE", "编年时间线"), ("EVENT", "编年事件")],
    }

    suggestions = []
    for cid in story_cards:
        if cid in card_suggestions:
            for btype, reason in card_suggestions[cid]:
                if btype not in existing_types:
                    suggestions.append({"block_type": btype, "reason": reason, "card_id": cid})

    # Deduplicate
    seen = set()
    unique = []
    for s in suggestions:
        key = s["block_type"]
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return {"suggestions": unique}


@router.post("/api/projects/{project_id}/audit/{chapter_num}")
async def audit_chapter(project_id: str, chapter_num: int):
    """单章审计，保存审计结果到数据库"""
    import asyncio
    import json
    from backend.pipeline.auditor import run as auditor_run
    from backend.narrative.aggregator import ContextAggregator
    conn = get_connection()
    chapter = conn.execute(
        "SELECT content FROM chapters WHERE project_id = ? AND chapter_num = ?",
        (project_id, chapter_num)
    ).fetchone()
    if not chapter or not chapter["content"]:
        conn.close()
        raise HTTPException(404, "章节不存在或无内容")

    aggregator = ContextAggregator()
    ctx = aggregator.aggregate(project_id, chapter_num)
    result = await auditor_run(chapter["content"], ctx)

    conn.execute(
        "UPDATE chapters SET audit_result = ?, updated_at = datetime('now') WHERE project_id = ? AND chapter_num = ?",
        (json.dumps(result, ensure_ascii=False), project_id, chapter_num)
    )
    conn.commit()
    conn.close()
    return {"audit": result}


@router.get("/api/projects/{project_id}/audit/{chapter_num}")
def get_audit_result(project_id: str, chapter_num: int):
    """获取已保存的审计结果"""
    import json
    conn = get_connection()
    chapter = conn.execute(
        "SELECT audit_result FROM chapters WHERE project_id = ? AND chapter_num = ?",
        (project_id, chapter_num)
    ).fetchone()
    conn.close()
    if not chapter or not chapter["audit_result"]:
        return {"audit": None}
    try:
        return {"audit": json.loads(chapter["audit_result"])}
    except json.JSONDecodeError:
        return {"audit": None}


@router.post("/api/projects/{project_id}/revise/{chapter_num}")
async def revise_chapter(project_id: str, chapter_num: int):
    """单章修订 - 使用已保存的审计结果一键修复全部问题"""
    import json
    from backend.pipeline.auditor import run as auditor_run
    from backend.pipeline.revisor import run as revisor_run
    from backend.narrative.aggregator import ContextAggregator
    conn = get_connection()
    chapter = conn.execute(
        "SELECT content, audit_result FROM chapters WHERE project_id = ? AND chapter_num = ?",
        (project_id, chapter_num)
    ).fetchone()
    if not chapter or not chapter["content"]:
        conn.close()
        raise HTTPException(404, "章节不存在或无内容")

    aggregator = ContextAggregator()
    ctx = aggregator.aggregate(project_id, chapter_num)

    audit = None
    if chapter["audit_result"]:
        try:
            audit = json.loads(chapter["audit_result"])
        except json.JSONDecodeError:
            pass

    if not audit or not audit.get("issues"):
        audit = await auditor_run(chapter["content"], ctx)

    if not audit.get("has_critical_issues", False) and not audit.get("issues"):
        conn.close()
        return {"message": "无需修订", "audit": audit}

    revised = await revisor_run(chapter["content"], audit.get("result", ""), ctx)
    conn.execute(
        "UPDATE chapters SET content = ?, audit_result = NULL, updated_at = datetime('now') WHERE project_id = ? AND chapter_num = ?",
        (revised, project_id, chapter_num)
    )
    conn.commit()
    conn.close()
    return {"message": "修订完成", "revised_content": revised}


# ─── 细纲特殊关联线 ──────────────────────────────────────

SPECIAL_LINK_TYPES = {
    "callback": "呼应前文——本内容与前面某章节的情节形成呼应",
    "foreshadow_setup": "铺设伏笔——本内容是后面某章节伏笔的埋设",
    "parallel_development": "并行发展——两条或多条线索在本章节同步推进",
    "strong_correlation": "强关联——本内容与特定块/事件有直接因果关系需要明确强化",
    "information_asymmetry": "信息差——本章有意让角色/读者掌握不对称的信息",
}


@router.get("/api/projects/{project_id}/chapters/{chapter_num}/special-links")
def get_special_links(project_id: str, chapter_num: int):
    """获取章节特殊关联线"""
    conn = get_connection()
    row = conn.execute(
        "SELECT special_links, outline FROM chapters WHERE project_id = ? AND chapter_num = ?",
        (project_id, chapter_num)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "章节不存在")
    links = json.loads(row["special_links"] or "[]")
    return {
        "links": links,
        "available_types": SPECIAL_LINK_TYPES,
        "outline_summary": (row["outline"] or "")[:200],
    }


@router.put("/api/projects/{project_id}/chapters/{chapter_num}/special-links")
def update_special_links(project_id: str, chapter_num: int, req: dict):
    """更新章节特殊关联线"""
    links = req.get("links", [])
    # 验证格式
    for link in links:
        if "type" not in link or "description" not in link:
            raise HTTPException(400, "每条关联线必须包含 type 和 description")
        if link["type"] not in SPECIAL_LINK_TYPES:
            raise HTTPException(400, f"无效的关联类型: {link['type']}")
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM chapters WHERE project_id = ? AND chapter_num = ?",
        (project_id, chapter_num)
    ).fetchone()
    if not existing:
        raise HTTPException(404, "章节不存在")
    conn.execute(
        "UPDATE chapters SET special_links = ?, updated_at = datetime('now') WHERE project_id = ? AND chapter_num = ?",
        (json.dumps(links, ensure_ascii=False), project_id, chapter_num)
    )
    conn.commit()
    conn.close()
    return {"message": "特殊关联线已更新", "links": links, "count": len(links)}


def _format_timelines(timelines: list) -> str:
    if not timelines:
        return "无"
    return "\n".join(f"- {t['name']} ({t['type']})" for t in timelines)


def _format_hooks(hooks: list) -> str:
    """把伏笔字典列表格式化为文本（不能直接 join，元素是 dict）"""
    if not hooks:
        return "无"
    lines = []
    for h in hooks:
        if isinstance(h, dict):
            title = h.get("title") or h.get("content_planted") or "未命名伏笔"
            payoff = h.get("payoff_chapter")
            urgency = h.get("urgency")
            extra = []
            if payoff not in (None, ""):
                extra.append(f"计划第{payoff}章回收")
            if urgency:
                extra.append(str(urgency))
            suffix = f"（{'，'.join(extra)}）" if extra else ""
            hint = h.get("hint_content") or h.get("content_planted")
            hint_text = f"\n  提示内容: {hint}" if hint else ""
            lines.append(f"- {title}{suffix}{hint_text}")
        else:
            lines.append(f"- {h}")
    return "\n".join(lines)


def _format_expression(expression) -> str:
    """格式化情绪/节奏指令（可能是列表或字典）"""
    if not expression:
        return "无"
    if isinstance(expression, str):
        return expression
    if isinstance(expression, dict):
        parts = []
        for key, value in expression.items():
            if not value:
                continue
            if isinstance(value, list):
                sub = "；".join(
                    ", ".join(f"{k}: {v}" for k, v in item.items() if v) if isinstance(item, dict) else str(item)
                    for item in value
                )
                parts.append(f"{key}: {sub}")
            elif isinstance(value, dict):
                parts.append(f"{key}: " + ", ".join(f"{k}: {v}" for k, v in value.items() if v))
            else:
                parts.append(f"{key}: {value}")
        return "\n".join(parts) or "无"
    if not isinstance(expression, list):
        return str(expression)
    parts = []
    for item in expression:
        if isinstance(item, dict):
            parts.append(", ".join(f"{k}: {v}" for k, v in item.items() if v))
        else:
            parts.append(str(item))
    return "\n".join(p for p in parts if p) or "无"


def _format_links(links: list) -> str:
    if not links:
        return "无"
    parts = []
    for link in links:
        if isinstance(link, dict):
            parts.append(", ".join(f"{k}: {v}" for k, v in link.items() if v))
        else:
            parts.append(str(link))
    return "\n".join(p for p in parts if p) or "无"


@router.post("/api/projects/{project_id}/generate/storyboard/{chapter_num}")
async def generate_storyboard(project_id: str, chapter_num: int):
    """将章节正文转化为分镜头脚本，自动创建 STORYBOARD 块。
    优化策略：
    1. 优先使用 strict tool calling（DeepSeek/OpenAI/中转站支持），格式合规性由服务端强制校验
    2. 按场景边界分段生成（避免长章节注意力衰减）
    3. 反重复约束（避免机位/运镜单一）
    4. 不支持 tool calling 的 provider 自动 fallback 到纯文本 JSON
    """
    conn = get_connection()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        conn.close()
        raise HTTPException(404, "项目不存在")

    chapter = conn.execute(
        "SELECT * FROM chapters WHERE project_id = ? AND chapter_num = ?",
        (project_id, chapter_num)
    ).fetchone()
    if not chapter or not chapter["content"]:
        conn.close()
        raise HTTPException(400, f"第{chapter_num}章没有正文，请先生成章节内容")

    chapter_title = chapter["title"] or f"第{chapter_num}章"
    chapter_content = chapter["content"]

    style_sig = {}
    if project["style_sig"]:
        try:
            style_sig = json.loads(project["style_sig"])
        except (json.JSONDecodeError, TypeError):
            pass

    conn.close()

    llm = create_llm()

    # 按场景边界切分章节正文
    scene_segments = _split_chapter_into_scenes(chapter_content, max_chars=1500)
    print(f"[STORYBOARD] 章节{chapter_num} 切分为 {len(scene_segments)} 个场景段落")

    # strict tool calling schema
    storyboard_tool = {
        "type": "function",
        "function": {
            "name": "submit_storyboard_shots",
            "strict": True,
            "description": "提交一段叙事文本对应的分镜头列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "shots": {
                        "type": "array",
                        "description": "镜头列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "shot_size": {
                                    "type": "string",
                                    "enum": ["远景", "全景", "中景", "近景", "特写", "大特写"]
                                },
                                "camera_angle": {
                                    "type": "string",
                                    "enum": ["平视", "仰视", "俯视", "鸟瞰", "倾斜", "主观视角", "过肩"]
                                },
                                "camera_movement": {
                                    "type": "string",
                                    "enum": ["固定", "推", "拉", "摇", "移", "跟", "升降", "环绕", "手持晃动"]
                                },
                                "description": {
                                    "type": "string",
                                    "description": "画面描述：观众看到什么，结合机位和运镜描述构图效果"
                                },
                                "dialogue": {
                                    "type": "string",
                                    "description": "对白，含角色名；无对白则填空字符串"
                                },
                                "audio": {
                                    "type": "string",
                                    "description": "声音设计：环境音/音效/现场声"
                                },
                                "music_note": {
                                    "type": "string",
                                    "description": "该镜头的配乐情绪线索，如'低沉大提琴铺垫紧张感'"
                                },
                                "duration_seconds": {
                                    "type": "integer",
                                    "description": "预估时长（秒），3-30之间"
                                },
                                "transition": {
                                    "type": "string",
                                    "enum": ["切", "淡入", "淡出", "叠化", "划变", "闪白", "闪黑"]
                                },
                                "narrative_purpose": {
                                    "type": "string",
                                    "description": "该镜头的叙事目的，如'建立环境'、'强调情绪'、'揭示信息'"
                                }
                            },
                            "required": ["shot_size", "camera_angle", "camera_movement", "description",
                                         "dialogue", "audio", "music_note", "duration_seconds",
                                         "transition", "narrative_purpose"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["shots"],
                "additionalProperties": False
            }
        }
    }

    system_prompt = """你是一位资深影视分镜头脚本编剧，曾参与多部院线电影的分镜设计。你的任务是将小说正文转化为专业的、可直接指导实拍的分镜头脚本。

【核心要求】
1. 每个场景切换必须拆分为新镜头；同一场景内的情绪/动作变化也要拆分
2. 景别要有节奏变化：建立环境用远景/全景，强调情绪用特写/大特写，对话用中景/近景
3. 机位角度有叙事含义：平视=客观，仰视=崇高/威慑，俯视=渺小/压迫，主观视角=代入角色
4. 运镜方式要具体：固定=稳定观察，推=聚焦/紧张，拉=揭示/疏离，摇=扫视环境，移=横向跟随，跟拍=角色行动
5. 画面描述要可视化、具体，结合机位和运镜描述构图效果（如"俯拍全景：李明在人群中显得渺小"）
6. 对白要标注角色名，无对白填空字符串
7. 每个镜头的music_note要单独写出该镜头的情绪配乐线索（不是整体音乐建议）
8. duration_seconds 在 3-30 之间，根据镜头复杂度合理估计

【反重复约束（重要）】
- 相邻两个镜头的 camera_movement 不能相同，除非是为了强调静止或对峙感
- 相邻两个镜头的 shot_size 不能相同，除非是为了强调对峙或重复
- 整个段落内 camera_angle 至少出现 2 种不同取值
- 不要让所有镜头都用"固定"+"平视"，这是偷懒

【输出方式】
通过调用 submit_storyboard_shots 工具提交分镜头列表，不要输出任何文本。"""

    style_info = ""
    if style_sig:
        parts = []
        if style_sig.get("prose_style"):
            parts.append(f"文风: {style_sig['prose_style']}")
        if style_sig.get("narrative_pov"):
            parts.append(f"叙事视角: {style_sig['narrative_pov']}")
        if style_sig.get("tone"):
            parts.append(f"基调: {','.join(style_sig['tone'])}")
        if parts:
            style_info = f"\n\n作品风格信息: {'; '.join(parts)}"

    # 分段生成镜头
    all_shots = []
    prev_shot_size = None
    prev_camera_movement = None

    for idx, segment in enumerate(scene_segments):
        segment_prompt = f"请将以下小说片段（第{idx + 1}/{len(scene_segments)}段）转化为分镜头脚本：\n\n## {chapter_title}（片段{idx + 1}）\n\n{segment}{style_info}"
        if prev_shot_size or prev_camera_movement:
            segment_prompt += f"\n\n【衔接约束】上一段最后一个镜头：景别={prev_shot_size or '未知'}，运镜={prev_camera_movement or '未知'}。本段第一个镜头的景别和运镜要与上一段不同。"

        # 优先尝试 strict tool calling
        tool_result = await llm.chat_with_tools(
            system_prompt, segment_prompt,
            tools=[storyboard_tool],
            temperature=0.8  # 格式由 schema 兜底，temperature 可以调高换取内容多样性
        )

        if tool_result and "shots" in tool_result and len(tool_result["shots"]) > 0:
            shots = tool_result["shots"]
            print(f"[STORYBOARD] 段落{idx + 1} tool calling 成功: {len(shots)} 个镜头")
        else:
            # fallback 到纯文本 JSON
            print(f"[STORYBOARD] 段落{idx + 1} tool calling 失败，fallback 到纯文本")
            shots = await _fallback_text_chat(llm, system_prompt, segment_prompt)

        # 给每个镜头补编号
        for shot_idx, shot in enumerate(shots):
            shot["shot_number"] = len(all_shots) + shot_idx + 1

        all_shots.extend(shots)
        if shots:
            last = shots[-1]
            prev_shot_size = last.get("shot_size")
            prev_camera_movement = last.get("camera_movement")

    if not all_shots:
        raise HTTPException(500, "分镜头生成失败：所有段落均未生成有效镜头，请检查 LLM 配置")

    # 计算总时长
    total_seconds = sum(s.get("duration_seconds", 0) for s in all_shots)
    if total_seconds >= 60:
        estimated_duration = f"{total_seconds // 60}分{total_seconds % 60}秒"
    else:
        estimated_duration = f"{total_seconds}秒"

    storyboard_data = {
        "chapter_number": chapter_num,
        "title": chapter_title,
        "shots": all_shots,
        "total_shots": len(all_shots),
        "estimated_duration": estimated_duration,
        "visual_style": _infer_visual_style(style_sig),
        "music_suggestion": _infer_music_suggestion(style_sig),
    }

    print(f"[STORYBOARD] 总计生成 {len(all_shots)} 个镜头，预估时长 {estimated_duration}")

    conn = get_connection()
    block_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO blocks (id, project_id, type, canvas_x, canvas_y, canvas_w, collapsed,
           color, timeline_id, chapter_pos, tags, notes, content, is_draft, on_canvas)
           VALUES (?, ?, 'STORYBOARD', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (block_id, project_id,
         100 + (chapter_num % 5) * 320, 200 + (chapter_num // 5) * 400,
         320, 0, '#FF6347', None, str(chapter_num),
         '[]', '',
         json.dumps(storyboard_data, ensure_ascii=False),
         0, 0)
    )
    conn.commit()
    conn.close()

    return {
        "block_id": block_id,
        "chapter_number": chapter_num,
        "title": storyboard_data["title"],
        "total_shots": storyboard_data["total_shots"],
        "estimated_duration": storyboard_data["estimated_duration"],
        "visual_style": storyboard_data["visual_style"],
        "music_suggestion": storyboard_data["music_suggestion"],
    }


def _split_chapter_into_scenes(content: str, max_chars: int = 1500) -> list:
    """按场景边界切分章节正文。
    优先按空行/换行符切分，保证每个段落是完整叙事单元。
    """
    if not content:
        return []

    # 按双换行（段落）切分
    paragraphs = re.split(r'\n\s*\n', content.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return [content]

    segments = []
    current_segment = ""
    for para in paragraphs:
        # 如果加上这段会超过 max_chars，且当前段已有内容，则切分
        if current_segment and len(current_segment) + len(para) + 2 > max_chars:
            segments.append(current_segment)
            current_segment = para
        else:
            if current_segment:
                current_segment += "\n\n" + para
            else:
                current_segment = para

    if current_segment:
        segments.append(current_segment)

    # 如果某个段落本身超长（>max_chars*1.5），按句号再切
    final_segments = []
    for seg in segments:
        if len(seg) > max_chars * 1.5:
            # 按句号切分
            sentences = re.split(r'(?<=[。！？!?])', seg)
            sub_seg = ""
            for s in sentences:
                if sub_seg and len(sub_seg) + len(s) > max_chars:
                    final_segments.append(sub_seg)
                    sub_seg = s
                else:
                    sub_seg += s
            if sub_seg:
                final_segments.append(sub_seg)
        else:
            final_segments.append(seg)

    return final_segments


async def _fallback_text_chat(llm, system_prompt: str, user_prompt: str) -> list:
    """纯文本 JSON fallback：当 provider 不支持 tool calling 时使用"""
    fallback_prompt = system_prompt + "\n\n【输出格式】请直接输出JSON对象，不要加markdown标记，格式为：\n{\"shots\": [{\"shot_size\": \"...\", \"camera_angle\": \"...\", \"camera_movement\": \"...\", \"description\": \"...\", \"dialogue\": \"...\", \"audio\": \"...\", \"music_note\": \"...\", \"duration_seconds\": 5, \"transition\": \"...\", \"narrative_purpose\": \"...\"}]}"

    result = await llm.chat(fallback_prompt, user_prompt, temperature=0.3)
    result = result.strip()
    if result.startswith("```json"):
        result = result[7:]
    elif result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]
    result = result.strip()

    try:
        data = json.loads(result)
        return data.get("shots", [])
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', result)
        if match:
            try:
                data = json.loads(match.group())
                return data.get("shots", [])
            except json.JSONDecodeError:
                return []
        return []


def _infer_visual_style(style_sig: dict) -> str:
    """根据风格签名推断视觉风格"""
    tone = style_sig.get("tone", []) if style_sig else []
    if isinstance(tone, str):
        tone = [tone]
    if not tone:
        return "根据章节内容自行确定"
    cold_keywords = ["冷峻", "压抑", "黑暗", "悬疑", "惊悚", "科幻"]
    warm_keywords = ["温馨", "治愈", "温暖", "怀旧", "日常"]
    if any(k in str(tone) for k in cold_keywords):
        return "冷色调、高对比、低饱和度，强调氛围感"
    if any(k in str(tone) for k in warm_keywords):
        return "暖黄光、柔焦、胶片颗粒感，强调温度"
    return "根据章节内容自行确定"


def _infer_music_suggestion(style_sig: dict) -> str:
    """根据风格签名推断整体配乐建议"""
    tone = style_sig.get("tone", []) if style_sig else []
    if isinstance(tone, str):
        tone = [tone]
    if not tone:
        return "根据章节情绪曲线设计配乐，注意情绪转折点的音乐变化"
    return f"配合基调({','.join(tone) if isinstance(tone, list) else tone})设计配乐情绪线，注意情绪转折点的音乐变化"


def _join_items(values) -> str:
    """拼接列表字段，元素是 dict 时取可读文本"""
    parts = []
    for v in values or []:
        if isinstance(v, dict):
            parts.append(str(v.get("info") or v.get("content") or v.get("belief") or v))
        elif v not in (None, ""):
            parts.append(str(v))
    return "；".join(parts)


def _format_characters(characters: list) -> str:
    if not characters:
        return "无"
    parts = []
    for c in characters:
        line = f"- {c.get('name', '未知')}: 想要 {c.get('want') or '?'}，需要 {c.get('need') or '?'}"
        if c.get("fatal_flaw"):
            line += f"，致命缺陷 {c['fatal_flaw']}"
        if c.get("role_archetype"):
            line += f"，定位 {c['role_archetype']}"
        surface = c.get("surface_personality")
        if surface:
            line += f"，表层性格 {'、'.join(map(str, surface)) if isinstance(surface, (list, tuple)) else surface}"
        lock = c.get("behavior_lock")
        if lock:
            line += f"，行为锁 {'、'.join(map(str, lock)) if isinstance(lock, (list, tuple)) else lock}"
        if c.get("appearance"):
            line += f"\n  外貌: {c['appearance']}"
        if c.get("voice_style"):
            line += f"\n  说话风格: {c['voice_style']}"
        boundary = c.get("knowledge_boundary") or {}
        knows = boundary.get("knows") or []
        if knows:
            line += f"\n  已知信息: {_join_items(knows)}"
        wrong = boundary.get("wrongly_believes") or []
        if wrong:
            line += f"\n  误信信息: {_join_items(wrong)}"
        parts.append(line)
    return "\n".join(parts)


def _format_scene_blocks(scenes: list) -> str:
    if not scenes:
        return "无"
    parts = []
    for s in scenes:
        parts.append(
            f"- {s.get('title', '未命名')}: {s.get('goal') or s.get('scene_goal') or '?'}"
            + (f"（场景类型: {s['scene_type']}）" if s.get("scene_type") else "")
            + (f"\n  出场角色: {s['characters_present']}" if s.get("characters_present") else "")
            + (f"\n  发生事件: {s['what_happens']}" if s.get("what_happens") else "")
        )
    return "\n".join(parts)


def _format_story_outline(structure: dict) -> str:
    """格式化故事大纲、主题与简介"""
    if not structure:
        return "无"
    parts = []
    synopsis = structure.get("synopsis") or {}
    if any(synopsis.values()):
        parts.append(
            f"故事简介: {synopsis.get('logline') or ''} {synopsis.get('synopsis') or ''}".strip()
            + (f"\n类型: {synopsis['genre']}" if synopsis.get("genre") else "")
            + (f"\n设定: {synopsis['setting']}" if synopsis.get("setting") else "")
            + (f"\n主角: {synopsis['protagonists']}" if synopsis.get("protagonists") else "")
            + (f"\n对手: {synopsis['antagonists']}" if synopsis.get("antagonists") else "")
            + (f"\n情感走向: {synopsis['emotional_roadmap']}" if synopsis.get("emotional_roadmap") else "")
        )
    outline = structure.get("story_outline") or {}
    if any(outline.values()):
        acts = [f"第一幕: {outline.get('act1')}", f"第二幕: {outline.get('act2')}", f"第三幕: {outline.get('act3')}"]
        parts.append("\n".join(a for a in acts if a.split(": ", 1)[1]))
        for key, label in (
            ("key_turning_points", "关键转折"),
            ("central_conflict", "核心冲突"),
            ("climax", "高潮设计"),
            ("ending", "结局类型"),
        ):
            if outline.get(key):
                parts.append(f"{label}: {outline[key]}")
    theme = structure.get("theme") or {}
    if any(theme.values()):
        parts.append(
            f"主题: {theme.get('theme', '')}（探讨方式: {theme.get('approach', '')}；反命题: {theme.get('counter', '')}）"
        )
    return "\n".join(p for p in parts if p) or "无"


def _format_chapter_outline(outline: dict) -> str:
    if not outline:
        return "无"
    parts = []
    if outline.get("title"):
        parts.append(f"标题: {outline['title']}")
    for key, label in (
        ("summary", "概要"),
        ("narrative_goal", "叙事目标"),
        ("dramatic_function", "戏剧功能"),
        ("emotional_arc", "情感曲线"),
        ("pov_character", "视角角色"),
        ("target_words", "目标字数"),
    ):
        if outline.get(key):
            parts.append(f"{label}: {outline[key]}")
    for i, beat in enumerate(outline.get("beats") or [], 1):
        parts.append(f"节拍{i}: {beat}")
    return "\n".join(parts)


def _format_story_card(framework: dict) -> str:
    if not framework:
        return "无"
    parts = []
    if framework.get("card_name"):
        parts.append(f"框架: {framework['card_name']}")
    if framework.get("genre"):
        parts.append(f"类型: {framework['genre']}")
    if framework.get("writing_modifier"):
        parts.append(f"写作要求: {framework['writing_modifier']}")
    if framework.get("reference_works"):
        parts.append(f"参考作品: {framework['reference_works']}")
    return "\n".join(parts) or "无"


def _format_act(value) -> str:
    """把 1 / "1" 形式的幕号转成「第1幕」，其他文本原样返回"""
    text = str(value).strip()
    return f"第{text}幕" if text.isdigit() else text


def _format_events(events: list) -> str:
    if not events:
        return "无"
    return "\n".join(
        f"- {e.get('title', '未命名事件')}"
        + (f"（类型: {_format_act(e['event_type'])}）" if e.get("event_type") else "")
        + (f"\n  经过: {e['what_happens']}" if e.get("what_happens") else "")
        + (f"\n  直接影响: {e['effects']}" if e.get("effects") else "")
        for e in events
    )


def _format_relationships(relations: list) -> str:
    if not relations:
        return "无"
    return "\n".join(
        f"- {r.get('party_a', '?')} ↔ {r.get('party_b', '?')}: {r.get('type', '')}"
        + (f"，关系张力 {r['intensity']}" if r.get("intensity") else "")
        + (f"，当前动态: {r['dynamic']}" if r.get("dynamic") else "")
        for r in relations
    )


def _format_conflicts(conflicts: list) -> str:
    if not conflicts:
        return "无"
    return "\n".join(
        f"- {c.get('title', '未命名冲突')}"
        + (f"（{c['conflict_type']}）" if c.get("conflict_type") else "")
        + (f"：{c['root_cause']}" if c.get("root_cause") else "")
        for c in conflicts
    )


def _format_turning_points(points: list) -> str:
    if not points:
        return "无"
    return "\n".join(
        f"- {p.get('title', '未命名转折')}"
        + (f"（类型: {p['turning_type']}）" if p.get("turning_type") else "")
        + (f"：{p['trigger']}" if p.get("trigger") else "")
        + (f" → 之后: {p['after_state']}" if p.get("after_state") else "")
        for p in points
    )


def extract_content(raw: str) -> str:
    """提取正文（去掉结算表）"""
    if "[结算表]" in raw:
        return raw.split("[结算表]")[0].strip()
    return raw.strip()


# ─── 图片生成 ──────────────────────────────────────────────────
import os
import base64
import httpx

IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "images")


@router.post("/api/projects/{project_id}/generate/image")
async def generate_image(project_id: str, req: dict):
    """根据文字描述生成图片，保存到本地并返回路径"""
    prompt = req.get("prompt", "")
    shot_index = req.get("shot_index")  # 镜头索引，可选
    block_id = req.get("block_id", "")

    if not prompt:
        raise HTTPException(400, "缺少图片描述(prompt)")

    # 读取图片生成配置
    image_provider = settings.image_provider
    image_cfg = settings.image_config
    api_key = image_cfg.get("api_key", "")
    base_url = image_cfg.get("base_url", "https://api.openai.com/v1")
    model = image_cfg.get("model", "dall-e-3")
    size = image_cfg.get("size", "1024x1024")
    quality = image_cfg.get("quality", "standard")

    if not api_key:
        raise HTTPException(400, "请先在设置中配置图片生成模型的API Key")

    # 构建增强 prompt
    enhanced_prompt = f"Cinematic storyboard frame: {prompt}. High quality, detailed, professional cinematography."

    # 调用 OpenAI 兼容的图片生成 API
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            # 尝试 /v1/images/generations 端点
            url = f"{base_url.rstrip('/')}/images/generations"
            payload = {
                "model": model,
                "prompt": enhanced_prompt,
                "n": 1,
                "size": size,
            }
            if quality and model.startswith("dall-e"):
                payload["quality"] = quality

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                error_detail = ""
                try:
                    error_detail = resp.json().get("error", {}).get("message", resp.text[:200])
                except Exception:
                    error_detail = resp.text[:200]
                raise HTTPException(resp.status_code, f"图片生成API错误: {error_detail}")

            data = resp.json()
            image_data = data.get("data", [])
            if not image_data:
                raise HTTPException(500, "图片生成API未返回图片数据")

            # 获取图片 URL 或 base64
            img_info = image_data[0]
            img_url = img_info.get("url", "")
            b64_json = img_info.get("b64_json", "")

            # 下载或解码图片
            os.makedirs(os.path.join(IMAGE_DIR, project_id), exist_ok=True)
            img_filename = f"{block_id}_{shot_index}_{uuid.uuid4().hex[:8]}.png" if shot_index is not None else f"{block_id}_{uuid.uuid4().hex[:8]}.png"
            img_path = os.path.join(IMAGE_DIR, project_id, img_filename)

            if b64_json:
                img_bytes = base64.b64decode(b64_json)
            elif img_url:
                img_resp = await client.get(img_url, timeout=60)
                img_bytes = img_resp.content
            else:
                raise HTTPException(500, "图片生成API返回格式不支持")

            with open(img_path, "wb") as f:
                f.write(img_bytes)

            # 返回图片相对路径
            relative_path = f"/images/{project_id}/{img_filename}"

            # 如果指定了 block_id 和 shot_index，更新块数据
            if block_id and shot_index is not None:
                conn = get_connection()
                block = conn.execute("SELECT content FROM blocks WHERE id = ?", (block_id,)).fetchone()
                if block:
                    content = json.loads(block["content"] or "{}")
                    shots = content.get("shots", [])
                    if 0 <= shot_index < len(shots):
                        shots[shot_index]["image"] = relative_path
                        content["shots"] = shots
                        conn.execute(
                            "UPDATE blocks SET content = ? WHERE id = ?",
                            (json.dumps(content, ensure_ascii=False), block_id)
                        )
                        conn.commit()
                conn.close()

            return {"image_path": relative_path, "prompt": enhanced_prompt}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"图片生成失败: {str(e)}")
