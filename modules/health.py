# ====================================================================
# PLACE AT: /app/modules/health.py
# ACTION: Replace existing file
# ====================================================================
"""
health.py — Tiny HTTP health-check server for Render free tier
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Render free-tier web services require an HTTP server listening on $PORT.
This module starts one in a background daemon thread so the Telegram bot
(long-polling) keeps running normally while Render's health checks pass.

Endpoints:
  GET /         → 200 "BeatVerse Bot is running 🤖"
  GET /health   → 200 JSON {"status":"ok","bot":"BeatVerseProbot"}
  HEAD /health  → 200 (for uptime monitors that use HEAD)
  anything else → 404

Keep-alive (prevents Render free tier 15-min sleep):
  Point UptimeRobot → https://<your-app>.onrender.com/health every 5 min.
"""

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

LOGGER = logging.getLogger(__name__)

PORT = int(os.environ.get("PORT", 10000))


class _HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # silence per-request logs
        pass

    def _send(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", ""):
            self._send(200, b"BeatVerse Bot is running \xf0\x9f\xa4\x96", "text/plain; charset=utf-8")
        elif self.path == "/health":
            body = json.dumps({"status": "ok", "bot": "BeatVerse Bot"}).encode()
            self._send(200, body, "application/json")
        else:
            self._send(404, b"Not Found", "text/plain")

    def do_HEAD(self):
        if self.path in ("/", "", "/health"):
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def _start_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), _HealthHandler)
        LOGGER.info("Health-check server listening on port %d", PORT)
        server.serve_forever()
    except OSError as e:
        LOGGER.error("Health-check server failed to start on port %d: %s", PORT, e)


# Daemon thread — dies automatically when the bot process exits
_t = threading.Thread(target=_start_server, name="HealthServer", daemon=True)
_t.start()

__mod_name__ = "Health"
__handlers__ = []
__command_list__ = []
# No __help__ — this module must NOT appear in the user-facing help menu
