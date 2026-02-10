import os
import calendar as _calendar
from datetime import datetime, date, timezone, timedelta
from typing import Optional
from rich.table import Table
from rich.panel import Panel
from rich.console import RenderableType
from decidrx.db import Database
from decidrx.ui import console

DB_ENV = "DECIDRX_DB"


def _parse_ymd(s: str) -> date:
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        raise ValueError("date must be YYYY-MM-DD")


def _format_cell(day: int, count: int, blocked: bool, is_today: bool) -> str:
    """Return a formatted string for a calendar cell."""
    if day == 0:
        return ""
    txt = f"{day:2d}"
    if blocked:
        # blocked day has strong red background and a pad lock
        return f"[white on red]{txt} 🔒[/]"
    if count == 0:
        return f"[dim]{txt}[/]"
    if count <= 2:
        return f"[magenta]{txt} ({count})[/]"
    # many tasks
    return f"[bold magenta]{txt} ({count})[/]"


def _render_month(db: Database, year: int, month: int, use_local: bool = True, include_completed: bool = False) -> RenderableType:
    # choose tz
    if use_local:
        local_tz = datetime.now().astimezone().tzinfo
    else:
        local_tz = timezone.utc

    # compute start/end in local timezone and convert to UTC for DB queries
    start_local = datetime(year, month, 1, 0, 0, tzinfo=local_tz)
    if month == 12:
        next_local = datetime(year + 1, 1, 1, 0, 0, tzinfo=local_tz)
    else:
        next_local = datetime(year, month + 1, 1, 0, 0, tzinfo=local_tz)

    start_utc = start_local.astimezone(timezone.utc)
    end_utc = next_local.astimezone(timezone.utc)

    tasks = db.get_tasks_between(start_utc, end_utc, include_completed=include_completed)
    # map tasks to local date
    counts = {}
    for t in tasks:
        dl = t['deadline']
        if not dl:
            continue
        try:
            ddt = datetime.fromisoformat(dl)
            if ddt.tzinfo is None:
                ddt = ddt.replace(tzinfo=timezone.utc)
            d_local = ddt.astimezone(local_tz).date()
            counts[d_local] = counts.get(d_local, 0) + 1
        except Exception:
            continue

    blocked_rows = db.get_blocked_days_in_month(year, month)
    blocked = {datetime.fromisoformat(r['date']).date() if isinstance(r['date'], str) else r['date']: r for r in blocked_rows}

    cal = _calendar.Calendar(firstweekday=0)  # Monday=0 in earlier decision, keep default
    month_weeks = cal.monthdayscalendar(year, month)

    table = Table(title=f"{year}-{month:02d}")
    headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for h in headers:
        table.add_column(h)

    today = datetime.now().astimezone(local_tz).date()

    for week in month_weeks:
        row = []
        for day in week:
            if day == 0:
                row.append("")
                continue
            d = date(year, month, day)
            cnt = counts.get(d, 0)
            is_block = d in blocked
            is_today = (d == today)
            cell = _format_cell(day, cnt, is_block, is_today)
            row.append(cell)
        table.add_row(*row)

    legend = "[dim]Legend:[/dim] [magenta]1-2[/magenta] tasks, [bold magenta]3+[/bold magenta] tasks, [white on red]blocked[/]"

    return Panel(table, title=f"Calendar: {year}-{month:02d}", subtitle=legend, expand=False)


def _show_day(db: Database, date_str: str, use_local: bool = True, include_completed: bool = False):
    d = _parse_ymd(date_str)
    if use_local:
        local_tz = datetime.now().astimezone().tzinfo
    else:
        local_tz = timezone.utc
    # compute start and end local to convert to UTC range
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=local_tz)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)
    tasks = db.get_tasks_between(start_utc, end_utc, include_completed=include_completed)
    # blocked day info
    cur = db.conn.cursor()
    cur.execute("SELECT * FROM blocked_days WHERE date = ?", (d.isoformat(),))
    blocked = cur.fetchone()

    lines = []
    lines.append(f"Date: {d.isoformat()}")
    if blocked:
        lines.append(f"Blocked: Yes — {blocked['reason'] or ''}")
    else:
        lines.append("Blocked: No")

    if tasks:
        tbl = Table(title=f"Tasks on {d.isoformat()}")
        tbl.add_column("id", style="cyan")
        tbl.add_column("title", style="bold")
        tbl.add_column("deadline", style="magenta")
        tbl.add_column("left", style="green")
        from datetime import timezone as _tz
        now = datetime.now(_tz.utc)

        for t in tasks:
            dl = t['deadline'] or ""
            left = ""
            if dl:
                try:
                    ddt = datetime.fromisoformat(dl)
                    if ddt.tzinfo is None:
                        ddt = ddt.replace(tzinfo=timezone.utc)
                    left = str(int((ddt - now).total_seconds() // 3600)) + "h"
                except Exception:
                    pass
            tbl.add_row(str(t['id']), t['title'] or "", dl or "", left)
        console.print(Panel('\n'.join(lines)))
        console.print(tbl)
    else:
        console.print(Panel('\n'.join(lines)))


def cmd_calendar(args):
    db = Database(os.environ.get(DB_ENV))
    args_list = getattr(args, "args", []) or []
    use_local = getattr(args, "local", False) or True
    include_completed = getattr(args, "all", False)

    # If no args, render current month
    if not args_list:
        now = datetime.now()
        year = now.year
        month = now.month
        panel = _render_month(db, year, month, use_local=use_local, include_completed=include_completed)
        console.print(panel)
        return

    # If first token is a known subcommand, handle it
    first = args_list[0]
    if first in ("add", "remove", "show"):
        if len(args_list) < 2:
            console.print("Missing date argument")
            return
        date_token = args_list[1]
        if first == "add":
            reason = None
            # optional --reason value
            if "--reason" in args_list:
                idx = args_list.index("--reason")
                if idx + 1 < len(args_list):
                    reason = args_list[idx + 1]
            try:
                d = _parse_ymd(date_token)
            except ValueError as e:
                console.print(str(e))
                return
            rid = db.add_blocked_day(d, reason=reason)
            console.print(f"Added blocked day {d.isoformat()} (id={rid})")
            return
        if first == "remove":
            try:
                d = _parse_ymd(date_token)
            except ValueError as e:
                console.print(str(e))
                return
            cnt = db.remove_blocked_day(d)
            if cnt:
                console.print(f"Removed blocked day {d.isoformat()}")
            else:
                console.print(f"No blocked day found for {d.isoformat()}")
            return
        if first == "show":
            try:
                _show_day(db, date_token, use_local=use_local, include_completed=include_completed)
            except ValueError as e:
                console.print(str(e))
            return

    # New: support `decidrx calendar bad add|remove|list` aliases
    if first == "bad":
        # form: bad add YYYY-MM-DD [--reason R]
        if len(args_list) < 2:
            console.print("Usage: calendar bad add|remove|list ...")
            return
        sub = args_list[1]
        if sub == "add":
            if len(args_list) < 3:
                console.print("Missing date argument for bad add")
                return
            date_token = args_list[2]
            reason = None
            if "--reason" in args_list:
                idx = args_list.index("--reason")
                if idx + 1 < len(args_list):
                    reason = args_list[idx + 1]
            try:
                d = _parse_ymd(date_token)
            except ValueError as e:
                console.print(str(e))
                return
            rid = db.add_blocked_day(d, reason=reason)
            console.print(f"Added bad day {d.isoformat()} (id={rid})")
            return
        if sub == "remove":
            if len(args_list) < 3:
                console.print("Missing date argument for bad remove")
                return
            date_token = args_list[2]
            try:
                d = _parse_ymd(date_token)
            except ValueError as e:
                console.print(str(e))
                return
            cnt = db.remove_blocked_day(d)
            if cnt:
                console.print(f"Removed bad day {d.isoformat()}")
            else:
                console.print(f"No bad day found for {d.isoformat()}")
            return
        if sub == "list":
            # optional year month
            if len(args_list) >= 4:
                try:
                    y = int(args_list[2]); m = int(args_list[3])
                except Exception:
                    console.print("Invalid year/month for bad list")
                    return
                rows = db.get_blocked_days_in_month(y, m)
            else:
                # show all
                cur = db.conn.cursor()
                cur.execute("SELECT * FROM blocked_days ORDER BY date")
                rows = cur.fetchall()
            tbl = Table(title="Blocked days (bad)")
            tbl.add_column("date")
            tbl.add_column("reason")
            tbl.add_column("id", style="cyan")
            for r in rows:
                tbl.add_row(r["date"], r["reason"] or "", str(r["id"]))
            console.print(tbl)
            return

    # Otherwise, assume it's YEAR [MONTH]
    try:
        year = int(args_list[0])
        month = int(args_list[1]) if len(args_list) > 1 else None
    except Exception:
        console.print("Invalid arguments. Use `decidrx calendar YEAR MONTH` or `decidrx calendar add YYYY-MM-DD ...`")
        return
    if not month:
        now = datetime.now()
        month = now.month
    panel = _render_month(db, year, month, use_local=use_local)
    console.print(panel)
    return
