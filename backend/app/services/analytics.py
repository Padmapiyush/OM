from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import Task, TaskStatus


def dashboard(db: Session) -> dict:
    now = datetime.utcnow()
    tasks = db.query(Task).all()
    total = len(tasks)
    completed = len([t for t in tasks if t.status == TaskStatus.completed.value])
    pending = len([t for t in tasks if t.status != TaskStatus.completed.value])
    overdue = len([t for t in tasks if t.due_date and t.due_date < now and t.status != TaskStatus.completed.value])
    resolved = [((t.completed_at - t.created_at).total_seconds() / 3600) for t in tasks if t.completed_at]
    trend = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        count = db.query(func.count(Task.id)).filter(func.date(Task.completed_at) == str(day)).scalar() or 0
        trend.append({"date": str(day), "completed": count})
    focus = db.query(Task).filter(Task.status != TaskStatus.completed.value).order_by(Task.priority_score.desc(), Task.due_date.asc().nullslast(), Task.created_at.asc()).limit(3).all()
    buckets = {"0-3 Days": 0, "4-7 Days": 0, "8-15 Days": 0, "15+ Days": 0}
    for task in tasks:
        if task.status == TaskStatus.completed.value:
            continue
        age = (now - task.created_at).days
        buckets["0-3 Days" if age <= 3 else "4-7 Days" if age <= 7 else "8-15 Days" if age <= 15 else "15+ Days"] += 1
    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "pending_tasks": pending,
        "overdue_tasks": overdue,
        "completion_rate": round((completed / total * 100) if total else 0, 1),
        "average_resolution_hours": round(sum(resolved) / len(resolved), 1) if resolved else 0,
        "weekly_productivity_trend": trend,
        "today_focus": focus,
        "workload_minutes": sum(t.estimated_effort_minutes for t in focus),
        "aging_buckets": buckets,
    }
