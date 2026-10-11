# Running the household

Run these from the project folder, the one that contains `scripts/` and `deploy/`. `deploy/.env` already exists after the first setup.

## See that it is up

```sh
docker compose -f deploy/compose.yml --env-file deploy/.env ps
docker compose -f deploy/compose.yml --env-file deploy/.env logs --tail 50 caddy
```

A phone that just imported its file should show a broker connection within a minute, outdoors or by a window, once GPS has a fix.

## When a dot looks frozen

1. The app is still in the app switcher. On an iPhone, swiping it away stops reports until it is opened.
2. iOS Location is Always, Precise is on, and Low Power Mode is off.
3. On the Pixel, location is allowed all the time and battery is Unrestricted.
4. The time on the map is the last report. An iPhone that has not moved blocks may honestly sit on the morning's point. Walk it around the block before treating that as a failure.
5. Import that person's travel file for one outing. If the travel file updates and the everyday file does not, use travel mode when you need a tighter trace.

## Add a person

```sh
python3 scripts/bootstrap.py --add "Riley"
docker compose -f deploy/compose.yml --env-file deploy/.env restart mosquitto caddy
```

Existing passwords stay. Riley gets a new sheet under `generated/members/`. Restarting reloads the broker password file and the map login. Eight phones is the limit baked into the script.

## Replace every password

`--force` throws away every password and every phone must import a new file. Use it only when a password has leaked.

```sh
./scripts/up.sh --force \
  --tailnet-host house.tail1234.ts.net \
  --tz UTC \
  --members "Alex,Sam,Jordan"
```

## Backups

```sh
./scripts/backup.sh
```

`backups/locations-*.tgz` is the location history. Keep it on a disk you control. The `generated/` folder is the passwords. Copy it to the same kind of disk, not into a git commit and not into a shared cloud drive. This folder's `.gitignore` already excludes `generated/`, `deploy/.env`, and `backups/`.

## Updates

```sh
docker compose -f deploy/compose.yml --env-file deploy/.env pull
docker compose -f deploy/compose.yml --env-file deploy/.env up -d
./scripts/tailscale-serve.sh
```

The image versions are pinned in `deploy/compose.yml`. Change those pins on purpose. Notes are in [versions.md](versions.md).

## One phone per person

Each login publishes as `owntracks/<username>/phone`. A second phone with the same file will disconnect the first. Turn the old phone's OwnTracks off before using the file on a new phone.

## Places

Edit `generated/places.json`. Each place needs a name, latitude, longitude, and `radius_m`. A point inside more than one circle shows the smaller circle. Restart is not required. The board reads the file on each refresh.

## Optional localhost storage check

`scripts/check_local.py` publishes one point to `127.0.0.1:1883` and reads it back from the recorder. It needs the extra localhost ports in `deploy/compose.local.yml`. Run it before the phones are in use, from this folder:

```sh
docker compose -f deploy/compose.yml -f deploy/compose.local.yml --env-file deploy/.env up -d
python3 scripts/check_local.py
./scripts/up.sh
```

`./scripts/up.sh` starts the loopback services again. `./scripts/tailscale-serve.sh` publishes them on the tailnet. The phones never use a public port.

## Logs

Mosquitto logs connections and usernames. It does not log coordinates at the levels turned on here. The coordinates are in the recorder's store, which is the Docker volume `family-location_recorder-store`.
