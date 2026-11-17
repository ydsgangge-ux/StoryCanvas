"""上下文聚合器 - 按章节收集所有相关块，生成结构化写作上下文

聚合优先级（从高到低）：
1. 本章SCENE块（直接场景指令）
2. 本章EMOTION_TARGET/RHYTHM（表达指令）
3. 活跃CHARACTER + 信息边界（角色视角约束）
4. HOOK/FORESHADOW（待回收伏笔）
5. OMNISCIENT_LAYER（截至本章已释放的真相）
6. WORLDVIEW/FACTION/RULE_CONSTRAINT（世界背景）
7. TIMELINE（时间线语境）
8. special_links（细纲特殊关联线）
9. 前n章history（连贯性上下文）
"""

import ast
import json
import re
from backend.core.database import get_connection
from backend.narrative.translator import style_to_prompt, block_to_context

# EVENT.suggested_function 的英文枚举 → 中文可读标签
EVENT_FUNCTION_LABELS = {
    "inciting_incident": "激励事件",
    "setup": "铺垫",
    "turning_point": "转折点",
    "midpoint": "中点反转",
    "climax": "高潮",
    "resolution": "结局",
}


class ContextAggregator:
    """上下文聚合器"""

    def aggregate(self, project_id: str, chapter_num: int, include_history: int = 3) -> dict:
        conn = get_connection()
        project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not project:
            conn.close()
            return {}

        chapter_str = f"chapter_{chapter_num}"

        # 排除草稿块（is_draft = 0 = 正式块）
        all_blocks = conn.execute(
            "SELECT * FROM blocks WHERE project_id = ? AND is_draft = 0", (project_id,)
        ).fetchall()

        all_conns = conn.execute(
            "SELECT * FROM connections WHERE project_id = ?", (project_id,)
        ).fetchall()

        # 特殊关联线
        special_links_raw = conn.execute(
            "SELECT special_links FROM chapters WHERE project_id = ? AND chapter_num = ?",
            (project_id, chapter_num)
        ).fetchone()
        conn.close()

        style_sig = project["style_sig"] if project["style_sig"] else "{}"

        # 核心上下文构造
        scenes_data = self._get_scene_instructions(all_blocks, chapter_num)
        characters_data = self._get_active_characters_with_boundaries(all_blocks, chapter_num)
        hooks_data = self._get_pending_hooks(all_blocks, chapter_num)
        expression_data = self._get_expression_instructions(all_blocks, chapter_str)
        world_data = self._get_world_context(all_blocks)
        timeline_data = self._get_chapter_timeline(all_blocks, all_conns, chapter_num)
        history_data = self._get_recent_chapters(project_id, chapter_num, n=include_history)
        story_structure = self._get_story_structure(all_blocks)
        chapter_outline = self._get_chapter_outline(all_blocks, chapter_num)
        relationships_data = self._get_relationships(all_blocks)
        foreshadows_data = self._get_foreshadows_to_plant(all_blocks, chapter_num)

        ctx = {
            "chapter_num": chapter_num,
            "chapter_target": project["chapter_count"] or 30,
            "aggregation_priority": [
                "story_card_framework",
                "scene_instructions",
                "expression_instructions",
                "active_characters",
                "pending_hooks",
                "revealed_truths",
                "world_background",
                "timeline_context",
                "special_links",
                "chapter_history",
            ],
            # 新key名（auditor.py 使用）
            "story_card_framework": self._get_story_card_framework(all_blocks),
            "scene_instructions": scenes_data,
            "expression_instructions": expression_data,
            "active_characters": characters_data,
            "pending_hooks": hooks_data,
            "revealed_truths": self._get_revealed_truths(all_blocks, chapter_num),
            "world_background": world_data,
            "timeline_context": timeline_data,
            "special_links": self._parse_special_links(special_links_raw),
            "chapter_history": history_data,
            "story_structure": story_structure,
            "relationships": relationships_data,
            "style_signature": style_to_prompt(self._loads(style_sig)),
            # 旧key别名（generate.py / architect.py / writer.py 使用）
            "characters": characters_data,
            "world": world_data,
            "expression": expression_data,
            "history": history_data,
            "timeline": timeline_data,
            "structure": {
                "scenes": scenes_data,
                "hooks_to_resolve": hooks_data,
                "foreshadows_to_plant": foreshadows_data,
                "turning_points": story_structure.get("turning_points", []),
                "events": story_structure.get("events", []),
                "conflicts": story_structure.get("conflicts", []),
                "goals": story_structure.get("goals", []),
                "chapter_outline": chapter_outline,
            },
            # 元信息
            "total_blocks": len(all_blocks),
            "total_connections": len(all_conns),
        }
        return ctx

    def _get_story_card_framework(self, blocks) -> dict:
        """获取故事卡框架信息（写作风格和结构定义）"""
        for b in blocks:
            bd = dict(b)
            if bd["type"] == "STORY_CARD":
                content = self._loads(bd.get("content"))
                return {
                    "card_id": content.get("card_id", ""),
                    "card_name": content.get("card_name", ""),
                    "genre": content.get("genre", ""),
                    "writing_modifier": content.get("writing_modifier", ""),
                    "reference_works": content.get("reference_works", ""),
                }
        return {}

    def _get_chapter_outline(self, blocks, chapter_num: int) -> dict:
        """获取本章的章节大纲块（CHAPTER_OUTLINE）"""
        for b in blocks:
            bd = dict(b)
            if bd["type"] != "CHAPTER_OUTLINE":
                continue
            content = self._loads(bd.get("content"))
            if self._safe_int(content.get("chapter_number") or content.get("chapter")) != chapter_num:
                continue
            beats = [
                content.get(f"beat{i}_desc", "")
                for i in range(1, 4)
                if content.get(f"beat{i}_desc")
            ]
            return {
                "block_id": bd["id"],
                "chapter_number": chapter_num,
                "title": content.get("title", ""),
                "summary": content.get("summary", ""),
                "narrative_goal": content.get("narrative_goal", ""),
                "dramatic_function": content.get("dramatic_function", ""),
                "emotional_arc": self._pair_text(content.get("emotional_arc", "")),
                "pov_character": content.get("pov_character", ""),
                "target_words": content.get("target_words", ""),
                "beats": beats,
                "status": content.get("status", ""),
            }
        return {}

    def _get_scene_instructions(self, blocks, chapter_num: int) -> list:
        """获取本章场景指令（最高优先级）

        场景的章节来源：blocks.chapter_pos（"chapter_3" / "3"）或内容里的
        chapter / chapter_number 字段。若没有任何场景标注章节，则把所有
        未标注章节的场景作为本章候选，避免「场景永远进不了上下文」。
        """
        assigned = []
        unassigned = []
        for b in blocks:
            bd = dict(b)
            content = self._loads(bd.get("content"))
            if bd["type"] != "SCENE":
                continue
            item = {
                "block_id": bd["id"],
                "chapter": self._chapter_of(bd, content),
                "title": content.get("title", ""),
                "goal": content.get("scene_goal", ""),
                "emotion_target": content.get("emotion_target", ""),
                "tension_level": content.get("tension_level", 5),
                "scene_type": content.get("scene_type", ""),
                "characters_present": content.get("characters_present", ""),
                "what_happens": content.get("what_happens", ""),
            }
            # 跳过内容为空的占位场景，避免脏块污染上下文
            if not any((item["title"], item["goal"], item["what_happens"])):
                continue
            if item["chapter"] is None:
                unassigned.append(item)
            elif item["chapter"] == chapter_num:
                assigned.append(item)
        return assigned if assigned else unassigned

    def _get_expression_instructions(self, blocks, chapter_str: str) -> dict:
        """获取本章表达指令"""
        chapter_num = self._safe_int(chapter_str.replace("chapter_", ""))
        result = {"emotion_targets": [], "rhythm": None, "atmosphere": None}
        for b in blocks:
            bd = dict(b)
            content = self._loads(bd.get("content"))
            if bd["type"] == "EMOTION_TARGET":
                if self._safe_int(content.get("chapter")) == chapter_num:
                    result["emotion_targets"].append({
                        "primary_emotion": content.get("primary_emotion", ""),
                        "intensity": content.get("intensity", 5),
                        "trigger": content.get("trigger", ""),
                        "resolution": content.get("resolution", ""),
                    })
            elif bd["type"] == "RHYTHM":
                if self._safe_int(content.get("chapter")) == chapter_num:
                    result["rhythm"] = {
                        "rhythm_type": content.get("rhythm_type", ""),
                        "pacing_notes": content.get("pacing_notes", ""),
                    }
            elif bd["type"] == "ATMOSPHERE":
                result["atmosphere"] = {
                    "name": content.get("name", ""),
                    "sensory_details": content.get("sensory_details", ""),
                    "emotional_tone": content.get("emotional_tone", ""),
                }
        return result

    def _get_active_characters_with_boundaries(self, blocks, chapter_num: int) -> list:
        """获取本章活跃角色及其信息边界"""
        chars = []
        for b in blocks:
            bd = dict(b)
            content = self._loads(bd.get("content"))
            if bd["type"] == "CHARACTER":
                name = content.get("name", "未命名角色")
                char_info = {
                    "id": bd["id"],
                    "name": name,
                    "role_archetype": content.get("role_archetype", ""),
                    "want": content.get("want", ""),
                    "need": content.get("need", ""),
                    "fatal_flaw": content.get("fatal_flaw", ""),
                    "superpower": content.get("superpower", ""),
                    "surface_personality": content.get("surface_personality", ""),
                    "behavior_lock": content.get("behavior_lock", ""),
                    "arc": content.get("arc", ""),
                    "appearance": content.get("appearance", ""),
                    "voice_style": content.get("voice_style", ""),
                    "age": content.get("age", ""),
                    "knowledge_boundary": self._get_character_knowledge(blocks, bd["id"], name),
                }
                # 附着当前状态
                current_state = self._find_attached_block(blocks, "CURRENT_STATE", bd["id"], name)
                if current_state:
                    cs_content = self._loads(dict(current_state).get("content"))
                    char_info["current_state"] = {
                        "physical": cs_content.get("physical_condition", ""),
                        "psychological": cs_content.get("psychological_condition", ""),
                        "emotional": cs_content.get("emotional_state", ""),
                        "active_goals": cs_content.get("active_goals", ""),
                    }
                # 附着成长弧线
                growth = self._find_attached_block(blocks, "GROWTH", bd["id"], name)
                if growth:
                    g_content = self._loads(dict(growth).get("content"))
                    char_info["arc"] = {
                        "arc_type": g_content.get("arc_type", ""),
                        "keystone_moments": g_content.get("keystone_moments", ""),
                    }
                chars.append(char_info)
        return chars

    def _get_character_knowledge(self, blocks, char_id: str, char_name: str = "") -> dict:
        """获取指定角色的信息边界（character_id 可填块ID或角色名）"""
        for b in blocks:
            bd = dict(b)
            if bd["type"] == "INFORMATION_BOUNDARY" and bd.get("content"):
                content = self._loads(bd.get("content"))
                ref = str(content.get("character_id") or content.get("character_name") or "").strip()
                if ref and (ref == char_id or ref == char_name or ref == str(bd.get("id"))):
                    return {
                        "knows": self._as_list(content.get("confirmed_knowledge")),
                        "wrongly_believes": self._as_list(content.get("wrongly_believes")),
                        "dramatic_irony": content.get("dramatic_irony", ""),
                    }
        return {"knows": [], "wrongly_believes": [], "dramatic_irony": ""}

    def _find_attached_block(self, blocks, block_type: str, char_id: str, char_name: str = ""):
        """查找附着到指定角色的块（支持按块ID或角色名关联）"""
        for b in blocks:
            bd = dict(b)
            if bd["type"] == block_type:
                content = self._loads(bd.get("content"))
                ref = str(content.get("character_id") or content.get("character_name") or "").strip()
                if ref and (ref == char_id or ref == char_name or ref == str(bd.get("id"))):
                    return bd
        return None

    def _get_pending_hooks(self, blocks, chapter_num: int) -> list:
        """获取截至本章待回收的伏笔"""
        hooks = []
        for b in blocks:
            bd = dict(b)
            content = self._loads(bd.get("content"))
            if bd["type"] in ("HOOK", "FORESHADOW"):
                status = content.get("status", "open")
                plant_ch = self._safe_int(content.get("plant_chapter", 0))
                payoff_ch = self._safe_int(content.get("payoff_chapter", 999))
                # 已埋设但尚未回收（前端创建的伏笔状态为 planted）
                if status in ("open", "planted") and plant_ch <= chapter_num and payoff_ch >= chapter_num:
                    hooks.append({
                        "id": bd["id"],
                        "type": bd["type"],
                        "title": content.get("title", ""),
                        "content_planted": content.get("content_planted", "") or content.get("hint_content", ""),
                        "plant_chapter": plant_ch,
                        "payoff_chapter": payoff_ch,
                        "urgency": "到期" if payoff_ch == chapter_num else "未到回收期" if payoff_ch > chapter_num else "已逾期",
                    })
        return hooks

    def _get_revealed_truths(self, blocks, chapter_num: int) -> list:
        """获取截至本章已向读者释放的全知层真相（合并多个全知层块）"""
        revealed = []
        for b in blocks:
            bd = dict(b)
            if bd["type"] != "OMNISCIENT_LAYER":
                continue
            content = self._loads(bd.get("content"))
            facts = self._as_list(content.get("true_facts"))
            plan = self._as_list(content.get("reader_reveal_plan"))
            plan_revealed = []
            for item in plan:
                if isinstance(item, dict) and self._safe_int(item.get("chapter", 999)) <= chapter_num:
                    plan_revealed.append({
                        "fact": item.get("reveal", ""),
                        "revelation_chapter": item.get("chapter"),
                        "is_sensitive": item.get("never_reveal_to_characters", False),
                    })
            if plan_revealed:
                revealed.extend(plan_revealed)
                continue
            # 没有 reveal plan 时，从 true_facts 中找本章应揭示的事实
            for fact in facts:
                if isinstance(fact, dict) and self._safe_int(fact.get("reveal_chapter", 999)) <= chapter_num:
                    revealed.append({
                        "fact": fact.get("content", ""),
                        "revelation_chapter": fact.get("reveal_chapter"),
                        "is_sensitive": bool(fact.get("is_sensitive", False)),
                    })
                elif isinstance(fact, str) and fact.strip():
                    # 纯文本真相视为作者已公开的信息，供写手保持一致性
                    revealed.append({
                        "fact": fact.strip(),
                        "revelation_chapter": 1,
                        "is_sensitive": False,
                    })
        return revealed

    def _get_foreshadows_to_plant(self, blocks, chapter_num: int) -> list:
        """获取本章需要埋设的铺垫"""
        result = []
        for b in blocks:
            bd = dict(b)
            content = self._loads(bd.get("content"))
            if bd["type"] != "FORESHADOW":
                continue
            if str(content.get("status", "")).lower() == "resolved":
                continue
            plant_ch = self._safe_int(content.get("plant_chapter", 0))
            if plant_ch == chapter_num:
                result.append({
                    "title": content.get("title", ""),
                    "hint_content": content.get("hint_content", ""),
                    "payoff_chapter": content.get("payoff_chapter", ""),
                })
        return result

    def _get_world_context(self, blocks) -> str:
        """获取世界背景上下文"""
        parts = []
        for b in blocks:
            bd = dict(b)
            content = self._loads(bd.get("content"))
            if bd["type"] == "WORLDVIEW":
                parts.append(
                    f"世界观「{content.get('world_name', '')}」:\n"
                    f"  核心规则: {self._join_text(content.get('fundamental_rules', []))}\n"
                    f"  力量体系: {content.get('power_system', '')}\n"
                    f"  宇宙结构: {content.get('cosmology', '')}\n"
                    f"  基调: {content.get('tone', '')}"
                )
            elif bd["type"] == "FACTION":
                parts.append(
                    f"势力「{content.get('name', '')}」: {content.get('ideology', '')} | "
                    f"目标: {content.get('goal', '')} | 弱点: {content.get('weakness', '')}"
                )
            elif bd["type"] == "RULE_CONSTRAINT":
                parts.append(
                    f"规则「{content.get('rule_name', '')}」: {self._text(content.get('mechanism'))[:80]}"
                )
            elif bd["type"] == "TIMESTAMP":
                parts.append(
                    f"时代锚点「{content.get('era_name', '')}」: {content.get('time_range', '')} | {self._text(content.get('key_changes'))[:80]}"
                )
            elif bd["type"] == "WORLD_DEVELOPMENT":
                parts.append(f"世界演变「{content.get('title', '')}」: {self._text(content.get('description') or content.get('change'))[:120]}")
        return "\n\n".join(parts)

    def _get_story_structure(self, blocks) -> dict:
        """聚合故事级结构块：简介/大纲/主题/事件/冲突/转折/目标"""
        result = {
            "synopsis": {}, "story_outline": {}, "theme": {},
            "events": [], "conflicts": [], "turning_points": [], "goals": [],
        }
        for b in blocks:
            bd = dict(b)
            content = self._loads(bd.get("content"))
            btype = bd["type"]
            if btype == "STORY_SYNOPSIS":
                result["synopsis"] = {
                    "title": content.get("title", ""),
                    "logline": content.get("logline", ""),
                    "synopsis": content.get("synopsis") or content.get("premise", ""),
                    "setting": content.get("setting", ""),
                    "genre": content.get("genre", ""),
                    "protagonists": content.get("protagonists", ""),
                    "antagonists": content.get("antagonists", ""),
                    "tone": content.get("tone", ""),
                    "emotional_roadmap": self._pair_text(content.get("emotional_roadmap", "")),
                }
            elif btype == "STORY_OUTLINE":
                result["story_outline"] = {
                    "title": content.get("title", ""),
                    "logline": content.get("logline", ""),
                    "genre": content.get("genre", ""),
                    "act1": content.get("act1_summary", ""),
                    "act2": content.get("act2_summary", ""),
                    "act3": content.get("act3_summary", ""),
                    "key_turning_points": content.get("key_turning_points", ""),
                    "central_conflict": content.get("central_conflict", ""),
                    "climax": content.get("climax_design", ""),
                    "ending": content.get("ending_type", ""),
                }
            elif btype == "THEME_STATEMENT":
                result["theme"] = {
                    "theme": content.get("theme", ""),
                    "approach": content.get("exploration_approach", ""),
                    "counter": content.get("counter_argument", ""),
                }
            elif btype == "EVENT" and len(result["events"]) < 10:
                function = content.get("immediate_effects") or content.get("suggested_function", "")
                result["events"].append({
                    "title": content.get("title", ""),
                    "event_type": content.get("event_type") or content.get("suggested_act", ""),
                    "what_happens": content.get("what_happens", ""),
                    "effects": EVENT_FUNCTION_LABELS.get(str(function), function),
                })
            elif btype == "CONFLICT" and len(result["conflicts"]) < 8:
                result["conflicts"].append({
                    "title": content.get("title", ""),
                    "conflict_type": content.get("conflict_type", ""),
                    "root_cause": content.get("root_cause", ""),
                    "manifestation": content.get("surface_manifestation", ""),
                })
            elif btype == "TURNING_POINT" and len(result["turning_points"]) < 8:
                result["turning_points"].append({
                    "title": content.get("title", ""),
                    "turning_type": content.get("turning_type", ""),
                    "trigger": content.get("trigger", ""),
                    "after_state": content.get("after_state", ""),
                })
            elif btype == "GOAL" and len(result["goals"]) < 8:
                result["goals"].append({
                    "surface_goal": content.get("surface_goal", ""),
                    "deep_goal": content.get("deep_goal", ""),
                    "obstacle": content.get("obstacle", ""),
                    "stakes": content.get("stakes", ""),
                })
        return result

    def _get_relationships(self, blocks) -> list:
        """聚合角色关系与势力关系，供写作时把握人物张力"""
        result = []
        for b in blocks:
            bd = dict(b)
            content = self._loads(bd.get("content"))
            if bd["type"] == "RELATIONSHIP":
                result.append({
                    "party_a": content.get("party_a_id", ""),
                    "party_b": content.get("party_b_id", ""),
                    "type": content.get("relationship_type", ""),
                    "dynamic": content.get("dynamic", ""),
                    "intensity": content.get("intensity", ""),
                })
            elif bd["type"] == "FACTION_RELATION":
                result.append({
                    "party_a": content.get("faction_a_id", ""),
                    "party_b": content.get("faction_b_id", ""),
                    "type": content.get("relation_type", ""),
                    "dynamic": content.get("key_events", ""),
                    "intensity": content.get("current_tension", ""),
                })
        return result

    def _get_chapter_timeline(self, blocks, connections, chapter_num: int) -> list:
        """获取时间线语境"""
        timelines = []
        for b in blocks:
            bd = dict(b)
            content = self._loads(bd.get("content"))
            if bd["type"] == "TIMELINE":
                # 找出附着到该时间线的本章场景
                scenes_on_timeline = []
                for b2 in blocks:
                    b2d = dict(b2)
                    if b2d["type"] != "SCENE":
                        continue
                    if b2d.get("timeline_id") != bd["id"] and b2d.get("id") not in self._linked_ids(connections, bd["id"]):
                        continue
                    s_content = self._loads(b2d.get("content"))
                    if self._chapter_of(b2d, s_content) == chapter_num:
                        scenes_on_timeline.append(s_content.get("title", "未命名"))
                timelines.append({
                    "id": bd["id"],
                    "name": content.get("timeline_name", "未命名时间线"),
                    "type": content.get("timeline_type", "main"),
                    "this_chapter_scenes": scenes_on_timeline,
                })
        return timelines

    @staticmethod
    def _linked_ids(connections, block_id: str) -> set:
        """获取与指定块直接相连的块ID集合"""
        ids = set()
        for c in connections:
            if c["from_block"] == block_id:
                ids.add(c["to_block"])
            elif c["to_block"] == block_id:
                ids.add(c["from_block"])
        return ids

    def _parse_special_links(self, row) -> list:
        """解析细纲特殊关联线"""
        if not row or not row["special_links"]:
            return []
        raw = row["special_links"]
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return []
        if isinstance(raw, (list, tuple)):
            return list(raw)
        return []

    def _get_recent_chapters(self, project_id: str, chapter_num: int, n: int = 3) -> str:
        """获取最近n章的摘要"""
        conn = get_connection()
        rows = conn.execute(
            """SELECT chapter_num, outline, content, word_count, block_refs
               FROM chapters
               WHERE project_id = ? AND chapter_num < ? AND status != 'planned'
               ORDER BY chapter_num DESC LIMIT ?""",
            (project_id, chapter_num, n)
        ).fetchall()
        conn.close()
        summaries = []
        for r in reversed(rows):
            outline = (r["outline"] or "").strip()
            word_count = r["word_count"] or 0
            # 上一章结尾通常包含结算表，保留尾部有助于延续角色状态
            content_tail = (r["content"] or "").strip()[-200:]
            piece = f"第{r['chapter_num']}章({word_count}字): {outline[:200]}"
            if content_tail:
                piece += f"\n  上章结尾: {content_tail}"
            summaries.append(piece)
        return "\n".join(summaries)

    @staticmethod
    def _loads(raw) -> dict:
        """安全解析块内容，避免单个坏块导致整个聚合失败"""
        if isinstance(raw, dict):
            return raw
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {"value": data}
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _as_list(value) -> list:
        """把列表或 JSON 字符串解析为列表"""
        if isinstance(value, list):
            return value
        if isinstance(value, str) and value.strip():
            text = value.strip()
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
            return [v.strip(" -•\t") for v in re.split(r"[\n；;、]+", text) if v.strip(" -•\t")]
        return []

    @staticmethod
    def _text(value) -> str:
        """把任意字段值安全转成字符串（列表/字典不会抛异常）"""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return "、".join(ContextAggregator._text(v) for v in value)
        if isinstance(value, dict):
            return ContextAggregator._text(value.get("content") or value.get("name") or value)
        return str(value)

    @staticmethod
    def _pair_text(value) -> str:
        """把 {start, end}、[{chapter, target_emotion}] 等结构化情感数据转成可读文本"""
        if not value:
            return ""
        if isinstance(value, str):
            text = value.strip()
            if text.startswith(("{", "[")):
                parsed = None
                try:
                    parsed = json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    try:
                        parsed = ast.literal_eval(text)
                    except (ValueError, SyntaxError):
                        parsed = None
                if parsed is not None and not isinstance(parsed, str):
                    return ContextAggregator._pair_text(parsed)
            return value
        if isinstance(value, dict):
            return " → ".join(
                ContextAggregator._text(v) for v in value.values() if v not in (None, "")
            )
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict):
                    chapter = item.get("chapter")
                    emotion = item.get("target_emotion") or item.get("emotion")
                    if chapter not in (None, "") and emotion:
                        parts.append(f"第{chapter}章 {ContextAggregator._text(emotion)}")
                    else:
                        parts.append(ContextAggregator._pair_text(item))
                elif item:
                    parts.append(str(item))
            return "；".join(p for p in parts if p)
        return str(value)

    @staticmethod
    def _chapter_of(bd: dict, content: dict):
        """解析场景所属章节：chapter_pos 列或内容字段"""
        raw = bd.get("chapter_pos")
        if raw not in (None, ""):
            match = re.search(r"\d+", str(raw))
            if match:
                return int(match.group())
        for key in ("chapter", "chapter_number", "chapter_pos"):
            val = content.get(key)
            if val in (None, ""):
                continue
            try:
                return int(val)
            except (ValueError, TypeError):
                match = re.search(r"\d+", str(val))
                if match:
                    return int(match.group())
        return None

    @staticmethod
    def _safe_int(val) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            try:
                match = re.search(r"\d+", str(val))
                return int(match.group()) if match else 0
            except Exception:
                return 0

    @staticmethod
    def _join_text(values) -> str:
        """安全拼接列表字段（元素可能是 dict，直接 join 会崩溃）"""
        if isinstance(values, str):
            return values
        if not isinstance(values, list):
            return str(values or "")
        parts = []
        for v in values:
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, dict):
                parts.append(str(v.get("content") or v.get("rule") or v.get("name") or v))
            else:
                parts.append(str(v))
        return ", ".join(parts)
