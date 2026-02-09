import os
from rich.prompt import Confirm
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_remove(args):
    db = Database(os.environ.get(DB_ENV))
    try:
        tid = int(args.task_id)
    except Exception:
        console.print("task_id must be an integer")
        return

    # check children count
    cur = db.conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tasks WHERE parent_id = ?", (tid,))
    child_count = cur.fetchone()[0]

    # build confirmation message
    if child_count > 0:
        msg = f"Task {tid} has {child_count} subtasks. Delete it and all subtasks?"
    else:
        msg = f"Delete task {tid}?"

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

    try:
        deleted = db.delete_task(tid, cascade=True)
        console.print(f"Deleted {deleted} task(s) (including subtasks if any)")
    except ValueError as e:
        console.print(str(e))
