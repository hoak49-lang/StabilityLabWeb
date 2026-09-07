"""Prefer the application-scoped, pinned scientific dependencies."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / '.vendor'
if VENDOR.is_dir():
    sys.path.insert(0, str(VENDOR))

