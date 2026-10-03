"""
VANA Control Center — Local Development Server & CORS Proxy Gateway
====================================================================
Serves the static web interface and transparently reverse-proxies
Group 1, Group 2, and Group 4 backend endpoints to eliminate CORS
and mixed-content issues during local development.

FOR LOCAL USE ONLY. In production (Vercel), the same /proxy/* routes
are handled by Vercel rewrites defined in vercel.json — no Python
server is required or used in production.

Proxy targets mirror vercel.json rewrites exactly:
  /proxy/g1  →  http://163.128.209.18:8013
  /proxy/g2  →  https://niyantran.blackholeinfiverse.com
  /proxy/g4  →  http://163.128.209.18:8010
"""

import http.server
import socketserver
import urllib.request
import urllib.error
import urllib.parse
import json
import os
import sys

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

TARGETS = {
    "/proxy/g1": "http://163.128.209.18:8013",
    "/proxy/g2": "https://niyantran.blackholeinfiverse.com",
    "/proxy/g4": "http://163.128.209.18:8010",
}

class VANAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, traceparent")
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

        target_url = target_base + subpath
        print(f"[VANA PROXY] {method} {self.path} -> {target_url}")

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else None

        req = urllib.request.Request(target_url, data=body, method=method)
        req.add_header("Content-Type", self.headers.get("Content-Type", "application/json"))
        req.add_header("User-Agent", "VANA-Control-Center-Proxy/2.2")

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
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/proxy/"):
            if self._handle_proxy("POST"):
                return
        self.send_error(404, "Endpoint not found")

def run():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), VANAHandler) as httpd:
        print(f"============================================================")
        print(f"  VANA Control Center Server Running at http://localhost:{PORT}")
        print(f"  Proxy Gateways:")
        print(f"    G1 -> http://localhost:{PORT}/proxy/g1 (163.128.209.18:8013)")
        print(f"    G2 -> http://localhost:{PORT}/proxy/g2 (niyantran.blackholeinfiverse.com)")
        print(f"    G4 -> http://localhost:{PORT}/proxy/g4 (163.128.209.18:8010)")
        print(f"============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down VANA Control Center server.")

if __name__ == "__main__":
    run()
