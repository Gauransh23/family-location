# Family location

A small household shares location through phones they already can install, and keeps the history on a computer they control. The computer is reached only through [Tailscale](https://tailscale.com/). The router forwards nothing.

This is an early public starting point, not a finished product. The broker rules and the place-matching board have automated checks. The Docker stack, Tailscale, and the phones have not been run together end to end. Read [Status](#status) before you trust it with a real household.

## What you get

- **OwnTracks** on each phone publishes to **Mosquitto** on the house computer.
- **OwnTracks Recorder** stores the points. Reverse geocoding is off.
- A **board** lists each person as a saved place, or “Between saved places,” plus the time of the last report.
- The existing **OwnTracks map** is one link away, for the trail.
- **Caddy** serves both on `127.0.0.1`. **Tailscale Serve** publishes them on the tailnet. **Funnel stays off.**

iOS cannot keep sharing location from a website while the phone is locked, so the phones use native apps:

| Phone | Apps |
| --- | --- |
| iPhone 14 Pro or later | OwnTracks from the App Store, and the Tailscale app |
| Android without Google Play, including GrapheneOS | OwnTracks from F-Droid (`org.owntracks.android`), and Tailscale’s own APK |

There is no OwnTracks account, no Life360 account, and no Google account in the path.

## Status

Safe to publish, because a reader of this repository still has no route to your machine. Not yet safe to treat as tested household software.

Checked:

- Mosquitto 2.1.2 rejects anonymous clients and a wrong password.
- A user can publish only as themselves. A cross-person publish is not delivered.
- Adding a person does not rotate existing passwords.
- The board picks the smallest saved place that contains a point, omits coordinates from its JSON, and renders the list in a browser.

Not checked:

- `docker compose up` against the pinned images.
- `tailscale serve` on a real tailnet.
- An iPhone or a GrapheneOS phone actually delivering a point.
- The Mac lid-shut helper on hardware.

`scripts/selftest.py` and `board/test_places.py` are the checks that exist today.

## Security model

Tailscale is the encrypted tunnel. Membership in your tailnet is the first gate. After that:

- The broker, board, and map bind to loopback. Serve publishes them only on the tailnet.
- Each person has a password. They can write only to `owntracks/<their-name>/#` and can read the family.
- Remote configuration on the phones stays off, so a phone password cannot retarget the app.
- The person who runs the computer can read the history. That is the household trust model.
- A MagicDNS name can appear on a certificate transparency log. With the router closed and Funnel off, that name is not a route to the computer.

Details are in [docs/threat-model.md](docs/threat-model.md).

## Quick start

On the house computer, not a laptop you carry:

1. Install Docker, and Tailscale with MagicDNS and HTTPS certificates.
2. Note the full MagicDNS name from `tailscale status` (`house.something.ts.net`). The short hostname has no certificate.
3. From this repository:

```sh
./scripts/up.sh \
  --tailnet-host house.something.ts.net \
  --tz Europe/Amsterdam \
  --members "Alex,Sam,Jordan"
./scripts/tailscale-serve.sh
```

4. Edit `generated/places.json` with real centers and radii.
5. Follow [docs/iphone.md](docs/iphone.md) and [docs/grapheneos.md](docs/grapheneos.md). Password sheets are under `generated/members/`. Hand them over in person. `generated/` is gitignored and must stay that way.

What gets published on the tailnet:

| URL or port | What it is |
| --- | --- |
| `https://<magicdns>/` | Board |
| `https://<magicdns>:8443/` | Map |
| `<magicdns>:8883` | MQTT with TLS, WebSockets off |

Do not forward 80, 443, 1883, or 8883 on the router. Do not enable Funnel.

A closed laptop sleeps unless macOS is told otherwise. [docs/hosting.md](docs/hosting.md) includes a root helper that stays awake only on AC power and clears that setting on battery, including after a reboot onto battery. A power cut with FileVault still waits for the disk password.

## iPhone Tailscale

In the Tailscale app: Wi-Fi **Do Nothing**, Cellular **Do Nothing**, **Detect MagicDNS hostnames** on. Always turns that matching off. OwnTracks dialing the MagicDNS name is what brings the tunnel up.

## GrapheneOS Tailscale

Sign in before enabling always-on. Then turn always-on on, and leave **Block connections without VPN** on. Ordinary internet may need an exit node you already trust. Do not use the house computer as that exit node.

## Repository layout

```
board/           household page and place matching
deploy/          Compose, Caddy, Mosquitto, the Mac awake helper
docs/            hosting, phones, operations, threat model
scripts/         setup, Tailscale Serve, backups, tests
generated/       passwords and real places; never commit
```

| Document | What it answers |
| --- | --- |
| [docs/hosting.md](docs/hosting.md) | House computer, Serve, closed lid |
| [docs/iphone.md](docs/iphone.md) | App Store app and iOS permissions |
| [docs/grapheneos.md](docs/grapheneos.md) | F-Droid app and the Pixel |
| [docs/operations.md](docs/operations.md) | Places, backups, adding a person |
| [docs/threat-model.md](docs/threat-model.md) | Who can see a point |
| [docs/why-this.md](docs/why-this.md) | Why these apps, and what was rejected |
| [docs/versions.md](docs/versions.md) | Pinned image digests |

## Development

```sh
python3 board/test_places.py
python3 scripts/selftest.py
```

The broker test needs the `mosquitto` and `mosquitto_passwd` binaries. Phone files and broker passwords are created in a temporary directory and removed when the test exits.

## License

The files in this repository are under the MIT license. See [LICENSE](LICENSE).

OwnTracks, Mosquitto, Caddy, and the other images keep their own licenses. This repository does not vendor their source.
