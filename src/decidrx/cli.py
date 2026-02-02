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
from rich.panel import Panel

# Per-command examples to surface in help
EXAMPLES = {
    "add": "decidrx add\n  decidrx add \"Write report\" --deadline 2 --duration 45 --reward 7",
    "now": "decidrx now  # shows top task",
    "quick": "decidrx quick  # shows quick wins (<20 min)",
    "edit": "decidrx edit 1 --title \"New title\"  # non-interactive\n  decidrx edit 1  # interactive edit",
    "show": "decidrx show  # show pending tasks\n  decidrx show --all  # include completed tasks",
    "reset": "decidrx reset  # interactively confirm and reset DB\n  decidrx reset --yes  # force reset without prompt",
}


# Re-export console at module level so tests can patch cli.console


def build_parser():
    parser = argparse.ArgumentParser(
        prog="decidrx",
        description="DecidRX — CLI decision engine to rank and pick tasks to do now",
        epilog="Examples:\n  decidrx add\n  decidrx now\n  decidrx quick\n  decidrx edit 1 --title 'New title'\n  decidrx help add"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add")
    # Make title optional so we can prompt interactively when it's omitted
    p_add.add_argument("title", nargs="?")
    p_add.add_argument("--deadline", type=int, help="deadline in days (from now)")
    p_add.add_argument("--duration", type=int, default=0)
    p_add.add_argument("--reward", type=int, default=0)
    p_add.add_argument("--penalty", type=int, default=0)
    p_add.add_argument("--effort", type=int, default=0)
    p_add.add_argument("--type", choices=["deep", "shallow"], default="shallow")
    p_add.set_defaults(func=cmd_add)

    p_now = sub.add_parser("now")
    p_now.set_defaults(func=cmd_now)

    p_quick = sub.add_parser("quick")
    p_quick.set_defaults(func=cmd_quick)

    p_done = sub.add_parser("done")
    p_done.add_argument("task_id", type=int)
    p_done.set_defaults(func=cmd_done)

    p_edit = sub.add_parser("edit", help="Edit a task (interactive if no flags)" )
    p_edit.add_argument("task_id", type=int)
    p_edit.add_argument("--title")
    p_edit.add_argument("--deadline", type=int, help="deadline in days (from now)")
    p_edit.add_argument("--duration", type=int)
    p_edit.add_argument("--reward", type=int)
    p_edit.add_argument("--penalty", type=int)
    p_edit.add_argument("--effort", type=int)
    p_edit.add_argument("--type", choices=["deep", "shallow"])
    p_edit.add_argument("--interactive", action="store_true", help="Force interactive editing")
    p_edit.set_defaults(func=cmd_edit)

    p_help = sub.add_parser("help", help="Show help for commands")
    p_help.add_argument("subcommand", nargs="?", help="Command to show help for")
    p_help.set_defaults(func=cmd_help)

    p_stats = sub.add_parser("stats")
    p_stats.set_defaults(func=cmd_stats)

    p_reset = sub.add_parser("reset", help="Reset the database (destructive)")
    p_reset.add_argument("--yes", action="store_true", help="Skip confirmation and reset immediately")
    p_reset.set_defaults(func=cmd_reset)

    p_show = sub.add_parser("show")
    p_show.add_argument("--all", action="store_true", help="Show all tasks including completed")
    p_show.set_defaults(func=cmd_show)

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

if __name__ == "__main__":
    main()
