from datetime import datetime, timezone, timedelta
from decidrx.db import Database


def test_now_shows_aggregated_marker(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_now_agg.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)

    parent = db.add_task("Parent Now", None, duration=5, reward=1, penalty=0, effort=1, type="shallow")
    c1 = db.add_task("Child Now 1", None, duration=10, reward=2, penalty=0, effort=1, type="shallow", parent_id=parent)
    c2 = db.add_task("Child Now 2", None, duration=10, reward=2, penalty=0, effort=1, type="shallow", parent_id=parent)

    from decidrx import cli
    printed = []

    def fake_print(obj, *args, **kwargs):
        from rich.console import Console
        c = Console(record=True)
        c.print(obj)
        printed.append(c.export_text())

    monkeypatch.setattr(cli.console, "print", fake_print)

    from decidrx.cli import build_parser, cmd_now

    args = build_parser().parse_args(["now"])
    cmd_now(args)

    text = "\n".join(s for s in printed if isinstance(s, str))
    # the aggregated parent row should include the "(agg)" marker
    assert "(agg)" in text
    # ensure parent id is present as well
    assert str(parent) in text
