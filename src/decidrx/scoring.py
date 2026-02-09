from datetime import datetime, timezone
from typing import List, Dict, Optional


def aggregate_task_for_scoring(task: Dict, children: List[Dict]) -> Dict:
    """Return an aggregated task dict that combines parent and its children for scoring.

    - duration/reward/penalty are summed
    - deadline is the earliest (minimum) non-null deadline among parent+children
    - created_at is the earliest created_at among parent+children
    """
    agg = dict(task)  # shallow copy
    total_duration = agg.get("duration") or 0
    total_reward = agg.get("reward") or 0
    total_penalty = agg.get("penalty") or 0
    deadlines = []
    createds = []

    if agg.get("deadline"):
        deadlines.append(agg["deadline"])
    if agg.get("created_at"):
        createds.append(agg["created_at"])

    for c in children:
        total_duration += c.get("duration") or 0
        total_reward += c.get("reward") or 0
        total_penalty += c.get("penalty") or 0
        if c.get("deadline"):
            deadlines.append(c["deadline"])
        if c.get("created_at"):
            createds.append(c["created_at"])

    agg["duration"] = total_duration
    agg["reward"] = total_reward
    agg["penalty"] = total_penalty

    # compute combined quick_win as sum of individual quick wins (1/duration)
    quick_sum = 0.0
    try:
        # include parent
        quick_sum += 1.0 / max(agg.get("duration") or 1, 1)
    except Exception:
        pass
    # better: compute per-item quick_win (parent + each child)
    quick_sum = 0.0
    try:
        pdur = task.get("duration") or 0
        if pdur > 0:
            quick_sum += 1.0 / max(pdur, 1)
    except Exception:
        pass
    for c in children:
        cd = c.get("duration") or 0
        if cd > 0:
            quick_sum += 1.0 / max(cd, 1)
    agg["_quick_win"] = quick_sum

    # pick earliest deadline (minimum datetime)
    earliest_deadline: Optional[str] = None
    if deadlines:
        try:
            parsed = []
            for d in deadlines:
                try:
                    parsed.append(datetime.fromisoformat(d))
                except Exception:
                    pass
            if parsed:
                earliest = min(parsed)
                earliest_deadline = earliest.isoformat()
        except Exception:
            earliest_deadline = None
    agg["deadline"] = earliest_deadline

    # pick earliest created_at
    earliest_created: Optional[str] = None
    if createds:
        try:
            parsed = []
            for d in createds:
                try:
                    parsed.append(datetime.fromisoformat(d))
                except Exception:
                    pass
            if parsed:
                earliest = min(parsed)
                earliest_created = earliest.isoformat()
        except Exception:
            earliest_created = None
    if earliest_created:
        agg["created_at"] = earliest_created

    # marker so callers can detect aggregated value if desired
    agg["_aggregated"] = True
    return agg


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
    # allow callers to inject a precomputed quick_win (sum of per-item 1/duration), used for aggregated parents
    if task.get("_quick_win") is not None:
        quick_win = float(task["_quick_win"])
    else:
        quick_win = 1.0 / max(duration, 1)
    age = ((now - created).total_seconds() / 3600.0) / 24.0

    score = urgency * value + quick_win + age
    return float(score)
