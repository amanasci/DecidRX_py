import os
from datetime import datetime, timezone
from rich.table import Table
from decidrx.db import Database
from decidrx.scoring import score_task
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_now(args):
    db = Database(os.environ.get(DB_ENV))
    tasks = db.get_pending_tasks()
    if not tasks:
        console.print("No pending tasks.")
        return
    scored = []
    now = datetime.now(timezone.utc)
    for t in tasks:
        tdict = dict(t)
        score = score_task(tdict, now)
        scored.append((score, tdict))
    scored.sort(key=lambda x: x[0], reverse=True)

    limit = getattr(args, "limit", 5) or 5
    top = scored[:limit]

    table = Table(title="Ranked Tasks")
    table.add_column("rank", justify="right")
    table.add_column("id", style="cyan")
    table.add_column("title", style="bold")
    table.add_column("score", justify="right")

    for idx, (score, t) in enumerate(top, start=1):
        table.add_row(str(idx), str(t["id"]), t["title"], f"{score:.3f}")

    console.print(table)
