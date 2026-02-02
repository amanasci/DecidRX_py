import os
from datetime import datetime, timezone
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
    best = scored[0][1]
    console.print(f"Do this now: [bold]{best['title']}[/bold] (score={scored[0][0]:.3f})")
