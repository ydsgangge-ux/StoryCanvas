"""结算回写器 - 将生成结果写回画布"""

import json
from backend.core.database import get_connection
from backend.narrative.progress import calculate_completeness


class WritebackService:
    """将Agent管线的结果写回画布状态"""

    def writeback(self, project_id: str, chapter_num: int, content: str) -> dict:
        """
        执行回写：更新角色状态、伏笔状态、关系强度等。

        Returns:
            更新的块ID列表
        """
        conn = get_connection()
        updated_blocks = []
        chapter_str = f"chapter_{chapter_num}"

        # Find character blocks to update
        chars = conn.execute(
            "SELECT id, content FROM blocks WHERE project_id = ? AND type = 'CHARACTER' AND is_draft = 0",
            (project_id,)
        ).fetchall()

        for char in chars:
            ch_content = json.loads(char["content"] or "{}")
            current_status = ch_content.get("current_status", {})

            # Update psychological state (simplified heuristic)
            old_psychological = current_status.get("psychological", "")
            current_status["psychological"] = f"经历了第{chapter_num}章的事件"

            if old_psychological != current_status["psychological"]:
                ch_content["current_status"] = current_status
                new_completeness = calculate_completeness("CHARACTER", ch_content)
                conn.execute(
                    "UPDATE blocks SET content = ?, completeness = ?, updated_at = datetime('now') WHERE id = ?",
                    (json.dumps(ch_content, ensure_ascii=False), new_completeness, char["id"])
                )
                updated_blocks.append(char["id"])

        # Update HOOK/FORESHADOW blocks that pay off in this chapter
        hooks = conn.execute(
            """SELECT id, content, type FROM blocks
               WHERE project_id = ? AND type IN ('HOOK', 'FORESHADOW') AND is_draft = 0""",
            (project_id,)
        ).fetchall()

        for hook in hooks:
            h_content = json.loads(hook["content"] or "{}")
            payoff = h_content.get("payoff_chapter") or h_content.get("payoff_in", "")
            if payoff == chapter_str or payoff == str(chapter_num):
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
