# Pixel 8 Pro on GrapheneOS

Use the F-Droid build. The Play Store build is a different compilation: it links Google Play Services and Google Maps. Leave that one uninstalled.

The file is `generated/members/<username>.android.otrc`.

## Tailscale

1. Install Tailscale’s own APK, not a Play Store build. The project documents the current APK on the Tailscale Android releases.
2. Open Tailscale and sign in before you turn on always-on. The first login needs a network path.
3. Then Settings → Network & internet → VPN → Tailscale → Always-on VPN.
4. Leave **Block connections without VPN** on. That is the control this phone is for. OwnTracks still reaches the house, because the house name is on the tailnet.
5. Ordinary websites may stop loading while that block is on, because Tailscale is a split tunnel. If you want the rest of the internet at the same time, use an exit node you already trust. Do not use the house Mac as that exit node. The location machine should not see the rest of the phone’s traffic.

## Install OwnTracks

1. Install F-Droid from [f-droid.org](https://f-droid.org/) if it is not already there. GrapheneOS does not need sandboxed Google Play for this.
2. In F-Droid, install OwnTracks. The package id is `org.owntracks.android`.
3. As of 10 October 2026 the suggested build was 2.5.9. A newer F-Droid build of that same package is fine.

## Permissions

1. Settings → Apps → OwnTracks → Permissions → Location → Allow all the time.
2. Use precise location.
3. Allow notifications. Android keeps the app alive with a persistent notification. That notification stays.
4. Battery → Unrestricted. GrapheneOS will otherwise defer background work.

## Location source

Leave Settings → Location → Location services → Network location **off**. With it off, the phone's position comes from GPS. The config file asks OwnTracks for high-accuracy GPS. The words in the file are `HighAccuracy`. Leave that value as written. OwnTracks' own preference note describes the integer `3` as high accuracy; version 2.5.9's importer treats `3` as the no-power setting and treats the name `HighAccuracy` as GPS.

## Import

1. Open the `.otrc` file and choose OwnTracks.
2. Build 2.5.9 imports it directly. If a newer build asks you to allow configuration files first, allow it, then open the file again.
3. The host is the full MagicDNS name, port 8883, TLS on, WebSockets off.

OwnTracks on this build does not reverse-geocode. The map inside the app is OpenStreetMap. The family web map is the one everyone else uses too.

## What you should see

The notification stays, and the app shows a connection. Walk far enough to move about 100 meters and the family map updates. About every 15 minutes the phone also takes a GPS point while you are still, so a long stop still refreshes.

If the dot updates only when you open the app, import `<username>.android.travel.otrc` for a day. That mode asks for GPS about every 30 seconds. If that works and the everyday file does not, stay on the everyday file only after you have confirmed a walk updates the map, and use travel mode when the everyday mode goes quiet. GrapheneOS has changed how often a balanced location request may use GPS; this file asks for GPS directly so it does not depend on that.

## A replaced phone

Disable OwnTracks on the old phone before importing the same file on the new one.
