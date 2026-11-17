"""修订者Agent - 根据审计结果修订正文"""

from backend.llm.base import create_llm
from backend.pipeline.architect import format_chapter_outline
from backend.pipeline.writer import format_characters, format_story_outline

REVISOR_SYSTEM_PROMPT = """你是一位专业的写作修订者。根据审计员的反馈，修改正文中存在的问题。
保持原文的风格和整体结构，只修改有问题的部分。
{output_language}"""


async def run(chapter_content: str, audit_result: str, ctx: dict, language: str = "zh") -> str:
    """修订正文"""
    llm = create_llm()

    # 语言指令：仅 en 时附加英文输出要求，中文保持不变
    _lang_hint = ""
    if language == "en":
        _lang_hint = "请始终使用英文输出全部内容。\nAlways respond entirely in English."
    system_prompt = REVISOR_SYSTEM_PROMPT.format(output_language=_lang_hint)

    user_prompt = f"""
## 原文
{chapter_content}

## 审计反馈
{audit_result}

## 上下文
### 世界背景
{ctx.get('world') or '无'}

### 故事大纲与主题
{format_story_outline(ctx.get('story_structure') or {})}

### 本章章节大纲
{format_chapter_outline(ctx.get('structure', {}).get('chapter_outline', {}))}

### 角色设定
{format_characters(ctx.get('characters', []))}

### 风格要求
{ctx.get('style_signature', '')}

请根据审计反馈修订正文中的问题。输出修订后的完整版本。
"""
    return await llm.chat(system_prompt, user_prompt, temperature=0.5)
