#!/usr/bin/env python3
"""Household board. Place name and report time. No coordinates in the response."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from places import format_when, place_line

ROOT = Path(__file__).resolve().parent
LEGEND = (
    "iPhone: the time moves when that phone sends a report, usually after a move "
    "of a few hundred meters. Pixel: the time also moves about every 15 minutes "
    "while the phone is still."
)


def load_json(path: str, fallback):
    file = Path(path)
    if not path or not file.is_file():
        return fallback
    return json.loads(file.read_text())


def recorder_last() -> list[dict]:
    fixture = os.environ.get("FIXTURE_LAST", "")
    if fixture:
        return json.loads(Path(fixture).read_text())
    url = os.environ.get("RECORDER_URL", "http://recorder:8083").rstrip("/") + "/api/0/last"
    with urlopen(url, timeout=5) as response:
        body = json.loads(response.read().decode())
    if isinstance(body, dict):
        return body.get("results") or body.get("data") or []
    return body or []


def board_payload() -> dict:
    tz_name = os.environ.get("TZ", "UTC")
    places_doc = load_json(os.environ.get("PLACES_FILE", ""), {"places": []})
    places = places_doc.get("places", []) if isinstance(places_doc, dict) else []
    roster = load_json(os.environ.get("ROSTER_FILE", ""), [])
    names = {person["username"]: person.get("display") or person["username"] for person in roster}
    order = [person["username"] for person in roster]
    people = []
    seen = set()
    rows = []
    try:
        rows = recorder_last()
        recorder_error = False
    except Exception:
        recorder_error = True
        rows = []
    for row in rows:
        username = row.get("username") or ""
        if not username:
            continue
        seen.add(username)
        lat = row.get("lat")
        lon = row.get("lon")
        tst = row.get("tst")
        if lat is None or lon is None or tst is None:
            place = "No report yet"
            when = ""
        else:
            place, _ready = place_line(float(lat), float(lon), places)
            when = format_when(int(tst), tz_name)
        people.append(
            {
                "username": username,
                "display": names.get(username, username),
                "place": place,
                "time": when,
            }
        )
    for username in order:
        if username in seen:
            continue
        people.append(
            {
                "username": username,
                "display": names.get(username, username),
                "place": "No report yet",
                "time": "",
            }
        )
    people.sort(key=lambda person: (order.index(person["username"]) if person["username"] in order else 99, person["display"]))
    return {
        "legend": LEGEND,
        "map_url": os.environ.get("MAP_URL", ""),
        "recorder_error": recorder_error,
        "people": people,
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path.split("?", 1)[0] == "/api/board":
            payload = json.dumps(board_payload()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path.split("?", 1)[0] in ("/", "/index.html"):
            body = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:
        return


def main() -> None:
    port = int(os.environ.get("PORT", "8787"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
