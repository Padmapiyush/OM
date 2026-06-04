from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

CATEGORIES = ["Contract Review", "Approval Required", "Supplier Follow-up", "Escalation", "RFQ", "Meeting Action", "Internal Task", "Information Request"]


class EmailIn(BaseModel):
    graph_id: str
    conversation_id: str | None = None
    folder: str = "Inbox"
    sender: str | None = None
    subject: str = ""
    body_preview: str | None = None
    body: str | None = None
    attachments: list[dict] = Field(default_factory=list)
    received_at: datetime | None = None
    sent_at: datetime | None = None
    is_read: bool = False


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    due_date: datetime | None
    suggested_owner: str | None
    category: str
    required_action: str
    estimated_effort_minutes: int
    priority_score: float
    priority_level: str
    priority_reasoning: list[str]
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DashboardOut(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    completion_rate: float
    average_resolution_hours: float
    weekly_productivity_trend: list[dict]
    today_focus: list[TaskOut]
    workload_minutes: int
    aging_buckets: dict[str, int]


class DraftRequest(BaseModel):
    conversation_id: str | None = None
    email_id: int | None = None
    mode: str = "Professional"
    user_intent: str | None = None


class DraftResponse(BaseModel):
    draft: str
    requires_user_approval: bool = True
