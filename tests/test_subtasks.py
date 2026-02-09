import os
import sys
from pathlib import Path
# Ensure local `src` is preferred over any installed package for tests
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from datetime import datetime, timezone, timedelta
from decidrx.db import Database


def test_subtask_creation_and_persistence(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_subtasks.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)

    parent = db.add_task("Parent Task", now + timedelta(days=1), duration=20, reward=2, penalty=0, effort=1, type="shallow")
    child = db.add_task("Child Task", None, duration=10, reward=1, penalty=0, effort=1, type="shallow", parent_id=parent)

    t = db.get_task(child)
    assert t is not None
    assert t["parent_id"] == parent

    children = db.get_children(parent)
    assert len(children) == 1
    assert children[0]["id"] == child


def test_subtask_marking_and_auto_propagation(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_subtasks_marking.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)

    parent = db.add_task("Parent 2", now + timedelta(days=2), duration=10, reward=1, penalty=0, effort=1, type="shallow")
    c1 = db.add_task("Child 1", None, duration=5, reward=1, penalty=0, effort=1, type="shallow", parent_id=parent)
    c2 = db.add_task("Child 2", None, duration=5, reward=1, penalty=0, effort=1, type="shallow", parent_id=parent)

    # mark first child done; parent should remain incomplete
    db.mark_done(c1)
    p = db.get_task(parent)
    assert p["completed"] == 0

    # mark second child done; now parent should be auto-marked done
    db.mark_done(c2)
    p = db.get_task(parent)
    assert p["completed"] == 1
    assert p["completed_at"] is not None

    # undo one child and parent should become undone
    db.mark_undone(c1)
    p = db.get_task(parent)
    assert p["completed"] == 0
    assert p["completed_at"] is None
