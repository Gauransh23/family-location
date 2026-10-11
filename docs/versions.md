# Pinned images

Confirmed on Docker Hub on 10 October 2026. `deploy/compose.yml` pins these digests.

| Image | Digest |
| --- | --- |
| `eclipse-mosquitto:2.1.2-alpine` | `sha256:38c0da4f2ef84284d47b3b3eeea1cb3bdeabe81ee10caf0cd5c5ff61ee3ea408` |
| `owntracks/recorder:1.0.4` | `sha256:bb292a481c94ef40bde26f52c8d3868d1395bd2da15bc9405be889e13f686a1b` |
| `owntracks/frontend:2.15.3` | `sha256:efa313bdec583939f6edc70eb148670a8bba1a5aed0508a326f5b2f2751d0861` |
| `caddy:2.10.2-alpine` | `sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d` |
| `alpine:3.22` (backups only) | `sha256:5291449c3df73caf6ed85e649dec1b9e818b39a5d8c871e97afc13e9cd5e8fa8` |

Mosquitto 2.1 still accepts `password_file` and `acl_file`. The project has marked those keys as deprecated in favor of plugins that are the same code. They worked in the 2.1.2 test. When a future Mosquitto removes them, the config will need the plugin lines and another test.

The frontend tag is from June 2024 and still matches the recorder's `/api/0/` and `/ws/` paths. It is pinned rather than `latest` so a surprise rebuild cannot change the map.

OwnTracks iOS 27.0.1 (30 September 2026) and Android F-Droid 2.5.9 (20 May 2026) are the phone versions this config was written against. Newer store and F-Droid builds of those same apps are the ones to install. Re-read the import step if a new Android build starts ignoring config files until a switch is enabled. iOS has had that switch since 26.2.2.
