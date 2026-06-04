from datetime import datetime, timedelta
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from app.models.schemas import CATEGORIES
from app.services.ollama import OllamaClient
from app.services.priority import score_task


class MailState(TypedDict, total=False):
    email: dict[str, Any]
    classification: dict[str, Any]
    task: dict[str, Any]
    pendency: dict[str, Any]
    draft: str


def _fallback_task(email: dict[str, Any]) -> dict[str, Any]:
    subject = email.get("subject") or "Mailbox action"
    text = f"{subject} {email.get('body_preview') or email.get('body') or ''}".lower()
    category = "Information Request"
    for candidate in CATEGORIES:
        if candidate.lower().split()[0] in text:
            category = candidate
            break
    if "approve" in text:
        category = "Approval Required"
    if "contract" in text:
        category = "Contract Review"
    if "rfq" in text or "quotation" in text:
        category = "RFQ"
    if "urgent" in text or "escalat" in text:
        category = "Escalation"
    return {
        "title": subject[:180],
        "description": email.get("body_preview") or "Review email thread and determine next action.",
        "due_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
        "suggested_owner": "Me",
        "category": category,
        "required_action": "Review and respond or complete the requested action.",
        "estimated_effort_minutes": 30,
    }


async def classify_email(state: MailState) -> MailState:
    email = state["email"]
    prompt = f"Classify this email for work management. Return JSON with category and sentiment. Categories: {CATEGORIES}. Email: {email}"
    result = await OllamaClient().generate_json(prompt, {"category": _fallback_task(email)["category"], "sentiment": "neutral"})
    return {**state, "classification": result}


async def extract_task(state: MailState) -> MailState:
    email = state["email"]
    prompt = f"Extract one actionable task from this Outlook email as JSON with title, description, due_date ISO or null, suggested_owner, category, required_action, estimated_effort_minutes. Categories: {CATEGORIES}. Email: {email}"
    task = await OllamaClient().generate_json(prompt, _fallback_task(email))
    fallback = _fallback_task(email)
    for key, value in fallback.items():
        task.setdefault(key, value)
    if task.get("category") not in CATEGORIES:
        task["category"] = state.get("classification", {}).get("category") or fallback["category"]
    return {**state, "task": task}


async def score_priority(state: MailState) -> MailState:
    task = dict(state["task"])
    score, level, reasons = score_task(task, state.get("email"))
    task.update(priority_score=score, priority_level=level, priority_reasoning=reasons)
    return {**state, "task": task}


async def analyze_pendency(state: MailState) -> MailState:
    email = state["email"]
    received = email.get("received_at")
    age_days = 0
    if received:
        if isinstance(received, str):
            received = datetime.fromisoformat(received.replace("Z", "+00:00")).replace(tzinfo=None)
        age_days = max(0, (datetime.utcnow() - received).days)
    bucket = "0-3 Days" if age_days <= 3 else "4-7 Days" if age_days <= 7 else "8-15 Days" if age_days <= 15 else "15+ Days"
    risk = "High" if age_days > 15 else "Medium" if age_days > 7 else "Low"
    return {**state, "pendency": {"age_days": age_days, "bucket": bucket, "risk": risk}}


def build_mail_workflow():
    graph = StateGraph(MailState)
    graph.add_node("classification", classify_email)
    graph.add_node("task_extraction", extract_task)
    graph.add_node("priority_scoring", score_priority)
    graph.add_node("pendency_analysis", analyze_pendency)
    graph.set_entry_point("classification")
    graph.add_edge("classification", "task_extraction")
    graph.add_edge("task_extraction", "priority_scoring")
    graph.add_edge("priority_scoring", "pendency_analysis")
    graph.add_edge("pendency_analysis", END)
    return graph.compile()


async def draft_reply(email_thread: str, mode: str, user_intent: str | None = None) -> str:
    prompt = f"Write a {mode} Outlook draft reply. Do not claim it was sent. Include only the draft body. Intent: {user_intent or 'respond appropriately'} Thread: {email_thread}"
    return await OllamaClient().generate_text(prompt, "Thank you for the update. I will review the details and respond with the next steps shortly.")
