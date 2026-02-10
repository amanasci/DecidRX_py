import os
from datetime import datetime
from rich.panel import Panel
from rich.table import Table
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_view(args):
    db = Database(os.environ.get(DB_ENV))
    try:
        task_id = int(args.task_id)
    except Exception:
        console.print("task_id must be an integer")
        return

    task = db.get_task(task_id)
    if not task:
        console.print(f"No task with id {task_id}")
        return

    # format deadline and timestamps
    def fmt_iso(s):
        try:
            return datetime.fromisoformat(s).isoformat(sep=" ", timespec="seconds")
        except Exception:
            return s or ""

    title = f"[bold]{task['title']}[/bold] (id={task['id']})"
    meta = []
    if 'type' in task.keys() and task['type']:
        meta.append(f"type={task['type']}")
    meta.append(f"duration={task['duration'] or 0}m")
    meta.append(f"reward={task['reward'] or 0}")
    meta.append(f"penalty={task['penalty'] or 0}")
    meta.append(f"effort={task['effort'] or 0}")
    if 'deadline' in task.keys() and task['deadline']:
        meta.append(f"deadline={fmt_iso(task['deadline'])}")
    meta_line = " | ".join(meta)

    created = fmt_iso(task['created_at']) if 'created_at' in task.keys() and task['created_at'] else ""
    completed = "Yes" if task['completed'] else "No"
    completed_at = fmt_iso(task['completed_at']) if 'completed_at' in task.keys() and task['completed_at'] else ""

    body_lines = [meta_line, f"created: {created}", f"completed: {completed} {('at ' + completed_at) if completed_at else ''}", "", "Description:\n"]
    desc = task['description'] if 'description' in task.keys() and task['description'] else ""
    body_lines.append(desc)

    panel = Panel("\n".join(body_lines), title=title, expand=False)
    console.print(panel)

    # subtasks
    children = db.get_children(task_id)
    if children:
        table = Table(title=f"Subtasks of {task_id}")
        table.add_column("id", style="cyan")
        table.add_column("title", style="bold")
        table.add_column("description")
        table.add_column("deadline", style="magenta")
        table.add_column("done", justify="center")

        for c in children:
            dl = c['deadline'] if 'deadline' in c.keys() and c['deadline'] else ''
            if dl:
                try:
                    dl = datetime.fromisoformat(dl).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass
            done = "✅" if c['completed'] else ""
            desc = c['description'] if 'description' in c.keys() and c['description'] else ""
            table.add_row(str(c['id']), c['title'] or "", desc, dl, done)

        console.print(table)
