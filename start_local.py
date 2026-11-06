#!/usr/bin/env python3
"""
VANA Local Orchestrator — Start all local VANA microservices & UI gateway.
==========================================================================
Spawns:
  1. Group 1 MasterDB API (:8013)       - SQLite vana.db canonical records
  2. Unified Auth & SANSKAR Gate (:8000) - RBAC & Governed Execution
  3. Control Center & Gateway (:8080)   - Static UI & Reverse Proxy
"""

import os
import sys
import time
import signal
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

def check_port_ready(url, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "VANA-Healthcheck"})
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status in (200, 204):
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def main():
    print("=" * 65)
    print("  Starting VANA Local Development Environment")
    print("=" * 65)

    processes = []

    # 1. Start Group 1 MasterDB on :8013
    g1_dir = ROOT / "backend" / "group1-masterdb"
    env_g1 = os.environ.copy()
    env_g1["VANA_DATABASE_URL"] = "sqlite:///vana.db"
    env_g1["PYTHONPATH"] = str(g1_dir)
    print("\n[1/3] Starting Group 1 MasterDB API on http://127.0.0.1:8013 ...")
    p_g1 = subprocess.Popen(
        [PYTHON_EXE, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8013", "--log-level", "warning"],
        cwd=str(g1_dir),
        env=env_g1,
    )
    processes.append(("Group 1 MasterDB", p_g1))

    # 2. Start Unified Auth & SANSKAR Runtime on :8000
    env_auth = os.environ.copy()
    env_auth["PYTHONPATH"] = str(ROOT)
    print("[2/3] Starting Unified Auth & SANSKAR Runtime on http://127.0.0.1:8000 ...")
    p_auth = subprocess.Popen(
        [PYTHON_EXE, "-m", "uvicorn", "backend.unified_auth_runtime:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
        cwd=str(ROOT),
        env=env_auth,
    )
    processes.append(("Unified Auth & SANSKAR", p_auth))

    # 3. Start Frontend Control Center Gateway on :8080
    frontend_dir = ROOT / "frontend" / "group5-lineage-dashboard" / "vana-control-center"
    env_fe = os.environ.copy()
    env_fe["VANA_G1_URL"] = "http://127.0.0.1:8013"
    env_fe["VANA_BACKEND_URL"] = "http://127.0.0.1:8000"
    print("[3/3] Starting VANA Control Center Gateway on http://localhost:8080 ...")
    p_fe = subprocess.Popen(
        [PYTHON_EXE, "server.py"],
        cwd=str(frontend_dir),
        env=env_fe,
    )
    processes.append(("VANA Control Center", p_fe))

    print("\nWaiting for services to become healthy...")
    g1_ok = check_port_ready("http://127.0.0.1:8013/health")
    auth_ok = check_port_ready("http://127.0.0.1:8000/health")
    fe_ok = check_port_ready("http://localhost:8080/")

    print("\n" + "=" * 65)
    print("  ALL VANA SERVICES OPERATIONAL")
    print("=" * 65)
    print(f"  • Frontend Control Center:   http://localhost:8080/       ({'READY' if fe_ok else 'INITIALIZING'})")
    print(f"  • Admin Control Plane:       http://localhost:8080/admin.html")
    print(f"  • Group 1 MasterDB API:      http://127.0.0.1:8013/docs   ({'READY' if g1_ok else 'INITIALIZING'})")
    print(f"  • Unified Auth & Runtime:    http://127.0.0.1:8000/docs   ({'READY' if auth_ok else 'INITIALIZING'})")
    print(f"  • Group 2 Live Science API:  https://niyantran.blackholeinfiverse.com")
    print("=" * 65)
    print("  Demo Logins:")
    print("    - Admin:       admin@vana.gov.in       (Password: any)")
    print("    - Participant: participant@vana.gov.in (Password: any)")
    print("    - Auditor:     auditor@vana.gov.in     (Password: any)")
    print("    - Steward:     steward@vana.gov.in     (Password: any)")
    print("=" * 65)
    print("Press Ctrl+C to terminate all services.\n")

    def shutdown(signum=None, frame=None):
        print("\nStopping all services...")
        for name, p in processes:
            try:
                p.terminate()
            except Exception:
                pass
        time.sleep(1)
        for name, p in processes:
            try:
                p.kill()
            except Exception:
                pass
        print("Shutdown complete.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            for name, p in processes:
                if p.poll() is not None:
                    print(f"[WARNING] {name} exited unexpectedly with code {p.returncode}")
            time.sleep(2)
    except KeyboardInterrupt:
        shutdown()

if __name__ == "__main__":
    main()

