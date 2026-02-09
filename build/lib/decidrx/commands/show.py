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

    for t in tasks:
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
        if dl:
            try:
                dl = datetime.fromisoformat(dl).strftime("%Y-%m-%d")
            except Exception:
                pass
        created = t["created_at"][:19] if t["created_at"] else ""
        done = "✅" if t["completed"] else ""
        desc_val = t["description"] if "description" in t.keys() else None
        desc = (desc_val or "")[:60] + "..." if desc_val and len(desc_val) > 60 else (desc_val or "")
        table.add_row(str(t["id"]), t["title"], desc, dl, left, str(t["duration"] or ""), str(t["reward"] or ""), str(t["penalty"] or ""), str(t["effort"] or ""), t["type"] or "", created, done)

    console.print(table)
