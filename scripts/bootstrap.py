#!/usr/bin/env python3
"""Create per-person OwnTracks configs and broker credentials.

The generated directory holds passwords. It is gitignored. Re-running keeps
the existing passwords unless --force is passed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?)+$")
RESERVED = {"recorder", "mosquitto", "caddy", "admin", "root", "owntracks"}


def slug(name: str) -> str:
    compact = re.sub(r"[^a-z0-9]", "", name.lower())
    if not re.fullmatch(r"[a-z][a-z0-9]{1,15}", compact):
        raise SystemExit(
            f"'{name}' needs a 2–16 letter username after removing spaces. "
            "Use a short first name such as Alex or MaryJane."
        )
    if compact in RESERVED:
        raise SystemExit(f"'{compact}' is reserved for the server. Pick another name.")
    return compact


def tids(usernames: list[str]) -> dict[str, str]:
    used: set[str] = set()
    out: dict[str, str] = {}
    for name in usernames:
        base = name[:2].upper()
        choice = base
        n = 2
        while choice in used:
            choice = name[0].upper() + str(n)
            n += 1
            if n > 9:
                choice = name[0].upper() + name[-1].upper()
                if choice in used:
                    raise SystemExit(f"Could not make a unique two-letter map id for {name}.")
        used.add(choice)
        out[name] = choice
    return out


def password() -> str:
    import secrets

    # URL-safe alphabet avoids shell, YAML, and JSON surprises.
    return secrets.token_urlsafe(18)


def client_id(username: str) -> str:
    return f"{username}phone"[:23]


def configuration(member: dict, mqtt_host: str, travel: bool, android: bool) -> dict:
    body = {
        "_type": "configuration",
        "mode": 0,
        "monitoring": 2 if travel else 1,
        "host": mqtt_host,
        "port": 8883,
        "tls": True,
        "ws": False,
        "auth": True,
        "username": member["username"],
        "password": member["password"],
        "deviceId": "phone",
        "clientId": client_id(member["username"]),
        "tid": member["tid"],
        "pubTopicBase": "owntracks/%u/%d",
        "sub": True,
        "subTopic": "owntracks/+/+",
        "subQos": 1,
        "pubQos": 1,
        "pubRetain": True,
        "cleanSession": False,
        "mqttProtocolLevel": 4,
        "keepalive": 120,
        "locatorInterval": 30 if travel else 180,
        "locatorDisplacement": 50 if travel else 100,
        "moveModeLocatorInterval": 30 if travel else 60,
        "extendedData": False,
        "cmd": False,
        "remoteConfiguration": False,
        "allowRemoteLocation": False,
        "allowinvalidcerts": False,
        "ranging": False,
    }
    if android:
        # "HighAccuracy" is the GPS setting in OwnTracks Android 2.5.9.
        # The app's preference note lists the integer 3 as high accuracy;
        # the v2.5.9 importer maps the integer 3 to no-power. Use the name.
        body.update(
            {
                "locatorPriority": "HighAccuracy",
                "reverseGeocodeProvider": "None",
                "autostartOnBoot": True,
                "pegLocatorFastestIntervalToInterval": True,
                "publishLocationOnConnect": True,
                "notificationLocation": True,
                "ping": 300 if travel else 900,
                "experimentalFeatures": ["locationPingUsesHighAccuracyLocationRequest"],
            }
        )
    return body


def write_json(path: Path, body: dict) -> None:
    path.write_text(json.dumps(body, indent=2) + "\n")
    os.chmod(path, 0o600)


def find_mosquitto_passwd() -> str | None:
    candidates = [
        shutil.which("mosquitto_passwd"),
        "/opt/homebrew/opt/mosquitto/bin/mosquitto_passwd",
        "/usr/local/sbin/mosquitto_passwd",
        "/usr/bin/mosquitto_passwd",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def write_passwd(path: Path, accounts: list[tuple[str, str]]) -> None:
    if path.exists():
        path.unlink()
    tool = find_mosquitto_passwd()
    if tool:
        for index, (user, secret) in enumerate(accounts):
            cmd = [tool, "-H", "sha512-pbkdf2", "-b"]
            if index == 0:
                cmd.append("-c")
            cmd += [str(path), user, secret]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
    else:
        if not shutil.which("docker"):
            raise SystemExit("Install Mosquitto or Docker so passwords can be hashed.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
        for index, (user, secret) in enumerate(accounts):
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{path.parent}:/work",
                "eclipse-mosquitto:2.1.2-alpine",
                "mosquitto_passwd",
                "-H",
                "sha512-pbkdf2",
                "-b",
            ]
            if index == 0:
                cmd.append("-c")
            cmd += ["/work/passwd", user, secret]
            subprocess.run(cmd, check=True)
    os.chmod(path, 0o600)
    text = path.read_text()
    if "$7$" not in text:
        raise SystemExit("Password file is not a Mosquitto 2.0 PBKDF2 hash ($7$).")


def caddy_hash(secret: str) -> str:
    try:
        import bcrypt
    except ImportError:
        bcrypt = None
    if bcrypt is not None:
        raw = bcrypt.hashpw(secret.encode(), bcrypt.gensalt(rounds=12)).decode()
    elif shutil.which("docker"):
        proc = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "caddy:2.10.2-alpine",
                "caddy",
                "hash-password",
                "--plaintext",
                secret,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        raw = proc.stdout.strip()
    elif shutil.which("caddy"):
        proc = subprocess.run(
            ["caddy", "hash-password", "--plaintext", secret],
            check=True,
            capture_output=True,
            text=True,
        )
        raw = proc.stdout.strip()
    else:
        raise SystemExit(
            "Install Docker, Caddy, or Python bcrypt so the map login can be hashed."
        )
    if not raw.startswith("$2"):
        raise SystemExit(f"Unexpected map hash: {raw[:7]}")
    return raw.replace("$", "$$")


def write_acl(path: Path, usernames: list[str]) -> None:
    lines = [
        "# First matching rule wins. A person's write rule has to come",
        "# before the family-wide read rule.",
        "user recorder",
        "topic read owntracks/#",
        "topic read $SYS/broker/version",
        "",
    ]
    for username in usernames:
        lines += [
            f"user {username}",
            f"topic write owntracks/{username}/#",
            "topic read owntracks/#",
            "",
        ]
    path.write_text("\n".join(lines))
    os.chmod(path, 0o600)


def setup_card(member: dict, tailnet_host: str) -> str:
    username = member["username"]
    return f"""# {member["display"]}

Board: https://{tailnet_host}/
Map: https://{tailnet_host}:8443/
Username: `{username}`
Password: `{member["password"]}`

The same password opens the board and the map. The phone uses the same username and password, host `{tailnet_host}`, port `8883`, TLS on, WebSockets off. Each person has a different password.

Phone files in this folder:

- `{username}.android.otrc` for the Pixel on GrapheneOS, everyday
- `{username}.ios.otrc` for an iPhone, everyday
- `{username}.android.travel.otrc` and `{username}.ios.travel.otrc` for a trip, when you want updates about every 30 seconds. Switch back to the everyday file afterwards. Travel mode uses more battery.

Hand the file over in person, with AirDrop or a USB cable. Delete the file from the phone's Files app after OwnTracks imports it.

The steps for each kind of phone are in `docs/iphone.md` and `docs/grapheneos.md`.
"""


def lock(path: Path) -> None:
    os.chmod(path, 0o600)


def write_roster(dest: Path, members: list[dict]) -> None:
    roster = [
        {"username": member["username"], "display": member["display"], "tid": member["tid"]}
        for member in members
    ]
    path = dest / "roster.json"
    path.write_text(json.dumps(roster, indent=2) + "\n")
    os.chmod(path, 0o644)


def ensure_places(dest: Path) -> None:
    path = dest / "places.json"
    if path.exists():
        return
    example = ROOT / "deploy" / "places.example.json"
    path.write_text(example.read_text())
    os.chmod(path, 0o644)


def fresh_tid(username: str, used: set[str]) -> str:
    choice = username[:2].upper()
    n = 2
    while choice in used:
        choice = (username[0] + str(n)).upper()
        n += 1
        if n > 9:
            raise SystemExit(f"Could not make a map initial for {username}.")
    return choice


def append_passwd(path: Path, username: str, secret: str) -> None:
    tool = find_mosquitto_passwd()
    if tool:
        subprocess.run(
            [tool, "-H", "sha512-pbkdf2", "-b", str(path), username, secret],
            check=True,
            capture_output=True,
            text=True,
        )
    elif shutil.which("docker"):
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{path.parent}:/work",
                "eclipse-mosquitto:2.1.2-alpine",
                "mosquitto_passwd",
                "-H",
                "sha512-pbkdf2",
                "-b",
                "/work/passwd",
                username,
                secret,
            ],
            check=True,
        )
    else:
        raise SystemExit("Install Mosquitto or Docker before adding a person.")
    lock(path)


def add_member(args: argparse.Namespace) -> None:
    dest = Path(args.dest).resolve()
    secrets_path = dest / "secrets.json"
    if not secrets_path.exists():
        raise SystemExit("Set the family up before adding someone.")
    secrets = json.loads(secrets_path.read_text())
    if len(secrets["members"]) >= 8:
        raise SystemExit("Stop at 8 phones. This design is for a small household.")
    username = slug(args.add)
    if any(member["username"] == username for member in secrets["members"]):
        raise SystemExit(f"{username} is already in the family.")
    used = {member["tid"] for member in secrets["members"]}
    member = {
        "display": args.add.strip(),
        "username": username,
        "password": password(),
        "tid": fresh_tid(username, used),
    }
    append_passwd(dest / "mosquitto" / "passwd", username, member["password"])
    with (dest / "mosquitto" / "acl").open("a") as handle:
        handle.write(
            f"user {username}\ntopic write owntracks/{username}/#\ntopic read owntracks/#\n\n"
        )
    auth = dest / "caddy" / "map-auth.caddy"
    with auth.open("a") as handle:
        handle.write(f"{username} {caddy_hash(member['password'])}\n")
    lock(auth)
    folder = dest / "members"
    mqtt_host = secrets["tailnet_host"]
    map_host = secrets["tailnet_host"]
    write_roster(dest, secrets["members"] + [member])
    write_json(folder / f"{username}.ios.otrc", configuration(member, mqtt_host, False, False))
    write_json(folder / f"{username}.android.otrc", configuration(member, mqtt_host, False, True))
    write_json(folder / f"{username}.ios.travel.otrc", configuration(member, mqtt_host, True, False))
    write_json(
        folder / f"{username}.android.travel.otrc",
        configuration(member, mqtt_host, True, True),
    )
    card = folder / f"{username}-setup.md"
    card.write_text(setup_card(member, map_host))
    lock(card)
    secrets["members"].append(member)
    secrets_path.write_text(json.dumps(secrets, indent=2) + "\n")
    lock(secrets_path)
    print(f"Added {member['display']}. Phone sheet: {card}")
    print("Restart the broker and the board login so this person can connect:")
    print("  docker compose -f deploy/compose.yml --env-file deploy/.env restart mosquitto caddy")


def build(args: argparse.Namespace) -> None:
    dest = Path(args.dest).resolve()
    secrets_path = dest / "secrets.json"
    if secrets_path.exists() and not args.force:
        print(f"Already configured: {secrets_path}")
        print("Leave it in place. --force replaces every password and logs the phones out.")
        return

    names = [part.strip() for part in args.members.split(",") if part.strip()]
    if not 1 <= len(names) <= 8:
        raise SystemExit("Give 1 to 8 names, separated by commas.")
    if not HOST_RE.match(args.tailnet_host) or not args.tailnet_host.endswith(".ts.net"):
        raise SystemExit(
            "The tailnet host must be the full MagicDNS name, such as house.tail1234.ts.net."
        )
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo(args.tz)
    except Exception as exc:
        raise SystemExit(f"Unknown timezone {args.tz}: {exc}") from exc

    usernames = [slug(name) for name in names]
    if len(set(usernames)) != len(usernames):
        raise SystemExit(f"Those names collide as usernames: {usernames}")
    letters = tids(usernames)
    members = [
        {
            "display": display,
            "username": username,
            "password": password(),
            "tid": letters[username],
        }
        for display, username in zip(names, usernames)
    ]
    recorder_password = password()
    dest.mkdir(parents=True, exist_ok=True)
    os.chmod(dest, 0o700)
    (dest / "mosquitto").mkdir(exist_ok=True)
    (dest / "caddy").mkdir(exist_ok=True)
    (dest / "members").mkdir(exist_ok=True)

    accounts = [("recorder", recorder_password)] + [(m["username"], m["password"]) for m in members]
    write_passwd(dest / "mosquitto" / "passwd", accounts)
    write_acl(dest / "mosquitto" / "acl", usernames)

    auth_lines = [f"{m['username']} {caddy_hash(m['password'])}" for m in members]
    auth_path = dest / "caddy" / "map-auth.caddy"
    auth_path.write_text("\n".join(auth_lines) + "\n")
    lock(auth_path)

    for member in members:
        user = member["username"]
        folder = dest / "members"
        write_json(folder / f"{user}.ios.otrc", configuration(member, args.tailnet_host, False, False))
        write_json(folder / f"{user}.android.otrc", configuration(member, args.tailnet_host, False, True))
        write_json(folder / f"{user}.ios.travel.otrc", configuration(member, args.tailnet_host, True, False))
        write_json(
            folder / f"{user}.android.travel.otrc",
            configuration(member, args.tailnet_host, True, True),
        )
        card = folder / f"{user}-setup.md"
        card.write_text(setup_card(member, args.tailnet_host))
        lock(card)

    write_roster(dest, members)
    ensure_places(dest)
    secrets = {
        "tailnet_host": args.tailnet_host,
        "tz": args.tz,
        "recorder_password": recorder_password,
        "members": members,
    }
    secrets_path.write_text(json.dumps(secrets, indent=2) + "\n")
    lock(secrets_path)

    env_path = ROOT / "deploy" / ".env"
    if args.write_env:
        env_path.write_text(
            "\n".join(
                [
                    f"TAILNET_HOST={args.tailnet_host}",
                    f"TZ={args.tz}",
                    f"RECORDER_MQTT_PASSWORD={recorder_password}",
                    "",
                ]
            )
        )
        lock(env_path)

    print(f"Wrote passwords and phone files under {dest}")
    print("Each person's sheet is generated/members/<name>-setup.md")
    print("Next: docs/hosting.md, then docs/iphone.md and docs/grapheneos.md")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the family location credentials")
    parser.add_argument("--tailnet-host", required=False, help="Full MagicDNS name, house.tail1234.ts.net")
    parser.add_argument("--tz", default="UTC")
    parser.add_argument("--members", required=False, help="Comma-separated first names")
    parser.add_argument("--dest", default=str(ROOT / "generated"))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--add", help="First name to add without changing anyone else's password")
    parser.add_argument("--write-env", action="store_true", default=True)
    parser.add_argument("--no-env", action="store_true", help="Used by the local broker test")
    args = parser.parse_args(argv)
    if args.no_env:
        args.write_env = False
    if args.add:
        return args
    if not (Path(args.dest) / "secrets.json").exists() or args.force or args.no_env:
        missing = [
            flag
            for flag, value in (
                ("--tailnet-host", args.tailnet_host),
                ("--members", args.members),
            )
            if not value
        ]
        if missing and not (Path(args.dest) / "secrets.json").exists():
            raise SystemExit("Missing " + ", ".join(missing))
        if missing and args.force:
            raise SystemExit("Missing " + ", ".join(missing))
    elif not args.members:
        # Existing config, nothing to do. build() prints that.
        args.tailnet_host = args.tailnet_host or "unused.example.ts.net"
        args.members = "Unused"
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.add:
        add_member(args)
        return
    build(args)


if __name__ == "__main__":
    main()
