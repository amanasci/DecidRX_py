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

    table = Table(title="Archive")
    table.add_column("id", style="cyan")
    table.add_column("title", style="bold")
    table.add_column("description", style="dim")
    table.add_column("deadline", style="magenta")
    # table.add_column("left", style="green")
    table.add_column("dur", justify="right")
    table.add_column("r")
    table.add_column("p")
    table.add_column("eff")
    table.add_column("type")
    table.add_column("created", style="dim")
    table.add_column("done", justify="center")
    table.add_column("completed_at", style="dim")

    now = datetime.now()

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

    # Render parents with nested children indented
    def render_task_row(t, indent_level=0):
        dl = t["deadline"] if t["deadline"] else ""
        left = ""
        if dl:
            try:
                ddt = datetime.fromisoformat(dl)
                if ddt.tzinfo is None:
                    from datetime import timezone

                    ddt = ddt.replace(tzinfo=timezone.utc)
                delta = (ddt - datetime.now()).total_seconds()
                left = format_time_left(delta)
            except Exception:
                pass
        if dl:
            try:
                dl = datetime.fromisoformat(dl).strftime("%Y-%m-%d")
            except Exception:
                pass
        created = t["created_at"][:19] if t["created_at"] else ""
        done = "✅" if t["completed"] else ""
        desc_val = t["description"] if "description" in t.keys() else None
        desc = (desc_val or "")[:60] + "..." if desc_val and len(desc_val) > 60 else (desc_val or "")
        prefix = ""
        if indent_level > 0:
            prefix = "  " * indent_level + "↳ "
        table.add_row(str(t["id"]), prefix + (t["title"] or ""), desc, dl, str(t["duration"] or ""), str(t["reward"] or ""), str(t["penalty"] or ""), str(t["effort"] or ""), t["type"] or "", created, done, t["completed_at"] or "")

    # top-level parents
    cur = db.conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE parent_id IS NULL ORDER BY id")
    parents = cur.fetchall()

    def render_recursive(task_row, depth=0):
        render_task_row(task_row, indent_level=depth)
        # fetch children
        children = db.get_children(task_row["id"])
        for c in children:
            render_recursive(c, depth + 1)

    for p in parents:
        render_recursive(p, depth=0)

    console.print(table)
