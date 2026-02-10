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
        "",  # description (blank)
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

    args = build_parser().parse_args(["add", "Arg Task", "--description", "Short description", "--duration", "10", "--reward", "3"])
    cmd_add(args)

    db = Database(str(dbfile))
    tasks = db.get_pending_tasks()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Arg Task"
    assert tasks[0]["duration"] == 10
    assert tasks[0]["reward"] == 3
    assert tasks[0]["description"] == "Short description"


def test_add_with_parent_noninteractive(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_add_parent.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    from decidrx.cli import build_parser, cmd_add

    db = Database(str(dbfile))
    parent = db.add_task("Parent for CLI", None, duration=5, reward=1, penalty=0, effort=1, type="shallow")

    args = build_parser().parse_args(["add", "Child CLI", "--parent", str(parent)])
    cmd_add(args)

    db2 = Database(str(dbfile))
    tasks = db2.get_pending_tasks()
    # find child
    child = next((t for t in tasks if t["title"] == "Child CLI"), None)
    assert child is not None
    assert child["parent_id"] == parent


def test_edit_set_parent(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_edit_parent.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    from decidrx.cli import build_parser, cmd_edit

    db = Database(str(dbfile))
    parent = db.add_task("Parent Edit", None, duration=5, reward=1, penalty=0, effort=1, type="shallow")
    t = db.add_task("Orphan", None, duration=10, reward=2, penalty=0, effort=1, type="shallow")

    args = build_parser().parse_args(["edit", str(t), "--parent", str(parent)])
    cmd_edit(args)

    updated = db.get_task(t)
    assert updated["parent_id"] == parent


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
        "",  # description (blank)
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


def test_add_interactive_with_subtasks(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_interactive_subtasks.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))

    from rich.prompt import Prompt, IntPrompt, Confirm

    # Parent responses: title, deadline(blank), duration, reward, penalty, effort, description, type
    prompt_responses = [
        "Interactive Parent",  # Title
        "",  # Deadline
        "",  # description (only used by Prompt.ask calls ordering)
        "shallow",  # Type
        # Subtask title
        "Subtask 1",
        "",  # Subtask deadline
        "",  # Subtask description
        "shallow",  # Subtask type
    ]

    # IntPrompt responses: parent duration, reward, penalty, effort then subtask duration, reward, penalty, effort
    int_responses = [
        "15",  # parent duration
        "4",
        "1",
        "2",
        "7",  # subtask duration
        "2",
        "0",
        "1",
    ]

    confirm_responses = [True, False]  # Add subtasks? -> yes; Add another? -> no

    def fake_prompt_ask(prompt, default=None):
        return prompt_responses.pop(0)

    def fake_int_prompt_ask(prompt, default=None):
        val = int_responses.pop(0)
        return int(val) if val != "" else default

    def fake_confirm_ask(prompt, default=None):
        return confirm_responses.pop(0)

    monkeypatch.setattr(Prompt, "ask", fake_prompt_ask)
    monkeypatch.setattr(IntPrompt, "ask", fake_int_prompt_ask)
    monkeypatch.setattr(Confirm, "ask", fake_confirm_ask)

    from decidrx.cli import build_parser, cmd_add

    args = build_parser().parse_args(["add"])
    cmd_add(args)

    db = Database(str(dbfile))
    tasks = db.get_pending_tasks()
    # there should be 2 tasks: parent and subtask
    assert len(tasks) == 2
    parent = next((t for t in tasks if t["title"] == "Interactive Parent"), None)
    child = next((t for t in tasks if t["title"] == "Subtask 1"), None)
    assert parent is not None
    assert child is not None
    assert child["parent_id"] == parent["id"]


def test_subtask_add_via_cli_noninteractive(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_subtask_cli.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    from decidrx.cli import build_parser

    db = Database(str(dbfile))
    parent = db.add_task("Parent CLI", None, duration=5, reward=1, penalty=0, effort=1, type="shallow")

    args = build_parser().parse_args(["subtask", "add", str(parent), "Child CLI", "--duration", "10", "--reward", "2"])
    # invoke command
    from decidrx.commands.subtask import cmd_subtask_add

    cmd_subtask_add(args)

    db2 = Database(str(dbfile))
    tasks = db2.get_pending_tasks()
    child = next((t for t in tasks if t["title"] == "Child CLI"), None)
    assert child is not None
    assert child["parent_id"] == parent


def test_subtask_list_shows_children(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_subtask_list.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    parent = db.add_task("Parent List", None, duration=5, reward=1, penalty=0, effort=1, type="shallow")
    c1 = db.add_task("Child L1", None, duration=5, reward=1, penalty=0, effort=1, type="shallow", parent_id=parent)
    c2 = db.add_task("Child L2", None, duration=5, reward=1, penalty=0, effort=1, type="shallow", parent_id=parent)

    from decidrx import cli
    printed = []

    def fake_print(obj, *args, **kwargs):
        from rich.console import Console
        c = Console(record=True)
        c.print(obj)
        printed.append(c.export_text())

    monkeypatch.setattr(cli.console, "print", fake_print)

    from decidrx.cli import build_parser
    args = build_parser().parse_args(["subtask", "list", str(parent)])
    from decidrx.commands.subtask import cmd_subtask_list
    cmd_subtask_list(args)

    text = "\n".join(s for s in printed if isinstance(s, str))
    assert str(c1) in text
    assert str(c2) in text


def test_remove_task_cascades_when_confirmed(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_remove.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    p = db.add_task("Parent R", None)
    c1 = db.add_task("Child R1", None, parent_id=p)
    c2 = db.add_task("Child R2", None, parent_id=p)

    from decidrx.cli import build_parser
    from rich.prompt import Confirm

    monkeypatch.setattr(Confirm, "ask", lambda *a, **k: True)

    args = build_parser().parse_args(["remove", str(p)])
    from decidrx.commands.remove import cmd_remove
    cmd_remove(args)

    assert db.get_task(p) is None
    assert db.get_task(c1) is None
    assert db.get_task(c2) is None


def test_subtask_remove_noninteractive(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_subtask_remove.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    parent = db.add_task("Parent R2", None)
    child = db.add_task("Child R", None, parent_id=parent)

    from decidrx.cli import build_parser
    from decidrx.commands.subtask import cmd_subtask_remove

    args = build_parser().parse_args(["subtask", "remove", str(parent), str(child)])
    # monkeypatch confirm to avoid interactive prompt
    from rich.prompt import Confirm
    monkeypatch.setattr(Confirm, "ask", lambda *a, **k: True)
    cmd_subtask_remove(args)

    assert db.get_task(child) is None
    assert db.get_task(parent) is not None


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

    from rich.console import Console
    from decidrx.cli import build_parser, cmd_show
    import re

    def fake_print(obj, *args, **kwargs):
        c = Console(record=True)
        c.print(obj)
        printed.append(c.export_text())

    monkeypatch.setattr(cli.console, "print", fake_print)

    args = build_parser().parse_args(["show"])
    cmd_show(args)
    assert any(isinstance(x, str) for x in printed)

    # ensure the rendered view includes at least one time-like token (e.g., '1d', '3h', '45m', 'overdue')
    text = "\n".join(s for s in printed if isinstance(s, str))
    assert re.search(r"\b(overdue\s)?\d+[dhms]\b", text)

    # nested display: parent and child should be visible in show with tree indicators
    printed.clear()
    p = db.add_task("Parent Show", now + timedelta(days=3), duration=10, reward=1, penalty=0, effort=1, type="shallow")
    c = db.add_task("Child Show", None, duration=5, reward=1, penalty=0, effort=1, type="shallow", parent_id=p)
    args = build_parser().parse_args(["show"])
    cmd_show(args)
    text = "\n".join(s for s in printed if isinstance(s, str))
    # parent/child ids and tree connector should be present
    assert str(p) in text
    assert str(c) in text
    assert re.search(r"[├└]", text)

    printed.clear()
    args = build_parser().parse_args(["show", "--all"])
    cmd_show(args)
    assert any(isinstance(x, str) for x in printed)
    text_all = "\n".join(s for s in printed if isinstance(s, str))
    assert "1" in text_all
    assert "2" in text_all
    assert re.search(r"\b(overdue\s)?\d+[dhms]\b", text_all)


def test_archive_shows_all(tmp_path, monkeypatch):
    from rich.console import Console
    dbfile = tmp_path / "test_archive.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    id1 = db.add_task("A", now + timedelta(days=1), duration=10, reward=1, penalty=0, effort=1, type="shallow")
    id2 = db.add_task("B", now + timedelta(days=2), duration=20, reward=2, penalty=0, effort=1, type="deep")
    db.mark_done(id2)

    from decidrx import cli
    printed = []

    def fake_print(obj, *args, **kwargs):
        c = Console(record=True)
        c.print(obj)
        printed.append(c.export_text())

    monkeypatch.setattr(cli.console, "print", fake_print)

    from decidrx.cli import build_parser, cmd_archive

    args = build_parser().parse_args(["archive"])
    cmd_archive(args)

    text = "\n".join(s for s in printed if isinstance(s, str))
    assert "A" in text
    assert "B" in text
    assert "1" in text
    assert "2" in text


def test_undone_marks_task_not_completed(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_undone.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    tid = db.add_task("Do then undo", now + timedelta(days=1), duration=10, reward=1, penalty=0, effort=1, type="shallow")
    db.mark_done(tid)

    from decidrx.cli import build_parser, cmd_undone

    args = build_parser().parse_args(["undone", str(tid)])
    cmd_undone(args)

    t = db.get_task(tid)
    assert t["completed"] == 0
    assert t["completed_at"] is None


def test_reset_cancelled(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_reset.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    tid = db.add_task("Keep me", now + timedelta(days=1), duration=10, reward=1, penalty=0, effort=1, type="shallow")

    from rich.prompt import Confirm

    monkeypatch.setattr(Confirm, "ask", lambda *a, **k: False)

    from decidrx.cli import build_parser, cmd_reset

    args = build_parser().parse_args(["reset"])
    cmd_reset(args)

    db2 = Database(str(dbfile))
    tasks = db2.get_pending_tasks()
    assert len(tasks) == 1


def test_reset_confirmed(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_reset2.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    tid = db.add_task("Delete me", now + timedelta(days=1), duration=10, reward=1, penalty=0, effort=1, type="shallow")

    from rich.prompt import Confirm

    monkeypatch.setattr(Confirm, "ask", lambda *a, **k: True)

    from decidrx.cli import build_parser, cmd_reset

    args = build_parser().parse_args(["reset"])
    cmd_reset(args)

    db2 = Database(str(dbfile))
    tasks = db2.get_pending_tasks()
    assert len(tasks) == 0


def test_reset_force_flag(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_reset3.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    tid = db.add_task("Delete me too", now + timedelta(days=1), duration=10, reward=1, penalty=0, effort=1, type="shallow")

    from decidrx.cli import build_parser, cmd_reset

    args = build_parser().parse_args(["reset", "--yes"])
    cmd_reset(args)

    db2 = Database(str(dbfile))
    tasks = db2.get_pending_tasks()
    assert len(tasks) == 0


def test_mark_done_records_completed_at(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_done.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    tid = db.add_task("Finish me", now + timedelta(days=1), duration=15, reward=2, penalty=0, effort=1, type="shallow")

    # mark done
    db.mark_done(tid)

    t = db.get_task(tid)
    assert t["completed"] == 1
    assert t["completed_at"] is not None
    # ensure it's parseable ISO datetime
    from datetime import datetime as _dt
    _dt.fromisoformat(t["completed_at"])  # should not raise


def test_edit_noninteractive(tmp_path, monkeypatch):
    dbfile = tmp_path / "test_edit.db"
    monkeypatch.setenv("DECIDRX_DB", str(dbfile))
    db = Database(str(dbfile))
    now = datetime.now(timezone.utc)
    tid = db.add_task("Old", now + timedelta(days=1), description="old desc", duration=30, reward=3, penalty=1, effort=2, type="shallow")

    from decidrx.cli import build_parser, cmd_edit

    args = build_parser().parse_args(["edit", str(tid), "--title", "New", "--duration", "10", "--reward", "5", "--description", "new desc"])
    cmd_edit(args)

    t = db.get_task(tid)
    assert t["title"] == "New"
    assert t["duration"] == 10
    assert t["reward"] == 5
    assert t["description"] == "new desc"


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
        "",  # description keep
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
