#!/usr/bin/env python3
"""Prove the generated broker config, then connect to a local Mosquitto."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bootstrap  # noqa: E402
from mqtt_probe import (  # noqa: E402
    MqttSession,
    connect_packet,
    decode_publish,
    publish_packet,
    subscribe_packet,
)


def fail(message: str) -> None:
    raise SystemExit(message)


def assert_true(cond: bool, message: str) -> None:
    if not cond:
        fail(message)


def check_static() -> None:
    compose = (ROOT / "deploy" / "compose.yml").read_text()
    broker = (ROOT / "deploy" / "mosquitto" / "mosquitto.conf").read_text()
    recorder = (ROOT / "deploy" / "recorder-entrypoint.sh").read_text()
    frontend = (ROOT / "deploy" / "frontend" / "config.js").read_text()
    caddy = (ROOT / "deploy" / "Caddyfile").read_text()
    assert_true("127.0.0.1:1883:1883" in compose, "broker must be loopback-only")
    assert_true("127.0.0.1:8080:8080" in compose, "board must be loopback-only")
    assert_true('"80:80"' not in compose and '"443:443"' not in compose, "compose still publishes public web ports")
    assert_true("auto_https off" in caddy, "Caddy still requests public certificates")
    assert_true("ACME" not in caddy, "Caddyfile still names a certificate account")
    assert_true("allow_anonymous false" in broker, "broker allows anonymous clients")
    assert_true("protocol websockets" in broker, "websocket listener missing")
    assert_true("--norevgeo" in recorder, "recorder can call a geocoder")
    assert_true("openstreetmap.org" in frontend, "map tiles are not OpenStreetMap")
    assert_true("mapbox" not in frontend.lower() and "google" not in frontend.lower(), "frontend names a tile company")


def connack(session: MqttSession, client_id: str, username: str | None, password: str | None) -> int:
    session.send(connect_packet(client_id, username, password))
    ptype, body = session.recv()
    assert_true(ptype == 0x20, f"expected CONNACK, got {ptype:#x}")
    return body[1]


def wait_port(port: int) -> None:
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return
        except OSError:
            time.sleep(0.1)
    fail(f"broker did not open {port}")


def collect_messages(session: MqttSession, seconds: float) -> list[str]:
    session.sock.settimeout(0.4)
    found: list[str] = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            ptype, body = session.recv()
        except (TimeoutError, socket.timeout):
            continue
        except ConnectionError:
            break
        if ptype & 0xF0 == 0x30:
            _topic, payload = decode_publish(ptype, body)
            found.append(payload)
    session.sock.settimeout(5)
    return found


def live_broker(dest: Path) -> None:
    secrets = json.loads((dest / "secrets.json").read_text())
    alice = secrets["members"][0]
    bob = secrets["members"][1]
    data = dest / "mosquitto-data"
    data.mkdir()
    prod = (ROOT / "deploy" / "mosquitto" / "mosquitto.conf").read_text()
    conf = prod.replace("/mosquitto/config/passwd", str(dest / "mosquitto" / "passwd"))
    conf = conf.replace("/mosquitto/config/acl", str(dest / "mosquitto" / "acl"))
    conf = conf.replace("persistence_location /mosquitto/data/", f"persistence_location {data}/")
    conf = conf.replace("listener 1883\n", "listener 18831 127.0.0.1\n")
    conf = conf.replace("listener 9001\n", "listener 19001 127.0.0.1\n")
    conf_path = dest / "mosquitto.test.conf"
    conf_path.write_text(conf)
    binary = "/opt/homebrew/opt/mosquitto/sbin/mosquitto"
    if not Path(binary).is_file():
        found = shutil.which("mosquitto")
        if not found:
            fail("mosquitto is not installed")
        binary = found
    proc = subprocess.Popen(
        [binary, "-c", str(conf_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_port(18831)
        wait_port(19001)
        anon = MqttSession("127.0.0.1", 18831)
        try:
            code = connack(anon, "anon", None, None)
            assert_true(code != 0, "anonymous login was accepted")
        finally:
            anon.close()

        bad = MqttSession("127.0.0.1", 18831)
        try:
            code = connack(bad, "bad", alice["username"], "wrong-password")
            assert_true(code != 0, "wrong password was accepted")
        finally:
            bad.close()

        reader = MqttSession("127.0.0.1", 18831)
        writer = MqttSession("127.0.0.1", 18831)
        try:
            assert_true(connack(reader, "bobreader", bob["username"], bob["password"]) == 0, "bob rejected")
            reader.send(subscribe_packet("owntracks/#"))
            ptype, body = reader.recv()
            assert_true(ptype == 0x90 and body[-1] <= 2, f"subscribe failed: {ptype:#x} {body!r}")
            assert_true(connack(writer, "alicewriter", alice["username"], alice["password"]) == 0, "alice rejected")
            own = f"owntracks/{alice['username']}/phone"
            writer.send(publish_packet(own, "ALICE-OK", 1))
            ptype, _body = writer.recv()
            assert_true(ptype == 0x40, "alice did not get PUBACK for her own topic")
            seen = collect_messages(reader, 2)
            assert_true("ALICE-OK" in seen, f"bob did not receive alice: {seen}")

            writer.send(publish_packet(f"owntracks/{bob['username']}/phone", "SPOOF", 2))
            try:
                writer.recv()
            except (ConnectionError, TimeoutError, socket.timeout):
                pass
            leaked = collect_messages(reader, 1.5)
            assert_true("SPOOF" not in leaked, "alice published as bob")
        finally:
            reader.close()
            writer.close()

        for path in ("/mqtt", "/"):
            ws = MqttSession("127.0.0.1", 19001, path)
            plain = MqttSession("127.0.0.1", 18831)
            try:
                assert_true(
                    connack(ws, f"ws{path.strip('/') or 'root'}", alice["username"], alice["password"]) == 0,
                    f"websocket {path} rejected alice",
                )
                assert_true(connack(plain, "wsreader", bob["username"], bob["password"]) == 0, "reader rejected")
                plain.send(subscribe_packet(f"owntracks/{alice['username']}/phone"))
                ptype, body = plain.recv()
                assert_true(ptype == 0x90 and body[-1] <= 2, "websocket reader subscribe failed")
                token = f"WS-{path}"
                ws.send(publish_packet(f"owntracks/{alice['username']}/phone", token, 7))
                seen = collect_messages(plain, 2)
                assert_true(token in seen, f"websocket path {path} did not deliver {seen}")
            finally:
                ws.close()
                plain.close()
    except Exception:
        if proc.poll() is not None and proc.stdout:
            print(proc.stdout.read())
        raise
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def check_generated(dest: Path) -> None:
    secrets = json.loads((dest / "secrets.json").read_text())
    assert_true(len(secrets["members"]) == 3, "expected three test people")
    android = json.loads((dest / "members" / "alex.android.otrc").read_text())
    iphone = json.loads((dest / "members" / "sam.ios.otrc").read_text())
    assert_true(android["locatorPriority"] == "HighAccuracy", android["locatorPriority"])
    assert_true(android["reverseGeocodeProvider"] == "None", "android geocoder is on")
    assert_true(android["extendedData"] is False, "extended data would include wifi identifiers")
    assert_true(android["ws"] is False and android["port"] == 8883 and android["tls"] is True, "phone is not on raw MQTT 8883")
    assert_true(android["cmd"] is False and android["remoteConfiguration"] is False, "remote configuration is on")
    assert_true(iphone["ws"] is False and iphone["port"] == 8883, "iPhone file is not on raw MQTT 8883")
    assert_true("locatorPriority" not in iphone, "iPhone file contains the Android GPS key")
    assert_true(iphone["monitoring"] == 1, "everyday iPhone mode is not significant-change")
    travel = json.loads((dest / "members" / "sam.ios.travel.otrc").read_text())
    assert_true(travel["monitoring"] == 2, "travel mode is not move mode")
    acl = (dest / "mosquitto" / "acl").read_text()
    alex_block = acl.split("user alex", 1)[1].split("user ", 1)[0]
    assert_true(
        alex_block.index("topic write owntracks/alex/#") < alex_block.index("topic read owntracks/#"),
        "alex's write rule is after alex's read rule",
    )
    mode = stat_mode(dest / "secrets.json")
    assert_true(mode & 0o077 == 0, f"secrets are group or world readable: {oct(mode)}")
    joined = json.dumps(android) + json.dumps(iphone)
    for banned in ("traccar", "life360", "googleapis", "firebase", "opencage"):
        assert_true(banned not in joined.lower(), f"phone config mentions {banned}")


def stat_mode(path: Path) -> int:
    return os.stat(path).st_mode & 0o777


def main() -> None:
    check_static()
    with tempfile.TemporaryDirectory(prefix="family-location-") as tmp:
        dest = Path(tmp)
        bootstrap.main(
            [
                "--tailnet-host",
                "house.example.ts.net",
                "--tz",
                "UTC",
                "--members",
                "Alex,Sam,Jordan",
                "--dest",
                str(dest),
                "--no-env",
            ]
        )
        check_generated(dest)
        before = json.loads((dest / "secrets.json").read_text())["members"][0]["password"]
        bootstrap.main(["--add", "Riley", "--dest", str(dest), "--no-env"])
        after = json.loads((dest / "secrets.json").read_text())
        assert_true(any(member["username"] == "riley" for member in after["members"]), "riley was not added")
        assert_true(after["members"][0]["password"] == before, "adding a person changed an existing password")
        assert_true("user riley" in (dest / "mosquitto" / "acl").read_text(), "riley cannot publish")
        live_broker(dest)
    print("selftest passed")


if __name__ == "__main__":
    main()
