import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
VENDOR=ROOT/'.vendor'
if not VENDOR.exists():VENDOR=ROOT.parent/'StabilityLab'/'.vendor'
if VENDOR.exists():sys.path.insert(0,str(VENDOR))
