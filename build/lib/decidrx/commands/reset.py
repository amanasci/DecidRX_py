import os
from rich.prompt import Confirm
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_reset(args):
    db = Database(os.environ.get(DB_ENV))

    # If --yes is passed, do not prompt
    if getattr(args, "yes", False):
        db.reset()
        console.print("Database reset.")
        return

    # Otherwise prompt for confirmation
    ok = Confirm.ask(f"Are you sure you want to reset the database at {db.path}? This will delete ALL tasks", default=False)
    if not ok:
        console.print("Aborted.")
        return
    db.reset()
    console.print("Database reset.")
