#!/usr/bin/env bash
#
# Nightly Postgres backup for Timetable-LLM.
# Intended to run from cron as the deploy user, e.g.:
#   0 2 * * * /opt/timetable-llm/scripts/backup-db.sh >> /var/log/tt-backup.log 2>&1
#
# Requires:
#   - pg_dump available on PATH (or in the db container)
#   - The following env vars: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
#   - S3_BUCKET set if you want offsite upload (aws-cli must be installed)
#
# Retention: 30 daily backups kept locally. Older files are removed.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/timetable-llm}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="${BACKUP_DIR}/timetable-${STAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

if [ -z "${POSTGRES_PASSWORD:-}" ] || [ -z "${POSTGRES_USER:-}" ] || [ -z "${POSTGRES_DB:-}" ]; then
    echo "[$(date -u)] ERROR: POSTGRES_USER/PASSWORD/DB must be set" >&2
    exit 1
fi

echo "[$(date -u)] Backing up ${POSTGRES_DB} → ${FILE}"

# Run inside the db compose service if it exists; otherwise fall back to local pg_dump.
if command -v docker >/dev/null 2>&1 && docker compose ps db >/dev/null 2>&1; then
    docker compose exec -T -e PGPASSWORD="${POSTGRES_PASSWORD}" db \
        pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
        | gzip > "${FILE}"
else
    PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
        -h "${DB_HOST:-localhost}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
        | gzip > "${FILE}"
fi

# Verify the dump is non-empty
if [ ! -s "${FILE}" ]; then
    echo "[$(date -u)] ERROR: backup file is empty" >&2
    rm -f "${FILE}"
    exit 2
fi

echo "[$(date -u)] Backup complete: $(du -h "${FILE}" | cut -f1)"

# Optional: upload to S3-compatible storage
if [ -n "${S3_BUCKET:-}" ]; then
    if command -v aws >/dev/null 2>&1; then
        aws s3 cp "${FILE}" "s3://${S3_BUCKET}/timetable-llm/$(basename "${FILE}")"
        echo "[$(date -u)] Uploaded to s3://${S3_BUCKET}/timetable-llm/"
    else
        echo "[$(date -u)] WARN: S3_BUCKET set but aws CLI not installed" >&2
    fi
fi

# Local retention
find "${BACKUP_DIR}" -type f -name 'timetable-*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete
echo "[$(date -u)] Pruned files older than ${RETENTION_DAYS} days."
