"""Vercel serverless function: GET /api/news.

This serves the latest committed X channel snapshot. Refresh data locally with:
python3 aggregator.py
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path


class handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - Vercel/BaseHTTPRequestHandler API
        data_path = Path(__file__).resolve().parents[1] / "data.json"
        try:
            body = data_path.read_bytes()
            json.loads(body.decode("utf-8"))
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "public, max-age=0, s-maxage=300, stale-while-revalidate=1800")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:  # noqa: BLE001
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
