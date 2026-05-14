import uuid
from fastapi import APIRouter, HTTPException
from backend.core.database import get_connection
from backend.core.models import ConnectionCreate, ConnectionUpdate

router = APIRouter()


@router.get("/api/projects/{project_id}/connections")
def list_connections(project_id: str):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM connections WHERE project_id = ? ORDER BY created_at ASC",
                        (project_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/api/projects/{project_id}/connections")
def create_connection(project_id: str, req: ConnectionCreate):
    conn = get_connection()
    # Verify blocks exist
    from_block = conn.execute("SELECT id FROM blocks WHERE id = ? AND project_id = ?",
                               (req.from_block, project_id)).fetchone()
    to_block = conn.execute("SELECT id FROM blocks WHERE id = ? AND project_id = ?",
                             (req.to_block, project_id)).fetchone()
    if not from_block or not to_block:
        raise HTTPException(400, "源块或目标块不存在")

    conn_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO connections (id, project_id, from_block, to_block, conn_type, label, chapter_hint)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (conn_id, project_id, req.from_block, req.to_block, req.conn_type,
         req.label, req.chapter_hint)
    )
    conn.commit()
    conn.close()
    return {"id": conn_id, "message": "连线创建成功"}


@router.put("/api/projects/{project_id}/connections/{conn_id}")
def update_connection(project_id: str, conn_id: str, req: ConnectionUpdate):
    conn = get_connection()
    existing = conn.execute("SELECT id FROM connections WHERE id = ? AND project_id = ?",
                            (conn_id, project_id)).fetchone()
    if not existing:
        raise HTTPException(404, "连线不存在")

    updates = {}
    if req.conn_type is not None: updates["conn_type"] = req.conn_type
    if req.label is not None: updates["label"] = req.label
    if req.chapter_hint is not None: updates["chapter_hint"] = req.chapter_hint

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values())
        values.append(conn_id)
        conn.execute(f"UPDATE connections SET {set_clause} WHERE id = ?", values)
        conn.commit()

    conn.close()
    return {"message": "更新成功"}


@router.delete("/api/projects/{project_id}/connections/{conn_id}")
def delete_connection(project_id: str, conn_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM connections WHERE id = ? AND project_id = ?",
                 (conn_id, project_id))
    conn.commit()
    conn.close()
    return {"message": "连线已删除"}


@router.get("/api/projects/{project_id}/connections/suggest")
def suggest_connections(project_id: str):
    """AI建议连线 - 分析现有块，返回可能相关的块对"""
    conn = get_connection()
    blocks = conn.execute("SELECT id, type, content, tags FROM blocks WHERE project_id = ? AND is_draft = 0",
                          (project_id,)).fetchall()
    existing_conns = conn.execute("SELECT from_block, to_block FROM connections WHERE project_id = ?",
                                   (project_id,)).fetchall()
    conn.close()

    existing_pairs = {(c["from_block"], c["to_block"]) for c in existing_conns}
    suggestions = []
    block_list = [dict(b) for b in blocks]

    # Simple heuristic: same chapter_pos blocks might be parallel
    for i, b1 in enumerate(block_list):
        for b2 in block_list[i+1:]:
            pair = (b1["id"], b2["id"])
            if pair in existing_pairs or (b2["id"], b1["id"]) in existing_pairs:
                continue
            # Character + Scene → contains
            if b1["type"] == "CHARACTER" and b2["type"] == "SCENE":
                suggestions.append({"from": b1["id"], "to": b2["id"], "type": "contains", "reason": "角色出现在场景中"})
            elif b1["type"] == "SCENE" and b2["type"] == "CHARACTER":
                suggestions.append({"from": b1["id"], "to": b2["id"], "type": "contains", "reason": "场景包含角色"})
            # Event + Event → follows
            if b1["type"] == "EVENT" and b2["type"] == "EVENT":
                suggestions.append({"from": b1["id"], "to": b2["id"], "type": "follows", "reason": "事件时序关联"})

    return {"suggestions": suggestions[:20]}
