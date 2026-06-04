from datetime import datetime, timezone
import re

ESCALATION_TERMS = ["urgent", "escalat", "critical", "asap", "blocked", "overdue", "breach", "risk"]
IMPORTANT_SENDERS = ["manager", "director", "vp", "chief", "legal", "procurement"]


def score_task(task: dict, email: dict | None = None) -> tuple[float, str, list[str]]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    score = 20.0
    reasons: list[str] = []
    due = task.get("due_date")
    if isinstance(due, str):
        try:
            due = datetime.fromisoformat(due.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            due = None
    if due:
        days = (due - now).days
        if days < 0:
            score += 35; reasons.append("Task is overdue")
        elif days <= 1:
            score += 30; reasons.append("Due within 24 hours")
        elif days <= 3:
            score += 20; reasons.append("Due in the next 3 days")
        elif days <= 7:
            score += 10; reasons.append("Due this week")
    text = " ".join([str(task.get(k, "")) for k in ["title", "description", "required_action"]] + [str((email or {}).get(k, "")) for k in ["sender", "subject", "body_preview"]]).lower()
    hits = [term for term in ESCALATION_TERMS if term in text]
    if hits:
        score += min(25, 8 * len(hits)); reasons.append("Escalation language detected")
    if any(s in text for s in IMPORTANT_SENDERS):
        score += 15; reasons.append("Important stakeholder involved")
    if task.get("category") in {"Escalation", "Approval Required", "Contract Review"}:
        score += 12; reasons.append(f"Business critical category: {task.get('category')}")
    impact_words = re.findall(r"\b(contract|supplier|customer|revenue|compliance|renewal|rfq|penalty)\b", text)
    if impact_words:
        score += min(15, len(set(impact_words)) * 5); reasons.append("Business impact terms detected")
    score = max(0, min(100, round(score, 1)))
    level = "Critical" if score >= 85 else "High" if score >= 70 else "Medium" if score >= 40 else "Low"
    if not reasons:
        reasons.append("Routine task with no urgent indicators")
    return score, level, reasons
