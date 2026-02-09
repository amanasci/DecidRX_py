from datetime import datetime, timezone, timedelta
from rich.prompt import Prompt, IntPrompt
from .ui import console


def parse_deadline(days: int) -> datetime:
    now = datetime.now(timezone.utc)
    return now + timedelta(days=days)


def prompt_str(prompt_text, current=None, required=False):
    while True:
        if current is None:
            resp = Prompt.ask(prompt_text, default="").strip()
        else:
            resp = Prompt.ask(prompt_text, default=str(current)).strip()
            if resp == "":
                return current
        if resp == "" and required:
            console.print("This field is required.")
            continue
        return resp


def prompt_int(prompt_text, current=0, minimum=None, maximum=None):
    while True:
        try:
            resp = IntPrompt.ask(prompt_text, default=current)
            val = int(resp)
            if minimum is not None and val < minimum:
                console.print(f"Value must be >= {minimum}.")
                continue
            if maximum is not None and val > maximum:
                console.print(f"Value must be <= {maximum}.")
                continue
            return val
        except Exception:
            console.print("Please enter a valid integer.")


def validate_args(args) -> bool:
    # Basic validations for non-interactive mode
    if getattr(args, "duration", 0) is not None and args.duration < 0:
        console.print("Duration must be >= 0.")
        return False
    for field in ("reward", "penalty", "effort"):
        v = getattr(args, field, 0) or 0
        if v < 0 or v > 10:
            console.print(f"{field.capitalize()} must be between 0 and 10.")
            return False
    if getattr(args, "deadline", None) is not None and args.deadline < 0:
        console.print("Deadline must be >= 0.")
        return False
    if getattr(args, "type", None) not in ("deep", "shallow"):
        console.print("Type must be 'deep' or 'shallow'.")
        return False
    return True
