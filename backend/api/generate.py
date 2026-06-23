import json
import re
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
        elif r["type"] == "STORYBOARD":
            title = content.get("title", "分镜头脚本")
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
