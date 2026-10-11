#!/bin/sh
# Publish the house services on this Mac's tailnet. No public ports.
# Run this on the house Mac after Docker is up. It replaces Tailscale Serve
# config on this machine. Do not turn Funnel on.
set -eu
cd "$(dirname "$0")/.."

tailscale serve --bg --https=443 http://127.0.0.1:8080
tailscale serve --bg --https=8443 http://127.0.0.1:8088
tailscale serve --bg --tls-terminated-tcp=8883 tcp://127.0.0.1:1883
echo
tailscale serve status
echo
echo "Funnel must stay off. If the status above shows Funnel, run: tailscale funnel reset"
