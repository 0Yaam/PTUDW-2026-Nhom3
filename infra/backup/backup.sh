#!/bin/sh
set -eu

# Run once during the 03:00 UTC hour, including after a container restart.
mkdir -p /backups
while :; do
  day="$(date -u +%Y%m%d)"
  hour="$(date -u +%H)"
  destination="/backups/${day}.dump"
  if [ "$hour" = "03" ] && [ ! -f "$destination" ]; then
    temporary="${destination}.tmp"
    if pg_dump -Fc -f "$temporary"; then
      mv "$temporary" "$destination"
      find /backups -type f -name '*.dump' -mtime +29 -delete
      echo "PostgreSQL backup complete: ${day}"
    else
      rm -f "$temporary"
      echo "PostgreSQL backup failed: ${day}" >&2
    fi
  fi
  sleep 300
done
