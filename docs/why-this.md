# Why this is the setup

Checked 10 October 2026 for a household of three to five: several iPhone 14 Pro or later phones, and one Pixel 8 Pro on de-googled GrapheneOS, with no sandboxed Google Play assumed.

## The constraint that decides it

iOS will not keep a website's GPS running while the phone is locked. WebKit turns location off when the page is hidden. The background-geolocation request in WebKit is still unresolved. Background updates require a native app using Core Location. Sources: WebKit bugs 147685 and 193946, and Apple's document "Handling location updates in the background."

A new iPhone app written here cannot be installed by the family as a normal app unless it is on the App Store or each person sideloads it. Sideloading expires, and it is a poor fit for relatives. So the iPhone side has to be an App Store app that can be pointed at a server you run.

The Pixel side has to use Android's location API. Builds that require Google's fused location provider do not belong on this phone.

The running setup is a place name or “Between saved places,” plus the report time, and one legend for the two phone clocks. The house Mac listens on loopback. Tailscale Serve is the only door. iPhones use MagicDNS on-demand with Wi-Fi and Cellular set to Do Nothing, not Always. The Pixel keeps “Block connections without VPN” on. `cmd` and remote configuration stay off.

## The setup

| Piece | Role | Why it qualifies |
| --- | --- | --- |
| OwnTracks iOS, App Store id 692424691 | Background publisher | Maintained. Store version 27.0.1 was released 30 September 2026. Privacy label: Data Not Collected. No demo server. |
| OwnTracks Android F-Droid, `org.owntracks.android` | Publisher on GrapheneOS | The OSS flavor does not link Play Services. GPS-only is `LocatorPriority.HighAccuracy` in v2.5.9, and the config file uses that name. F-Droid suggested 2.5.9 on 20 May 2026. |
| Mosquitto 2.1.2 | Broker | Per-person passwords. Write limited to that person's topic. Tested locally, including a rejected cross-person publish and WebSocket on `/` and `/mqtt`. |
| Recorder 1.0.4 | History | `--norevgeo` is a real flag in that release. Storage is files on your disk. |
| Frontend 2.15.3 | Map | Proxies `/api/` and `/ws/` to the recorder. Default tiles are OpenStreetMap. |
| Caddy 2.10.2 | Logins on loopback | Serves the board and the map on `127.0.0.1`. Tailscale Serve publishes them. No public 80 or 443. |

OwnTracks' significant-change mode on iOS is Apple's mode: on the order of 500 meters and not more often than about every five minutes. That is the everyday file. Move mode is the travel file. Both are in the generated `.otrc` files.

On Android 2.5.9, significant mode uses `locatorInterval`, `locatorDisplacement`, and `locatorPriority`. The everyday file sets 180 seconds, 100 meters, and `HighAccuracy`, so the OSS client requests the GPS provider only. A ping every 900 seconds asks for a fresh high-accuracy fix when the experimental flag in that file is honored. Source: `BackgroundService.setupLocationRequest` and `AospLocationProviderClient.locationSourcesForPriority` at tag v2.5.9.

## Options that miss a requirement

**Traccar Client 10.1.6** can run without Play Services, and the server is a capable map. The shipping client depends on Firebase Analytics, Crashlytics, and Cloud Messaging. A fresh install's default server is `http://demo.traccar.org:5055`. The default web map loads LocationIQ tiles. The phone port accepts a position from anyone who knows the device id. F-Droid's current package for it is gone. That is a lot of third-party contact for a project whose point is to avoid it.

**Home Assistant's companion app** tracks location in the full build, which uses Google's fused provider. The minimal F-Droid build does not track location. Standing up Home Assistant only as a family map also fails the "small and specific" test.

**Dawarich** is a strong self-hosted timeline. Its official Android app uses Play Services. GPSLogger on F-Droid can feed it, and there is an iOS app, but the product is a personal history first. Live mutual tracking is what OwnTracks and the recorder already do.

**Nextcloud PhoneTrack** can draw several people if something else uploads points. Its own Android app on F-Droid is still the 2020 build. It becomes OwnTracks or GPSLogger plus another server.

**OpenFamily, Draugar, OpenBeacon** are new and small, with no App Store build verified for the iPhones. They are not something relatives can install this week.

**Hauk** shares a timed session. It is a good "I am on my way" tool and a poor always-on family map.

**Find My Device (FMD)** finds a lost Android phone. It is not a family map, and it has no iPhone client for this job.

**Life360, Google location sharing, FamilyWall, Glympse, and Apple Find My** are the services this project is replacing.

## What was run here

`scripts/selftest.py` loads the generated Mosquitto config under Mosquitto 2.1.2. Anonymous login is rejected. A wrong password is rejected. One user can publish only on their own topic, and that publish is delivered to another user. The same publish works over a WebSocket on `/mqtt` and on `/`. Adding a person does not change existing passwords.

That check does not boot the Docker images, Tailscale, or a phone. The image tags and digests were confirmed on Docker Hub on 10 October 2026. The recorder flags `--norevgeo` and `--useretained` are in recorder 1.0.4's `recorder.c`. The frontend image's nginx template proxies `/api/` and `/ws/` and substitutes `SERVER_HOST`. The board's place matching is covered by `board/test_places.py`.

The phones were not in the room. The first walk outside is the remaining test, and the phone guides say what success looks like.

## A footgun in the Android accuracy setting

`LocatorPriority.kt` at v2.5.9 declares `HighAccuracy(3)` but imports an integer with `entries.getOrElse(index)`, so integer `0` is high accuracy and integer `3` is no power. `docs/PREFERENCES.md` in that same tag says the opposite. The generated file uses the enum name `HighAccuracy`, which the string importer matches by name. Do not "correct" it to `3`.
