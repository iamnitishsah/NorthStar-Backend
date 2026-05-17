from app.tasks.email_tasks import send_email


def _enqueue_email(to_email: str | None, subject: str, body: str) -> None:
    if not to_email:
        return
    try:
        send_email.delay(to_email, subject, body)
    except Exception:
        return


def notify_goals_submitted(manager_email: str | None, employee_name: str, goal_titles: list[str]) -> None:
    titles = "\n".join(f"- {title}" for title in goal_titles)
    _enqueue_email(
        manager_email,
        f"Goals submitted for review by {employee_name}",
        (
            f"{employee_name} submitted {len(goal_titles)} goal(s) for review.\n\n"
            f"{titles}\n\n"
            "Please review them in NorthStar."
        ),
    )


def notify_goal_approved(employee_email: str | None, goal_title: str, manager_name: str) -> None:
    _enqueue_email(
        employee_email,
        f"Goal approved: {goal_title}",
        (
            f"Your goal \"{goal_title}\" was approved by {manager_name}.\n\n"
            "The goal is now locked for quarterly check-ins."
        ),
    )


def notify_goal_returned(employee_email: str | None, goal_title: str, manager_name: str, manager_note: str | None) -> None:
    note = f"\n\nManager note:\n{manager_note}" if manager_note else ""
    _enqueue_email(
        employee_email,
        f"Goal returned for revision: {goal_title}",
        (
            f"Your goal \"{goal_title}\" was returned by {manager_name} for revision."
            f"{note}\n\n"
            "Please update and resubmit it in NorthStar."
        ),
    )
