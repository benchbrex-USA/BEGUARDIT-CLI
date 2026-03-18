# Backup & Restore Runbook

Source: ARCH-002-2026-03-17, Fix 7 (Backup & DR Documentation)

---

## 1. RPO / RTO Objectives

| Metric | Target | Notes |
|--------|--------|-------|
| **RPO** (Recovery Point Objective) | 1 hour | WAL archiving streams continuously; worst-case data loss is the last un-archived segment. |
| **RTO** (Recovery Time Objective) | 4 hours | Includes restore, validation, DNS failover, and smoke tests. |

---

## 2. PostgreSQL Backup

### 2.1 Daily Logical Backup (pg_dump)

A Kubernetes CronJob runs daily at 02:00 UTC (see `infra/k8s/backup-cronjob.yaml`).

Manual execution:

```bash
export PGHOST=db.beguardit.internal
export PGUSER=bg_backup
export PGDATABASE=beguardit

pg_dump \
  --format=custom \
  --compress=9 \
  --verbose \
  --file="/tmp/beguardit_$(date -u +%Y%m%d_%H%M%S).dump"
```

Upload to S3:

```bash
aws s3 cp /tmp/beguardit_*.dump \
  s3://beguardit-backups/postgres/daily/ \
  --storage-class STANDARD_IA \
  --sse aws:kms
```

### 2.2 WAL Archiving (Continuous)

PostgreSQL is configured with `archive_mode = on` and `archive_command` pointing to an S3-upload script. WAL segments are streamed to:

```
s3://beguardit-backups/postgres/wal/
```

This provides point-in-time recovery (PITR) granularity down to the last committed transaction.

### 2.3 Retention Policy

| Type | Retention |
|------|-----------|
| Daily pg_dump | 30 days |
| WAL segments | 14 days |
| Monthly snapshots | 12 months |

---

## 3. Restore Procedure

### 3.1 Full Restore from pg_dump

```bash
# 1. Stop the API and worker deployments
kubectl scale deploy api-deployment worker-deployment --replicas=0 -n beguardit

# 2. Download the most recent backup
aws s3 cp s3://beguardit-backups/postgres/daily/beguardit_LATEST.dump /tmp/

# 3. Create a fresh database (or drop/recreate)
psql -h $PGHOST -U bg_admin -c "DROP DATABASE IF EXISTS beguardit_restore;"
psql -h $PGHOST -U bg_admin -c "CREATE DATABASE beguardit_restore OWNER bg_app;"

# 4. Restore
pg_restore \
  --dbname=beguardit_restore \
  --verbose \
  --no-owner \
  --role=bg_app \
  /tmp/beguardit_LATEST.dump

# 5. Validate row counts against the pre-backup manifest
psql -h $PGHOST -U bg_app -d beguardit_restore \
  -c "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname;"

# 6. Swap databases
psql -h $PGHOST -U bg_admin -c "ALTER DATABASE beguardit RENAME TO beguardit_old;"
psql -h $PGHOST -U bg_admin -c "ALTER DATABASE beguardit_restore RENAME TO beguardit;"

# 7. Restart services
kubectl scale deploy api-deployment worker-deployment --replicas=3 -n beguardit

# 8. Run smoke tests
curl -sf https://api.beguardit.io/api/v1/health | jq .
```

### 3.2 Point-in-Time Recovery (PITR)

```bash
# 1. Restore base backup
pg_restore --dbname=beguardit_pitr /tmp/beguardit_base.dump

# 2. Configure recovery.conf (PG 12+: use postgresql.conf)
cat >> /var/lib/postgresql/data/postgresql.conf <<CONF
restore_command = 'aws s3 cp s3://beguardit-backups/postgres/wal/%f %p'
recovery_target_time = '2026-03-18 10:30:00 UTC'
recovery_target_action = 'promote'
CONF

# 3. Create recovery signal and start
touch /var/lib/postgresql/data/recovery.signal
pg_ctl start -D /var/lib/postgresql/data
```

---

## 4. Redis Backup

Redis is used for rate-limiting counters and ephemeral job queues. Data is **not** backed up because it is fully reconstructable:

- Rate-limit keys expire within 60 seconds.
- Report job state is persisted in PostgreSQL; ARQ re-enqueues on restart.

If persistence is enabled (RDB/AOF), snapshots are written to the Redis data volume. No off-site backup is required for the current architecture.

---

## 5. S3 Report File Redundancy

Report files (HTML, PDF, SARIF) stored in S3 are protected by:

| Control | Setting |
|---------|---------|
| Versioning | Enabled |
| Replication | Cross-region replication to `us-west-2` |
| Lifecycle | Transition to Glacier after 90 days, expire after 365 days |
| Encryption | SSE-KMS with per-tenant key |

Reports can be regenerated from assessment data in PostgreSQL at any time via the worker queue.

---

## 6. Disaster Recovery Scenarios

| Scenario | Impact | Recovery Steps | Expected RTO |
|----------|--------|----------------|-------------|
| **Single pod crash** | None | Kubernetes restarts automatically. | < 1 min |
| **Database corruption** | High | Restore from latest pg_dump + WAL replay (Section 3). | 2-4 hours |
| **Availability zone failure** | Medium | Failover to read-replica in another AZ; promote to primary. | 15-30 min |
| **Region failure** | High | Deploy to DR region; restore from cross-region S3 backup; update DNS. | 4-8 hours |
| **Accidental data deletion** | Medium | PITR to timestamp before deletion (Section 3.2). | 1-2 hours |
| **Ransomware / compromise** | Critical | Isolate cluster; restore from immutable S3 backup (Object Lock); rotate all credentials. | 4-8 hours |

---

## 7. Testing Schedule

| Test | Frequency | Owner | Procedure |
|------|-----------|-------|-----------|
| Restore from pg_dump to staging | Monthly | Platform team | Run full restore (Section 3.1) against staging DB; compare row counts. |
| PITR drill | Quarterly | Platform team | Restore to a random timestamp within the last 7 days; validate data integrity. |
| Full DR failover | Semi-annually | SRE + Engineering leads | Simulate region failure; execute full failover; measure actual RTO. |
| Backup alert validation | Monthly | On-call engineer | Verify that backup-cronjob failure triggers PagerDuty alert. |
