# Run the house Mac

Use the old M1, plugged in, lid shut. The daily Mac only opens the board. Install Tailscale on the house Mac, turn on MagicDNS and HTTPS certificates, and set the machine name:

```sh
tailscale set --hostname house
```

The name OwnTracks and the browser use is the full MagicDNS name from `tailscale status`, like `house.tail1234.ts.net`. The short name `house` has no HTTPS certificate.

Install Docker Desktop and leave it set to start at login. A power cut with FileVault on still stops at the password screen until someone types it. This project does not unlock the disk.

## Create the family

From this folder, on the house Mac:

```sh
./scripts/up.sh \
  --tailnet-host house.tail1234.ts.net \
  --tz UTC \
  --members "Alex,Sam,Jordan"
```

Use the real MagicDNS name and the household timezone. The script writes passwords under `generated/` and starts the containers. They listen on `127.0.0.1` only. The second time, `./scripts/up.sh` with no arguments keeps those passwords.

Then publish them on the tailnet:

```sh
./scripts/tailscale-serve.sh
```

That serves three things, and only to devices on your tailnet:

- `https://house.tail1234.ts.net/` is the board
- `https://house.tail1234.ts.net:8443/` is the map
- port `8883` is MQTT with TLS, which the phones use

Do not turn on Tailscale Funnel. Do not forward 80, 443, 1883, or 8883 on the router.

## Lid shut, on the charger

A closed MacBook sleeps unless macOS is told otherwise. `caffeinate` does not cover a shut lid with no external display. The switch that does is `disablesleep`, and it applies to battery as well as AC until something clears it.

On the house Mac only:

```sh
sudo mkdir -p /usr/local/libexec
sudo cp deploy/macos/awake.sh /usr/local/libexec/family-location-awake.sh
sudo chmod 755 /usr/local/libexec/family-location-awake.sh
sudo cp deploy/macos/com.family.location.awake.plist /Library/LaunchDaemons/
sudo launchctl bootstrap system /Library/LaunchDaemons/com.family.location.awake.plist
```

While the charger is connected, the lid can stay shut and Docker keeps running. On battery, the helper clears `disablesleep`. It also clears it on a boot that is running from the battery, so a 1 left in the setting cannot keep the laptop awake in a bag. Unplug it and the lid is allowed to sleep.

## Places

`generated/places.json` starts from `deploy/places.example.json`. Put real latitude, longitude, and a radius in meters for Home and School. Leave a place out until you know the point. The board says “Places not set” until at least one place has coordinates. Overlapping circles show the smaller place.

## Phones

Each person gets `generated/members/<username>-setup.md` and an `.otrc` file. Hand them over in person. The phone files already point at the MagicDNS name, port 8883, TLS on, WebSockets off.

iPhone Tailscale settings and the Pixel’s always-on VPN are in the phone guides. The iPhone setting is not “Always.” The Pixel keeps “Block connections without VPN” on.
