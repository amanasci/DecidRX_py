from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import math
import sqlite3
from .db import Database

@dataclass
class GameUpdate:
    xp_gained: int
    new_level: int
    level_up: bool
    streak_bonus: int
    current_streak: int
    message: str

class Gamification:
    def __init__(self, db: Database):
        self.db = db

    def calculate_task_xp(self, task: sqlite3.Row) -> int:
        """Calculate XP for a completed task based on its attributes."""
        # Base XP
        xp = 10
        
        # Difficulty multipliers
        effort = task["effort"] or 0
        reward = task["reward"] or 0
        
        xp += effort * 5
        xp += reward * 5
        
        # Type multiplier
        if task["type"] == "deep":
            xp += 50
        else:
            xp += 10
            
        # Urgency bonus (if completed well before deadline)
        if task["deadline"]:
            try:
                deadline = datetime.fromisoformat(task["deadline"]).replace(tzinfo=timezone.utc)
                # If we have a completed_at in the task row, use it. But usually this is called AFTER marking done.
                if "completed_at" in task.keys() and task["completed_at"]:
                    completed_at = datetime.fromisoformat(task["completed_at"]).replace(tzinfo=timezone.utc)
                else:
                    completed_at = datetime.now(timezone.utc)
                
                # If completed > 24 hours before deadline
                if (deadline - completed_at).total_seconds() > 86400:
                    xp += 20
            except Exception:
                pass
                
        return int(xp)

    def _get_user_stats(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM user_stats WHERE id = 1")
        row = cur.fetchone()
        if not row:
             # Should be initialized by db.py but just in case
             cur.execute("INSERT OR IGNORE INTO user_stats (id, xp, level, current_streak, best_streak) VALUES (1, 0, 1, 0, 0)")
             self.db.conn.commit()
             cur.execute("SELECT * FROM user_stats WHERE id = 1")
             row = cur.fetchone()
        return row

    def update_stats(self, task_id: int) -> GameUpdate:
        """Update user stats after a task completion."""
        task = self.db.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        stats = self._get_user_stats()
        current_xp = stats["xp"]
        current_level = stats["level"]
        current_streak = stats["current_streak"]
        last_date_str = stats["last_completed_date"]
        best_streak = stats["best_streak"]

        # Calculate XP
        xp_gained = self.calculate_task_xp(task)

        # Streak Calculation
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        
        new_streak = current_streak
        streak_bonus = 0

        # if last_date_str is None, it's the first task ever
        last_date = None
        if last_date_str:
            last_date = datetime.fromisoformat(last_date_str).date()

        if last_date == yesterday:
            new_streak += 1
            streak_bonus = new_streak * 2 # Bonus XP for streak
        elif last_date == today:
            # Already did a task today, streak continues but does not increment? 
            # Usually streak is "days in a row". So if I do 2 tasks today, streak is still X.
            # But maybe we want to reward doing multiple tasks?
            # Let's keep streak count purely as "days".
            # So if last_date == today, new_streak = current_streak
            new_streak = current_streak
            streak_bonus = 0 # No extra bonus for 2nd task of day? Or maybe small?
            # Let's verify logic:
            # Day 1: Task 1 -> last_date=None -> New Streak 1.
            # Day 2: Task 1 -> last_date=Day1 (yesterday) -> New Streak 2. Bonus = 4.
            # Day 2: Task 2 -> last_date=Day2 (today) -> New Streak 2.
        else:
            # Streak broken (last_date < yesterday or None)
            # Exception: if last_date is None (first task), streak = 1
            if last_date is None:
                new_streak = 1
            elif last_date < yesterday:
                 new_streak = 1
            streak_bonus = 0

        xp_gained += streak_bonus
        new_xp = current_xp + xp_gained

        # Level Calculation
        # Level = floor(sqrt(total_xp / 100)) + 1
        new_level = math.floor(math.sqrt(new_xp / 100)) + 1
        level_up = new_level > current_level
        
        if new_streak > best_streak:
            best_streak = new_streak

        # Update DB
        cur = self.db.conn.cursor()
        cur.execute("""
            UPDATE user_stats 
            SET xp = ?, level = ?, current_streak = ?, last_completed_date = ?, best_streak = ?
            WHERE id = 1
        """, (new_xp, new_level, new_streak, today.isoformat(), best_streak))
        self.db.conn.commit()

        message = f"Task Complete! +{xp_gained} XP"
        if streak_bonus > 0:
            message += f" (incl. {streak_bonus} streak bonus)"
        
        # We can construct a nice rich string
        if level_up:
            message += f"\n[bold yellow]LEVEL UP! You are now Level {new_level}![/bold yellow]"
        
        if new_streak > 1 and (last_date != today):
             # Only show streak msg if it updated today
            message += f"\n[bold red]Streak: {new_streak} days![/bold red]"
        elif new_streak > 1:
             message += f"\n[dim]Streak: {new_streak} days[/dim]"


        return GameUpdate(
            xp_gained=xp_gained,
            new_level=new_level,
            level_up=level_up,
            streak_bonus=streak_bonus,
            current_streak=new_streak,
            message=message
        )
