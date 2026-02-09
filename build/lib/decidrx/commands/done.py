import os
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_done(args):
    db = Database(os.environ.get(DB_ENV))
    db.mark_done(args.task_id)
    console.print(f"Marked task {args.task_id} done")
