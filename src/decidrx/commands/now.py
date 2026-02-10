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
        # compute base score for the task itself
        score = score_task(tdict, now)
        scored.append((score, tdict))
        # if this task has children, also compute an aggregated parent score
        children = db.get_children(t["id"])
        if children:
            # convert children rows to dicts
            child_dicts = [dict(c) for c in children]
            try:
                from decidrx.scoring import aggregate_task_for_scoring

                agg = aggregate_task_for_scoring(tdict, child_dicts)
                agg_score = score_task(agg, now)
                # attach an aggregated marker so UI can highlight if needed
                agg_record = dict(agg)
                agg_record["id"] = tdict["id"]
                agg_record["_is_aggregate"] = True
                scored.append((agg_score, agg_record))
            except Exception:
                # fall back to base behaviour on any error
                pass
    scored.sort(key=lambda x: x[0], reverse=True)

    limit = getattr(args, "limit", 5) or 5
    top = scored[:limit]

    table = Table(title="Ranked Tasks")
    table.add_column("rank", justify="right")
    table.add_column("id", style="cyan")
    table.add_column("title", style="bold")
    table.add_column("score", justify="right")

    displayed = set()
    for idx, (score, t) in enumerate(top, start=1):
        # If this row is a child that was already displayed under its parent, skip
        if t.get("id") in displayed:
            continue
        # mark aggregated parent rows so users can tell them apart
        title = t.get("title") or ""
        if t.get("_is_aggregate"):
            title = f"{title} (agg)"
        table.add_row(str(idx), str(t["id"]), title, f"{score:.3f}")
        displayed.add(t.get("id"))
        # if task has children, render them as inline rows with tree-style prefixes
        try:
            children = db.get_children(t["id"])
        except Exception:
            children = []
        for i, c in enumerate(children):
            # skip if child was explicitly in top and already displayed
            if c["id"] in displayed:
                continue
            is_more = (i < len(children) - 1)
            prefix = "├── " if is_more else "└── "
            def v(key):
                return c[key] if key in c.keys() and c[key] is not None else 0
            child_title = f"{prefix}{c['title']}"
            table.add_row("", str(c["id"]), child_title, "")
            displayed.add(c["id"])

    console.print(table)
