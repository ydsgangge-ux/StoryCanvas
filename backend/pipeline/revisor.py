"""修订者Agent - 根据审计结果修订正文"""

from backend.llm.base import create_llm

REVISOR_SYSTEM_PROMPT = """你是一位专业的写作修订者。根据审计员的反馈，修改正文中存在的问题。
保持原文的风格和整体结构，只修改有问题的部分。"""


async def run(chapter_content: str, audit_result: str, ctx: dict) -> str:
    """修订正文"""
    llm = create_llm()
    user_prompt = f"""
## 原文
{chapter_content}

## 审计反馈
{audit_result}

## 上下文
{ctx.get('style_signature', '')}

请根据审计反馈修订正文中的问题。输出修订后的完整版本。
"""
    return await llm.chat(REVISOR_SYSTEM_PROMPT, user_prompt, temperature=0.5)
