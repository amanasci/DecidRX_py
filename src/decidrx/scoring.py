from datetime import datetime, timezone


def score_task(task: dict, now: datetime = None) -> float:
    """Calculate score according to PRD v0 formula.

    task: expects keys 'deadline' (ISO string or None), 'duration' (int), 'reward', 'penalty', 'created_at' (ISO string)
    """
    now = now or datetime.now(timezone.utc)

    # parse times
    deadline = None
    if task.get("deadline"):
        try:
            deadline = datetime.fromisoformat(task["deadline"]).replace(tzinfo=timezone.utc)
        except Exception:
            deadline = None
    created = None
    if task.get("created_at"):
        try:
            created = datetime.fromisoformat(task["created_at"]).replace(tzinfo=timezone.utc)
        except Exception:
            created = now
    else:
        created = now

    # hours_left
    if deadline:
        hours_left = (deadline - now).total_seconds() / 3600.0
    else:
        hours_left = 24 * 365  # effectively very low urgency

    urgency = 1.0 / max(hours_left, 1.0)
    value = (task.get("reward", 0) or 0) + (task.get("penalty", 0) or 0)
    duration = task.get("duration") or 1
    quick_win = 1.0 / max(duration, 1)
    age = ((now - created).total_seconds() / 3600.0) / 24.0

    score = urgency * value + quick_win + age
    return float(score)
