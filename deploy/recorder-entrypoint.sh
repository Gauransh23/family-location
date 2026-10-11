#!/bin/sh
# Store location history with no reverse-geocoder calls.
# --norevgeo keeps coordinates off Google and OpenCage.
# --useretained reloads the last published point after a restart.
set -eu
if [ ! -f /store/ghash/data.mdb ]; then
  ot-recorder --initialize
fi
exec ot-recorder --norevgeo --useretained owntracks/#
