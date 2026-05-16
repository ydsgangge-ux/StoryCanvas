"""审计员Agent - 12维度叙事质量审计，输出结构化JSON"""

from backend.llm.base import create_llm

AUDIT_DIMENSIONS = [
    "OOC（角色行为是否符合性格锁定，want/need/fatal_flaw 不能违背）",
    "信息边界（角色是否知道了他不应知道的信息，信息来源是否合理）",
    "因果一致性（每个事件的发生是否有前因，不靠巧合推进）",
    "情感弧线（本章情感弧是否符合目标，情绪变化是否有足够铺垫）",
    "大纲偏离（本章是否完成了核心冲突/场景目标，使用场景块目标作为参照）",
    "节奏（快场景与慢场景的分配是否合理，是否有张弛）",
    "伏笔管理（新埋伏笔是否有铺垫，应回收的伏笔是否在正文中落地）",
    "去AI味（AI标记词、套话、元叙事、报告式语言、集体反应）",
    "连续性（角色位置/物品/时间线/称谓/数值是否前后一致）",
    "冲突质量（每个场景的冲突是否源于角色目标与障碍的张力，不靠巧合）",
    "结尾钩子（章末钩子是否有效驱动读者继续读）",
    "风格一致（是否符合风格签名和故事卡框架的要求）",
]


async def run(chapter_content: str, ctx: dict) -> dict:
    """执行12维度审计，输出结构化JSON"""
    llm = create_llm()

    # 智能截断：保留开头+结尾
    content_for_audit = chapter_content
    if len(chapter_content) > 5000:
        content_for_audit = chapter_content[:2500] + "\n\n...[中间省略]...\n\n" + chapter_content[-1500:]

    # 构建蓝图参照（从上下文提取）
    blueprint_summary = _build_blueprint_summary(ctx)

    # 构建结算表参照
    settlement_summary = _build_settlement_summary(ctx)

    # 构建真相文件参照
    truth_context = _build_truth_context(ctx)

    dimensions_str = "\n".join(f"{i+1}. {d}" for i, d in enumerate(AUDIT_DIMENSIONS))

    prompt = f"""## 叙事审计：第 {ctx.get('chapter_num', '?')} 章

### 审计维度（逐一检查，不可遗漏）
{dimensions_str}

### 章节正文
{content_for_audit}

### 写前参照（场景指令/角色设定）
{blueprint_summary}

### 结算表参照（需与正文交叉验证）
{settlement_summary}

### 真相文件参照（连续性）
{truth_context[:2000]}

## 评判标准
- critical：叙事逻辑断裂、明显 OOC、重大连续性错误、伏笔遗漏到期未收
- warning：轻微节奏问题、AI痕迹、伏笔处理不当、情感弧线偏差
- info：可选优化建议

## 输出格式（严格 JSON）
{{
  "chapter_number": {ctx.get('chapter_num', 0)},
  "passed": true,
  "issues": [
    {{
      "dimension": "维度名称",
      "severity": "critical",
      "description": "具体问题描述，指出原文哪里出了问题",
      "location": "原文关键句引用（30字以内）",
      "suggestion": "具体修复建议"
    }}
  ],
  "foreshadows_extracted": [
    {{
      "title": "伏笔/悬念标题（简短概括）",
      "type": "foreshadow 或 hook",
      "description": "伏笔的具体内容描述",
      "location": "原文关键句引用",
      "urgency": "high/medium/low",
      "suggested_payoff_chapter": "建议回收章节号（数字或空字符串）"
    }}
  ],
  "overall_note": "整体评价（1-2句话）"
}}

只输出 JSON，不要任何说明。"""

    system_prompt = (
        "你是严格的叙事审计员，专注叙事质量，"
        "对 critical 问题零容忍但不制造假阳性。"
        "只输出合法 JSON，不输出任何说明文字。"
    )

    result = await llm.chat(system_prompt, prompt, temperature=0.0)

    # 解析JSON
    import json
    result = result.strip()
    if result.startswith("```"):
        result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    if result.startswith("```json"):
        result = result[7:].rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(result)
        issues = parsed.get("issues", [])
        has_critical = any(i.get("severity") == "critical" for i in issues)
        foreshadows_extracted = parsed.get("foreshadows_extracted", [])
        return {
            "result": result,
            "parsed": parsed,
            "passed": not has_critical,
            "has_critical_issues": has_critical,
            "issues": issues,
            "total_issues": len(issues),
            "critical_count": sum(1 for i in issues if i.get("severity") == "critical"),
            "foreshadows_extracted": foreshadows_extracted,
        }
    except json.JSONDecodeError:
        has_critical = "critical" in result.lower() and "不通过" in result
        return {
            "result": result,
            "parsed": None,
            "passed": not has_critical,
            "has_critical_issues": has_critical,
            "issues": [],
            "total_issues": 0,
            "critical_count": 0,
        }


def _build_blueprint_summary(ctx: dict) -> str:
    """从上下文中提取写前参照"""
    parts = []

    scenes = ctx.get("scene_instructions", [])
    if scenes:
        parts.append("### 本章场景指令")
        for s in scenes:
            parts.append(f"- {s.get('title', '')}: {s.get('goal', '')}")

    chars = ctx.get("active_characters", [])
    if chars:
        parts.append("### 角色设定")
        for c in chars:
            parts.append(
                f"- {c.get('name', '')}: 想要 {c.get('want', '')}, "
                f"需要 {c.get('need', '')}, 缺陷 {c.get('fatal_flaw', '')}"
            )

    hooks = ctx.get("pending_hooks", [])
    if hooks:
        parts.append("### 待回收伏笔")
        for h in hooks:
            parts.append(f"- {h.get('title', '')}（{h.get('urgency', '')}）")

    expression = ctx.get("expression_instructions", {})
    if expression.get("emotion_targets"):
        for et in expression["emotion_targets"]:
            parts.append(f"### 情绪目标: {et.get('primary_emotion', '')}")

    return "\n".join(parts) if parts else "无蓝图参照"


def _build_settlement_summary(ctx: dict) -> str:
    """从上下文中提取结算表参照（实际由writeback提供）"""
    # 目前简化：只输出概要
    chars = ctx.get("active_characters", [])
    char_states = []
    for c in chars:
        cs = c.get("current_state", {})
        if cs:
            char_states.append(f"- {c.get('name', '')}: {cs.get('physical', '')} | {cs.get('emotional', '')}")
    return "\n".join(char_states) if char_states else "无结算表参照"


def _build_truth_context(ctx: dict) -> str:
    """构建真相文件参照"""
    parts = []
    story_card = ctx.get("story_card_framework", {})
    if story_card:
        parts.append(f"故事框架: {story_card.get('card_name', '')} - {story_card.get('writing_modifier', '')[:200]}")

    world = ctx.get("world_background", "")
    if world:
        parts.append(f"世界背景: {world[:500]}")

    style = ctx.get("style_signature", "")
    if style:
        parts.append(f"风格要求: {style[:300]}")

    return "\n".join(parts) if parts else "无真相文件参照"
