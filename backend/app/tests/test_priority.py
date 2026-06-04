from app.services.priority import score_task


def test_escalation_due_soon_scores_critical():
    task = {"title": "Urgent contract escalation", "category": "Escalation", "description": "Manager says supplier breach risk", "required_action": "Respond ASAP", "due_date": "2099-01-01T00:00:00"}
    score, level, reasons = score_task(task, {"sender": "legal director@example.com"})
    assert score >= 70
    assert level in {"High", "Critical"}
    assert reasons
