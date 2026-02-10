from datetime import datetime, timezone, timedelta
from decidrx.db import Database


def test_view_shows_task_and_subtask_details(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_view.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)

    parent = db.add_task("View Parent", now + timedelta(days=2), description="Parent full description\nLine2", duration=30, reward=3, penalty=1, effort=2, type="deep")
    c1 = db.add_task("View Child 1", None, description="Child one detailed description", duration=10, reward=1, parent_id=parent)

    from decidrx import cli
    printed = []

    def fake_print(obj, *args, **kwargs):
        from rich.console import Console
        c = Console(record=True)
        c.print(obj)
        printed.append(c.export_text())

    monkeypatch.setattr(cli.console, "print", fake_print)

    from decidrx.cli import build_parser, cmd_view

    args = build_parser().parse_args(["view", str(parent)])
    cmd_view(args)

    text = "\n".join(s for s in printed if isinstance(s, str))
    assert "Parent full description" in text
    assert "View Child 1" in text
    assert "Child one detailed description" in text


def test_view_nonexistent_task_shows_message(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_view2.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    from decidrx import cli
    printed = []

    def fake_print(obj, *args, **kwargs):
        from rich.console import Console
        c = Console(record=True)
        c.print(obj)
        printed.append(c.export_text())

    monkeypatch.setattr(cli.console, "print", fake_print)

    from decidrx.cli import build_parser, cmd_view

    args = build_parser().parse_args(["view", "999"])  # non-existent
    cmd_view(args)

    text = "\n".join(s for s in printed if isinstance(s, str))
    assert "No task with id 999" in text
