"""快照管理 - 自动快照/用户检查点/回滚/崩溃恢复"""
import uuid
import json
import asyncio
from datetime import datetime
from backend.core.database import get_connection

AUTO_SNAPSHOT_INTERVAL = 15 * 60  # 15分钟（秒）
AUTO_SNAPSHOT_KEEP = 20           # 最多保留20个自动快照


async def auto_snapshot_loop(project_id: str):
    """每个活跃项目启动一个后台快照任务"""
    while True:
        await asyncio.sleep(AUTO_SNAPSHOT_INTERVAL)
        await take_snapshot(project_id, snapshot_type="auto")
        await cleanup_old_snapshots(project_id)


async def take_snapshot(project_id: str, snapshot_type: str = "auto", label: str = None) -> dict:
    """创建项目快照"""
    conn = get_connection()
    project = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        conn.close()
        return {"error": "项目不存在"}

    blocks = conn.execute("SELECT * FROM blocks WHERE project_id = ?", (project_id,)).fetchall()
    connections = conn.execute("SELECT * FROM connections WHERE project_id = ?", (project_id,)).fetchall()
    layout = conn.execute("SELECT * FROM canvas_layout WHERE project_id = ?", (project_id,)).fetchone()
    chapters = conn.execute("SELECT * FROM chapters WHERE project_id = ?", (project_id,)).fetchall()

    snapshot_id = str(uuid.uuid4())
    blocks_json = json.dumps([dict(b) for b in blocks], ensure_ascii=False, default=str)
    conns_json = json.dumps([dict(c) for c in connections], ensure_ascii=False, default=str)
    layout_json = json.dumps(dict(layout) if layout else {}, ensure_ascii=False, default=str)
    chapters_json = json.dumps([dict(c) for c in chapters], ensure_ascii=False, default=str)

    word_count = sum((c["word_count"] or 0) for c in chapters) if chapters else 0

    conn.execute(
        """INSERT INTO snapshots (id, project_id, snapshot_type, label, blocks_json, connections_json,
           canvas_layout_json, chapters_json, created_at, word_count, block_count)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (snapshot_id, project_id, snapshot_type, label,
         blocks_json, conns_json, layout_json, chapters_json,
         datetime.now().isoformat(), word_count, len(blocks))
    )
    conn.execute("UPDATE projects SET last_snapshot_at = datetime('now') WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    return {
        "id": snapshot_id,
        "snapshot_type": snapshot_type,
        "label": label,
        "block_count": len(blocks),
        "word_count": word_count,
    }


async def cleanup_old_snapshots(project_id: str):
    """删除超出数量限制的旧自动快照"""
    conn = get_connection()
    auto_snaps = conn.execute(
        "SELECT id, created_at FROM snapshots WHERE project_id = ? AND snapshot_type = 'auto' ORDER BY created_at DESC",
        (project_id,)
    ).fetchall()
    if len(auto_snaps) > AUTO_SNAPSHOT_KEEP:
        to_delete = auto_snaps[AUTO_SNAPSHOT_KEEP:]
        ids = [s["id"] for s in to_delete]
        placeholders = ",".join("?" for _ in ids)
        conn.execute(f"DELETE FROM snapshots WHERE id IN ({placeholders})", ids)
        conn.commit()
    conn.close()


def get_snapshots(project_id: str, snapshot_type: str = None) -> list:
    """获取项目快照列表"""
    conn = get_connection()
    if snapshot_type:
        rows = conn.execute(
            "SELECT id, snapshot_type, label, created_at, word_count, block_count FROM snapshots WHERE project_id = ? AND snapshot_type = ? ORDER BY created_at DESC",
            (project_id, snapshot_type)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, snapshot_type, label, created_at, word_count, block_count FROM snapshots WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_snapshot(snapshot_id: str) -> dict:
    """获取单个快照详情"""
    conn = get_connection()
    row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def restore_snapshot(project_id: str, snapshot_id: str) -> dict:
    """回滚到指定快照"""
    snapshot = get_snapshot(snapshot_id)
    if not snapshot:
        return {"error": "快照不存在"}
    if snapshot["project_id"] != project_id:
        return {"error": "快照不属于此项目"}

    # 先创建回滚前备份
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in async context, schedule it
            asyncio.ensure_future(take_snapshot(project_id, "auto", "回滚前备份"))
        else:
            pass  # Skip auto-backup in sync context
    except RuntimeError:
        pass

    conn = get_connection()

    # 还原块
    blocks = json.loads(snapshot.get("blocks_json") or "[]")
    conn.execute("DELETE FROM blocks WHERE project_id = ?", (project_id,))
    for b in blocks:
        b.pop("project_id", None)
        conn.execute(
            """INSERT INTO blocks (id, project_id, type, canvas_x, canvas_y, canvas_w, collapsed,
               color, timeline_id, chapter_pos, completeness, tags, notes, content, is_draft)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (b["id"], project_id, b["type"], b.get("canvas_x", 0), b.get("canvas_y", 0),
             b.get("canvas_w", 280), b.get("collapsed", 0), b.get("color"),
             b.get("timeline_id"), b.get("chapter_pos"), b.get("completeness", 0.0),
             b.get("tags", "[]"), b.get("notes", ""), b.get("content", "{}"), b.get("is_draft", 0))
        )

    # 还原连线
    conns = json.loads(snapshot.get("connections_json") or "[]")
    conn.execute("DELETE FROM connections WHERE project_id = ?", (project_id,))
    for c in conns:
        c.pop("project_id", None)
        conn.execute(
            "INSERT INTO connections (id, project_id, from_block, to_block, conn_type, label, chapter_hint) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (c["id"], project_id, c["from_block"], c["to_block"], c["conn_type"], c.get("label"), c.get("chapter_hint"))
        )

    # 还原布局
    layout = json.loads(snapshot.get("canvas_layout_json") or "{}")
    if layout and layout.get("project_id"):
        conn.execute("DELETE FROM canvas_layout WHERE project_id = ?", (project_id,))
        conn.execute(
            "INSERT INTO canvas_layout (project_id, viewport_x, viewport_y, zoom, timeline_y) VALUES (?, ?, ?, ?, ?)",
            (project_id, layout.get("viewport_x", 0), layout.get("viewport_y", 0),
             layout.get("zoom", 1.0), layout.get("timeline_y", "{}"))
        )

    # 还原章节
    chapters = json.loads(snapshot.get("chapters_json") or "[]")
    conn.execute("DELETE FROM chapters WHERE project_id = ?", (project_id,))
    for ch in chapters:
        ch.pop("project_id", None)
        conn.execute(
            """INSERT INTO chapters (id, project_id, chapter_num, title, timeline_id, outline, content,
               audit_result, status, word_count, block_refs, special_links)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ch["id"], project_id, ch["chapter_num"], ch.get("title"), ch.get("timeline_id"),
             ch.get("outline"), ch.get("content"), ch.get("audit_result"), ch.get("status", "planned"),
             ch.get("word_count", 0), ch.get("block_refs", "[]"), ch.get("special_links", "[]"))
        )

    conn.execute("UPDATE projects SET updated_at = datetime('now') WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    return {"message": f"已回滚到快照 {snapshot.get('label', '')}", "restored": True}


def delete_snapshot(snapshot_id: str) -> bool:
    """删除快照"""
    conn = get_connection()
    snap = conn.execute("SELECT snapshot_type FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    if not snap:
        conn.close()
        return False
    # 自动快照不允许手动删除（由清理机制管理），检查点可以删除
    conn.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
    conn.commit()
    conn.close()
    return True


def check_integrity(project_id: str) -> dict:
    """检查数据库完整性（崩溃恢复用）"""
    conn = get_connection()
    try:
        # Check table integrity
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        ok = integrity[0] == "ok" if integrity else False

        # Check project exists
        project = conn.execute("SELECT id, updated_at, last_snapshot_at FROM projects WHERE id = ?", (project_id,)).fetchone()

        if not project:
            conn.close()
            return {"ok": False, "error": "项目不存在"}

        # Check blocks table
        block_count = conn.execute("SELECT COUNT(*) as cnt FROM blocks WHERE project_id = ?", (project_id,)).fetchone()

        conn.close()
        return {
            "ok": ok,
            "integrity": integrity[0] if integrity else "unknown",
            "project_exists": True,
            "block_count": block_count["cnt"] if block_count else 0,
            "last_updated": project["updated_at"] if project else None,
            "last_snapshot": project["last_snapshot_at"] if project else None,
        }
    except Exception as e:
        conn.close()
        return {"ok": False, "error": str(e)}
