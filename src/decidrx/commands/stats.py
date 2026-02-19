import os
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def cmd_stats(args):
    db = Database(os.environ.get(DB_ENV))
    s = db.stats()
    # helper for gamification stats
    from decidrx.gamification import Gamification
    from rich.panel import Panel
    from rich.table import Table

    try:
        game = Gamification(db)
        user_stats = game._get_user_stats()
        
        table = Table(title="User Stats", show_header=True, header_style="bold magenta")
        table.add_column("Level", style="cyan", justify="center")
        table.add_column("XP", style="green", justify="center")
        table.add_column("Current Streak", style="red", justify="center")
        table.add_column("Best Streak", style="yellow", justify="center")
        
        if user_stats:
            table.add_row(
                str(user_stats["level"]), 
                str(user_stats["xp"]), 
                f"{user_stats['current_streak']} days",
                f"{user_stats['best_streak']} days"
            )
            console.print(table)
            console.print("")
    except Exception as e:
        console.print(f"[red]Error loading stats: {e}[/red]")
        pass

    console.print(f"[bold]Task Stats:[/bold] Total: {s['total']}, Done: {s['done']}")
