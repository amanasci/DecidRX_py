<!-- Adding logo from images/DecidRX.svg -->
![DecidRX Logo](images/DecidRX.svg)

🔧 DecidRX is a lightweight terminal-first decision engine that tells you *what to do right now*. It ranks your tasks based on deadlines, effort, reward and penalty so you can reduce decision fatigue and get daily wins.

---

## Quick facts

- Language: Python (>=3.10)
- CLI entrypoint: `decidrx`
- DB: SQLite (defaults to `~/.local/share/decidrx/decidrx.db`)
- Key dependency: `rich`

---

## Installation

Recommended: create a virtual environment and install in editable mode so you can iterate:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

You can also use `pip install .` for a normal install.

---

## Usage (examples) ✨

- Add a task (interactive):

```bash
decidrx add
# Prompts: title, deadline (days), duration (min), reward (1-10), penalty (1-10), effort (1-10), type (deep/shallow)
```

- Add non-interactive:

```bash
decidrx add "Write report" --deadline 2 --duration 45 --reward 7 --penalty 2 --effort 3 --type deep
```

- Ask what to do now:

```bash
decidrx now
```

- Show quick wins (<20 min):

```bash
decidrx quick
```

- Edit a task (non-interactive or interactive):

```bash
decidrx edit 1 --title "New title" --duration 20
# or
decidrx edit 1   # opens interactive prompt
```

- Show tasks (pending or all):

```bash
decidrx show        # pending
decidrx show --all  # include completed
```

- Mark task done:

```bash
decidrx done 3
```

- Daily stats:

```bash
decidrx stats
```

- Read the pretty help:

```bash
decidrx help
decidrx help add
```

---

## Configuration

- `DECIDRX_DB`: set this environment variable to point to an alternate SQLite DB file for testing or multi-profile use. Example:

```bash
export DECIDRX_DB=/tmp/decidrx-test.db
```

---

## Development & Tests

Run the unit tests with pytest (inside the virtualenv):

```bash
.venv/bin/pytest -q
```

Code is organized into small modules under `src/decidrx/` and `src/decidrx/commands/` so adding commands or features is straightforward.

---

## Contributing

Contributions welcome! Open issues or PRs with small, focused changes. Add tests for new behavior and keep the public CLI consistent.


