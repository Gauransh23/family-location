#!/bin/sh
# Copy secrets into the container and lock them down before Mosquitto
# drops from root to the mosquitto user. A bind-mounted 600 file owned
# by the host user is not readable by that account.
set -eu
cp /opt/family-secrets/passwd /mosquitto/config/passwd
cp /opt/family-secrets/acl /mosquitto/config/acl
chown mosquitto:mosquitto /mosquitto/config/passwd /mosquitto/config/acl
chmod 600 /mosquitto/config/passwd
chmod 640 /mosquitto/config/acl
mkdir -p /mosquitto/data
chown mosquitto:mosquitto /mosquitto/data
exec /usr/sbin/mosquitto -c /mosquitto/config/mosquitto.conf
