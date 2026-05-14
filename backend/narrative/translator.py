"""块转译器 - 将块内容转化为 AI 可理解的提示词片段"""

POV_MAP = {
    "多视角轮换": "本章采用多视角叙事，每个视角切换时明确标注，每个视角保持信息隔离",
    "限制第三人称": "严格限制在单一角色视角，不写该角色感知不到的任何信息",
    "全知叙事": "上帝视角，可自由进入任何角色内心，但不滥用全知权力",
    "第一人称": "始终以\"我\"的视角叙述，只写主角感知和思考的内容",
    "无焦点群像": "没有固定主角，每个场景展示不同角色的截面",
}

DENSITY_MAP = {
    "厚重史诗": "语言厚重，细节丰富，注重历史感和仪式感，每个场景都有环境描写",
    "极简风格": "海明威式极简，冰山原则，大量留白，避免形容词堆砌",
    "标准叙事": "语言流畅自然，描写与叙述平衡",
    "意识流": "内心独白为主，时间和逻辑可以跳跃，感受优先于事件",
    "诗化散文": "语言富有诗意和韵律感，注重修辞和意象",
}

PROSE_STYLE_MAP = {
    "标准文笔": "文笔平实流畅，描写与叙述保持均衡，不刻意炫技也不过于简略",
    "华丽辞藻": "文笔华丽富丽，善用修辞和丰富的形容词，注重语言的装饰性和画面感",
    "朴实白描": "文笔朴实无华，以白描手法为主，用最简洁的语言传达最准确的信息，不添加多余修饰",
    "幽默诙谐": "文笔轻松幽默，善用反讽、夸张和俏皮话，对话活泼有趣，叙述带有机智感",
    "冷峻犀利": "文笔冷峻犀利，用词精准锋利，节奏紧凑，情感克制，不拖泥带水",
    "诗意浪漫": "文笔富有诗意，善用意象和隐喻，语言优美抒情，注重氛围营造和情感渲染",
    "简洁明快": "文笔简洁明快，句子短促有力，节奏快，信息密度高，不写长句和复杂结构",
}


def style_to_prompt(style_sig: dict) -> str:
    """将风格签名转化为AI写作指令"""
    if not style_sig:
        return ""
    parts = []
    pov = style_sig.get("narrative_pov", "")
    if pov in POV_MAP:
        parts.append(POV_MAP[pov])

    density = style_sig.get("language_density", "")
    if density in DENSITY_MAP:
        parts.append(DENSITY_MAP[density])

    prose = style_sig.get("prose_style", "")
    if prose in PROSE_STYLE_MAP:
        parts.append(PROSE_STYLE_MAP[prose])

    tone = style_sig.get("tone", [])
    if isinstance(tone, list):
        if "冷峻克制" in tone:
            parts.append("不煽情，不用感叹号，情感通过行为和细节体现，不直接描述")
        if "道德灰度" in tone:
            parts.append("避免非黑即白，每个角色的选择都有其内在逻辑，不设绝对善恶")
        if "热血燃向" in tone:
            parts.append("情绪饱满，节奏明快，战斗/对抗场面富有动感")

    ref_authors = style_sig.get("reference_authors", [])
    if ref_authors:
        parts.append(f"风格参考作者: {', '.join(ref_authors)}")

    avoid = style_sig.get("avoid_tropes", [])
    if avoid:
        parts.append(f"明确避免的套路: {', '.join(avoid)}")

    custom = style_sig.get("custom_instructions", "")
    if custom:
        parts.append(custom)

    return "\n".join(parts)


def block_to_context(block_dict: dict) -> str:
    """将单个块转换为上下文文本"""
    import json
    btype = block_dict["type"]
    content = block_dict.get("content", {})
    if isinstance(content, str):
        content = json.loads(content)

    if btype == "CHARACTER":
        return (
            f"角色: {content.get('name', '未命名')}\n"
            f"  外在目标: {content.get('want', '未设定')}\n"
            f"  内在渴望: {content.get('need', '未设定')}\n"
            f"  致命缺陷: {content.get('fatal_flaw', '未设定')}\n"
            f"  表面性格: {content.get('surface_personality', '未设定')}\n"
        )
    elif btype == "SCENE":
        return (
            f"场景: {content.get('title', '未命名场景')}\n"
            f"  目标: {content.get('scene_goal', '未设定')}\n"
            f"  情绪目标: {content.get('emotion_target', '未设定')}\n"
            f"  张力级别: {content.get('tension_level', 5)}/10\n"
        )
    elif btype == "WORLDVIEW":
        return (
            f"世界观: {content.get('world_name', '')}\n"
            f"  核心规则: {', '.join(content.get('fundamental_rules', []))}\n"
            f"  基调: {content.get('tone', '')}\n"
        )
    elif btype == "FACTION":
        return f"势力: {content.get('name', '')} - {content.get('ideology', '')}"
    elif btype == "HOOK":
        status = content.get("status", "open")
        return (
            f"悬念: {content.get('title', '')} ({'已解决' if status == 'resolved' else '进行中'})\n"
            f"  类型: {content.get('hook_type', '')}\n"
        )
    elif btype == "TURNING_POINT":
        return (
            f"转折点: {content.get('title', '')}\n"
            f"  类型: {content.get('turning_type', '')}\n"
            f"  转折前: {content.get('before_state', '')}\n"
            f"  转折后: {content.get('after_state', '')}\n"
        )
    elif btype == "TIMELINE":
        return (
            f"时间线: {content.get('timeline_name', '未命名')}\n"
            f"  类型: {content.get('timeline_type', 'main')}\n"
        )
    elif btype == "RELATIONSHIP":
        return f"关系: {content.get('relationship_type', '')} (强度: {content.get('intensity', 0)})"
    elif btype == "EVENT":
        return (
            f"事件: {content.get('title', '')}\n"
            f"  内容: {content.get('what_happens', '')}\n"
        )
    elif btype == "CONFLICT":
        return (
            f"冲突: {content.get('title', '')}\n"
            f"  类型: {content.get('conflict_type', '')}\n"
            f"  根源: {content.get('root_cause', '')}\n"
            f"  表面表现: {content.get('surface_manifestation', '')}\n"
        )
    elif btype == "GOAL":
        return (
            f"目标: {content.get('surface_goal', '')}\n"
            f"  深层目标: {content.get('deep_goal', '')}\n"
            f"  障碍: {content.get('obstacle', '')}\n"
            f"  代价: {content.get('stakes', '')}\n"
        )
    elif btype == "FORESHADOW":
        return (
            f"铺垫: {content.get('title', '')}\n"
            f"  暗示内容: {content.get('hint_content', '')}\n"
            f"  埋设章节: {content.get('plant_chapter', '')}\n"
            f"  回收章节: {content.get('payoff_chapter', '')}\n"
            f"  回收方式: {content.get('payoff_content', '')}\n"
        )
    elif btype == "SURPRISE":
        return (
            f"意外: {content.get('title', '')}\n"
            f"  类型: {content.get('surprise_type', '')}\n"
            f"  揭示: {content.get('revelation', '')}\n"
            f"  所需铺垫: {content.get('setup_required', '')}\n"
        )
    elif btype == "PERSONALITY":
        return (
            f"性格: 角色ID={content.get('character_id', '')}\n"
            f"  核心价值观: {content.get('core_values', '')}\n"
            f"  行为模式: {content.get('behavior_patterns', '')}\n"
            f"  Dramatica功能: {content.get('dramatica_function', '')}\n"
        )
    elif btype == "GROWTH":
        return (
            f"成长弧线: 角色ID={content.get('character_id', '')}\n"
            f"  弧线类型: {content.get('arc_type', '')}\n"
            f"  起点: {content.get('start_state', '')}\n"
            f"  终点: {content.get('end_state', '')}\n"
            f"  关键时刻: {content.get('keystone_moments', '')}\n"
        )
    elif btype == "BACKSTORY":
        return (
            f"过去: 角色ID={content.get('character_id', '')}\n"
            f"  起源: {content.get('origin', '')}\n"
            f"  成型事件: {content.get('formative_events', '')}\n"
            f"  秘密: {content.get('secrets', '')}\n"
        )
    elif btype == "CURRENT_STATE":
        return (
            f"当前状态: 角色ID={content.get('character_id', '')} 第{content.get('chapter', '?')}章\n"
            f"  生理: {content.get('physical_condition', '')}\n"
            f"  心理: {content.get('psychological_condition', '')}\n"
            f"  情绪: {content.get('emotional_state', '')}\n"
        )
    elif btype == "INFORMATION_BOUNDARY":
        return (
            f"信息边界: 角色ID={content.get('character_id', '')} 第{content.get('chapter', '?')}章\n"
            f"  已知信息: {content.get('confirmed_knowledge', '')}\n"
            f"  错误信念: {content.get('wrongly_believes', '')}\n"
            f"  戏剧反讽: {content.get('dramatic_irony', '')}\n"
        )
    elif btype == "RULE_CONSTRAINT":
        return (
            f"规则约束: {content.get('rule_name', '')}\n"
            f"  类型: {content.get('rule_type', '')}\n"
            f"  机制: {content.get('mechanism', '')}\n"
            f"  违反后果: {content.get('consequence_of_breaking', '')}\n"
        )
    elif btype == "WORLD_DEVELOPMENT":
        return (
            f"世界发展: {content.get('aspect', '')}\n"
            f"  当前状态: {content.get('current_state', '')}\n"
            f"  发展轨迹: {content.get('trajectory', '')}\n"
            f"  关键事件: {content.get('key_events', '')}\n"
        )
    elif btype == "TIMESTAMP":
        return (
            f"时间戳: {content.get('era_name', '')}\n"
            f"  时间范围: {content.get('time_range', '')}\n"
            f"  关键变化: {content.get('key_changes', '')}\n"
        )
    elif btype == "FACTION_RELATION":
        return (
            f"势力关系: {content.get('faction_a_id', '')} ↔ {content.get('faction_b_id', '')}\n"
            f"  关系类型: {content.get('relation_type', '')}\n"
            f"  当前紧张度: {content.get('current_tension', '')}\n"
        )
    elif btype == "ATMOSPHERE":
        return (
            f"意境: {content.get('name', '')}\n"
            f"  感官细节: {content.get('sensory_details', '')}\n"
            f"  情感基调: {content.get('emotional_tone', '')}\n"
        )
    elif btype == "EMOTION_TARGET":
        return (
            f"情绪目标: 第{content.get('chapter', '?')}章\n"
            f"  主要情绪: {content.get('primary_emotion', '')}\n"
            f"  强度: {content.get('intensity', '')}\n"
            f"  触发: {content.get('trigger', '')}\n"
        )
    elif btype == "RHYTHM":
        return (
            f"节奏: 第{content.get('chapter', '?')}章\n"
            f"  节奏类型: {content.get('rhythm_type', '')}\n"
            f"  节拍说明: {content.get('pacing_notes', '')}\n"
        )
    elif btype == "THEME_STATEMENT":
        return (
            f"主题: {content.get('theme', '')}\n"
            f"  探索方式: {content.get('exploration_approach', '')}\n"
            f"  反方论点: {content.get('counter_argument', '')}\n"
        )
    elif btype == "LENS":
        return (
            f"镜头: {content.get('lens_type', '')}\n"
            f"  焦点描述: {content.get('focus_description', '')}\n"
            f"  应用说明: {content.get('application_notes', '')}\n"
        )
    elif btype == "SCENE_HEADING":
        return (
            f"场景头: {content.get('interior_exterior', '')} {content.get('location', '')} - {content.get('time_of_day', '')}\n"
        )
    elif btype == "ACTION_LINE":
        return (
            f"动作行: 角色ID={content.get('character_id', '')}\n"
            f"  描述: {content.get('description', '')}\n"
        )
    elif btype == "DIALOGUE":
        return (
            f"对白: 角色ID={content.get('character_id', '')}\n"
            f"  提示词: {content.get('parenthetical', '')}\n"
            f"  台词: {content.get('line_text', '')}\n"
        )
    elif btype == "VISUAL_MOTIF":
        return (
            f"视觉主题: {content.get('motif_name', '')}\n"
            f"  视觉描述: {content.get('visual_description', '')}\n"
            f"  象征意义: {content.get('symbolic_meaning', '')}\n"
        )
    elif btype == "STORY_CARD":
        return (
            f"故事卡框架: {content.get('card_id', '')} - {content.get('card_name', '')}\n"
            f"  类型: {content.get('genre', '')}\n"
            f"  写作风格要求: {content.get('writing_modifier', '')}\n"
            f"  参考作品: {content.get('reference_works', '')}\n"
        )
    elif btype == "STORY_SYNOPSIS":
        return (
            f"故事简介: {content.get('title', '')}\n"
            f"  梗概: {content.get('logline', '')}\n"
            f"  简介: {content.get('synopsis', '')[:300]}\n"
            f"  类型: {content.get('genre', '')}\n"
            f"  核心主题: {content.get('theme', '')}\n"
            f"  基调: {content.get('tone', '')}\n"
            f"  主角: {content.get('protagonists', '')}\n"
            f"  对手: {content.get('antagonists', '')}\n"
            f"  背景设定: {content.get('setting', '')}\n"
        )
    elif btype == "STORY_OUTLINE":
        return (
            f"故事大纲: {content.get('title', '')}\n"
            f"  梗概: {content.get('logline', '')}\n"
            f"  类型: {content.get('genre', '')}\n"
            f"  第一幕·建置: {content.get('act1_summary', '')[:200]}\n"
            f"  第二幕·对抗: {content.get('act2_summary', '')[:200]}\n"
            f"  第三幕·结局: {content.get('act3_summary', '')[:200]}\n"
            f"  转折点: {content.get('key_turning_points', '')[:200]}\n"
            f"  核心冲突: {content.get('central_conflict', '')}\n"
            f"  高潮: {content.get('climax_design', '')}\n"
            f"  结局类型: {content.get('ending_type', '')}\n"
            f"  情感路线: {content.get('emotional_roadmap', '')[:200]}\n"
        )
    elif btype == "CHAPTER_OUTLINE":
        return (
            f"第{content.get('chapter_number', '?')}章大纲: {content.get('title', '')}\n"
            f"  概要: {content.get('summary', '')[:200]}\n"
            f"  叙事目标: {content.get('narrative_goal', '')}\n"
            f"  戏剧功能: {content.get('dramatic_function', '')}\n"
            f"  节拍1: {content.get('beat1_desc', '')[:150]}\n"
            f"  节拍2: {content.get('beat2_desc', '')[:150]}\n"
            f"  节拍3: {content.get('beat3_desc', '')[:150]}\n"
            f"  视角角色: {content.get('pov_character', '')}\n"
            f"  情感弧线: {content.get('emotional_arc', '')}\n"
            f"  目标字数: {content.get('target_words', '')}\n"
            f"  状态: {content.get('status', 'planned')}\n"
        )
    elif btype == "CHAPTER_DETAIL":
        return (
            f"第{content.get('chapter_number', '?')}章细纲 - {content.get('title', '')}\n"
            f"  场景1: {content.get('scene1_heading', '')} - {content.get('scene1_content', '')[:200]}\n"
            f"  场景2: {content.get('scene2_heading', '')} - {content.get('scene2_content', '')[:200]}\n"
            f"  场景3: {content.get('scene3_heading', '')} - {content.get('scene3_content', '')[:200]}\n"
            f"  核心冲突: {content.get('key_conflicts', '')[:200]}\n"
            f"  角色目标: {content.get('character_goals', '')[:200]}\n"
            f"  写作备注: {content.get('writing_notes', '')}\n"
        )
    elif btype == "READER_EMOTION_CURVE":
        return (
            f"读者情绪曲线:\n"
            f"  高峰点: {content.get('peak_points', '')}\n"
            f"  低谷点: {content.get('valley_points', '')}\n"
            f"  整体走向: {content.get('overall_trajectory', '')}\n"
        )

    return f"[{btype}块]: {json.dumps(content, ensure_ascii=False)[:100]}"
