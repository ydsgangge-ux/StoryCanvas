from fastapi import APIRouter, HTTPException
from backend.core.database import get_connection
from backend.core.models import CanvasLayoutUpdate

router = APIRouter()


@router.get("/api/projects/{project_id}/canvas-layout")
def get_canvas_layout(project_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM canvas_layout WHERE project_id = ?", (project_id,)).fetchone()
    conn.close()
    if not row:
        return {"project_id": project_id, "viewport_x": 0, "viewport_y": 0, "zoom": 1.0, "timeline_y": "{}"}
    return dict(row)


@router.put("/api/projects/{project_id}/canvas-layout")
def update_canvas_layout(project_id: str, req: CanvasLayoutUpdate):
    conn = get_connection()
    existing = conn.execute("SELECT project_id FROM canvas_layout WHERE project_id = ?",
                            (project_id,)).fetchone()

    updates = {}
    if req.viewport_x is not None: updates["viewport_x"] = req.viewport_x
    if req.viewport_y is not None: updates["viewport_y"] = req.viewport_y
    if req.zoom is not None: updates["zoom"] = req.zoom
    if req.timeline_y is not None: updates["timeline_y"] = req.timeline_y
    updates["updated_at"] = "datetime('now')"

    if existing:
        set_clause = ", ".join(f"{k} = ?" for k in updates if k != "updated_at")
        set_clause += ", updated_at = datetime('now')"
        values = [v for k, v in updates.items() if k != "updated_at"]
        values.append(project_id)
        conn.execute(f"UPDATE canvas_layout SET {set_clause} WHERE project_id = ?", values)
    else:
        keys = ", ".join(updates.keys() if "updated_at" not in updates else updates.keys())
        placeholders = ", ".join("?" for _ in updates)
        values = list(updates.values())
        values.insert(0, project_id)
        conn.execute(f"INSERT INTO canvas_layout (project_id, {keys}) VALUES (?, {placeholders})", values)

    conn.commit()
    conn.close()
    return {"message": "布局已保存"}
