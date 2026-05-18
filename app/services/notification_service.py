from app.audit.logs import log_action
from app.tasks.email_tasks import send_email


async def _enqueue_email(to_email: str | None, subject: str, body: str, event_type: str, user_id: str, metadata: dict | None = None) -> None:
    details = {
        "event_type": event_type,
        "to_email": to_email,
        "subject": subject,
        **(metadata or {}),
    }

    if not to_email:
        await log_action(
            user_id=user_id,
            action="EMAIL_NOTIFICATION_SKIPPED",
            details={**details, "reason": "Missing recipient email"},
        )
        return

    try:
        result = send_email.delay(to_email, subject, body, event_type, metadata or {})
        await log_action(
            user_id=user_id,
            action="EMAIL_NOTIFICATION_QUEUED",
            details={**details, "task_id": result.id},
        )
    except Exception as exc:
        await log_action(
            user_id=user_id,
            action="EMAIL_NOTIFICATION_QUEUE_FAILED",
            details={**details, "error": str(exc)},
        )


async def notify_goals_submitted(manager_email: str | None, employee_name: str, goal_titles: list[str], user_id: str, metadata: dict | None = None) -> None:
    titles = "\n".join(f"- {title}" for title in goal_titles)
    await _enqueue_email(
        manager_email,
        f"Goals submitted for review by {employee_name}",
        (
            f"{employee_name} submitted {len(goal_titles)} goal(s) for review.\n\n"
            f"{titles}\n\n"
            "Please review them in NorthStar."
        ),
        event_type="GOALS_SUBMITTED",
        user_id=user_id,
        metadata=metadata,
    )


async def notify_goal_approved(employee_email: str | None, goal_title: str, manager_name: str, user_id: str, metadata: dict | None = None) -> None:
    await _enqueue_email(
        employee_email,
        f"Goal approved: {goal_title}",
        (
            f"Your goal \"{goal_title}\" was approved by {manager_name}.\n\n"
            "The goal is now locked for quarterly check-ins."
        ),
        event_type="GOAL_APPROVED",
        user_id=user_id,
        metadata=metadata,
    )


async def notify_goal_returned(employee_email: str | None, goal_title: str, manager_name: str, manager_note: str | None, user_id: str, metadata: dict | None = None) -> None:
    note = f"\n\nManager note:\n{manager_note}" if manager_note else ""
    await _enqueue_email(
        employee_email,
        f"Goal returned for revision: {goal_title}",
        (
            f"Your goal \"{goal_title}\" was returned by {manager_name} for revision."
            f"{note}\n\n"
            "Please update and resubmit it in NorthStar."
        ),
        event_type="GOAL_RETURNED",
        user_id=user_id,
        metadata=metadata,
    )
