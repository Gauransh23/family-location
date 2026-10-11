#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
docker run --rm \
  -v family-location_recorder-store:/store:ro \
  -v "$PWD/backups":/backup \
  alpine:3.22@sha256:5291449c3df73caf6ed85e649dec1b9e818b39a5d8c871e97afc13e9cd5e8fa8 \
  tar -C /store -czf "/backup/locations-$stamp.tgz" .
echo "Wrote backups/locations-$stamp.tgz"
echo "That archive is the family's location history. Keep it on a disk you control."
