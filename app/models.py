from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

Category = Literal["tactics", "strategy", "openings", "endgames", "analysis"]
State = Literal["todo", "in_progress", "done", "skipped", "snoozed"]

class TaskIn(BaseModel):
    title: str
    category: Category
    estimated_minutes: int = Field(ge=1, le=240)
    due_at: Optional[datetime] = None

class TaskDB(TaskIn):
    id: str
    user_id: str
    state: State = "todo"
    created_at: datetime
    completed_at: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    material_id: Optional[str] = None
    priority: int = 50

class TaskPatch(BaseModel):
    state: Optional[State] = None
    snoozed_until: Optional[datetime] = None

class ProgressEvent(BaseModel):
    user_id: str
    task_id: str
    type: Literal["completed", "started", "skipped"]
    timestamp: datetime
    duration_minutes: Optional[int] = None

class RecoItem(BaseModel):
    task_id: str
    score: float
    reason: str

class RecoResponse(BaseModel):
    items: list[RecoItem]
