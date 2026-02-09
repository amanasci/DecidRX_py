import os
from typing import Optional
from rich.prompt import Prompt, IntPrompt, Confirm
from decidrx.prompt import parse_deadline, prompt_str, prompt_int
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_subtask_add(args):
    db = Database(os.environ.get(DB_ENV))
    try:
        parent_id = int(args.parent_id)
    except Exception:
        console.print("Parent id must be an integer")
        return

    # If title provided non-interactively
    if getattr(args, "title", None):
        # validate fields minimally
        deadline_dt = parse_deadline(args.deadline) if getattr(args, "deadline", None) is not None else None
        try:
            child_id = db.add_task(title=args.title, deadline=deadline_dt, description=getattr(args, 'description', None), duration=args.duration or 0, reward=args.reward or 0, penalty=args.penalty or 0, effort=args.effort or 0, type=args.type or 'shallow', parent_id=parent_id)
            console.print(f"Added subtask [bold]{args.title}[/bold] (id={child_id})")
        except ValueError as e:
            console.print(str(e))
        return

    # Interactive flow
    console.print(f"Adding a subtask to parent id {parent_id}")
    title = prompt_str("Subtask Title", required=True)

    # deadline
    while True:
        dl = prompt_str("Subtask Deadline (days, leave blank for none)", current="")
        if dl == "":
            deadline = None
            break
        try:
            dli = int(dl)
            if dli < 0:
                console.print("Deadline must be 0 or positive.")
                continue
            deadline = dli
            break
        except ValueError:
            console.print("Please enter a valid integer for deadline.")

    duration = prompt_int("Subtask Duration (minutes)", current=0, minimum=0)
    reward = prompt_int("Subtask Reward (1-10)", current=0, minimum=0, maximum=10)
    penalty = prompt_int("Subtask Penalty (1-10)", current=0, minimum=0, maximum=10)
    effort = prompt_int("Subtask Effort (1-10)", current=0, minimum=0, maximum=10)
    description = prompt_str("Subtask Description (optional)", current="")

    while True:
        t = prompt_str("Subtask Type (deep/shallow)", current="shallow")
        if t in ("deep", "shallow"):
            typ = t
            break
        console.print("Type must be 'deep' or 'shallow'.")

    deadline_dt = parse_deadline(deadline) if deadline is not None else None
    try:
        child_id = db.add_task(title=title, deadline=deadline_dt, description=description or None, duration=duration, reward=reward, penalty=penalty, effort=effort, type=typ, parent_id=parent_id)
        console.print(f"Added subtask [bold]{title}[/bold] (id={child_id})")
    except ValueError as e:
        console.print(str(e))


def cmd_subtask_list(args):
    db = Database(os.environ.get(DB_ENV))
    try:
        parent_id = int(args.parent_id)
    except Exception:
        console.print("Parent id must be an integer")
        return

    children = db.get_children(parent_id)
    from rich.table import Table

    table = Table(title=f"Subtasks of {parent_id}")
    table.add_column("id", style="cyan")
    table.add_column("title")
    table.add_column("done", justify="center")

    for c in children:
        done = "✅" if c["completed"] else ""
        table.add_row(str(c["id"]), c["title"], done)

    console.print(table)


def cmd_subtask_remove(args):
    db = Database(os.environ.get(DB_ENV))
    try:
        parent_id = int(args.parent_id)
        child_id = int(args.child_id)
    except Exception:
        console.print("parent_id and child_id must be integers")
        return

    # verify relationship
    c = db.get_task(child_id)
    if not c or c["parent_id"] != parent_id:
        console.print("Child not found for the given parent")
        return

    # confirm
    try:
        ok = Confirm.ask(f"Delete subtask {child_id} (parent {parent_id})?")
    except Exception:
        ok = False
    if not ok:
        console.print("Aborted.")
        return

    # delete
    try:
        db.delete_task(child_id, cascade=True)
        console.print(f"Deleted subtask {child_id}")
    except ValueError as e:
        console.print(str(e))


def cmd_subtask_edit(args):
    db = Database(os.environ.get(DB_ENV))
    try:
        parent_id = int(args.parent_id)
        child_id = int(args.child_id)
    except Exception:
        console.print("parent_id and child_id must be integers")
        return

    # verify relationship
    child = db.get_task(child_id)
    if not child or child["parent_id"] != parent_id:
        console.print("Child not found for the given parent")
        return

    # accept similar flags to edit
    provided_flags = any(
        getattr(args, k) is not None for k in ("title", "deadline", "duration", "reward", "penalty", "effort", "type")
    )
    interactive = getattr(args, "interactive", False) or not provided_flags

    updates = {}
    if interactive:
        console.print(f"Editing subtask [bold]{child['title']}[/bold] (id={child['id']})")
        new_title = Prompt.ask("Title", default=child["title"]).strip()
        if new_title != child["title"]:
            updates["title"] = new_title

        # deadline
        while True:
            dl = Prompt.ask("Deadline (days, leave blank to keep)", default="").strip()
            if dl == "":
                break
            try:
                dli = int(dl)
                if dli < 0:
                    console.print("Deadline must be 0 or positive.")
                    continue
                updates["deadline"] = parse_deadline(dli)
                break
            except ValueError:
                console.print("Please enter a valid integer for deadline.")

        # duration
        while True:
            try:
                dur = IntPrompt.ask("Duration (minutes)", default=child["duration"] or 0)
                dur_i = int(dur)
                if dur_i < 0:
                    console.print("Duration must be >= 0.")
                    continue
                break
            except Exception:
                console.print("Please enter a valid integer for duration.")
        if dur_i != (child["duration"] or 0):
            updates["duration"] = dur_i

        # reward
        while True:
            try:
                r = IntPrompt.ask("Reward (1-10)", default=child["reward"] or 0)
                r_i = int(r)
                if r_i < 0 or r_i > 10:
                    console.print("Reward must be between 0 and 10.")
                    continue
                break
            except Exception:
                console.print("Please enter a valid integer for reward.")
        if r_i != (child["reward"] or 0):
            updates["reward"] = r_i

        # penalty
        while True:
            try:
                p = IntPrompt.ask("Penalty (1-10)", default=child["penalty"] or 0)
                p_i = int(p)
                if p_i < 0 or p_i > 10:
                    console.print("Penalty must be between 0 and 10.")
                    continue
                break
            except Exception:
                console.print("Please enter a valid integer for penalty.")
        if p_i != (child["penalty"] or 0):
            updates["penalty"] = p_i

        # effort
        while True:
            try:
                e = IntPrompt.ask("Effort (1-10)", default=child["effort"] or 0)
                e_i = int(e)
                if e_i < 0 or e_i > 10:
                    console.print("Effort must be between 0 and 10.")
                    continue
                break
            except Exception:
                console.print("Please enter a valid integer for effort.")
        if e_i != (child["effort"] or 0):
            updates["effort"] = e_i

        # description
        cur_desc = child["description"] if "description" in child.keys() else None
        new_desc = Prompt.ask("Description (leave blank to keep)", default=cur_desc or "").strip()
        if new_desc != (cur_desc or ""):
            updates["description"] = new_desc

        # type
        t = Prompt.ask("Type (deep/shallow)", default=child["type"] or "shallow").strip()
        if t and t in ("deep", "shallow") and t != child["type"]:
            updates["type"] = t

    else:
        if args.title is not None:
            updates["title"] = args.title
        if args.deadline is not None:
            if args.deadline < 0:
                console.print("Deadline must be >= 0.")
                return
            updates["deadline"] = parse_deadline(args.deadline)
        if args.description is not None:
            updates["description"] = args.description
        if args.duration is not None:
            if args.duration < 0:
                console.print("Duration must be >= 0.")
                return
            updates["duration"] = args.duration
        if args.reward is not None:
            if args.reward < 0 or args.reward > 10:
                console.print("Reward must be 0-10.")
                return
            updates["reward"] = args.reward
        if args.penalty is not None:
            if args.penalty < 0 or args.penalty > 10:
                console.print("Penalty must be 0-10.")
                return
            updates["penalty"] = args.penalty
        if args.effort is not None:
            if args.effort < 0 or args.effort > 10:
                console.print("Effort must be 0-10.")
                return
            updates["effort"] = args.effort
        if args.type is not None:
            if args.type not in ("deep", "shallow"):
                console.print("Type must be 'deep' or 'shallow'.")
                return
            updates["type"] = args.type

    if not updates:
        console.print("No changes.")
        return

    db.update_task(child_id, **updates)
    console.print(f"Updated subtask {child_id}")
