import os
import sqlite3
from datetime import datetime, timezone
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
            description TEXT,
            duration INTEGER,
            reward INTEGER,
            penalty INTEGER,
            effort INTEGER,
            type TEXT,
            created_at TEXT,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            parent_id INTEGER
        )
        """)
        # Ensure older DBs get the new columns
        cur.execute("PRAGMA table_info(tasks)")
        cols = [r[1] for r in cur.fetchall()]
        if "description" not in cols:
            cur.execute("ALTER TABLE tasks ADD COLUMN description TEXT")
            self.conn.commit()
        if "completed_at" not in cols:
            cur.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")
            self.conn.commit()
        if "parent_id" not in cols:
            cur.execute("ALTER TABLE tasks ADD COLUMN parent_id INTEGER")
            self.conn.commit()
        # create an index on parent_id for faster child lookups
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id)")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS completions (
            task_id INTEGER,
            completed_at TEXT
        )
        """)
        # blocked_days: dates when the user cannot work (one-off dates with optional reason)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS blocked_days (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_blocked_days_date ON blocked_days(date)")
        self.conn.commit()

    def add_task(self, title: str, deadline: Optional[datetime], description: Optional[str] = None, duration: int = 0, reward: int = 0, penalty: int = 0, effort: int = 0, type: str = "shallow", parent_id: Optional[int] = None) -> int:
        """Create a task. Optional `parent_id` links this task as a subtask of an existing task."""
        created_at = datetime.now(timezone.utc).isoformat()
        deadline_s = deadline.isoformat() if deadline else None
        cur = self.conn.cursor()
        # validate parent exists if provided
        if parent_id is not None:
            cur.execute("SELECT id FROM tasks WHERE id = ?", (parent_id,))
            if cur.fetchone() is None:
                raise ValueError(f"parent_id {parent_id} does not exist")
        cur.execute(
            "INSERT INTO tasks (title, deadline, description, duration, reward, penalty, effort, type, created_at, parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (title, deadline_s, description, duration, reward, penalty, effort, type, created_at, parent_id),
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

    # Date-range and blocked-days helpers
    def get_tasks_between(self, start_dt: datetime, end_dt: datetime, include_completed: bool = False) -> List[sqlite3.Row]:
        """Return tasks with a non-null deadline where deadline >= start_dt and deadline < end_dt.
        Expects start_dt and end_dt to be timezone-aware datetimes. Will compare ISO strings.
        By default this excludes completed tasks unless include_completed=True.
        """
        cur = self.conn.cursor()
        start_s = start_dt.isoformat()
        end_s = end_dt.isoformat()
        sql = "SELECT * FROM tasks WHERE deadline IS NOT NULL AND deadline >= ? AND deadline < ?"
        if not include_completed:
            sql += " AND completed = 0"
        sql += " ORDER BY deadline"
        cur.execute(sql, (start_s, end_s))
        return cur.fetchall()

    def get_tasks_on(self, date_obj, tzinfo=None, include_completed: bool = False) -> List[sqlite3.Row]:
        """Return tasks whose deadlines fall on the provided date (date or YYYY-MM-DD string).
        The date is interpreted in the provided tzinfo (defaults to UTC). Excludes completed tasks by default.
        """
        from datetime import timezone, datetime as _datetime
        if isinstance(date_obj, str):
            d = _datetime.fromisoformat(date_obj).date()
        else:
            d = date_obj
        tz = tzinfo or timezone.utc
        start = _datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz).astimezone(timezone.utc)
        end = (start + __import__('datetime').timedelta(days=1))
        return self.get_tasks_between(start, end, include_completed=include_completed)

    def get_tasks_for_month(self, year: int, month: int, tzinfo=None, include_completed: bool = False) -> List[sqlite3.Row]:
        from datetime import datetime as _datetime, timezone
        tz = tzinfo or timezone.utc
        start_local = _datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
        # compute first of next month
        if month == 12:
            next_local = _datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=tz)
        else:
            next_local = _datetime(year, month + 1, 1, 0, 0, 0, tzinfo=tz)
        start_utc = start_local.astimezone(timezone.utc)
        end_utc = next_local.astimezone(timezone.utc)
        return self.get_tasks_between(start_utc, end_utc, include_completed=include_completed)

    def add_blocked_day(self, date_obj, reason: Optional[str] = None) -> int:
        """Add a blocked day. `date_obj` may be a date or a YYYY-MM-DD string. Returns inserted row id."""
        from datetime import datetime as _datetime
        if isinstance(date_obj, str):
            # accept 'YYYY-MM-DD'
            d = _datetime.fromisoformat(date_obj).date()
        else:
            d = date_obj
        date_s = d.isoformat()
        created_at = _datetime.now(timezone.utc).isoformat()
        cur = self.conn.cursor()
        cur.execute("INSERT INTO blocked_days (date, reason, created_at) VALUES (?, ?, ?)", (date_s, reason, created_at))
        self.conn.commit()
        return cur.lastrowid

    def remove_blocked_day(self, date_obj) -> int:
        """Remove blocked day(s) matching the date. Returns number of rows deleted."""
        if isinstance(date_obj, str):
            date_s = date_obj
        else:
            date_s = date_obj.isoformat()
        cur = self.conn.cursor()
        cur.execute("DELETE FROM blocked_days WHERE date = ?", (date_s,))
        self.conn.commit()
        return cur.rowcount

    def get_blocked_days_in_month(self, year: int, month: int) -> List[sqlite3.Row]:
        from datetime import date as _date
        start = _date(year, month, 1).isoformat()
        if month == 12:
            end = _date(year + 1, 1, 1).isoformat()
        else:
            end = _date(year, month + 1, 1).isoformat()
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM blocked_days WHERE date >= ? AND date < ? ORDER BY date", (start, end))
        return cur.fetchall()

    def mark_done(self, task_id: int):
        cur = self.conn.cursor()
        completed_at = datetime.now(timezone.utc).isoformat()
        cur.execute("UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?", (completed_at, task_id))
        cur.execute("INSERT INTO completions (task_id, completed_at) VALUES (?, ?)", (task_id, completed_at))
        self.conn.commit()
        # propagate up to parents: if all siblings are completed, mark parent done
        parent = cur.execute("SELECT parent_id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if parent:
            parent_id = parent[0]
            if parent_id is not None:
                self._propagate_done_up(parent_id)

    def mark_undone(self, task_id: int):
        """Mark a task as not completed and clear completed_at. Unmarks parents if necessary."""
        cur = self.conn.cursor()
        cur.execute("UPDATE tasks SET completed = 0, completed_at = NULL WHERE id = ?", (task_id,))
        self.conn.commit()
        # propagate up: if parent was marked completed, unmark it
        parent = cur.execute("SELECT parent_id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if parent:
            parent_id = parent[0]
            if parent_id is not None:
                self._propagate_undone_up(parent_id)
        return True

    # Helper methods for parent/child traversal and propagation
    def get_children(self, parent_id: int) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE parent_id = ? ORDER BY id", (parent_id,))
        return cur.fetchall()

    def get_task_with_children(self, task_id: int) -> Dict:
        t = self.get_task(task_id)
        if t is None:
            return None
        children = self.get_children(task_id)
        return {"task": t, "children": children}

    def _propagate_done_up(self, parent_id: int):
        cur = self.conn.cursor()
        # if parent has no incomplete children, mark it done and continue upward
        while parent_id is not None:
            incomplete = cur.execute("SELECT COUNT(*) FROM tasks WHERE parent_id = ? AND completed = 0", (parent_id,)).fetchone()[0]
            if incomplete == 0:
                completed_at = datetime.now(timezone.utc).isoformat()
                cur.execute("UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?", (completed_at, parent_id))
                cur.execute("INSERT INTO completions (task_id, completed_at) VALUES (?, ?)", (parent_id, completed_at))
                self.conn.commit()
                # move to parent's parent
                row = cur.execute("SELECT parent_id FROM tasks WHERE id = ?", (parent_id,)).fetchone()
                parent_id = row[0] if row else None
            else:
                break

    def _propagate_undone_up(self, parent_id: int):
        cur = self.conn.cursor()
        # if parent is completed, unmark it and continue upward
        while parent_id is not None:
            row = cur.execute("SELECT completed, parent_id FROM tasks WHERE id = ?", (parent_id,)).fetchone()
            if row is None:
                break
            completed = row[0]
            next_parent = row[1]
            if completed:
                cur.execute("UPDATE tasks SET completed = 0, completed_at = NULL WHERE id = ?", (parent_id,))
                self.conn.commit()
                parent_id = next_parent
            else:
                break

    def delete_task(self, task_id: int, cascade: bool = False):
        """Delete a task. If cascade is True, delete all descendants as well.

        If cascade is False and the task has children, raises ValueError.
        This method also removes rows from the completions table for deleted tasks.
        """
        cur = self.conn.cursor()
        # check existence
        row = cur.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise ValueError(f"Task {task_id} does not exist")

        # collect descendants if any
        def collect_descendants(tid, acc):
            children = cur.execute("SELECT id FROM tasks WHERE parent_id = ?", (tid,)).fetchall()
            for c in children:
                cid = c[0]
                acc.append(cid)
                collect_descendants(cid, acc)

        descendants = []
        collect_descendants(task_id, descendants)

        if descendants and not cascade:
            raise ValueError("Task has subtasks; use cascade=True to delete them")

        # build delete list
        to_delete = [task_id] + descendants
        # delete completions entries
        cur.execute(f"DELETE FROM completions WHERE task_id IN ({','.join(['?']*len(to_delete))})", tuple(to_delete))
        # delete tasks
        cur.execute(f"DELETE FROM tasks WHERE id IN ({','.join(['?']*len(to_delete))})", tuple(to_delete))
        self.conn.commit()
        return len(to_delete)

    def stats(self) -> Dict[str, int]:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as total FROM tasks")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) as done FROM tasks WHERE completed = 1")
        done = cur.fetchone()[0]
        return {"total": total, "done": done}

    def reset(self):
        """Reset the database by removing the file and creating a fresh DB.

        This is destructive. Callers should confirm with the user before invoking.
        """
        # Close existing connection
        try:
            self.conn.close()
        except Exception:
            pass
        # Remove file
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
        except Exception:
            pass
        # Recreate connection and schema
        self._ensure_dir()
        self.conn = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self.init_db()
        return True
