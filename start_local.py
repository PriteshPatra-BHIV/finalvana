#!/usr/bin/env python3
"""
VANA Local Orchestrator — Start all local VANA microservices & UI gateway.
==========================================================================
FOR LOCAL DEVELOPMENT ONLY (production VM deployment uses Docker / Nginx / systemd).

Reads optional overrides from root `.env` (without overriding existing OS env vars):
  - VANA_G1_PORT       (default: 8013)
  - VANA_AUTH_PORT     (default: 8000)
  - VANA_FRONTEND_PORT (default: 8080)
  - VANA_DATABASE_URL  (default: sqlite:///vana.db)
  - VANA_G2_URL        (default: https://niyantran.blackholeinfiverse.com)
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


def load_dotenv_if_present():
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    try:
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, val)
    except Exception:
        pass


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
    load_dotenv_if_present()

    g1_port = os.environ.get("VANA_G1_PORT", "8013")
    auth_port = os.environ.get("VANA_AUTH_PORT", "8000")
    fe_port = os.environ.get("VANA_FRONTEND_PORT", "8080")
    g2_url = os.environ.get("VANA_G2_URL", "https://niyantran.blackholeinfiverse.com")

    print("=" * 65)
    print("  Starting VANA Local Development Environment")
    print("=" * 65)

    processes = []

    # 1. Start Group 1 MasterDB
    g1_dir = ROOT / "backend" / "group1-masterdb"
    env_g1 = os.environ.copy()
    env_g1.setdefault("VANA_ENV", "development")
    env_g1.setdefault("VANA_DATABASE_URL", "sqlite:///vana.db")
    env_g1["PYTHONPATH"] = str(g1_dir)
    print(f"\n[1/3] Starting Group 1 MasterDB API on http://127.0.0.1:{g1_port} ...")
    p_g1 = subprocess.Popen(
        [PYTHON_EXE, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", g1_port, "--log-level", "warning"],
        cwd=str(g1_dir),
        env=env_g1,
    )
    processes.append(("Group 1 MasterDB", p_g1))

    # 2. Start Unified Auth & SANSKAR Runtime
    env_auth = os.environ.copy()
    env_auth.setdefault("VANA_ENV", "development")
    env_auth["PYTHONPATH"] = str(ROOT)
    print(f"[2/3] Starting Unified Auth & SANSKAR Runtime on http://127.0.0.1:{auth_port} ...")
    p_auth = subprocess.Popen(
        [PYTHON_EXE, "-m", "uvicorn", "backend.unified_auth_runtime:app", "--host", "127.0.0.1", "--port", auth_port, "--log-level", "warning"],
        cwd=str(ROOT),
        env=env_auth,
    )
    processes.append(("Unified Auth & SANSKAR", p_auth))

    # 3. Start Frontend Control Center Gateway
    frontend_dir = ROOT / "frontend" / "group5-lineage-dashboard" / "vana-control-center"
    env_fe = os.environ.copy()
    env_fe.setdefault("VANA_FRONTEND_PORT", fe_port)
    env_fe.setdefault("VANA_G1_URL", f"http://127.0.0.1:{g1_port}")
    env_fe.setdefault("VANA_BACKEND_URL", f"http://127.0.0.1:{auth_port}")
    env_fe.setdefault("VANA_G4_URL", f"http://127.0.0.1:{auth_port}")
    print(f"[3/3] Starting VANA Control Center Gateway on http://localhost:{fe_port} ...")
    p_fe = subprocess.Popen(
        [PYTHON_EXE, "server.py"],
        cwd=str(frontend_dir),
        env=env_fe,
    )
    processes.append(("VANA Control Center", p_fe))

    print("\nWaiting for services to become healthy...")
    g1_ok = check_port_ready(f"http://127.0.0.1:{g1_port}/health")
    auth_ok = check_port_ready(f"http://127.0.0.1:{auth_port}/health")
    fe_ok = check_port_ready(f"http://localhost:{fe_port}/")

    print("\n" + "=" * 65)
    print("  ALL VANA SERVICES OPERATIONAL")
    print("=" * 65)
    print(f"  - Frontend Control Center:   http://localhost:{fe_port}/       ({'READY' if fe_ok else 'INITIALIZING'})")
    print(f"  - Admin Control Plane:       http://localhost:{fe_port}/admin")
    print(f"  - Group 1 MasterDB API:      http://127.0.0.1:{g1_port}/docs   ({'READY' if g1_ok else 'INITIALIZING'})")
    print(f"  - Unified Auth & Runtime:    http://127.0.0.1:{auth_port}/docs   ({'READY' if auth_ok else 'INITIALIZING'})")
    print(f"  - Group 2 Science API:       {g2_url}")
    print("=" * 65)
    print("  Accounts are seeded via VANA_*_EMAIL / VANA_*_PASSWORD env vars.")
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
