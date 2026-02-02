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
    table.add_column("deadline", style="magenta")
    table.add_column("dur", justify="right")
    table.add_column("r")
    table.add_column("p")
    table.add_column("eff")
    table.add_column("type")
    table.add_column("created", style="dim")
    table.add_column("done", justify="center")

    for t in tasks:
        dl = t["deadline"] if t["deadline"] else ""
        if dl:
            try:
                dl = datetime.fromisoformat(dl).strftime("%Y-%m-%d")
            except Exception:
                pass
        created = t["created_at"][:19] if t["created_at"] else ""
        done = "✅" if t["completed"] else ""
        table.add_row(str(t["id"]), t["title"], dl, str(t["duration"] or ""), str(t["reward"] or ""), str(t["penalty"] or ""), str(t["effort"] or ""), t["type"] or "", created, done)

    console.print(table)
