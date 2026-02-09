import os
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_undone(args):
    db = Database(os.environ.get(DB_ENV))
    task = db.get_task(args.task_id)
    if not task:
        console.print(f"No task with id {args.task_id}")
        return
    if not task["completed"]:
        console.print(f"Task {args.task_id} is already not completed")
        return
    db.mark_undone(args.task_id)
    console.print(f"Marked task {args.task_id} as not completed")
