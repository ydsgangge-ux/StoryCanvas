"""脚手架渐进拆除 - 经验标记管理与触发规则

每次关键操作后自动检查并更新标记，前端据此调整UI复杂度。
独立模块以避免 projects.py ↔ blocks.py 的循环导入。
"""

import json
from backend.core.database import get_connection


EXPERIENCE_FLAGS_RULES = {
    "has_applied_story_card": {
        "trigger": "已应用故事卡",
        "unlocks": ["自由添加自定义块", "不再显示故事卡引导弹窗"],
    },
    "has_added_custom_blocks": {
        "trigger": "已手动添加超过5个块",
        "unlocks": ["批量操作工具可见", "块模板建议"],
    },
    "has_generated_chapter": {
        "trigger": "已成功生成至少1章正文",
        "unlocks": ["审计/修订功能", "导出菜单", "写作面板高级选项"],
    },
    "has_created_second_project": {
        "trigger": "创建了第2个项目",
        "unlocks": ["模板保存", "风格签名复制"],
    },
    "expert_mode_enabled": {
        "trigger": "用户手动开启专家模式",
        "unlocks": ["所有视图模式", "剧本类块", "全知层编辑", "API直接调用"],
    },
}


def get_experience_flags(project_id: str) -> dict:
    """读取经验标记"""
    conn = get_connection()
    row = conn.execute("SELECT experience_flags FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    if not row or not row["experience_flags"]:
        return {}
    return json.loads(row["experience_flags"])


def update_flag(project_id: str, flag: str, value: bool = True):
    """原子更新单个经验标记"""
    flags = get_experience_flags(project_id)
    flags[flag] = value
    conn = get_connection()
    conn.execute(
        "UPDATE projects SET experience_flags = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(flags, ensure_ascii=False), project_id)
    )
    conn.commit()
    conn.close()


def auto_check(project_id: str) -> dict:
    """触发检查所有可自动检测的规则"""
    conn = get_connection()
    project = conn.execute("SELECT experience_flags FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        conn.close()
        return {}
    flags = json.loads(project["experience_flags"] or "{}")
    changed = False

    if not flags.get("has_added_custom_blocks"):
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM blocks WHERE project_id = ?", (project_id,)
        ).fetchone()["cnt"]
        if count >= 5:
            flags["has_added_custom_blocks"] = True
            changed = True

    if not flags.get("has_generated_chapter"):
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM chapters WHERE project_id = ? AND status IN ('generated','approved')",
            (project_id,)
        ).fetchone()["cnt"]
        if count >= 1:
            flags["has_generated_chapter"] = True
            changed = True

    if changed:
        conn.execute(
            "UPDATE projects SET experience_flags = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(flags, ensure_ascii=False), project_id)
        )
        conn.commit()
    conn.close()
    return flags


def get_next_steps(flags: dict) -> list:
    """根据当前经验标记推荐下一步引导"""
    steps = []
    if not flags.get("has_applied_story_card"):
        steps.append({"action": "apply_story_card", "label": "选择一张故事卡构建初始结构", "priority": 1})
    if not flags.get("has_added_custom_blocks"):
        steps.append({"action": "add_custom_blocks", "label": "添加角色和场景块并填写信息", "priority": 2})
    if not flags.get("has_generated_chapter"):
        steps.append({"action": "generate_content", "label": "使用写作面板生成第一章正文", "priority": 3})
    steps.append({"action": "explore", "label": "探索更高阶功能（快照/导出/追踪）", "priority": 4})
    return steps
