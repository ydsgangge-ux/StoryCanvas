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

import json
from backend.core.database import get_connection
from backend.narrative.translator import style_to_prompt, block_to_context


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
        scenes_data = self._get_scene_instructions(all_blocks, chapter_str)
        characters_data = self._get_active_characters_with_boundaries(all_blocks, chapter_str)
        hooks_data = self._get_pending_hooks(all_blocks, chapter_num)
        expression_data = self._get_expression_instructions(all_blocks, chapter_str)
        world_data = self._get_world_context(all_blocks)
        timeline_data = self._get_chapter_timeline(all_blocks, all_conns, chapter_str)
        history_data = self._get_recent_chapters(project_id, chapter_num, n=include_history)

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
            "style_signature": style_to_prompt(json.loads(style_sig)),
            # 旧key别名（generate.py / architect.py / writer.py 使用）
            "characters": characters_data,
            "world": world_data,
            "expression": expression_data,
            "history": history_data,
            "timeline": timeline_data,
            "structure": {
                "scenes": scenes_data,
                "hooks_to_resolve": hooks_data,
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
                content = json.loads(bd.get("content") or "{}")
                return {
                    "card_id": content.get("card_id", ""),
                    "card_name": content.get("card_name", ""),
                    "genre": content.get("genre", ""),
                    "writing_modifier": content.get("writing_modifier", ""),
                    "reference_works": content.get("reference_works", ""),
                }
        return {}

    def _get_scene_instructions(self, blocks, chapter_str: str) -> list:
        """获取本章场景指令（最高优先级）"""
        scenes = []
        for b in blocks:
            bd = dict(b)
            content = json.loads(bd.get("content") or "{}")
            if bd["type"] == "SCENE" and bd.get("chapter_pos") == chapter_str:
                scenes.append({
                    "block_id": bd["id"],
                    "title": content.get("title", ""),
                    "goal": content.get("scene_goal", ""),
                    "emotion_target": content.get("emotion_target", ""),
                    "tension_level": content.get("tension_level", 5),
                    "characters_present": content.get("characters_present", ""),
                    "what_happens": content.get("what_happens", ""),
                })
        return scenes

    def _get_expression_instructions(self, blocks, chapter_str: str) -> dict:
        """获取本章表达指令"""
        result = {"emotion_targets": [], "rhythm": None, "atmosphere": None}
        for b in blocks:
            bd = dict(b)
            content = json.loads(bd.get("content") or "{}")
            if bd["type"] == "EMOTION_TARGET":
                ch = content.get("chapter", "")
                if str(ch) == chapter_str.replace("chapter_", ""):
                    result["emotion_targets"].append({
                        "primary_emotion": content.get("primary_emotion", ""),
                        "intensity": content.get("intensity", 5),
                        "trigger": content.get("trigger", ""),
                        "resolution": content.get("resolution", ""),
                    })
            elif bd["type"] == "RHYTHM":
                ch = content.get("chapter", "")
                if str(ch) == chapter_str.replace("chapter_", ""):
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

    def _get_active_characters_with_boundaries(self, blocks, chapter_str: str) -> list:
        """获取本章活跃角色及其信息边界"""
        chars = []
        for b in blocks:
            bd = dict(b)
            content = json.loads(bd.get("content") or "{}")
            if bd["type"] == "CHARACTER":
                char_info = {
                    "id": bd["id"],
                    "name": content.get("name", "未命名角色"),
                    "want": content.get("want", ""),
                    "need": content.get("need", ""),
                    "fatal_flaw": content.get("fatal_flaw", ""),
                    "appearance": content.get("appearance", ""),
                    "voice_style": content.get("voice_style", ""),
                    "knowledge_boundary": self._get_character_knowledge(blocks, bd["id"], chapter_str),
                }
                # 附着当前状态
                current_state = self._find_attached_block(blocks, "CURRENT_STATE", bd["id"])
                if current_state:
                    cs_content = json.loads(dict(current_state).get("content") or "{}")
                    char_info["current_state"] = {
                        "physical": cs_content.get("physical_condition", ""),
                        "psychological": cs_content.get("psychological_condition", ""),
                        "emotional": cs_content.get("emotional_state", ""),
                        "active_goals": cs_content.get("active_goals", ""),
                    }
                # 附着成长弧线
                growth = self._find_attached_block(blocks, "GROWTH", bd["id"])
                if growth:
                    g_content = json.loads(dict(growth).get("content") or "{}")
                    char_info["arc"] = {
                        "arc_type": g_content.get("arc_type", ""),
                        "keystone_moments": g_content.get("keystone_moments", ""),
                    }
                chars.append(char_info)
        return chars

    def _get_character_knowledge(self, blocks, char_id: str, chapter_str: str) -> dict:
        """获取指定角色在指定章节的信息边界"""
        for b in blocks:
            bd = dict(b)
            if bd["type"] == "INFORMATION_BOUNDARY" and bd.get("content"):
                content = json.loads(bd.get("content") or "{}")
                if content.get("character_id") == char_id:
                    return {
                        "knows": content.get("confirmed_knowledge", []),
                        "wrongly_believes": content.get("wrongly_believes", []),
                        "dramatic_irony": content.get("dramatic_irony", ""),
                    }
        return {"knows": [], "wrongly_believes": [], "dramatic_irony": ""}

    def _find_attached_block(self, blocks, block_type: str, char_id: str):
        """查找附着到指定角色的块"""
        for b in blocks:
            bd = dict(b)
            if bd["type"] == block_type:
                content = json.loads(bd.get("content") or "{}")
                if content.get("character_id") == char_id:
                    return bd
        return None

    def _get_pending_hooks(self, blocks, chapter_num: int) -> list:
        """获取截至本章待回收的伏笔"""
        hooks = []
        for b in blocks:
            bd = dict(b)
            content = json.loads(bd.get("content") or "{}")
            if bd["type"] in ("HOOK", "FORESHADOW"):
                status = content.get("status", "open")
                plant_ch = self._safe_int(content.get("plant_chapter", 0))
                payoff_ch = self._safe_int(content.get("payoff_chapter", 999))
                # 已埋设但尚未回收
                if status == "open" and plant_ch <= chapter_num and payoff_ch >= chapter_num:
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
        """获取截至本章已向读者释放的全知层真相"""
        for b in blocks:
            bd = dict(b)
            if bd["type"] == "OMNISCIENT_LAYER":
                content = json.loads(bd.get("content") or "{}")
                facts = content.get("true_facts", [])
                plan = content.get("reader_reveal_plan", [])
                revealed = []
                for item in plan:
                    if isinstance(item, dict) and item.get("chapter", 999) <= chapter_num:
                        revealed.append({
                            "fact": item.get("reveal", ""),
                            "revelation_chapter": item.get("chapter"),
                            "is_sensitive": item.get("never_reveal_to_characters", False),
                        })
                # 如果没设置reveal plan，找所有本章应揭示的事实
                if not revealed:
                    for fact in facts:
                        if isinstance(fact, dict) and fact.get("reveal_chapter", 999) <= chapter_num:
                            revealed.append({
                                "fact": fact.get("content", ""),
                                "revelation_chapter": fact.get("reveal_chapter"),
                                "is_sensitive": False,
                            })
                return revealed
        return []

    def _get_world_context(self, blocks) -> str:
        """获取世界背景上下文"""
        parts = []
        for b in blocks:
            bd = dict(b)
            content = json.loads(bd.get("content") or "{}")
            if bd["type"] == "WORLDVIEW":
                parts.append(
                    f"世界观「{content.get('world_name', '')}」:\n"
                    f"  核心规则: {', '.join(content.get('fundamental_rules', []))}\n"
                    f"  力量体系: {content.get('power_system', '')}\n"
                    f"  基调: {content.get('tone', '')}"
                )
            elif bd["type"] == "FACTION":
                parts.append(
                    f"势力「{content.get('name', '')}」: {content.get('ideology', '')} | "
                    f"目标: {content.get('goal', '')} | 弱点: {content.get('weakness', '')}"
                )
            elif bd["type"] == "RULE_CONSTRAINT":
                parts.append(
                    f"规则「{content.get('rule_name', '')}」: {content.get('mechanism', '')[:80]}"
                )
            elif bd["type"] == "TIMESTAMP":
                parts.append(
                    f"时代锚点「{content.get('era_name', '')}」: {content.get('time_range', '')} | {content.get('key_changes', '')[:80]}"
                )
        return "\n\n".join(parts)

    def _get_chapter_timeline(self, blocks, connections, chapter_str: str) -> list:
        """获取时间线语境"""
        timelines = []
        for b in blocks:
            bd = dict(b)
            content = json.loads(bd.get("content") or "{}")
            if bd["type"] == "TIMELINE":
                # 找出附着到该时间线的本章场景
                scenes_on_timeline = []
                for b2 in blocks:
                    b2d = dict(b2)
                    if b2d["type"] == "SCENE" and b2d.get("timeline_id") == bd["id"] and b2d.get("chapter_pos") == chapter_str:
                        s_content = json.loads(b2d.get("content") or "{}")
                        scenes_on_timeline.append(s_content.get("title", "未命名"))
                timelines.append({
                    "id": bd["id"],
                    "name": content.get("timeline_name", "未命名时间线"),
                    "type": content.get("timeline_type", "main"),
                    "this_chapter_scenes": scenes_on_timeline,
                })
        return timelines

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
            outline = r["outline"] or ""
            word_count = r["word_count"] or 0
            block_refs = json.loads(r["block_refs"] or "[]")
            summaries.append(
                f"第{r['chapter_num']}章({word_count}字): {outline[:200]}"
            )
        return "\n".join(summaries)

    @staticmethod
    def _safe_int(val) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0
