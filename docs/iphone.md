# iPhone

This is for an iPhone 14 Pro or later, kept on a current iOS. The current OwnTracks app is built for recent iOS. Update the phone first.

Use the everyday file `generated/members/<username>.ios.otrc` from the setup sheet. The travel file is only for a trip.

## Tailscale

1. Install Tailscale from the App Store and sign in to the family tailnet.
2. In the Tailscale app, set VPN On Demand like this: Wi-Fi **Do Nothing**, Cellular **Do Nothing**, and **Detect MagicDNS hostnames** on.
3. Do not set Wi-Fi or Cellular to Always. Always turns MagicDNS matching off, so OwnTracks dialing the house name would not bring the tunnel up.
4. A hotel login page is not a `*.ts.net` name, so it can load while Tailscale is down. The next OwnTracks report to the house name connects the tunnel. If a hotel page will not load because the tunnel stayed up, turn Tailscale off, finish the login, and leave it off. The next report turns it on again.

## Install OwnTracks

1. App Store. Search OwnTracks. The seller is Christoph Krey. Install that app.
2. Open it once and leave it in the app switcher. Swiping it away stops location until someone opens it again.

## Allow a configuration file

Current iOS builds ignore a config file until you allow it.

1. In OwnTracks, open settings.
2. Turn on the switch that allows configuration from a file or a link. The app warns you that a file can change the server settings. Turn it on anyway, because this file is the one you created.
3. Open the `.otrc` file from Files, AirDrop, or Mail, and open it in OwnTracks.
4. Read the summary of what will change. The host is the full MagicDNS name, port `8883`, TLS on, WebSockets off. Accept it when that host is the one on the setup sheet.

If the file will not import, type those values from the setup sheet by hand. Device ID is `phone`.

## iOS location permission

1. Settings → OwnTracks → Location → Always.
2. Precise Location on.
3. Settings → OwnTracks → Background App Refresh on.
4. Low Power Mode slows or stops background updates. Leave it off when you want the map to keep up.

## What you should see

OwnTracks shows a connection to your server. After a walk of a few blocks, the family map shows the new place. Sitting still leaves the last report in place. That timestamp is the last time the phone moved enough to report, which is what iOS allows without treating the app like a navigation app.

Looking up a street address inside OwnTracks can send that one point to Apple Maps. Use the family web map when you want to see where someone is.

## A trip

Import `<username>.ios.travel.otrc` the same way. The phone reports about every 30 seconds while moving. Import the everyday file again when you are home. Travel mode is the one that drains the battery.

## A replaced phone

Turn OwnTracks off on the old phone, or delete the app. Import the same everyday file on the new phone. Two phones signed in as the same person will take turns kicking each other off.
