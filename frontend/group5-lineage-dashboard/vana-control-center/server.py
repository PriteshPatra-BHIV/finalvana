"""
VANA Control Center — Local Development Server & CORS Proxy Gateway
====================================================================
Serves the static web interface and transparently reverse-proxies
Group 1, Group 2, Group 4, and Auth endpoints during local development.

FOR LOCAL DEV ONLY. On the VM in production, the same /proxy/* routes
are handled by Nginx (see nginx.conf.template) using values from .env.

Environment variables (loaded from root .env if present):
  VANA_FRONTEND_PORT : Local listen port (default: 8080)
  VANA_BACKEND_URL   : Auth & Group 4 base URL (default: http://localhost:8000)
  VANA_G1_URL        : Group 1 MasterDB URL (default: http://127.0.0.1:8013)
  VANA_G2_URL        : Group 2 Pravah API URL (default: https://niyantran.blackholeinfiverse.com)
  VANA_G4_URL        : Group 4 SANSKAR URL (default: VANA_BACKEND_URL)
  VANA_CORS_ORIGINS  : CORS allow origin header (default: *)
"""

import http.server
import socketserver
import urllib.request
import urllib.error
import urllib.parse
import json
import os
import sys
from pathlib import Path

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = Path(DIRECTORY).resolve().parents[2]


def _load_dotenv_if_present():
    env_file = REPO_ROOT / ".env"
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


_load_dotenv_if_present()

PORT = int(os.environ.get("VANA_FRONTEND_PORT", "8080"))
CORS_ALLOW_ORIGIN = os.environ.get("VANA_CORS_ORIGINS", "*").split(",")[0].strip() or "*"

# Unified runtime base URL for authentication and governed execution.
UNIFIED_BACKEND = os.environ.get(
    "VANA_BACKEND_URL",
    os.environ.get("VITE_API_URL", "http://localhost:8000")
).rstrip("/")

DEFAULT_G1 = "http://127.0.0.1:8013"

TARGETS = {
    "/proxy/auth": UNIFIED_BACKEND + "/auth",
    "/proxy/g1": os.environ.get("VANA_G1_URL", DEFAULT_G1).rstrip("/"),
    "/proxy/g2": os.environ.get("VANA_G2_URL", "https://niyantran.blackholeinfiverse.com").rstrip("/"),
    "/proxy/g4": os.environ.get("VANA_G4_URL", UNIFIED_BACKEND).rstrip("/"),
}

# Explicitly allowed subpaths for authentication to prevent open proxy misuse
ALLOWED_AUTH_SUBPATHS = {"/login", "/me", "/logout"}

class VANAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", CORS_ALLOW_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, traceparent, Idempotency-Key, X-Product-Id, X-API-Key")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def _handle_proxy(self, method="GET"):
        matched_prefix = None
        target_base = None
        for prefix, base in TARGETS.items():
            if self.path.startswith(prefix):
                matched_prefix = prefix
                target_base = base
                break

        if not matched_prefix:
            return False

        subpath = self.path[len(matched_prefix):]
        if not subpath.startswith("/"):
            subpath = "/" + subpath

        # Prevent path traversal and enforce security boundaries
        parsed = urllib.parse.urlparse(subpath)
        clean_path = os.path.normpath(parsed.path).replace("\\", "/")
        if ".." in clean_path or clean_path.startswith("../"):
            self.send_error(400, "Bad Request: Path traversal prohibited")
            return True

        # Restrict /proxy/auth to explicitly expected authentication routes
        if matched_prefix == "/proxy/auth":
            base_subpath = clean_path.rstrip("/")
            if base_subpath in ("/register", "register"):
                err_payload = json.dumps({
                    "error": "Registration Disabled",
                    "message": "Public registration is disabled. VANA operates under a strict predefined role-based access control policy.",
                    "status_code": 403
                }).encode("utf-8")
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err_payload)))
                self.end_headers()
                self.wfile.write(err_payload)
                return True
            if base_subpath not in ALLOWED_AUTH_SUBPATHS:
                self.send_error(404, "Endpoint not found on auth proxy")
                return True

        target_url = target_base + subpath
        # Log method and path ONLY — NEVER log authorization header or tokens
        print(f"[VANA PROXY] {method} {self.path} -> {target_url}")

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else None

        req = urllib.request.Request(target_url, data=body, method=method)
        req.add_header("Content-Type", self.headers.get("Content-Type", "application/json"))
        req.add_header("User-Agent", "VANA-Control-Center-Proxy/2.2")

        # Forward Authorization header safely without logging
        auth_header = self.headers.get("Authorization")
        if auth_header:
            req.add_header("Authorization", auth_header)

        # Forward Accept and custom VANA governance headers
        accept_header = self.headers.get("Accept")
        if accept_header:
            req.add_header("Accept", accept_header)

        for custom_hdr in ["Idempotency-Key", "X-Product-Id", "X-API-Key"]:
            hdr_val = self.headers.get(custom_hdr)
            if hdr_val:
                req.add_header(custom_hdr, hdr_val)

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)
                return True
        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)
            return True
        except Exception as e:
            err_payload = json.dumps({"error": "Proxy Error", "detail": str(e), "target_url": target_url}).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err_payload)))
            self.end_headers()
            self.wfile.write(err_payload)
            return True

    def do_GET(self):
        if self.path.startswith("/proxy/"):
            if self._handle_proxy("GET"):
                return

        parsed = urllib.parse.urlparse(self.path)
        clean_path = parsed.path.rstrip("/")
        if clean_path in ("/login", "login"):
            self.path = "/login.html" + (("?" + parsed.query) if parsed.query else "")
        elif clean_path in ("/admin", "admin"):
            self.path = "/admin.html" + (("?" + parsed.query) if parsed.query else "")
        elif clean_path in ("/field-agent", "/forest-officer"):
            role_param = "FIELD_AGENT" if "field" in clean_path else "FOREST_OFFICER"
            query = f"role={role_param}" + (("&" + parsed.query) if parsed.query else "")
            self.path = "/index.html?" + query

        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/proxy/"):
            if self._handle_proxy("POST"):
                return
        self.send_error(404, "Endpoint not found")

    def do_PUT(self):
        if self.path.startswith("/proxy/"):
            if self._handle_proxy("PUT"):
                return
        self.send_error(404, "Endpoint not found")

    def do_DELETE(self):
        if self.path.startswith("/proxy/"):
            if self._handle_proxy("DELETE"):
                return
        self.send_error(404, "Endpoint not found")

def run():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), VANAHandler) as httpd:
        print(f"============================================================")
        print(f"  VANA Control Center Server Running at http://localhost:{PORT}")
        print(f"  Proxy Gateways:")
        print(f"    Auth -> http://localhost:{PORT}/proxy/auth ({TARGETS['/proxy/auth']})")
        print(f"    G1   -> http://localhost:{PORT}/proxy/g1 ({TARGETS['/proxy/g1']})")
        print(f"    G2   -> http://localhost:{PORT}/proxy/g2 ({TARGETS['/proxy/g2']})")
        print(f"    G4   -> http://localhost:{PORT}/proxy/g4 ({TARGETS['/proxy/g4']})")
        print(f"============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down VANA Control Center server.")

if __name__ == "__main__":
    run()
