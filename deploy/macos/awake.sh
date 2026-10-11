#!/bin/sh
# Keep a closed MacBook awake only while it is on AC power.
# disablesleep is global and survives reboot, so every run on battery clears it.
set -eu

apply() {
  if pmset -g ps | head -n 1 | grep -q "AC Power"; then
    pmset -a disablesleep 1
  else
    pmset -a disablesleep 0
  fi
}

apply
pmset -g pslog | while IFS= read -r _; do
  apply
done
