from datetime import datetime, timezone, timedelta
from decidrx.scoring import score_task


def test_score_urgency_and_quickness():
    now = datetime.now(timezone.utc)
    task_urgent = {
        "deadline": (now + timedelta(hours=2)).isoformat(),
        "duration": 30,
        "reward": 5,
        "penalty": 2,
        "created_at": (now - timedelta(hours=1)).isoformat(),
    }
    task_later = {
        "deadline": (now + timedelta(days=5)).isoformat(),
        "duration": 30,
        "reward": 5,
        "penalty": 2,
        "created_at": (now - timedelta(hours=1)).isoformat(),
    }
    s1 = score_task(task_urgent, now)
    s2 = score_task(task_later, now)
    assert s1 > s2


def test_quick_win_boosts_short_tasks():
    now = datetime.now(timezone.utc)
    task_short = {"deadline": None, "duration": 5, "reward": 1, "penalty": 0, "created_at": now.isoformat()}
    task_long = {"deadline": None, "duration": 60, "reward": 1, "penalty": 0, "created_at": now.isoformat()}
    assert score_task(task_short, now) > score_task(task_long, now)


def test_parent_aggregation_improves_score():
    now = datetime.now(timezone.utc)
    parent = {"deadline": None, "duration": 5, "reward": 1, "penalty": 0, "created_at": now.isoformat()}
    child1 = {"deadline": None, "duration": 10, "reward": 2, "penalty": 0, "created_at": now.isoformat()}
    child2 = {"deadline": None, "duration": 10, "reward": 2, "penalty": 0, "created_at": now.isoformat()}

    from decidrx.scoring import aggregate_task_for_scoring

    agg = aggregate_task_for_scoring(parent, [child1, child2])
    s_parent = score_task(parent, now)
    s_agg = score_task(agg, now)
    s_child1 = score_task(child1, now)
    s_child2 = score_task(child2, now)

    # aggregated parent should have higher score than individual children and parent alone
    assert s_agg > max(s_child1, s_child2)
    assert s_agg > s_parent
