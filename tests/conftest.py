import sys
from pathlib import Path

FINALVANA_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = FINALVANA_DIR / "backend"
MASTERDB_DIR = BACKEND_DIR / "group1-masterdb"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(MASTERDB_DIR) not in sys.path:
    sys.path.insert(0, str(MASTERDB_DIR))
