"""建筑师Agent - 将细纲和上下文转化为写作蓝图"""

from backend.llm.base import create_llm

ARCHITECT_SYSTEM_PROMPT = """你是一位资深叙事建筑师。你的工作是将章节细纲和完整上下文转化为详细的写作蓝图。
写作蓝图包含每个场景的具体写作指令，包括：开场方式、核心冲突展开、角色行为逻辑、对话方向、情绪节奏。"""


async def run(ctx: dict, outline: str) -> str:
    """生成写作蓝图"""
    llm = create_llm()
    structure = ctx.get("story_structure") or {}
    user_prompt = f"""
## 章节 {ctx.get('chapter_num', 0)} 细纲
{outline or '（本章暂无细纲，请依据以下结构信息自行规划）'}

## 故事大纲与主题
{format_story_outline(structure)}

## 故事框架
{format_story_card(ctx.get('story_card_framework', {}))}

## 关键事件
{format_events(structure.get('events', []))}

## 世界背景
{ctx.get('world') or '无'}

## 本章活跃角色
{format_characters(ctx.get('characters', []))}

## 人物关系
{format_relationships(ctx.get('relationships', []))}

## 本章场景
{format_scenes(ctx.get('structure', {}).get('scenes', []))}

## 已有章节大纲
{format_chapter_outline(ctx.get('structure', {}).get('chapter_outline', {}))}

## 待回收悬念
{format_hooks(ctx.get('structure', {}).get('hooks_to_resolve', []))}

## 待埋设铺垫
{format_hooks(ctx.get('structure', {}).get('foreshadows_to_plant', []))}

## 待触发的转折点
{format_turning_points(ctx.get('structure', {}).get('turning_points', []))}

## 本章已向读者揭示的真相
{format_truths(ctx.get('revealed_truths', []))}

## 时间线
{format_timeline(ctx.get('timeline', []))}

## 情绪目标
{format_expression(ctx.get('expression', []))}

## 特殊关联线
{format_links(ctx.get('special_links', []))}

## 最近章节摘要
{ctx.get('history') or '无'}

## 风格签名
{ctx.get('style_signature') or '无标准风格'}

请生成详细的写作蓝图，包含每个场景的：
1. 开场策略
2. 核心冲突展开方式
3. 角色行为轨迹（必须遵守角色的信息边界）
4. 对话要点
5. 情绪曲线设计
6. 伏笔操作（埋设/回收）
"""
    return await llm.chat(ARCHITECT_SYSTEM_PROMPT, user_prompt, temperature=0.7)


def _join_items(values) -> str:
    """拼接列表字段，元素是 dict 时取可读文本"""
    parts = []
    for v in values or []:
        if isinstance(v, dict):
            parts.append(str(v.get("info") or v.get("content") or v.get("belief") or v))
        elif v not in (None, ""):
            parts.append(str(v))
    return "；".join(parts)


def format_characters(characters: list) -> str:
    if not characters:
        return "无"
    parts = []
    for c in characters:
        line = f"- {c.get('name', '未知')}: 想要 {c.get('want') or '?'}，需要 {c.get('need') or '?'}"
        if c.get("role_archetype"):
            line += f"，定位 {c['role_archetype']}"
        surface = c.get("surface_personality")
        if surface:
            line += f"，表层性格 {'、'.join(map(str, surface)) if isinstance(surface, (list, tuple)) else surface}"
        lock = c.get("behavior_lock")
        if lock:
            line += f"，行为锁 {'、'.join(map(str, lock)) if isinstance(lock, (list, tuple)) else lock}"
        if c.get("arc"):
            line += f"\n  人物弧光: {c['arc']}"
        if c.get("fatal_flaw"):
            line += f"，致命缺陷 {c['fatal_flaw']}"
        if c.get("appearance"):
            line += f"\n  外貌: {c['appearance']}"
        if c.get("voice_style"):
            line += f"\n  说话风格: {c['voice_style']}"
        if c.get("current_state"):
            line += f"\n  当前状态: {c['current_state']}"
        if c.get("growth"):
            line += f"\n  成长阶段: {c['growth']}"
        boundary = c.get("knowledge_boundary") or {}
        if boundary.get("knows"):
            line += f"\n  已知信息: {_join_items(boundary['knows'])}"
        if boundary.get("wrongly_believes"):
            line += f"\n  误信信息: {_join_items(boundary['wrongly_believes'])}"
        parts.append(line)
    return "\n".join(parts)


def format_scenes(scenes: list) -> str:
    if not scenes:
        return "无"
    parts = []
    for s in scenes:
        line = f"- {s.get('title', '未命名')}: {s.get('goal') or s.get('scene_goal') or '?'}"
        if s.get("scene_type"):
            line += f"（类型: {s['scene_type']}）"
        if s.get("characters_present"):
            line += f"\n  出场角色: {s['characters_present']}"
        if s.get("what_happens"):
            line += f"\n  发生事件: {s['what_happens']}"
        parts.append(line)
    return "\n".join(parts)


def format_story_outline(structure: dict) -> str:
    if not structure:
        return "无"
    parts = []
    synopsis = structure.get("synopsis") or {}
    if any(synopsis.values()):
        parts.append(
            f"故事简介: {synopsis.get('logline') or ''} {synopsis.get('synopsis') or ''}".strip()
            + (f"\n类型: {synopsis['genre']}" if synopsis.get("genre") else "")
            + (f"\n设定: {synopsis['setting']}" if synopsis.get("setting") else "")
            + (f"\n情感走向: {synopsis['emotional_roadmap']}" if synopsis.get("emotional_roadmap") else "")
        )
    outline = structure.get("story_outline") or {}
    acts = [outline.get("act1"), outline.get("act2"), outline.get("act3")]
    if any(acts):
        parts.append("\n".join(f"第{i + 1}幕: {a}" for i, a in enumerate(acts) if a))
    for key, label in (
        ("key_turning_points", "关键转折"),
        ("central_conflict", "核心冲突"),
        ("climax", "高潮设计"),
        ("ending", "结局类型"),
    ):
        if outline.get(key):
            parts.append(f"{label}: {outline[key]}")
    theme = structure.get("theme") or {}
    if theme.get("theme"):
        parts.append(
            f"主题: {theme['theme']}"
            + (f"（探讨方式: {theme['approach']}）" if theme.get("approach") else "")
            + (f"（反命题: {theme['counter']}）" if theme.get("counter") else "")
        )
    return "\n".join(parts) or "无"


def format_chapter_outline(outline: dict) -> str:
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
    ):
        if outline.get(key):
            parts.append(f"{label}: {outline[key]}")
    for i, beat in enumerate(outline.get("beats") or [], 1):
        parts.append(f"节拍{i}: {beat}")
    return "\n".join(parts)


def format_story_card(framework: dict) -> str:
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


def format_act(value) -> str:
    """把 1 / "1" 形式的幕号转成「第1幕」，其他文本原样返回"""
    text = str(value).strip()
    return f"第{text}幕" if text.isdigit() else text


def format_events(events: list) -> str:
    if not events:
        return "无"
    return "\n".join(
        f"- {e.get('title', '未命名事件')}"
        + (f"（类型: {format_act(e['event_type'])}）" if e.get("event_type") else "")
        + (f"：{e['what_happens']}" if e.get("what_happens") else "")
        + (f" → 影响: {e['effects']}" if e.get("effects") else "")
        for e in events
    )


def format_hooks(hooks: list) -> str:
    if not hooks:
        return "无"
    return "\n".join(
        f"- {h.get('title') or h.get('content_planted') or '未命名伏笔'}"
        + (f"（计划第{h['payoff_chapter']}章回收）" if h.get("payoff_chapter") else "")
        + (f"：{h.get('hint_content') or h.get('content_planted')}" if (h.get("hint_content") or h.get("content_planted")) else "")
        for h in hooks
    )


def format_turning_points(points: list) -> str:
    if not points:
        return "无"
    return "\n".join(
        f"- {p.get('title', '未命名转折')}"
        + (f"（类型: {p['turning_type']}）" if p.get("turning_type") else "")
        + (f"：{p['trigger']}" if p.get("trigger") else "")
        for p in points
    )


def format_relationships(relations: list) -> str:
    if not relations:
        return "无"
    return "\n".join(
        f"- {r.get('party_a', '?')} ↔ {r.get('party_b', '?')}: {r.get('type', '')}"
        + (f"，张力 {r['intensity']}" if r.get("intensity") else "")
        + (f"，动态: {r['dynamic']}" if r.get("dynamic") else "")
        for r in relations
    )


def format_truths(truths: list) -> str:
    if not truths:
        return "无"
    return "\n".join(
        f"- {t.get('fact', '')}"
        + ("（已向读者揭示，但故事内角色不知情）" if t.get("is_sensitive") else "")
        for t in truths
    )


def format_timeline(timelines: list) -> str:
    if not timelines:
        return "无"
    parts = []
    for t in timelines:
        line = f"- {t.get('name', '未命名时间线')}（{t.get('type', 'main')}）"
        scenes = t.get("this_chapter_scenes") or []
        if scenes:
            line += f"：本章场景 {'、'.join(scenes)}"
        parts.append(line)
    return "\n".join(parts)


def format_expression(expression) -> str:
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
    for e in expression:
        if isinstance(e, dict):
            parts.append(", ".join(f"{k}: {v}" for k, v in e.items() if v))
        else:
            parts.append(str(e))
    return "\n".join(parts) or "无"


def format_links(links: list) -> str:
    if not links:
        return "无"
    parts = []
    for link in links:
        if isinstance(link, dict):
            parts.append(", ".join(f"{k}: {v}" for k, v in link.items() if v))
        else:
            parts.append(str(link))
    return "\n".join(parts)
