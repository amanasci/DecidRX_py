from datetime import datetime, timezone, timedelta
from decidrx.db import Database


def test_description_roundtrip(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_desc.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    tid = db.add_task("Task with desc", now + timedelta(days=1), description="this is a test description", duration=10)
    t = db.get_task(tid)
    assert t["description"] == "this is a test description"
