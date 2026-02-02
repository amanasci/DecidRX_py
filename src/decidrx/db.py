import os
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict

DEFAULT_DB = os.environ.get("DECIDRX_DB") or os.path.expanduser("~/.local/share/decidrx/decidrx.db")

class Database:
    def __init__(self, path: Optional[str] = None):
        self.path = path or DEFAULT_DB
        self._ensure_dir()
        self.conn = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def _ensure_dir(self):
        d = os.path.dirname(self.path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def init_db(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            deadline TEXT,
            duration INTEGER,
            reward INTEGER,
            penalty INTEGER,
            effort INTEGER,
            type TEXT,
            created_at TEXT,
            completed INTEGER DEFAULT 0
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS completions (
            task_id INTEGER,
            completed_at TEXT
        )
        """)
        self.conn.commit()

    def add_task(self, title: str, deadline: Optional[datetime], duration: int = 0, reward: int = 0, penalty: int = 0, effort: int = 0, type: str = "shallow") -> int:
        created_at = datetime.utcnow().isoformat()
        deadline_s = deadline.isoformat() if deadline else None
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO tasks (title, deadline, duration, reward, penalty, effort, type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, deadline_s, duration, reward, penalty, effort, type, created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_task(self, task_id: int, **fields):
        """Update provided fields for a task. Accepts same keys as columns.
        If 'deadline' is a datetime it will be converted to ISO string; if None it will be cleared.
        """
        if not fields:
            return 0
        cur = self.conn.cursor()
        cols = []
        vals = []
        for k, v in fields.items():
            if k == "deadline":
                if v is None:
                    vals.append(None)
                elif isinstance(v, datetime):
                    vals.append(v.isoformat())
                else:
                    vals.append(v)
                cols.append("deadline = ?")
            else:
                cols.append(f"{k} = ?")
                vals.append(v)
        vals.append(task_id)
        sql = f"UPDATE tasks SET {', '.join(cols)} WHERE id = ?"
        cur.execute(sql, tuple(vals))
        self.conn.commit()
        return cur.rowcount

    def get_task(self, task_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return cur.fetchone()

    def get_pending_tasks(self) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE completed = 0")
        return cur.fetchall()

    def mark_done(self, task_id: int):
        cur = self.conn.cursor()
        cur.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
        cur.execute("INSERT INTO completions (task_id, completed_at) VALUES (?, ?)", (task_id, datetime.utcnow().isoformat()))
        self.conn.commit()

    def stats(self) -> Dict[str, int]:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as total FROM tasks")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) as done FROM tasks WHERE completed = 1")
        done = cur.fetchone()[0]
        return {"total": total, "done": done}
