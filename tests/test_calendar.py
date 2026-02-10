from datetime import datetime, timedelta, timezone
from decidrx.db import Database
import os
from decidrx import cli


def fake_printer_capture(monkeypatch, printed):
    def fake_print(obj, *args, **kwargs):
        from rich.console import Console
        c = Console(record=True)
        c.print(obj)
        printed.append(c.export_text())
    monkeypatch.setattr(cli.console, "print", fake_print)


def test_blocked_day_crud(tmp_path):
    dbfile = tmp_path / "test_cal.db"
    os.environ["DECIDRX_DB"] = str(dbfile)
    db = Database(str(dbfile))

    # add blocked day
    rid = db.add_blocked_day("2026-02-14", reason="Valentine's")
    assert isinstance(rid, int)

    # query month
    rows = db.get_blocked_days_in_month(2026, 2)
    assert any(r["date"] == "2026-02-14" for r in rows)

    # remove
    n = db.remove_blocked_day("2026-02-14")
    assert n == 1
    rows2 = db.get_blocked_days_in_month(2026, 2)
    assert not any(r["date"] == "2026-02-14" for r in rows2)


def test_calendar_month_render_and_show(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_cal2.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))

    # create tasks on Feb 10 and Feb 10 again, and Feb 14
    now = datetime.now(timezone.utc)
    # deadlines are stored as aware datetimes
    t1 = db.add_task("Task A", now + timedelta(days=5), description="A")
    t2 = db.add_task("Task B", now + timedelta(days=5), description="B")
    t3 = db.add_task("Task C", now + timedelta(days=9), description="C")

    # Add blocked day Feb 14
    db.add_blocked_day((now + timedelta(days=9)).date().isoformat(), reason="Off")

    printed = []
    fake_printer_capture(monkeypatch, printed)

    # call calendar for the month of the tasks
    from decidrx.cli import build_parser
    args = build_parser().parse_args(["calendar", str((now + timedelta(days=5)).year), str((now + timedelta(days=5)).month)])
    from decidrx.commands.calendar import cmd_calendar
    cmd_calendar(args)

    # output should contain the month title and day numbers and a legend
    output = "\n".join(printed)
    expected = f"Calendar: {(now + timedelta(days=5)).year}-{(now + timedelta(days=5)).month:02d}"
    assert expected in output
    # there should be an indicator for at least one day with tasks (the count in parentheses)
    assert "(" in output or "🔒" in output

    printed.clear()
    # show for specific date (day of t3)
    day_str = (now + timedelta(days=9)).date().isoformat()
    args2 = build_parser().parse_args(["calendar", "show", day_str])
    cmd_calendar(args2)
    out2 = "\n".join(printed)
    assert "Blocked" in out2
    assert "Task" in out2


def test_exclude_completed_by_default(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_cal4.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))

    now = datetime.now(timezone.utc)
    day = (now + timedelta(days=7)).date().isoformat()
    # create two tasks same day
    t1 = db.add_task("Done Task", now + timedelta(days=7), description="done")
    t2 = db.add_task("Open Task", now + timedelta(days=7), description="open")
    # mark first done
    db.mark_done(t1)

    printed = []
    fake_printer_capture(monkeypatch, printed)

    from decidrx.cli import build_parser
    # default behavior (no --all) should NOT show completed task
    args = build_parser().parse_args(["calendar", "show", day])
    from decidrx.commands.calendar import cmd_calendar
    cmd_calendar(args)
    out = "\n".join(printed)
    assert "Done Task" not in out
    assert "Open Task" in out

    printed.clear()
    # with --all flag provided before subcommand, completed tasks should be included
    args2 = build_parser().parse_args(["calendar", "--all", "show", day])
    cmd_calendar(args2)
    out2 = "\n".join(printed)
    assert "Done Task" in out2
    assert "Open Task" in out2


def test_bad_alias_subcommands(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_cal3.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))

    printed = []
    fake_printer_capture(monkeypatch, printed)

    # add a bad day via alias
    from decidrx.cli import build_parser
    args = build_parser().parse_args(["calendar", "bad", "add", "2026-03-01", "--reason", "Travel"])
    from decidrx.commands.calendar import cmd_calendar
    cmd_calendar(args)
    out = "\n".join(printed)
    assert "Added bad day" in out

    printed.clear()
    # list bad days
    args2 = build_parser().parse_args(["calendar", "bad", "list"])
    cmd_calendar(args2)
    out2 = "\n".join(printed)
    assert "2026-03-01" in out2

    printed.clear()
    # remove it
    args3 = build_parser().parse_args(["calendar", "bad", "remove", "2026-03-01"])
    cmd_calendar(args3)
    out3 = "\n".join(printed)
    assert "Removed bad day" in out3

    printed.clear()
    # list to confirm removal
    args4 = build_parser().parse_args(["calendar", "bad", "list"])
    cmd_calendar(args4)
    out4 = "\n".join(printed)
    assert "2026-03-01" not in out4


def test_help_shows_bad(monkeypatch):
    printed = []
    fake_printer_capture(monkeypatch, printed)

    from decidrx.cli import build_parser, cmd_help
    args = build_parser().parse_args(["help", "calendar"])
    cmd_help(args)
    out = "\n".join(printed)
    assert "bad add" in out or "bad" in out
