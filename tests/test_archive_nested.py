from datetime import datetime, timezone, timedelta
from decidrx.db import Database


def test_archive_nested_display(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_archive_nested.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)

    parent = db.add_task("Parent Archive", now + timedelta(days=2), duration=10, reward=1, penalty=0, effort=1, type="shallow")
    child = db.add_task("Child Archive", None, duration=5, reward=1, penalty=0, effort=1, type="shallow", parent_id=parent)

    from decidrx import cli
    printed = []

    def fake_print(obj, *args, **kwargs):
        from rich.console import Console
        c = Console(record=True)
        c.print(obj)
        printed.append(c.export_text())

    monkeypatch.setattr(cli.console, "print", fake_print)

    from decidrx.cli import build_parser, cmd_archive

    args = build_parser().parse_args(["archive"])
    cmd_archive(args)

    text = "\n".join(s for s in printed if isinstance(s, str))
    # verify parent/child ids and tree connector are present
    assert str(parent) in text
    assert str(child) in text
    import re
    assert re.search(r"[├└]", text)