#!/usr/bin/env python3
"""Place matching: smallest circle wins, and the board JSON has no coordinates."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from places import format_when, match_place, place_line  # noqa: E402
import server  # noqa: E402


def main() -> None:
    places = [
        {"name": "Home", "lat": 47.6062, "lon": -122.3321, "radius_m": 500},
        {"name": "School", "lat": 47.6062, "lon": -122.3321, "radius_m": 120},
        {"name": "Blank", "lat": None, "lon": None, "radius_m": 100},
    ]
    assert match_place(47.6062, -122.3321, places) == "School"
    assert match_place(47.70, -122.20, places) is None
    words, ready = place_line(47.70, -122.20, places)
    assert ready and words == "Between saved places"
    words, ready = place_line(47.60, -122.33, [{"name": "Home", "lat": None, "lon": None, "radius_m": 100}])
    assert words == "Places not set" and ready is False

    moment = datetime(2026, 10, 10, 22, 11, tzinfo=timezone.utc)
    assert format_when(int(moment.timestamp()), "UTC", now=moment) == "10:11 PM"

    now_tst = int(time.time())
    fixture = Path("/tmp/family-board-fixture.json")
    fixture.write_text(
        json.dumps(
            [
                {
                    "username": "alex",
                    "device": "phone",
                    "lat": 47.6062,
                    "lon": -122.3321,
                    "tst": now_tst,
                    "tid": "AL",
                }
            ]
        )
    )
    places_file = Path("/tmp/family-board-places.json")
    places_file.write_text(json.dumps({"places": places}))
    roster = Path("/tmp/family-board-roster.json")
    roster.write_text(json.dumps([{"username": "alex", "display": "Alex"}, {"username": "sam", "display": "Sam"}]))
    os.environ["FIXTURE_LAST"] = str(fixture)
    os.environ["PLACES_FILE"] = str(places_file)
    os.environ["ROSTER_FILE"] = str(roster)
    os.environ["TZ"] = "UTC"
    os.environ["MAP_URL"] = "https://house.example.ts.net:8443/"
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/board") as response:
            payload = json.loads(response.read().decode())
        blob = json.dumps(payload)
        assert "lat" not in blob and "lon" not in blob and "47.6062" not in blob
        alex = next(person for person in payload["people"] if person["username"] == "alex")
        sam = next(person for person in payload["people"] if person["username"] == "sam")
        assert alex["place"] == "School"
        assert alex["time"] == format_when(now_tst, "UTC")
        assert sam["place"] == "No report yet"
        assert "few hundred meters" in payload["legend"]
        assert payload["map_url"].endswith(":8443/")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as response:
            html = response.read().decode()
        assert "Family" in html and "/api/board" in html
    finally:
        httpd.shutdown()
    print("board tests passed")


if __name__ == "__main__":
    main()
