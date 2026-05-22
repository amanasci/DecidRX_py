import os
from rich.prompt import Confirm
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_remove(args):
    db = Database(os.environ.get(DB_ENV))
    task_ids = []
    for task_id in args.task_id:
        try:
            task_ids.append(int(task_id))
        except Exception:
            console.print("task_id must be an integer")
            return

    # remove duplicates while preserving order
    unique_task_ids = []
    seen = set()
    for tid in task_ids:
        if tid not in seen:
            unique_task_ids.append(tid)
            seen.add(tid)

    invalid_ids = [tid for tid in unique_task_ids if db.get_task(tid) is None]
    if invalid_ids:
        console.print("Task id(s) do not exist: " + ", ".join(str(tid) for tid in invalid_ids))
        return

    cur = db.conn.cursor()
    total_children = 0
    for tid in unique_task_ids:
        cur.execute("SELECT COUNT(*) FROM tasks WHERE parent_id = ?", (tid,))
        total_children += cur.fetchone()[0]

    if total_children > 0:
        msg = (
            f"Delete {len(unique_task_ids)} selected task(s) and their {total_children} subtasks?"
        )
    else:
        msg = f"Delete {len(unique_task_ids)} selected task(s)?"

    if not getattr(args, "yes", False):
        try:
            ok = Confirm.ask(msg)
        except Exception:
            ok = False
    else:
        ok = True

    if not ok:
        console.print("Aborted.")
        return

    deleted_total = 0
    for tid in unique_task_ids:
        if db.get_task(tid) is None:
            continue
        deleted_total += db.delete_task(tid, cascade=True)

    console.print(f"Deleted {deleted_total} task(s) (including subtasks if any)")
