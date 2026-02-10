import os
from datetime import datetime
from rich.table import Table
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_archive(args):
    """Show all tasks regardless of completed status (archive view)."""
    db = Database(os.environ.get(DB_ENV))
    cur = db.conn.cursor()
    cur.execute("SELECT * FROM tasks ORDER BY id")
    tasks = cur.fetchall()

    from rich.tree import Tree
    from datetime import timezone

    now = datetime.now(timezone.utc)

    def format_time_left(seconds: float) -> str:
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
                if ddt.tzinfo is None:
                    from datetime import timezone

                    ddt = ddt.replace(tzinfo=timezone.utc)
                delta = (ddt - now).total_seconds()
                left = format_time_left(delta)
            except Exception:
                pass
        created = t["created_at"][:19] if t["created_at"] else ""
        done = "✅" if t["completed"] else ""
        completed_at = t["completed_at"] or ""
        def v(key):
            return t[key] if key in t.keys() and t[key] is not None else 0
        return f"[cyan]{t['id']}[/cyan] [bold]{t['title']}[/bold] {left} dur:{v('duration')} r:{v('reward')} p:{v('penalty')} eff:{v('effort')} {done} [dim]{created}[/dim] [dim]{completed_at}[/dim]"
    # Render as table with inlined tree-style titles
    table = Table(title="Archive")
    table.add_column("id", style="cyan")
    table.add_column("title", style="bold")
    table.add_column("description", style="dim")
    table.add_column("deadline", style="magenta")
    table.add_column("dur", justify="right")
    table.add_column("r")
    table.add_column("p")
    table.add_column("eff")
    table.add_column("type")
    table.add_column("created", style="dim")
    table.add_column("done", justify="center")
    table.add_column("completed_at", style="dim")

    cur = db.conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE parent_id IS NULL ORDER BY id")
    parents = cur.fetchall()

    def v(row, key):
        return row[key] if key in row.keys() and row[key] is not None else 0

    def render_recursive(task_row, prefix_parts):
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
        completed_at = task_row["completed_at"] or ""
        desc_val = task_row["description"] if "description" in task_row.keys() else None
        desc = (desc_val or "")[:60] + "..." if desc_val and len(desc_val) > 60 else (desc_val or "")
        table.add_row(str(task_row["id"]), title, desc, dl, str(v(task_row, "duration")), str(v(task_row, "reward")), str(v(task_row, "penalty")), str(v(task_row, "effort")), task_row["type"] or "", created, done, completed_at)

        children = db.get_children(task_row["id"])
        for idx, c in enumerate(children):
            is_more = (idx < len(children) - 1)
            render_recursive(c, prefix_parts + [is_more])

    for p in parents:
        render_recursive(p, [])

    console.print(table)
