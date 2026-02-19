import pytest
import os
from datetime import datetime, timezone, timedelta
from decidrx.db import Database
from decidrx.gamification import Gamification

@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    os.environ["DECIDRX_DB"] = str(db_path)
    db = Database(str(db_path))
    return db

def test_xp_calculation(db):
    game = Gamification(db)
    
    # Create a task
    # Base 10 + Effort(5)*5 + Reward(5)*5 + Shallow(10) = 10 + 25 + 25 + 10 = 70
    tid = db.add_task("Test Task", deadline=None, effort=5, reward=5, type="shallow")
    
    # Mark done
    db.mark_done(tid)
    
    # Update stats
    update = game.update_stats(tid)
    
    assert update.xp_gained == 70
    assert update.new_level == 1  # 70 XP < 100
    assert update.current_streak == 1 # First task
    
    # Verify DB
    stats = game._get_user_stats()
    assert stats["xp"] == 70
    assert stats["current_streak"] == 1

def test_level_up(db):
    game = Gamification(db)
    
    # XP needed for level 2 is 100.
    # Task yielding 110 XP: Base 10 + Deep 50 + Effort 10 * 5 = 110
    tid = db.add_task("Big Task", deadline=None, effort=10, type="deep")
    db.mark_done(tid)
    
    update = game.update_stats(tid)
    
    assert update.xp_gained == 110
    assert update.new_level == 2
    assert update.level_up is True
    
def test_streak_increment(db):
    game = Gamification(db)
    
    # Mock yesterday completion
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    cur = db.conn.cursor()
    # Manually set stats: streak 5, last_completed = yesterday
    cur.execute("UPDATE user_stats SET current_streak = 5, last_completed_date = ? WHERE id = 1", (yesterday,))
    db.conn.commit()
    
    tid = db.add_task("Streak Task", deadline=None)
    db.mark_done(tid)
    update = game.update_stats(tid)
    
    assert update.current_streak == 6
    assert update.streak_bonus == 12 # 6 * 2
    
def test_streak_reset(db):
    game = Gamification(db)
    
    # Mock day before yesterday completion (streak broken)
    day_before = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
    cur = db.conn.cursor()
    cur.execute("UPDATE user_stats SET current_streak = 5, last_completed_date = ? WHERE id = 1", (day_before,))
    db.conn.commit()
    
    tid = db.add_task("Streak Broken Task", deadline=None)
    db.mark_done(tid)
    update = game.update_stats(tid)
    
    assert update.current_streak == 1
    assert update.streak_bonus == 0

def test_same_day_no_streak_duplicate(db):
    game = Gamification(db)
    
    tid1 = db.add_task("Task 1", deadline=None)
    db.mark_done(tid1)
    update1 = game.update_stats(tid1)
    
    assert update1.current_streak == 1
    
    tid2 = db.add_task("Task 2", deadline=None)
    db.mark_done(tid2)
    update2 = game.update_stats(tid2)
    
    assert update2.current_streak == 1 # Still 1 day streak
    assert update2.streak_bonus == 0
