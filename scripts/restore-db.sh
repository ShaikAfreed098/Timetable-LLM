#!/usr/bin/env bash
#
# Restore a Timetable-LLM Postgres backup.
# Usage:  ./restore-db.sh /path/to/timetable-YYYYMMDDTHHMMSSZ.sql.gz
#
# REFUSES to run against a database that already has tables unless --force is
# passed, to prevent accidental destruction of a live system.

set -euo pipefail

FILE="${1:-}"
FORCE="${2:-}"

if [ -z "${FILE}" ] || [ ! -f "${FILE}" ]; then
    echo "Usage: $0 <path-to-backup.sql.gz> [--force]" >&2
    exit 1
fi

if [ -z "${POSTGRES_USER:-}" ] || [ -z "${POSTGRES_PASSWORD:-}" ] || [ -z "${POSTGRES_DB:-}" ]; then
    echo "ERROR: POSTGRES_USER/PASSWORD/DB must be set" >&2
    exit 1
fi

count_tables() {
    docker compose exec -T -e PGPASSWORD="${POSTGRES_PASSWORD}" db \
        psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
}

if [ "${FORCE}" != "--force" ]; then
    EXISTING=$(count_tables | tr -d '[:space:]')
    if [ "${EXISTING:-0}" -gt 0 ]; then
        echo "ERROR: target database has ${EXISTING} tables. Pass --force to drop and restore." >&2
        exit 2
    fi
fi

echo "Restoring ${FILE} into ${POSTGRES_DB}..."
gunzip -c "${FILE}" | docker compose exec -T -e PGPASSWORD="${POSTGRES_PASSWORD}" db \
    psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"

echo "Restore complete. Verifying row counts..."
docker compose exec -T -e PGPASSWORD="${POSTGRES_PASSWORD}" db \
    psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c \
    "SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 15;"
