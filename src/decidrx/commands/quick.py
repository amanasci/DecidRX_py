import os
from datetime import datetime, timezone
from rich.table import Table
from decidrx.db import Database
from decidrx.scoring import score_task
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_quick(args):
    db = Database(os.environ.get(DB_ENV))
    tasks = db.get_pending_tasks()
    now = datetime.now(timezone.utc)
    quicks = []
    for t in tasks:
        if (t["duration"] or 0) <= 20:
            score = score_task(dict(t), now)
            quicks.append((score, dict(t)))
    quicks.sort(key=lambda x: x[0], reverse=True)
    table = Table(title="Quick Wins (<20 min)")
    table.add_column("id")
    table.add_column("title")
    table.add_column("duration")
    table.add_column("score")
    for s, t in quicks:
        table.add_row(str(t["id"]), t["title"], str(t.get("duration") or ""), f"{s:.3f}")
    console.print(table)
