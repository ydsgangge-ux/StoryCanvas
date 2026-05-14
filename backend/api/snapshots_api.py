"""快照管理 API"""
import asyncio
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from backend.core import snapshot as snap
from backend.core.database import get_connection

router = APIRouter()


class CheckpointCreate(BaseModel):
    label: str


@router.get("/api/projects/{project_id}/snapshots")
def list_snapshots(project_id: str, snapshot_type: Optional[str] = Query(None)):
    """获取所有快照列表"""
    # Verify project exists
    conn = get_connection()
    existing = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    if not existing:
        raise HTTPException(404, "项目不存在")
    return snap.get_snapshots(project_id, snapshot_type)


@router.post("/api/projects/{project_id}/snapshots")
def create_checkpoint(project_id: str, req: CheckpointCreate):
    """手动创建检查点"""
    conn = get_connection()
    existing = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    if not existing:
        raise HTTPException(404, "项目不存在")

    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            result = asyncio.ensure_future(snap.take_snapshot(project_id, "checkpoint", req.label))
        else:
            # Fallback: run synchronously
            import asyncio
            result = asyncio.run(snap.take_snapshot(project_id, "checkpoint", req.label))
    except RuntimeError:
        # No event loop
        result = asyncio.run(snap.take_snapshot(project_id, "checkpoint", req.label))

    return {"message": f"检查点已保存: {req.label}", "snapshot": result}


@router.post("/api/projects/{project_id}/snapshots/{snapshot_id}/restore")
def restore_snapshot(project_id: str, snapshot_id: str):
    """回滚到某快照"""
    # Verify project
    conn = get_connection()
    existing = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    if not existing:
        raise HTTPException(404, "项目不存在")

    result = snap.restore_snapshot(project_id, snapshot_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.delete("/api/projects/{project_id}/snapshots/{snapshot_id}")
def delete_snapshot(project_id: str, snapshot_id: str):
    """删除快照（仅检查点可删除）"""
    success = snap.delete_snapshot(snapshot_id)
    if not success:
        raise HTTPException(404, "快照不存在")
    return {"message": "快照已删除"}


@router.get("/api/projects/{project_id}/integrity")
def check_integrity(project_id: str):
    """检查数据库完整性（崩溃恢复用）"""
    return snap.check_integrity(project_id)
