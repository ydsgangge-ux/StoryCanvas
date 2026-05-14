"""建筑师Agent - 将细纲和上下文转化为写作蓝图"""

from backend.llm.base import create_llm

ARCHITECT_SYSTEM_PROMPT = """你是一位资深叙事建筑师。你的工作是将章节细纲和完整上下文转化为详细的写作蓝图。
写作蓝图包含每个场景的具体写作指令，包括：开场方式、核心冲突展开、角色行为逻辑、对话方向、情绪节奏。"""


async def run(ctx: dict, outline: str) -> str:
    """生成写作蓝图"""
    llm = create_llm()
    user_prompt = f"""
## 章节 {ctx.get('chapter_num', 0)} 细纲
{outline}

## 世界背景
{ctx.get('world', '无')}

## 本章活跃角色
{format_characters(ctx.get('characters', []))}

## 本章场景
{format_scenes(ctx.get('structure', {}).get('scenes', []))}

## 情绪目标
{ctx.get('expression', '无')}

## 待回收悬念
{ctx.get('structure', {}).get('hooks_to_resolve', [])}

## 风格签名
{ctx.get('style_signature', '无标准风格')}

请生成详细的写作蓝图，包含每个场景的：
1. 开场策略
2. 核心冲突展开方式
3. 角色行为轨迹
4. 对话要点
5. 情绪曲线设计
6. 伏笔操作（埋设/回收）
"""
    return await llm.chat(ARCHITECT_SYSTEM_PROMPT, user_prompt, temperature=0.7)


def format_characters(characters: list) -> str:
    parts = []
    for c in characters:
        parts.append(f"- {c.get('name', '未知')}: 想要 {c.get('want', '?')}，需要 {c.get('need', '?')}")
    return "\n".join(parts)


def format_scenes(scenes: list) -> str:
    parts = []
    for s in scenes:
        parts.append(f"- {s.get('title', '未命名')}: {s.get('scene_goal', '?')}")
    return "\n".join(parts)
