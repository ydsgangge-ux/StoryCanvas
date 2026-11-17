"""写手Agent - 根据写作蓝图生成章节正文"""

from typing import AsyncGenerator
from backend.llm.base import create_llm

WRITER_SYSTEM_PROMPT = """你是一位专业小说写手。根据写作蓝图生成高质量的章节正文。
要求：
1. 严格遵守角色信息边界
2. 保持风格一致性
3. 情绪曲线符合设计
4. 自然回收伏笔
5. 不要直接说教或暴露主题
6. 写好每章后的结算表，记录角色位置/情感/关系的变化
{output_language}"""


async def stream(blueprint: str, ctx: dict, language: str = "zh") -> AsyncGenerator[str, None]:
    """流式生成正文"""
    llm = create_llm()

    # 语言指令：仅 en 时附加英文输出要求，中文保持不变
    _lang_hint = ""
    if language == "en":
        _lang_hint = "请始终使用英文输出全部内容。\nAlways respond entirely in English."
    system_prompt = WRITER_SYSTEM_PROMPT.format(output_language=_lang_hint)

    # Build writing prompt from blueprint
    structure = ctx.get("story_structure") or {}
    user_prompt = f"""
## 写作蓝图
{blueprint}

## 世界背景
{ctx.get('world') or '无'}

## 故事大纲与主题
{format_story_outline(structure)}

## 本章关键事件
{format_events(structure.get('events', []))}

## 风格指令
{ctx.get('style_signature', '')}

## 本章角色信息
{format_characters(ctx.get('characters', []))}

## 人物关系
{format_relationships(ctx.get('relationships', []))}

## 待回收伏笔
{format_hooks(ctx.get('structure', {}).get('hooks_to_resolve', []))}

## 待埋设铺垫
{format_hooks(ctx.get('structure', {}).get('foreshadows_to_plant', []))}

## 已向读者释放的信息
{format_revealed_truths(ctx.get('revealed_truths', []))}

## 最近章节
{ctx.get('history') or '无'}

请生成章节正文，并在正文后附上写后结算表。

## 写后结算表格式
```
[结算表]
角色位置变化：
角色情感变化：
关系变化：
伏笔状态变化：
下一章提示：
```
"""
    async for chunk in llm.chat_stream(system_prompt, user_prompt, temperature=0.8):
        yield chunk


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
        line = f"- {c.get('name', '未知')}"
        if c.get("role_archetype"):
            line += f"（{c['role_archetype']}）"
        surface = c.get("surface_personality")
        if surface:
            line += f"\n  表层性格: {'、'.join(map(str, surface)) if isinstance(surface, (list, tuple)) else surface}"
        lock = c.get("behavior_lock")
        if lock:
            line += f"\n  行为锁: {'、'.join(map(str, lock)) if isinstance(lock, (list, tuple)) else lock}"
        if c.get("want"):
            line += f"：想要 {c['want']}"
        if c.get("appearance"):
            line += f"\n  外貌: {c['appearance']}"
        if c.get("voice_style"):
            line += f"\n  说话风格: {c['voice_style']}"
        if c.get("current_state"):
            line += f"\n  当前状态: {c['current_state']}"
        boundary = c.get("knowledge_boundary") or {}
        if boundary.get("knows"):
            line += f"\n  只能知道: {_join_items(boundary['knows'])}"
        if boundary.get("wrongly_believes"):
            line += f"\n  误信: {_join_items(boundary['wrongly_believes'])}"
        parts.append(line)
    return "\n".join(parts)


def format_story_outline(structure: dict) -> str:
    if not structure:
        return "无"
    parts = []
    synopsis = structure.get("synopsis") or {}
    if synopsis.get("logline"):
        parts.append(f"简介: {synopsis['logline']}")
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
        parts.append(f"主题: {theme['theme']}")
    return "\n".join(parts) or "无"


def format_events(events: list) -> str:
    if not events:
        return "无"
    return "\n".join(
        f"- {e.get('title', '')}：{e.get('what_happens', '')}"
        for e in events
        if e.get("title") or e.get("what_happens")
    ) or "无"


def format_relationships(relations: list) -> str:
    if not relations:
        return "无"
    return "\n".join(
        f"- {r.get('party_a', '?')} ↔ {r.get('party_b', '?')}: {r.get('type', '')}"
        + (f"，张力 {r['intensity']}" if r.get("intensity") else "")
        for r in relations
    )


def format_hooks(hooks: list) -> str:
    if not hooks:
        return "无"
    return "\n".join(
        f"- {h.get('title') or h.get('content_planted') or '未命名伏笔'}"
        + (f"（第{h['payoff_chapter']}章回收）" if h.get("payoff_chapter") else "")
        + (f"：{h.get('hint_content') or h.get('content_planted')}" if (h.get("hint_content") or h.get("content_planted")) else "")
        for h in hooks
    )


def format_revealed_truths(truths: list) -> str:
    """把全知层真相格式化为文本（元素可能是 dict，不能直接 join）"""
    if not truths:
        return "无"
    lines = []
    for item in truths:
        if isinstance(item, dict):
            fact = item.get("fact") or item.get("content") or "未命名真相"
            suffix = "（已向读者揭示，但故事内角色不知情）" if item.get("is_sensitive") else ""
            lines.append(f"- {fact}{suffix}")
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)
