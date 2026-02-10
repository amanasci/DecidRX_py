import os
from datetime import datetime
from rich.table import Table
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_show(args):
    db = Database(os.environ.get(DB_ENV))
    if getattr(args, "all", False):
        cur = db.conn.cursor()
        cur.execute("SELECT * FROM tasks ORDER BY completed, id")
        tasks = cur.fetchall()
    else:
        tasks = db.get_pending_tasks()

    from rich.tree import Tree
    from datetime import timezone

    # use timezone-aware now (UTC) so comparisons with stored ISO datetimes work
    now = datetime.now(timezone.utc)

    def format_time_left(seconds: float) -> str:
        # human friendly: days, hours, minutes
        if seconds < 0:
            seconds = -seconds
            prefix = "overdue "
        else:
            prefix = ""
        if seconds >= 86400:
            days = int(seconds // 86400)
            return f"{prefix}{days}d"
        if seconds >= 3600:
            hours = int(seconds // 3600)
            return f"{prefix}{hours}h"
        if seconds >= 60:
            mins = int(seconds // 60)
            return f"{prefix}{mins}m"
        return f"{prefix}{int(seconds)}s"

    def make_label(t):
        dl = t["deadline"] if t["deadline"] else ""
        left = ""
        if dl:
            try:
                ddt = datetime.fromisoformat(dl)
                # assume naive datetimes mean UTC
                if ddt.tzinfo is None:
                    from datetime import timezone

                    ddt = ddt.replace(tzinfo=timezone.utc)
                delta = (ddt - now).total_seconds()
                left = format_time_left(delta)
            except Exception:
                pass
        created = t["created_at"][:19] if t["created_at"] else ""
        done = "✅" if t["completed"] else ""
        def v(key):
            return t[key] if key in t.keys() and t[key] is not None else 0
        return f"[cyan]{t['id']}[/cyan] [bold]{t['title']}[/bold] {left} dur:{v('duration')} r:{v('reward')} p:{v('penalty')} eff:{v('effort')} {done} [dim]{created}[/dim]"
    # Render as a table but show tree-like titles using box-drawing characters
    table = Table(title="Tasks")
    table.add_column("id", style="cyan")
    table.add_column("title", style="bold")
    table.add_column("description", style="dim")
    table.add_column("deadline", style="magenta")
    table.add_column("left", style="green")
    table.add_column("dur", justify="right")
    table.add_column("r")
    table.add_column("p")
    table.add_column("eff")
    table.add_column("type")
    table.add_column("created", style="dim")
    table.add_column("done", justify="center")

    # Determine root tasks (parents with parent_id IS NULL)
    cur = db.conn.cursor()
    if getattr(args, "all", False):
        cur.execute("SELECT * FROM tasks WHERE parent_id IS NULL ORDER BY completed, id")
    else:
        cur.execute("SELECT * FROM tasks WHERE parent_id IS NULL AND completed = 0 ORDER BY id")
    parents = cur.fetchall()

    # helper to get value from sqlite Row safely
    def v(row, key):
        return row[key] if key in row.keys() and row[key] is not None else 0

    def render_recursive(task_row, prefix_parts):
        # prefix_parts is a list of booleans where True means this ancestor has more siblings
        if not prefix_parts:
            title = f"{task_row['title']}"
        else:
            prefix = "".join("│   " if p else "    " for p in prefix_parts[:-1])
            connector = "├── " if prefix_parts[-1] else "└── "
            title = f"{prefix}{connector}{task_row['title']}"

        dl = task_row["deadline"] if task_row["deadline"] else ""
        left = ""
        if dl:
            try:
                ddt = datetime.fromisoformat(dl)
                if ddt.tzinfo is None:
                    from datetime import timezone

                    ddt = ddt.replace(tzinfo=timezone.utc)
                delta = (ddt - now).total_seconds()
                left = format_time_left(delta)
            except Exception:
                pass
        created = task_row["created_at"][:19] if task_row["created_at"] else ""
        done = "✅" if task_row["completed"] else ""
        desc_val = task_row["description"] if "description" in task_row.keys() else None
        desc = (desc_val or "")[:60] + "..." if desc_val and len(desc_val) > 60 else (desc_val or "")
        table.add_row(str(task_row["id"]), title, desc, dl, left, str(v(task_row, "duration")), str(v(task_row, "reward")), str(v(task_row, "penalty")), str(v(task_row, "effort")), task_row["type"] or "", created, done)

        children = db.get_children(task_row["id"])
        for idx, c in enumerate(children):
            is_more = (idx < len(children) - 1)
            render_recursive(c, prefix_parts + [is_more])

    for p in parents:
        render_recursive(p, [])

    console.print(table)
