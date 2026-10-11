#!/usr/bin/env python3
"""Publish one point into a localhost recorder and read it back.

Run only while deploy/compose.local.yml is up. This checks the storage path
on a computer that has Docker. It does not open a public port.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mqtt_probe import MqttSession, connect_packet, publish_packet  # noqa: E402


def main() -> None:
    secrets_path = ROOT / "generated" / "secrets.json"
    if not secrets_path.exists():
        raise SystemExit("Run scripts/bootstrap.py before this check.")
    secrets = json.loads(secrets_path.read_text())
    person = secrets["members"][0]
    session = MqttSession("127.0.0.1", 1883)
    try:
        session.send(connect_packet("localcheck", person["username"], person["password"]))
        ptype, body = session.recv()
        if ptype != 0x20 or body[1] != 0:
            raise SystemExit(f"broker rejected the check login, code {body[1] if body else 'none'}")
        payload = json.dumps(
            {
                "_type": "location",
                "lat": 47.6062,
                "lon": -122.3321,
                "tst": int(time.time()),
                "acc": 10,
                "tid": person["tid"],
                "t": "u",
            }
        )
        # The probe publishes a raw string. OwnTracks publishes JSON.
        session.send(publish_packet(f"owntracks/{person['username']}/phone", payload, 1))
        session.recv()
    finally:
        session.close()

    with urllib.request.urlopen("http://127.0.0.1:8083/api/0/last", timeout=5) as response:
        body = response.read().decode()
    if person["username"] not in body or "47.6062" not in body:
        raise SystemExit(f"recorder did not store the point: {body[:300]}")
    print(f"recorder stored a point for {person['username']}")


if __name__ == "__main__":
    main()
