import json
import uuid
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from backend.core.database import get_connection
from backend.core.models import GenerateOutlineRequest, GenerateContentRequest, GenerateBlockContentRequest, RewriteContentRequest
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

## 本章时间线
{timeline_info}

## 本章登场角色
{characters_with_boundaries}

## 本章场景规划
{scene_blocks}

## 结构要求
- 待触发的转折点：{turning_points}
- 待回收的伏笔：{hooks_to_resolve}
- 待埋设的铺垫：{foreshadows_to_plant}

## 情绪目标
{emotion_target}

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
        world_context=ctx.get("world", "无"),
        timeline_info=_format_timelines(ctx.get("timeline", [])),
        characters_with_boundaries=_format_characters(ctx.get("characters", [])),
        scene_blocks=_format_scene_blocks(ctx.get("structure", {}).get("scenes", [])),
        turning_points="无",
        hooks_to_resolve=", ".join(ctx.get("structure", {}).get("hooks_to_resolve", [])) or "无",
        foreshadows_to_plant="无",
        emotion_target=ctx.get("expression", "无"),
        style_signature=ctx.get("style_signature", "无标准风格"),
        recent_summaries=ctx.get("history", "无"),
    )

    if req.additional_instructions:
        prompt += f"\n\n## 用户额外指令\n{req.additional_instructions}"

    async def event_stream():
        yield {"data": json.dumps({"event": "stage", "data": {"stage": "outlining", "msg": "正在生成章节细纲..."}})}
        llm = create_llm()
        outline_text = ""
        async for chunk in llm.chat_stream(
            "你是一个专业的叙事策划师，擅长生成详细的章节细纲。",
            prompt,
            temperature=0.7
        ):
            outline_text += chunk
            yield {"data": json.dumps({"event": "chunk", "data": {"text": chunk}})}

        yield {"data": json.dumps({"event": "done", "data": {"outline": outline_text, "chapter_num": req.chapter_num}})}

    return EventSourceResponse(event_stream())


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
            content = json.loads(detail_block["content"] or "{}")
            scenes = []
            for i in range(1, 4):
                heading = content.get(f"scene{i}_heading", "")
                body = content.get(f"scene{i}_content", "")
                if heading or body:
                    scenes.append(f"【场景{i}】{heading}\n{body}")
            outline = "\n\n".join(scenes) if scenes else None

    # 如果没有 CHAPTER_DETAIL 块内容，回退到 chapters.outline
    if not outline:
        chapter = conn.execute(
            "SELECT * FROM chapters WHERE project_id = ? AND chapter_num = ?",
            (project_id, req.chapter_num)
        ).fetchone()
        outline = chapter["outline"] if chapter and chapter["outline"] else "(无细纲，直接生成)"

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
            async for chunk in writer_stream(blueprint, ctx):
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
            char_boundaries[c.get("id", "")] = {"doesnt_know": []}
        violations = validator.validate(content_only, char_boundaries)
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
        if not audit.get("passed", True) and audit.get("has_critical_issues", False):
            yield {"data": json.dumps({"event": "stage", "data": {"stage": "revising", "msg": "修订者修复中..."}})}
            for attempt in range(settings.max_retries):
                try:
                    revised = await revisor_run(final_content, audit.get("result", ""), ctx)
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

        conn2.commit()

        # 触发经验标记：has_generated_chapter
        from backend.core.experience import auto_check
        try:
            auto_check(project_id)
        except Exception:
            pass

        # ⑤ 回写器
        writeback = WritebackService()
        wb_result = writeback.writeback(project_id, req.chapter_num, final_content)
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

    prompt_parts = [f"## 当前正文（第{req.chapter_num}章）\n{full_text}"] if not is_segment else []

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
    existing_content = json.loads(block["content"] or "{}")

    # 查询连出/连入的块
    connected_blocks = _get_connected_blocks(conn, req.block_id, project_id)
    conn.close()

    # 构建连线上下文
    conn_context = ""
    if connected_blocks:
        conn_parts = []
        for cb in connected_blocks:
            conn_parts.append(
                f"[{cb['conn_type']}] ←→ {cb['type']}块「{cb['title']}」:\n{cb['content_summary']}"
            )
        conn_context = "## 连线关联的块\n" + "\n\n".join(conn_parts)

    # 构建各个字段的生成提示
    from backend.narrative.progress import COMPLETENESS_RULES
    rules = COMPLETENESS_RULES.get(block_type, {})

    # 确定要生成的字段（已填的跳过）
    fields_to_generate = {k: v for k, v in rules.items() if not existing_content.get(k)}

    llm = create_llm()
    system_prompt = f"""你是一位资深叙事设计师。根据已有信息和关联块，为{block_type}类型块生成内容。
直接输出JSON对象，不要解释，不要加markdown标记。JSON键名必须严格匹配指定字段。"""

    user_prompt_parts = [
        f"## 目标块类型: {block_type}",
        f"## 已有内容: {json.dumps(existing_content, ensure_ascii=False, indent=2)}" if existing_content else "",
        conn_context,
        f"## 需要填充的字段及其权重(越高越重要)",
        *[f"- {field_name} (权重{weight:.0%})" for field_name, weight in fields_to_generate.items()],
    ]
    if req.hint:
        user_prompt_parts.append(f"## 用户提示: {req.hint}")

    user_prompt_parts.append(f'\n请生成包含以下字段的JSON: {{{", ".join(f'"{k}": "生成的内容"'.format(k=k) for k in fields_to_generate.keys())}}}')
    user_prompt = "\n".join(p for p in user_prompt_parts if p)

    result = await llm.chat(system_prompt, user_prompt, temperature=0.7)

    # 解析JSON结果
    result = result.strip()
    if result.startswith("```"):
        result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    if result.startswith("```json"):
        result = result[7:].rsplit("```", 1)[0].strip()

    try:
        generated = json.loads(result)
    except json.JSONDecodeError:
        # 尝试提取JSON
        import re
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            generated = json.loads(match.group())
        else:
            generated = {list(fields_to_generate.keys())[0]: result[:200]}

    # 合并到已有内容
    merged = {**existing_content, **generated}

    return {
        "block_id": req.block_id,
        "block_type": block_type,
        "generated_fields": generated,
        "merged_content": merged,
        "connections_used": len(connected_blocks),
    }


def _get_connected_blocks(conn, block_id: str, project_id: str) -> list:
    """获取与指定块有连线关系的所有块及其连线类型"""
    rows = conn.execute(
        """SELECT c.conn_type, c.from_block, c.to_block, b.type, b.content, b.id as other_id
           FROM connections c
           JOIN blocks b ON (b.id = CASE WHEN c.from_block = ? THEN c.to_block ELSE c.from_block END)
           WHERE c.project_id = ? AND (c.from_block = ? OR c.to_block = ?)
           AND b.id != ?""",
        (block_id, project_id, block_id, block_id, block_id)
    ).fetchall()

    result = []
    for r in rows:
        content = json.loads(r["content"] or "{}")
        title = ""

        # 提取不同类型块的标题
        if r["type"] == "CHARACTER":
            title = content.get("name", "未命名角色")
        elif r["type"] == "SCENE":
            title = content.get("title", "未命名场景")
        elif r["type"] in ("EVENT", "HOOK", "CONFLICT", "TURNING_POINT", "FORESHADOW", "SURPRISE"):
            title = content.get("title", "")
        elif r["type"] == "WORLDVIEW":
            title = content.get("world_name", "")
        elif r["type"] == "FACTION":
            title = content.get("name", "")
        elif r["type"] == "GOAL":
            title = content.get("surface_goal", "")
        else:
            title = r["type"]

        # 提取关键内容摘要
        summary = json.dumps({k: v for k, v in content.items() if v}, ensure_ascii=False)[:200]

        result.append({
            "conn_type": r["conn_type"],
            "type": r["type"],
            "title": title,
            "content_summary": summary,
        })
    return result


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


def _format_characters(characters: list) -> str:
    if not characters:
        return "无"
    parts = []
    for c in characters:
        parts.append(f"- {c.get('name', '未知')}: 想要 {c.get('want', '?')}，需要 {c.get('need', '?')}")
    return "\n".join(parts)


def _format_scene_blocks(scenes: list) -> str:
    if not scenes:
        return "无"
    parts = []
    for s in scenes:
        parts.append(f"- {s.get('title', '未命名')}: {s.get('scene_goal', '?')}")
    return "\n".join(parts)


def extract_content(raw: str) -> str:
    """提取正文（去掉结算表）"""
    if "[结算表]" in raw:
        return raw.split("[结算表]")[0].strip()
    return raw.strip()
