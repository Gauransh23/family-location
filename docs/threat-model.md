# Who can see a location

The household trust model is: the person who runs the computer can read the history, and the people you created logins for can see the live map. Everyone else on the network sees an encrypted connection to your two DNS names.

## On the wire

Phones and browsers reach the house Mac through Tailscale. Docker binds the broker, the board, and the map to `127.0.0.1`. Tailscale Serve publishes them on the machine’s MagicDNS name. Funnel stays off. The router forwards nothing.

The board is `https://<magicdns>/`. The map is `https://<magicdns>:8443/`. Phones use raw MQTT on port 8883, with TLS ended by Tailscale, then the existing username and password. WebSockets are off.

Tailscale’s HTTPS certificate is on the public certificate transparency log. That entry is the MagicDNS name. With the router closed and Funnel off, the name is not a route to the laptop. A clone of this repository can join its own tailnet. It cannot finish a handshake with yours.

The broker password file gives each person write access only to `owntracks/<their-name>/#` and read access to the whole family. A stolen phone password can publish fake points for that person and can read the others. It cannot publish as someone else. That rule was exercised against Mosquitto 2.1.2, the version pinned for Docker. Remote configuration on the phones stays off, so that password cannot point the app at a different broker.

The recorder stores plain coordinates. Payload encryption was left off on purpose. If the phones encrypted the payload, the map on the server could not draw it unless the server also held the key, which puts the coordinates back in the store. TLS is the boundary against the network. The disk is the boundary against everyone but the operator.

## The operator and the machine

You can read `generated/`, the Docker volume, and the backup archives. A backup is a copy of the history. Treat it like the history.

A VPS provider can read the disk of a machine they host. A computer at home does not have that reader. Full-disk encryption on the home computer protects the history if the computer is stolen while it is off.

## The phones

The OwnTracks apps send nothing until a server is configured. There is no OwnTracks demo server in these config files.

The iPhone app's App Store privacy label says the developer collects no data. Positioning still uses Apple's location services on the phone. Wi-Fi positioning is part of iOS. That is the phone finding itself, then OwnTracks sending the result to your server. Showing a street address inside the OwnTracks app can send that point to Apple Maps. The family map in the browser does not do that lookup.

The Pixel uses the F-Droid build. Its location code calls Android's `LocationManager` and, with this config, GPS only. It does not include the Play Services location client. Leave GrapheneOS network location off so the phone does not ask Apple's network-location service either.

GrapheneOS can still download assisted-GPS data. By default that assistance goes to a GrapheneOS server which proxies SUPL to Google, so a faster satellite fix can involve that assistance channel. It is not the family trail. It can be turned off in GrapheneOS if you would rather wait longer for a cold GPS fix.

The Android file turns off extended fields, which is where Wi-Fi names and access-point identifiers would otherwise ride along with a point.

## The map pictures

The browser loads map tiles from `tile.openstreetmap.org`. Those servers see the IP address of whoever has the map open and the area on screen. They do not get the OwnTracks username or the stored history. Five people looking at a city is ordinary use of that tile service. A later upgrade, if you want even that viewport to stay home, is a map file served from the same computer.

## Explicitly absent

No Firebase, no Google Maps SDK, and no Play Services in the GrapheneOS app. No Life360. No Traccar demo server. No phone-home account at owntracks.org. The recorder is started with `--norevgeo`, so it does not call a geocoder.
