from pydantic import BaseModel
from typing import Any, Optional, List
from datetime import datetime


class ProjectCreate(BaseModel):
    title: str
    genre: Optional[str] = None
    story_cards: Optional[str] = None
    style_sig: Optional[str] = None
    omniscient: Optional[str] = None
    chapter_count: Optional[int] = 30


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    genre: Optional[str] = None
    style_sig: Optional[str] = None
    omniscient: Optional[str] = None
    chapter_count: Optional[int] = None


class BlockBase(BaseModel):
    type: str
    canvas_x: float = 0
    canvas_y: float = 0
    canvas_w: float = 280
    collapsed: bool = False
    color: Optional[str] = None
    timeline_id: Optional[str] = None
    chapter_pos: Optional[str] = None
    tags: List[str] = []
    notes: str = ""
    content: dict = {}
    is_draft: bool = False


class BlockCreate(BlockBase):
    pass


class BlockUpdate(BaseModel):
    canvas_x: Optional[float] = None
    canvas_y: Optional[float] = None
    canvas_w: Optional[float] = None
    collapsed: Optional[bool] = None
    color: Optional[str] = None
    timeline_id: Optional[str] = None
    chapter_pos: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    content: Optional[dict] = None
    is_draft: Optional[bool] = None
    on_canvas: Optional[bool] = None


class BlockResponse(BlockBase):
    id: str
    project_id: str
    completeness: float
    created_at: str
    updated_at: str


class ConnectionCreate(BaseModel):
    from_block: str
    to_block: str
    conn_type: str
    label: Optional[str] = None
    chapter_hint: Optional[str] = None


class ConnectionUpdate(BaseModel):
    conn_type: Optional[str] = None
    label: Optional[str] = None
    chapter_hint: Optional[str] = None


class ConnectionResponse(BaseModel):
    id: str
    project_id: str
    from_block: str
    to_block: str
    conn_type: str
    label: Optional[str] = None
    chapter_hint: Optional[str] = None
    created_at: str


class CanvasLayoutUpdate(BaseModel):
    viewport_x: Optional[float] = None
    viewport_y: Optional[float] = None
    zoom: Optional[float] = None
    timeline_y: Optional[str] = None


class GenerateOutlineRequest(BaseModel):
    chapter_num: int
    additional_instructions: str = ""


class GenerateContentRequest(BaseModel):
    chapter_num: int
    outline_confirmed: bool = True
    block_id: Optional[str] = None  # 指定使用的 CHAPTER_DETAIL 块ID
    save_only: Optional[bool] = False  # 仅保存正文，不运行管线
    content: Optional[str] = None  # save_only=True 时要保存的正文字


class GenerateBlockContentRequest(BaseModel):
    block_id: str
    field: str
    hint: str = ""

class RewriteContentRequest(BaseModel):
    chapter_num: int
    selected_text: str = ""
    instruction: str = ""
    issue: Optional[str] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None


class ApplyStoryCardsRequest(BaseModel):
    primary: str
    secondary: List[str] = []


class ChapterOutlineResponse(BaseModel):
    chapter_num: int
    outline: str
