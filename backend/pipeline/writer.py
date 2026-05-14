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
6. 写好每章后的结算表，记录角色位置/情感/关系的变化"""


async def stream(blueprint: str, ctx: dict) -> AsyncGenerator[str, None]:
    """流式生成正文"""
    llm = create_llm()

    # Build writing prompt from blueprint
    user_prompt = f"""
## 写作蓝图
{blueprint}

## 风格指令
{ctx.get('style_signature', '')}

## 本章角色信息
{format_characters(ctx.get('characters', []))}

## 已向读者释放的信息
{chr(10).join(ctx.get('revealed_truths', []))}

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
    async for chunk in llm.chat_stream(WRITER_SYSTEM_PROMPT, user_prompt, temperature=0.8):
        yield chunk


def format_characters(characters: list) -> str:
    if not characters:
        return "无"
    parts = []
    for c in characters:
        parts.append(f"- {c.get('name', '未知')}")
    return "\n".join(parts)
