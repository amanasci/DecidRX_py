import sys
from pathlib import Path

# Ensure local `src` is preferred over any installed package for all tests
ROOT = Path(__file__).resolve().parents[1]
SRC = str(ROOT / "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
# If an older installed decidrx package was already imported, remove it so the
# tests use the local package from `src`.
if "decidrx" in sys.modules:
    del sys.modules["decidrx"]
