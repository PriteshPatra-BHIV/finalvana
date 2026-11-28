import sys
import json
import time
from pathlib import Path
import pytest

FINALVANA_DIR = Path(__file__).resolve().parent
TESTS_DIR = FINALVANA_DIR / "tests"

test_files = [
    str(TESTS_DIR / "test_phase1_nagarpranali_alignment.py"),
    str(TESTS_DIR / "test_phase2_nagarpranali_build.py"),
    str(TESTS_DIR / "test_phase3_nagarpranali_integration.py"),
    str(TESTS_DIR / "test_phase4_nagarpranali_ux.py"),
    str(TESTS_DIR / "test_phase2_bucket_integration.py"),
]

print(f"Starting Phase 4 Test Suite execution on {len(test_files)} test modules...")
t0 = time.time()
exit_code = pytest.main(["-q", "--no-header"] + test_files)
elapsed = round(time.time() - t0, 3)

results = {
    "exit_code": int(exit_code),
    "success": exit_code == 0,
    "elapsed_seconds": elapsed,
    "test_modules": test_files,
}

report_path = FINALVANA_DIR / "phase4_verification_report.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"Phase 4 Test execution completed in {elapsed}s with exit code {exit_code}.")
sys.exit(exit_code)
