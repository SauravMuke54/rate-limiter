"""
A tiny, dependency-free mock upstream server for load testing.
Responds instantly to any path/method with a 200 JSON body.
Run alongside the rate limiter proxy during load tests.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sys


class MockHandler(BaseHTTPRequestHandler):
    def _respond(self):
        body = json.dumps({"ok": True, "path": self.path, "method": self.command}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._respond()

    def do_POST(self):
        self._respond()

    def do_PUT(self):
        self._respond()

    def do_DELETE(self):
        self._respond()

    def do_PATCH(self):
        self._respond()

    def log_message(self, format, *args):
        pass  # silence per-request logging so it doesn't spam your terminal under load


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    server = ThreadingHTTPServer(("localhost", port), MockHandler)
    print(f"Mock upstream running on http://localhost:{port}")
    server.serve_forever()
