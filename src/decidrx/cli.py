import argparse
from rich.table import Table

from .ui import console
from .prompt import parse_deadline, validate_args
from .commands.add import cmd_add as cmd_add
from .commands.now import cmd_now as cmd_now
from .commands.quick import cmd_quick as cmd_quick
from .commands.done import cmd_done as cmd_done
from .commands.stats import cmd_stats as cmd_stats
from .commands.show import cmd_show as cmd_show
from .commands.edit import cmd_edit as cmd_edit
from .commands.reset import cmd_reset as cmd_reset
from .commands.archive import cmd_archive as cmd_archive
from .commands.undone import cmd_undone as cmd_undone
from rich.panel import Panel

# Per-command examples to surface in help
EXAMPLES = {
    "add": (
        "decidrx add\n"
        "  # Interactive: prompts for fields if title omitted\n"
        "  decidrx add \"Write report\" --deadline 2 --duration 45 --reward 7\n"
        "  # Create subtask: --parent <parent_id> or use interactive 'Add subtasks' flow"
    ),
    "now": (
        "decidrx now  # shows ranked tasks by score (parents aggregated from subtasks when applicable)\n"
        "  # Use --limit to control how many are shown"
    ),
    "quick": "decidrx quick  # quick wins (short duration tasks, default <20 min)",
    "edit": (
        "decidrx edit 1 --title \"New title\"  # non-interactive edit (set fields via flags)\n"
        "  decidrx edit 1  # interactive edit prompts for fields"
    ),
    "show": (
        "decidrx show  # show pending tasks (nested subtasks are indented)\n"
        "  decidrx show --all  # include completed tasks in the view"
    ),
    "reset": (
        "decidrx reset  # interactively confirm and reset DB (destructive)\n"
        "  decidrx reset --yes  # force reset without prompt"
    ),
    "archive": "decidrx archive  # show every task in the DB (history view)",
    "remove": (
        "decidrx remove <task_id>  # delete a task; will ask to confirm if it has subtasks\n"
        "  decidrx remove <task_id> --yes  # delete without prompting (use in scripts)"
    ),
    "subtask": (
        "decidrx subtask add <parent_id> [title] [--flags]  # add a subtask to an existing task\n"
        "  decidrx subtask add <parent_id>  # interactive prompt flow\n"
        "  decidrx subtask list <parent_id>  # list children of a parent\n"
        "  decidrx subtask remove <parent_id> <child_id>  # remove a subtask (confirms)\n"
        "  decidrx subtask edit <parent_id> <child_id> [--flags]  # edit a subtask"
    ),
}


# Re-export console at module level so tests can patch cli.console


def build_parser():
    parser = argparse.ArgumentParser(
        prog="decidrx",
        description=(
            "DecidRX — CLI decision engine to rank and pick tasks to do now.\n\n"
            "Features:\n"
            " - Rank tasks to help you pick what to do now (urgency, reward, quick-wins)\n"
            " - Optional subtasks with parent/child relationships (nested display, cascading delete)\n"
            " - Interactive and non-interactive workflows for scripting and convenience"
        ),
        epilog=(
            "Examples:\n  decidrx add\n  decidrx now\n  decidrx quick\n  decidrx edit 1 --title 'New title'\n  decidrx help add\n\n"
            "Tip: Use `decidrx help <command>` for command-specific examples and flags."
        )
    )
    sub = parser.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add")
    # Make title optional so we can prompt interactively when it's omitted
    p_add.add_argument("title", nargs="?")
    p_add.add_argument("--deadline", type=int, help="deadline in days (from now)")
    p_add.add_argument("--description", type=str, help="Short description of the task")
    p_add.add_argument("--duration", type=int, default=0)
    p_add.add_argument("--reward", type=int, default=0)
    p_add.add_argument("--penalty", type=int, default=0)
    p_add.add_argument("--effort", type=int, default=0)
    p_add.add_argument("--type", choices=["deep", "shallow"], default="shallow")
    p_add.add_argument("--parent", type=int, help="Parent task id (make this a subtask)")
    p_add.set_defaults(func=cmd_add)

    p_now = sub.add_parser("now", help="Show a ranked list of tasks to do now")
    p_now.add_argument("--limit", type=int, default=5, help="How many tasks to show (default: 5)")
    p_now.set_defaults(func=cmd_now)

    p_quick = sub.add_parser("quick", help="Show quick-win tasks (short duration tasks prioritized)")
    p_quick.set_defaults(func=cmd_quick)

    p_done = sub.add_parser("done", help="Mark a task as completed (records completion time)")
    p_done.add_argument("task_id", type=int, help="ID of the task to mark done")
    p_done.set_defaults(func=cmd_done)

    p_edit = sub.add_parser("edit", help="Edit a task (interactive if no flags)" )
    p_edit.add_argument("task_id", type=int)
    p_edit.add_argument("--title")
    p_edit.add_argument("--deadline", type=int, help="deadline in days (from now)")
    p_edit.add_argument("--description", type=str, help="Short description of the task")
    p_edit.add_argument("--duration", type=int)
    p_edit.add_argument("--reward", type=int)
    p_edit.add_argument("--penalty", type=int)
    p_edit.add_argument("--effort", type=int)
    p_edit.add_argument("--type", choices=["deep", "shallow"])
    p_edit.add_argument("--parent", type=int, help="Set parent task id (use 0 to clear parent)")
    p_edit.add_argument("--interactive", action="store_true", help="Force interactive editing")
    p_edit.set_defaults(func=cmd_edit)

    p_undone = sub.add_parser("undone", help="Mark a task as not completed (undo a done)")
    p_undone.add_argument("task_id", type=int, help="ID of the task to unmark as done")
    p_undone.set_defaults(func=cmd_undone)

    p_help = sub.add_parser("help", help="Show help for commands")
    p_help.add_argument("subcommand", nargs="?", help="Command to show help for")
    p_help.set_defaults(func=cmd_help)

    p_stats = sub.add_parser("stats", help="Show aggregate counts for tasks (total, done)")
    p_stats.set_defaults(func=cmd_stats)

    p_reset = sub.add_parser("reset", help="Reset the database (destructive)")
    p_reset.add_argument("--yes", action="store_true", help="Skip confirmation and reset immediately")
    p_reset.set_defaults(func=cmd_reset)

    p_show = sub.add_parser("show", help="Show pending tasks in a readable table (subtasks indented)")
    p_show.add_argument("--all", action="store_true", help="Show all tasks including completed")
    p_show.set_defaults(func=cmd_show)

    p_archive = sub.add_parser("archive", help="Show all tasks irrespective of done status")
    p_archive.set_defaults(func=cmd_archive)

    p_remove = sub.add_parser("remove", help="Remove a task (asks to confirm and cascades to subtasks)")
    p_remove.add_argument("task_id", help="Task id to remove")
    p_remove.add_argument("--yes", action="store_true", help="Skip confirmation and remove immediately")
    from .commands.remove import cmd_remove as cmd_remove
    p_remove.set_defaults(func=cmd_remove)

    # subtask commands: add a new subtask under an existing task, or list subtasks
    p_sub = sub.add_parser("subtask", help="Manage subtasks for a parent task")
    sub_sub = p_sub.add_subparsers(dest="subtask_cmd")

    p_sub_add = sub_sub.add_parser("add", help="Add a subtask to an existing task")
    p_sub_add.add_argument("parent_id", help="Parent task id")
    p_sub_add.add_argument("title", nargs="?", help="Subtask title (omit for interactive)")
    p_sub_add.add_argument("--deadline", type=int, help="deadline in days (from now)")
    p_sub_add.add_argument("--description", type=str, help="Short description of the subtask")
    p_sub_add.add_argument("--duration", type=int, default=0)
    p_sub_add.add_argument("--reward", type=int, default=0)
    p_sub_add.add_argument("--penalty", type=int, default=0)
    p_sub_add.add_argument("--effort", type=int, default=0)
    p_sub_add.add_argument("--type", choices=["deep", "shallow"], default="shallow")
    from .commands.subtask import cmd_subtask_add as cmd_subtask_add
    p_sub_add.set_defaults(func=cmd_subtask_add)

    p_sub_list = sub_sub.add_parser("list", help="List subtasks for a parent task")
    p_sub_list.add_argument("parent_id", help="Parent task id")
    from .commands.subtask import cmd_subtask_list as cmd_subtask_list
    p_sub_list.set_defaults(func=cmd_subtask_list)

    p_sub_remove = sub_sub.add_parser("remove", help="Remove a subtask from a parent task")
    p_sub_remove.add_argument("parent_id", help="Parent task id")
    p_sub_remove.add_argument("child_id", help="Subtask id to remove")
    from .commands.subtask import cmd_subtask_remove as cmd_subtask_remove
    p_sub_remove.set_defaults(func=cmd_subtask_remove)

    p_sub_edit = sub_sub.add_parser("edit", help="Edit a subtask for a parent task")
    p_sub_edit.add_argument("parent_id", help="Parent task id")
    p_sub_edit.add_argument("child_id", help="Subtask id to edit")
    p_sub_edit.add_argument("--title")
    p_sub_edit.add_argument("--deadline", type=int, help="deadline in days (from now)")
    p_sub_edit.add_argument("--description", type=str)
    p_sub_edit.add_argument("--duration", type=int)
    p_sub_edit.add_argument("--reward", type=int)
    p_sub_edit.add_argument("--penalty", type=int)
    p_sub_edit.add_argument("--effort", type=int)
    p_sub_edit.add_argument("--type", choices=["deep", "shallow"])
    p_sub_edit.add_argument("--interactive", action="store_true", help="Force interactive editing")
    from .commands.subtask import cmd_subtask_edit as cmd_subtask_edit
    p_sub_edit.set_defaults(func=cmd_subtask_edit)

    return parser


def cmd_help(args):
    """Show general help or per-command help using the built parser, formatted with rich.Panel."""
    parser = build_parser()
    subcmd = getattr(args, "subcommand", None)
    if not subcmd:
        # general help as a panel
        content = parser.format_help()
        console.print(Panel(content, title="DecidRX Help", expand=False))
        return

    # locate subparser
    for action in parser._actions:
        if getattr(action, "__class__", None).__name__ == "_SubParsersAction":
            choices = getattr(action, "choices", {})
            sub = choices.get(subcmd)
            if sub:
                content = sub.format_help()
                # append examples if available
                ex = EXAMPLES.get(subcmd)
                if ex:
                    content = content + "\nExamples:\n" + ex
                console.print(Panel(content, title=f"Help: {subcmd}", expand=False))
                return
            else:
                console.print(Panel(f"No such command: {subcmd}", title="Error", expand=False))
                return


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()

