#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 scripts/bootstrap.py "$@"
cd deploy
docker compose --env-file .env up -d
docker compose --env-file .env ps
