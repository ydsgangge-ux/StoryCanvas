"""信息边界校验器 - 零LLM纯规则检测"""


class InformationValidator:
    """检测正文中角色是否说出了不应知道的信息"""

    def validate(self, chapter_content: str, character_boundaries: dict) -> list:
        """
        检查正文是否存在信息边界违规。

        Args:
            chapter_content: 章节正文
            character_boundaries: 角色信息边界 {char_id: {doesnt_know: [...]}}

        Returns:
            违规列表 [{"character": "name", "info": "违规信息", "sentence": "原文句子", "severity": "warning"}]
        """
        violations = []
        for char_id, boundary in character_boundaries.items():
            doesnt_know = boundary.get("doesnt_know", [])
            for info in doesnt_know:
                if info and info in chapter_content:
                    # Find the sentence containing the violation
                    import re
                    sentences = re.split(r'[。！？\n]', chapter_content)
                    for sentence in sentences:
                        if info in sentence:
                            violations.append({
                                "character": char_id,
                                "info": info,
                                "sentence": sentence.strip()[:100],
                                "severity": "warning"
                            })
                            break
        return violations

    def validate_dialogue(self, character_name: str, line: str,
                          character_knowledge: list) -> bool:
        """验证单句对白是否包含角色不应知道的信息"""
        for knowledge in character_knowledge:
            if knowledge and knowledge in line:
                return False
        return True
