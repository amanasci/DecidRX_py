import os
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_done(args):
    db = Database(os.environ.get(DB_ENV))
    db.mark_done(args.task_id)
    # Gamification
    from decidrx.gamification import Gamification
    from rich.panel import Panel
    
    try:
        game = Gamification(db)
        update = game.update_stats(args.task_id)
        console.print(Panel(update.message, title="[bold magenta]Gamification[/bold magenta]", border_style="green"))
    except Exception as e:
        # Fallback if gamification fails (e.g. schema migration issue on old install)
        # But we don't want to crash the main functionality
        console.print(f"[green]Marked task {args.task_id} done[/green]")
        pass
