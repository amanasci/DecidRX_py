import os
from typing import Optional
from decidrx.prompt import prompt_str, prompt_int, parse_deadline, validate_args
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_add(args):
    db = Database(os.environ.get(DB_ENV))

    # If title is missing, assume interactive mode
    if not args.title:
        args.title = prompt_str("Title", required=True)

        # deadline
        while True:
            dl = prompt_str("Deadline (days, leave blank for none)", current="")
            if dl == "":
                args.deadline = None
                break
            try:
                dli = int(dl)
                if dli < 0:
                    console.print("Deadline must be 0 or positive.")
                    continue
                args.deadline = dli
                break
            except ValueError:
                console.print("Please enter a valid integer for deadline.")

        args.duration = prompt_int("Duration (minutes)", current=getattr(args, "duration", 0) or 0, minimum=0)
        args.reward = prompt_int("Reward (1-10)", current=getattr(args, "reward", 0) or 0, minimum=0, maximum=10)
        args.penalty = prompt_int("Penalty (1-10)", current=getattr(args, "penalty", 0) or 0, minimum=0, maximum=10)
        args.effort = prompt_int("Effort (1-10)", current=getattr(args, "effort", 0) or 0, minimum=0, maximum=10)

        # description (optional)
        args.description = prompt_str("Description (optional)", current=getattr(args, 'description', '') or '')

        while True:
            t = prompt_str("Type (deep/shallow)", current=getattr(args, "type", "shallow"))
            if t in ("deep", "shallow"):
                args.type = t
                break
            console.print("Type must be 'deep' or 'shallow'.")

    else:
        # Non-interactive: validate provided args and bail out if invalid
        if not validate_args(args):
            return

    deadline_dt = parse_deadline(args.deadline) if args.deadline is not None else None
    task_id = db.add_task(title=args.title, deadline=deadline_dt, description=getattr(args, 'description', None), duration=args.duration, reward=args.reward, penalty=args.penalty, effort=args.effort, type=args.type)
    console.print(f"Added task [bold]{args.title}[/bold] (id={task_id})")
