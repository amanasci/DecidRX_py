import os
import tempfile
from datetime import datetime, timezone, timedelta
from decidrx.db import Database
from decidrx.scoring import score_task


def test_add_and_now(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    # add two tasks
    id1 = db.add_task("Do urgent", now + timedelta(hours=1), duration=30, reward=5, penalty=2, effort=1, type="shallow")
    id2 = db.add_task("Do later", now + timedelta(days=5), duration=30, reward=5, penalty=2, effort=1, type="shallow")
    tasks = db.get_pending_tasks()
    assert len(tasks) == 2
    scored = [(score_task(dict(t), now), t) for t in tasks]
    scored.sort(key=lambda x: x[0], reverse=True)
    assert scored[0][1]["id"] == id1


def test_add_interactive(tmp_path, monkeypatch):
    # simulate interactive input for add
    dbfile = tmp_path / "test_interactive.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))

    from rich.prompt import Prompt, IntPrompt

    responses = [
        "Interactive Task",  # Title
        "",  # Deadline (blank => none)
        "15",  # Duration
        "4",  # Reward
        "1",  # Penalty
        "2",  # Effort
        "shallow",  # Type
    ]

    def fake_prompt_ask(prompt, default=None):
        return responses.pop(0)

    def fake_int_prompt_ask(prompt, default=None):
        val = responses.pop(0)
        return int(val) if val != "" else default

    monkeypatch.setattr(Prompt, "ask", fake_prompt_ask)
    monkeypatch.setattr(IntPrompt, "ask", fake_int_prompt_ask)

    from decidrx.cli import build_parser, cmd_add

    args = build_parser().parse_args(["add"])
    cmd_add(args)

    db = Database(str(dbfile))
    tasks = db.get_pending_tasks()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Interactive Task"


def test_add_with_args_stays_noninteractive(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_args.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    from decidrx.cli import build_parser, cmd_add

    args = build_parser().parse_args(["add", "Arg Task", "--duration", "10", "--reward", "3"])
    cmd_add(args)

    db = Database(str(dbfile))
    tasks = db.get_pending_tasks()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Arg Task"
    assert tasks[0]["duration"] == 10
    assert tasks[0]["reward"] == 3


def test_help_general_and_command(monkeypatch):
    from decidrx import cli
    from rich.panel import Panel
    printed = []

    def fake_print(obj, *args, **kwargs):
        printed.append(obj)

    monkeypatch.setattr(cli.console, "print", fake_print)

    # general help should print a Panel
    args = cli.build_parser().parse_args(["help"])
    cli.cmd_help(args)
    assert any(isinstance(s, Panel) for s in printed)

    printed.clear()
    # command help should include examples text in panel renderable
    args = cli.build_parser().parse_args(["help", "add"])
    cli.cmd_help(args)
    # find the Panel and inspect renderable text
    panel = next((s for s in printed if isinstance(s, Panel)), None)
    assert panel is not None
    assert "examples:" in str(panel.renderable).lower()
    assert "deadline" in str(panel.renderable).lower()


def test_add_interactive_validation(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_interactive_valid.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))

    from rich.prompt import Prompt, IntPrompt

    # Sequence: title, deadline(blank), duration, reward(invalid=99), reward(valid=5), penalty, effort, type
    responses = [
        "Bad Reward Task",
        "",
        "10",
        "99",
        "5",
        "1",
        "2",
        "shallow",
    ]

    def fake_prompt_ask(prompt, default=None):
        return responses.pop(0)

    def fake_int_prompt_ask(prompt, default=None):
        val = responses.pop(0)
        return int(val) if val != "" else default

    monkeypatch.setattr(Prompt, "ask", fake_prompt_ask)
    monkeypatch.setattr(IntPrompt, "ask", fake_int_prompt_ask)

    from decidrx.cli import build_parser, cmd_add

    args = build_parser().parse_args(["add"])
    cmd_add(args)

    db = Database(str(dbfile))
    tasks = db.get_pending_tasks()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Bad Reward Task"
    assert tasks[0]["reward"] == 5


def test_show_shows_tasks(tmp_path, monkeypatch):
    from rich.table import Table
    dbfile = tmp_path / "test_show.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    id1 = db.add_task("A", now + timedelta(days=1), duration=10, reward=1, penalty=0, effort=1, type="shallow")
    id2 = db.add_task("B", now + timedelta(days=2), duration=20, reward=2, penalty=0, effort=1, type="deep")
    db.mark_done(id2)

    from decidrx import cli
    printed = []

    def fake_print(obj, *args, **kwargs):
        printed.append(obj)

    monkeypatch.setattr(cli.console, "print", fake_print)

    from decidrx.cli import build_parser, cmd_show

    args = build_parser().parse_args(["show"])
    cmd_show(args)
    assert any(isinstance(x, Table) for x in printed)

    printed.clear()
    args = build_parser().parse_args(["show", "--all"])
    cmd_show(args)
    assert any(isinstance(x, Table) for x in printed)


def test_edit_noninteractive(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_edit.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    tid = db.add_task("Old", now + timedelta(days=1), duration=30, reward=3, penalty=1, effort=2, type="shallow")

    from decidrx.cli import build_parser, cmd_edit

    args = build_parser().parse_args(["edit", str(tid), "--title", "New", "--duration", "10", "--reward", "5"])
    cmd_edit(args)

    t = db.get_task(tid)
    assert t["title"] == "New"
    assert t["duration"] == 10
    assert t["reward"] == 5


def test_edit_interactive(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_edit_int.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    tid = db.add_task("Old2", now + timedelta(days=1), duration=20, reward=2, penalty=0, effort=1, type="shallow")

    from rich.prompt import Prompt, IntPrompt

    responses = [
        "New2",  # title
        "",  # deadline keep
        "15",  # duration
        "99",  # reward invalid
        "5",  # reward valid
        "1",  # penalty
        "2",  # effort
        "deep",  # type
    ]

    def fake_prompt_ask(prompt, default=None):
        return responses.pop(0)

    def fake_int_prompt_ask(prompt, default=None):
        # note: duration answered by this too
        val = responses.pop(0)
        return int(val) if val != "" else default

    monkeypatch.setattr(Prompt, "ask", fake_prompt_ask)
    monkeypatch.setattr(IntPrompt, "ask", fake_int_prompt_ask)

    from decidrx.cli import build_parser, cmd_edit

    args = build_parser().parse_args(["edit", str(tid)])
    cmd_edit(args)

    t = db.get_task(tid)
    assert t["title"] == "New2"
    assert t["duration"] == 15
    assert t["reward"] == 5
