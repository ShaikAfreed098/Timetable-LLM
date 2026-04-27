# Timetable-LLM Runbook

Operational procedures for the production stack. Keep this doc up to date; it
is the first thing to read during an incident.

## 1. Stack layout

```
Internet
   ↓ 443/80
nginx (host)                         — /etc/nginx/conf.d/timetable.conf
   ↓
docker compose -f docker-compose.prod.yml
   ├── backend          (FastAPI + uvicorn, port 8000)
   ├── celery-worker    (background jobs)
   ├── redis            (queue + cache)
   ├── db               (Postgres 16, encrypted volume)
   └── frontend         (Next.js, port 3000)
```

## 2. Routine operations

### Restart a service
```bash
cd /opt/timetable-llm
docker compose -f docker-compose.prod.yml restart backend
```

### Roll out a new version (zero-downtime-ish)
```bash
git pull
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d --no-deps backend
# wait until /health/ready returns 200, then:
docker compose -f docker-compose.prod.yml up -d --no-deps frontend
```

### Apply database migrations
Migrations run automatically at backend startup via `entrypoint.sh`. To force
manually:
```bash
docker compose exec backend alembic upgrade head
```

### Tail logs
```bash
docker compose logs -f backend celery-worker
```

## 3. Backups

Backups run nightly via cron (`scripts/backup-db.sh`). Files live under
`/var/backups/timetable-llm` and optionally in S3.

### Manual backup
```bash
./scripts/backup-db.sh
```

### Restore (DANGEROUS — see script)
```bash
./scripts/restore-db.sh /var/backups/timetable-llm/timetable-20260424T020000Z.sql.gz
# If the target DB already has tables, add --force to drop and restore.
```

### Quarterly restore test
1. `docker compose -f docker-compose.prod.yml --profile scratch up -d db-scratch`
   (a second db service pointed at a disposable volume)
2. Restore last night's backup into `db-scratch`
3. Spot-check a few tables (institutions, users, timetable_slots)
4. Destroy the scratch volume

## 4. Credential rotation

### JWT_SECRET
Rotating invalidates every live session by design.
```bash
NEW=$(openssl rand -hex 32)
sed -i "s/^JWT_SECRET=.*/JWT_SECRET=${NEW}/" /opt/timetable-llm/.env
docker compose -f docker-compose.prod.yml up -d --no-deps backend celery-worker
```

### Database password
1. Create the new password inside Postgres:
   ```bash
   docker compose exec db psql -U timetable -c "ALTER USER timetable WITH PASSWORD 'NEW_PASSWORD';"
   ```
2. Update `.env` (`POSTGRES_PASSWORD`), then restart backend + worker.

### LLM API key
Update `LLM_API_KEY` in `.env`, then `docker compose up -d --no-deps backend celery-worker`.

### Firebase service account
Generate a new service account in the Firebase console, download the JSON, and
replace the file referenced by `FIREBASE_CREDENTIALS_PATH`. Then restart the
backend so `firebase_admin` picks up the new credentials.

## 5. Scaling

### Add Celery workers
```bash
docker compose -f docker-compose.prod.yml up -d --scale celery-worker=3
```

### Scale up DB
Move Postgres to a managed instance (RDS, DigitalOcean Managed Database), point
`DATABASE_URL` at the new host, re-run migrations. Do this before you pass
~50 concurrent institutions.

## 6. Common errors

| Symptom | Likely cause | First step |
|---------|--------------|------------|
| 500 on `/api/chat` | LLM_API_KEY invalid or provider outage | `docker compose logs backend \| grep -i "llm"` |
| `/health/ready` = 503 | DB or Redis unreachable | check `docker compose ps` |
| New user can't log in | Invite expired or institution slug mismatch | inspect `invites` table |
| Timetable generation 422 "No ScheduleConfig" | institution is missing a schedule config | `POST /api/config` |
| Rate-limit 429s | legitimate traffic spike or attack | check nginx access log for source IP |

## 7. Incident response

### Data breach
1. Cut external access: `docker compose -f docker-compose.prod.yml stop frontend backend`
2. Rotate every credential in section 4.
3. Preserve logs (copy `/var/log` and `docker compose logs` to a separate host).
4. Notify affected institutions within **72 hours** (GDPR Art. 33 / DPDP).
5. File a post-mortem in `docs/incidents/`.

### Service outage
1. Check `/health/ready` first — reveals which dependency is failing.
2. Status page / email template lives in `docs/templates/outage-email.md`
   (create once, update for each incident).

## 8. Contact points

- Primary on-call: _fill in_
- Backup on-call: _fill in_
- Hosting provider support: _fill in_
- Firebase support: firebase-support@google.com
- LLM provider support: _fill in_
