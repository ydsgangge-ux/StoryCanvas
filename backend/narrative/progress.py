"""进度条计算 - 计算单个块完整度和项目整体进度"""

COMPLETENESS_RULES = {
    # ─── 角色类（7种） ─────────────────────────────────────────
    "CHARACTER": {
        "name": 0.30,
        "want": 0.20,
        "need": 0.20,
        "fatal_flaw": 0.15,
        "surface_personality": 0.15,
    },
    "PERSONALITY": {
        "character_id": 0.20,
        "core_values": 0.30,
        "behavior_patterns": 0.30,
        "dramatica_function": 0.20,
    },
    "GROWTH": {
        "character_id": 0.20,
        "arc_type": 0.25,
        "start_state": 0.20,
        "end_state": 0.20,
        "keystone_moments": 0.15,
    },
    "BACKSTORY": {
        "character_id": 0.20,
        "origin": 0.30,
        "formative_events": 0.30,
        "secrets": 0.20,
    },
    "CURRENT_STATE": {
        "character_id": 0.15,
        "chapter": 0.10,
        "physical_condition": 0.15,
        "psychological_condition": 0.20,
        "active_goals": 0.20,
        "emotional_state": 0.20,
    },
    "INFORMATION_BOUNDARY": {
        "character_id": 0.15,
        "chapter": 0.10,
        "confirmed_knowledge": 0.30,
        "wrongly_believes": 0.20,
        "dramatic_irony": 0.25,
    },
    "OMNISCIENT_LAYER": {
        "true_facts": 0.50,
        "reader_reveal_plan": 0.50,
    },
    # ─── 世界类（5种） ─────────────────────────────────────────
    "WORLDVIEW": {
        "world_name": 0.10,
        "fundamental_rules": 0.40,
        "power_system": 0.30,
        "tone": 0.20,
    },
    "FACTION": {
        "name": 0.25,
        "ideology": 0.20,
        "goal": 0.20,
        "resources": 0.15,
        "weakness": 0.20,
    },
    "RULE_CONSTRAINT": {
        "rule_name": 0.20,
        "rule_type": 0.20,
        "mechanism": 0.30,
        "consequence_of_breaking": 0.30,
    },
    "WORLD_DEVELOPMENT": {
        "aspect": 0.20,
        "current_state": 0.30,
        "trajectory": 0.30,
        "key_events": 0.20,
    },
    "TIMESTAMP": {
        "era_name": 0.30,
        "time_range": 0.30,
        "key_changes": 0.40,
    },
    # ─── 叙事结构类（9种） ─────────────────────────────────────
    "TIMELINE": {
        "timeline_name": 0.40,
        "timeline_type": 0.30,
        "pov_characters": 0.30,
    },
    "SCENE": {
        "title": 0.20,
        "scene_goal": 0.30,
        "characters_present": 0.20,
        "emotion_target": 0.30,
    },
    "EVENT": {
        "title": 0.20,
        "what_happens": 0.40,
        "immediate_effects": 0.40,
    },
    "GOAL": {
        "surface_goal": 0.25,
        "deep_goal": 0.20,
        "obstacle": 0.30,
        "stakes": 0.25,
    },
    "CONFLICT": {
        "title": 0.15,
        "conflict_type": 0.15,
        "root_cause": 0.25,
        "surface_manifestation": 0.25,
        "resolution_type": 0.20,
    },
    "TURNING_POINT": {
        "title": 0.15,
        "turning_type": 0.20,
        "before_state": 0.25,
        "trigger": 0.20,
        "after_state": 0.20,
    },
    "HOOK": {
        "title": 0.20,
        "plant_chapter": 0.15,
        "content_planted": 0.30,
        "payoff_chapter": 0.15,
        "content_resolved": 0.20,
    },
    "FORESHADOW": {
        "title": 0.15,
        "hint_content": 0.25,
        "plant_chapter": 0.15,
        "payoff_chapter": 0.15,
        "payoff_content": 0.30,
    },
    "SURPRISE": {
        "title": 0.20,
        "surprise_type": 0.20,
        "revelation": 0.30,
        "setup_required": 0.30,
    },
    # ─── 关系类（2种） ─────────────────────────────────────────
    "RELATIONSHIP": {
        "party_a_id": 0.15,
        "party_b_id": 0.15,
        "relationship_type": 0.25,
        "dynamic": 0.25,
        "history": 0.20,
    },
    "FACTION_RELATION": {
        "faction_a_id": 0.15,
        "faction_b_id": 0.15,
        "relation_type": 0.25,
        "key_events": 0.25,
        "current_tension": 0.20,
    },
    # ─── 表达类（5种） ─────────────────────────────────────────
    "ATMOSPHERE": {
        "name": 0.20,
        "sensory_details": 0.30,
        "emotional_tone": 0.25,
        "associated_elements": 0.25,
    },
    "EMOTION_TARGET": {
        "chapter": 0.15,
        "primary_emotion": 0.30,
        "intensity": 0.20,
        "trigger": 0.20,
        "resolution": 0.15,
    },
    "RHYTHM": {
        "chapter": 0.15,
        "rhythm_type": 0.25,
        "pacing_notes": 0.30,
        "transition_style": 0.30,
    },
    "THEME_STATEMENT": {
        "theme": 0.40,
        "exploration_approach": 0.30,
        "counter_argument": 0.30,
    },
    "LENS": {
        "lens_type": 0.30,
        "focus_description": 0.40,
        "application_notes": 0.30,
    },
    # ─── 剧本专属类（4种） ─────────────────────────────────────
    "SCENE_HEADING": {
        "location": 0.40,
        "time_of_day": 0.30,
        "interior_exterior": 0.30,
    },
    "ACTION_LINE": {
        "description": 0.50,
        "character_id": 0.25,
        "continuation_note": 0.25,
    },
    "DIALOGUE": {
        "character_id": 0.30,
        "line_text": 0.40,
        "parenthetical": 0.15,
        "delivery_note": 0.15,
    },
    "VISUAL_MOTIF": {
        "motif_name": 0.30,
        "visual_description": 0.40,
        "symbolic_meaning": 0.30,
    },
    # ─── 大纲类（4种，参考 Dramatica-Flow 叙事架构） ──────────
    "STORY_SYNOPSIS": {
        "title": 0.15,
        "logline": 0.15,
        "synopsis": 0.15,
        "genre": 0.10,
        "theme": 0.10,
        "tone": 0.10,
        "protagonists": 0.10,
        "antagonists": 0.05,
        "setting": 0.10,
    },
    "STORY_OUTLINE": {
        "title": 0.10,
        "logline": 0.10,
        "genre": 0.05,
        "act1_summary": 0.15,
        "act2_summary": 0.15,
        "act3_summary": 0.15,
        "key_turning_points": 0.10,
        "central_conflict": 0.05,
        "climax_design": 0.05,
        "ending_type": 0.05,
        "emotional_roadmap": 0.05,
    },
    "CHAPTER_OUTLINE": {
        "chapter_number": 0.05,
        "title": 0.10,
        "summary": 0.15,
        "narrative_goal": 0.10,
        "dramatic_function": 0.05,
        "beat1_desc": 0.10,
        "beat2_desc": 0.10,
        "beat3_desc": 0.10,
        "pov_character": 0.10,
        "target_words": 0.05,
        "emotional_arc": 0.05,
        "status": 0.05,
    },
    "CHAPTER_DETAIL": {
        "chapter_number": 0.05,
        "title": 0.05,
        "scene1_heading": 0.10,
        "scene1_content": 0.15,
        "scene2_heading": 0.10,
        "scene2_content": 0.15,
        "scene3_heading": 0.10,
        "scene3_content": 0.15,
        "key_conflicts": 0.05,
        "character_goals": 0.05,
        "writing_notes": 0.05,
    },
    # ─── 特殊类（2种） ─────────────────────────────────────────
    "STORY_CARD": {
        "card_id": 0.15,
        "card_name": 0.20,
        "genre": 0.15,
        "writing_modifier": 0.30,
        "reference_works": 0.20,
    },
    "READER_EMOTION_CURVE": {
        "chapters": 0.30,
        "peak_points": 0.30,
        "valley_points": 0.20,
        "overall_trajectory": 0.20,
    },
    # ─── 分镜头脚本类（1种） ─────────────────────────────────────
    "STORYBOARD": {
        "chapter_number": 0.05,
        "title": 0.05,
        "shots": 0.40,
        "total_shots": 0.10,
        "estimated_duration": 0.10,
        "visual_style": 0.15,
        "music_suggestion": 0.15,
    },
}


def calculate_completeness(block_type: str, content: dict) -> float:
    """计算单个块的完整度"""
    rules = COMPLETENESS_RULES.get(block_type, {})
    if not rules:
        # Default: check if content has any non-empty fields
        filled = sum(1 for v in content.values() if v != "" and v != [] and v != {})
        total = len(content) or 1
        return round(min(filled / total, 1.0), 2)

    total_weight = 0.0
    for field, weight in rules.items():
        value = content.get(field)
        if isinstance(value, str) and value.strip():
            total_weight += weight
        elif isinstance(value, list) and len(value) > 0:
            total_weight += weight
        elif isinstance(value, dict) and len(value) > 0:
            total_weight += weight
        elif value is not None and not isinstance(value, (str, list, dict)):
            total_weight += weight

    return round(min(total_weight, 1.0), 2)


# Progress by block category for project-level display
CATEGORY_WEIGHTS = {
    "world": {"WORLDVIEW": 0.3, "FACTION": 0.2, "RULE_CONSTRAINT": 0.2,
              "WORLD_DEVELOPMENT": 0.2, "TIMESTAMP": 0.1},
    "character": {"CHARACTER": 0.3, "PERSONALITY": 0.15, "GROWTH": 0.15,
                  "BACKSTORY": 0.1, "CURRENT_STATE": 0.1,
                  "INFORMATION_BOUNDARY": 0.1, "OMNISCIENT_LAYER": 0.1},
    "structure": {"SCENE": 0.2, "TIMELINE": 0.15, "EVENT": 0.15, "GOAL": 0.1,
                  "CONFLICT": 0.1, "TURNING_POINT": 0.1, "HOOK": 0.1,
                  "FORESHADOW": 0.05, "SURPRISE": 0.05},
    "tension": {"RELATIONSHIP": 0.2, "FACTION_RELATION": 0.15,
                "READER_EMOTION_CURVE": 0.3, "EMOTION_TARGET": 0.2,
                "RHYTHM": 0.15},
}


def calculate_project_progress(project: dict, blocks: list) -> dict:
    """计算项目整体进度"""
    import json

    category_progress = {}
    for cat, type_weights in CATEGORY_WEIGHTS.items():
        total_cat = 0.0
        cat_weight_count = 0
        for btype, weight in type_weights.items():
            matching_blocks = [b for b in blocks if b["type"] == btype]
            if matching_blocks:
                avg_completeness = sum(
                    calculate_completeness(b["type"], json.loads(b.get("content") or "{}"))
                    for b in matching_blocks
                ) / len(matching_blocks)
                total_cat += avg_completeness * weight
                cat_weight_count += weight
        if cat_weight_count > 0:
            category_progress[cat] = round(total_cat / cat_weight_count, 2)
        else:
            category_progress[cat] = 0.0

    total_progress = sum(category_progress.values()) / max(len(category_progress), 1)

    # Generate status message
    if total_progress < 0.2:
        status = "完全自由发挥——结果不可控，但可能有惊喜"
        level = 0
    elif total_progress < 0.4:
        status = "有基本方向——AI会有倾向，细节随机"
        level = 1
    elif total_progress < 0.6:
        status = "结构可控——生成后可能需要调整细节"
        level = 2
    elif total_progress < 0.8:
        status = "高度可控——AI主要在执行你的意图"
        level = 3
    else:
        status = "精确控制——AI是纯执行者"
        level = 4

    return {
        "overall": round(total_progress, 2),
        "categories": category_progress,
        "status": status,
        "level": level,
    }
