import os
from datetime import datetime
from rich.prompt import Prompt, IntPrompt
from decidrx.db import Database
from decidrx.prompt import parse_deadline
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_edit(args):
    db = Database(os.environ.get(DB_ENV))
    task = db.get_task(args.task_id)
    if not task:
        console.print(f"No task with id {args.task_id}")
        return

    provided_flags = any(
        getattr(args, k) is not None for k in ("title", "deadline", "duration", "reward", "penalty", "effort", "type", "parent")
    )
    interactive = getattr(args, "interactive", False) or not provided_flags

    updates = {}

    if interactive:
        console.print(f"Editing task [bold]{task['title']}[/bold] (id={task['id']})")
        new_title = Prompt.ask("Title", default=task["title"]).strip()
        if new_title != task["title"]:
            updates["title"] = new_title


        # deadline
        cur_dl = task["deadline"]
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

        # duration with validation
        while True:
            try:
                dur = IntPrompt.ask("Duration (minutes)", default=task["duration"] or 0)
                dur_i = int(dur)
                if dur_i < 0:
                    console.print("Duration must be >= 0.")
                    continue
                break
            except Exception:
                console.print("Please enter a valid integer for duration.")
        if dur_i != (task["duration"] or 0):
            updates["duration"] = dur_i

        # reward/penalty/effort with validation
        while True:
            try:
                r = IntPrompt.ask("Reward (1-10)", default=task["reward"] or 0)
                r_i = int(r)
                if r_i < 0 or r_i > 10:
                    console.print("Reward must be between 0 and 10.")
                    continue
                break
            except Exception:
                console.print("Please enter a valid integer for reward.")
        if r_i != (task["reward"] or 0):
            updates["reward"] = r_i

        while True:
            try:
                p = IntPrompt.ask("Penalty (1-10)", default=task["penalty"] or 0)
                p_i = int(p)
                if p_i < 0 or p_i > 10:
                    console.print("Penalty must be between 0 and 10.")
                    continue
                break
            except Exception:
                console.print("Please enter a valid integer for penalty.")
        if p_i != (task["penalty"] or 0):
            updates["penalty"] = p_i

        while True:
            try:
                e = IntPrompt.ask("Effort (1-10)", default=task["effort"] or 0)
                e_i = int(e)
                if e_i < 0 or e_i > 10:
                    console.print("Effort must be between 0 and 10.")
                    continue
                break
            except Exception:
                console.print("Please enter a valid integer for effort.")
        if e_i != (task["effort"] or 0):
            updates["effort"] = e_i

        # description
        # use explicit index access on sqlite Row
        cur_desc = task["description"] if "description" in task.keys() else None
        new_desc = Prompt.ask("Description (leave blank to keep)", default=cur_desc or "").strip()
        if new_desc != (cur_desc or ""):
            updates["description"] = new_desc

        # type
        t = Prompt.ask("Type (deep/shallow)", default=task["type"] or "shallow").strip()
        if t and t in ("deep", "shallow") and t != task["type"]:
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
        if getattr(args, 'parent', None) is not None:
            # explicit parent flag provided (use 0 to clear parent)
            if args.parent == 0:
                updates["parent_id"] = None
            else:
                updates["parent_id"] = args.parent
    if not updates:
        console.print("No changes.")
        return

    db.update_task(args.task_id, **updates)
    console.print(f"Updated task {args.task_id}")
