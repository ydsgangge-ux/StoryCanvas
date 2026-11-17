"""结算回写器 - 将生成结果写回画布"""

import json
import re
from backend.core.database import get_connection
from backend.narrative.progress import calculate_completeness

SETTLEMENT_SECTIONS = (
    "角色位置变化",
    "角色情感变化",
    "关系变化",
    "伏笔状态变化",
    "下一章提示",
)


def _to_chapter_num(value) -> int:
    """把 3 / "3" / "chapter_3" / "第3章" 统一解析成章节号，失败返回 -1"""
    if isinstance(value, bool):
        return -1
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group())
    return -1


def _load_dict(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _parse_settlement(content: str) -> dict:
    """解析正文末尾的写后结算表，返回 {section: [行文本]}"""
    result = {name: [] for name in SETTLEMENT_SECTIONS}
    if not content or "[结算表]" not in content:
        return result
    tail = content.split("[结算表]", 1)[1]
    current = None
    for raw_line in tail.splitlines():
        line = raw_line.strip().strip("*# ").strip()
        if not line:
            continue
        matched_section = next((name for name in SETTLEMENT_SECTIONS if line.startswith(name)), None)
        if matched_section:
            current = matched_section
            rest = line.split("：", 1)[1].strip() if "：" in line else line.split(":", 1)[1].strip() if ":" in line else ""
            if rest:
                result[current].append(rest)
            continue
        if current:
            result[current].append(line.lstrip("-•").strip())
    return result


class WritebackService:
    """将Agent管线的结果写回画布状态"""

    def writeback(self, project_id: str, chapter_num: int, content: str) -> dict:
        """
        执行回写：根据结算表更新角色状态、关系、伏笔状态。

        Returns:
            更新的块ID列表
        """
        conn = get_connection()
        updated_blocks = []
        settlement = _parse_settlement(content)
        emotion_lines = settlement.get("角色情感变化", [])
        position_lines = settlement.get("角色位置变化", [])
        relation_lines = settlement.get("关系变化", [])
        hook_lines = settlement.get("伏笔状态变化", [])

        # 更新角色状态（按名字匹配结算表中的变化）
        chars = conn.execute(
            "SELECT id, content FROM blocks WHERE project_id = ? AND type = 'CHARACTER' AND is_draft = 0",
            (project_id,)
        ).fetchall()

        for char in chars:
            ch_content = _load_dict(char["content"])
            name = ch_content.get("name", "")
            if not name:
                continue

            emotion = next((line for line in emotion_lines if name in line), "")
            position = next((line for line in position_lines if name in line), "")
            if not emotion and not position:
                continue

            current_status = ch_content.get("current_status")
            if not isinstance(current_status, dict):
                current_status = {"summary": str(current_status)} if current_status else {}
            if position:
                current_status["position"] = self._strip_name(position, name)
            if emotion:
                current_status["psychological"] = self._strip_name(emotion, name)
            current_status["last_chapter"] = chapter_num

            ch_content["current_status"] = current_status
            conn.execute(
                "UPDATE blocks SET content = ?, completeness = ?, updated_at = datetime('now') WHERE id = ?",
                (json.dumps(ch_content, ensure_ascii=False),
                 calculate_completeness("CHARACTER", ch_content), char["id"])
            )
            updated_blocks.append(char["id"])

        # 更新关系块的动态
        if relation_lines:
            relations = conn.execute(
                "SELECT id, content FROM blocks WHERE project_id = ? AND type = 'RELATIONSHIP' AND is_draft = 0",
                (project_id,)
            ).fetchall()
            char_names = {_load_dict(c["content"]).get("name", "") for c in chars}
            id_to_name = {
                c["id"]: _load_dict(c["content"]).get("name", "")
                for c in chars
            }
            for rel in relations:
                r_content = _load_dict(rel["content"])
                party_a = str(r_content.get("party_a_id") or "")
                party_b = str(r_content.get("party_b_id") or "")
                name_a = id_to_name.get(party_a, party_a)
                name_b = id_to_name.get(party_b, party_b)
                related_line = next(
                    (line for line in relation_lines
                     if (name_a or name_b) and name_a in line and name_b in line),
                    "",
                )
                if not related_line:
                    # 兼容只提到一方的描述（用角色名而非ID填写的旧数据）
                    related_line = next(
                        (line for line in relation_lines
                         if (name_a and name_a in char_names and name_a in line)
                         or (name_b and name_b in char_names and name_b in line)),
                        "",
                    )
                if not related_line:
                    continue
                history = r_content.get("dynamic") or ""
                if related_line in history:
                    continue
                r_content["dynamic"] = (history + ("\n" if history else "") + related_line)[-300:]
                conn.execute(
                    "UPDATE blocks SET content = ?, updated_at = datetime('now') WHERE id = ?",
                    (json.dumps(r_content, ensure_ascii=False), rel["id"])
                )
                updated_blocks.append(rel["id"])

        # 更新 HOOK/FORESHADOW 回收状态（按计划章节或结算表描述）
        hooks = conn.execute(
            """SELECT id, content, type FROM blocks
               WHERE project_id = ? AND type IN ('HOOK', 'FORESHADOW') AND is_draft = 0""",
            (project_id,)
        ).fetchall()

        for hook in hooks:
            h_content = _load_dict(hook["content"])
            title = str(h_content.get("title") or h_content.get("content_planted") or "")
            payoff = h_content.get("payoff_chapter") or h_content.get("payoff_in", "")
            resolved_by_plan = _to_chapter_num(payoff) == chapter_num
            resolved_by_settlement = bool(title) and any(
                title in line and any(word in line for word in ("已回收", "回收", "揭晓", "已揭示"))
                for line in hook_lines
            ) and not any(word in line for line in hook_lines if title in line for word in ("未回收", "尚未回收"))
            if resolved_by_plan or resolved_by_settlement:
                h_content["status"] = "resolved"
                conn.execute(
                    "UPDATE blocks SET content = ?, updated_at = datetime('now') WHERE id = ?",
                    (json.dumps(h_content, ensure_ascii=False), hook["id"])
                )
                updated_blocks.append(hook["id"])

        conn.commit()
        conn.close()

        return {
            "updated_blocks": updated_blocks,
            "message": f"第{chapter_num}章回写完成，更新了{len(updated_blocks)}个块"
        }

    @staticmethod
    def _strip_name(line: str, name: str) -> str:
        """去掉行首的角色名和前导标点，保留状态描述"""
        text = line.replace(name, "", 1).lstrip("：:，, -—").strip()
        return text or line.strip()
