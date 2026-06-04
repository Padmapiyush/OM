from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.agents.workflows import build_mail_workflow, draft_reply
from app.db.models import EmailMessage, Task, Setting, TaskStatus
from app.db.session import get_db
from app.models.schemas import EmailIn, TaskOut, DashboardOut, DraftRequest, DraftResponse
from app.services.analytics import dashboard
from app.services.graph import GraphClient

router = APIRouter()
workflow = build_mail_workflow()


@router.post("/emails/ingest", response_model=TaskOut)
async def ingest_email(email: EmailIn, db: Session = Depends(get_db)):
    existing = db.query(EmailMessage).filter(EmailMessage.graph_id == email.graph_id).first()
    if existing:
        message = existing
    else:
        message = EmailMessage(**email.model_dump())
        db.add(message); db.commit(); db.refresh(message)
    result = await workflow.ainvoke({"email": email.model_dump(mode="json")})
    extracted = result["task"]
    task = Task(email_id=message.id, **{k: extracted[k] for k in ["title", "description", "suggested_owner", "category", "required_action", "estimated_effort_minutes", "priority_score", "priority_level", "priority_reasoning"]}, due_date=_parse_dt(extracted.get("due_date")))
    db.add(task); db.commit(); db.refresh(task)
    return task


@router.get("/mail-folders")
async def list_mail_folders(include_hidden: bool = False, authorization: str | None = Header(default=None)):
    client = _graph_client_from_header(authorization)
    folders = await client.list_folders(include_hidden=include_hidden)
    return [folder.as_dict() for folder in folders]


@router.post("/sync/graph")
async def sync_graph(folder: str = "Inbox", include_subfolders: bool = True, top_per_folder: int = 25, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    client = _graph_client_from_header(authorization)
    try:
        messages = await (
            client.list_messages_recursive(folder, top_per_folder=top_per_folder)
            if include_subfolders
            else client.list_messages(folder=folder, top=top_per_folder)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    created = 0
    for raw in messages:
        if not db.query(EmailMessage).filter(EmailMessage.graph_id == raw["graph_id"]).first():
            db.add(EmailMessage(**raw)); created += 1
    db.commit()
    return {"folder": folder, "include_subfolders": include_subfolders, "messages_seen": len(messages), "messages_created": created}


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Task)
    if status:
        q = q.filter(Task.status == status)
    return q.order_by(Task.priority_score.desc(), Task.due_date.asc().nullslast()).all()


@router.patch("/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = TaskStatus.completed.value
    task.completed_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()
    db.commit(); db.refresh(task)
    return task


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    return dashboard(db)


@router.post("/draft", response_model=DraftResponse)
async def create_draft(request: DraftRequest, db: Session = Depends(get_db)):
    q = db.query(EmailMessage)
    if request.email_id:
        q = q.filter(EmailMessage.id == request.email_id)
    elif request.conversation_id:
        q = q.filter(EmailMessage.conversation_id == request.conversation_id)
    messages = q.order_by(EmailMessage.received_at.asc().nullslast()).all()
    thread = "\n\n".join([f"From: {m.sender}\nSubject: {m.subject}\n{m.body or m.body_preview or ''}" for m in messages])
    if not thread:
        raise HTTPException(status_code=404, detail="Email thread not found")
    return DraftResponse(draft=await draft_reply(thread, request.mode, request.user_intent))


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return {s.key: s.value for s in db.query(Setting).all()}


@router.put("/settings/{key}")
def put_setting(key: str, value: dict, db: Session = Depends(get_db)):
    setting = db.get(Setting, key) or Setting(key=key, value={})
    setting.value = value
    setting.updated_at = datetime.utcnow()
    db.merge(setting); db.commit()
    return {key: value}


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _graph_client_from_header(authorization: str | None) -> GraphClient:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer Microsoft Graph token required")
    return GraphClient(authorization.split(" ", 1)[1])
