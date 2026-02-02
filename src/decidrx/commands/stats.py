import os
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_stats(args):
    db = Database(os.environ.get(DB_ENV))
    s = db.stats()
    console.print(f"Total: {s['total']}, Done: {s['done']}")
