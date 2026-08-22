#!/bin/sh
set -eu

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="/backups/regagent_${timestamp}.dump"
pg_dump --format=custom --file="$output"
sha256sum "$output" > "${output}.sha256"

retention="${BACKUP_RETENTION_DAYS:-14}"
find /backups -type f -name 'regagent_*.dump' -mtime "+${retention}" -delete
find /backups -type f -name 'regagent_*.dump.sha256' -mtime "+${retention}" -delete
echo "postgres_backup_created=${output}"
