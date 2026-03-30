# Runbook — Day-2 Operations

Covers operational tasks beyond initial deployment. For first-time setup see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Health Checks

```bash
# Check all services are running
docker compose ps

# Backend API
curl https://api.vpp.digital/health

# TimescaleDB
docker compose exec timescaledb pg_isready -U $POSTGRES_USER -d $POSTGRES_DB

# Kafka broker
docker compose exec kafka kafka-broker-api-versions --bootstrap-server=localhost:29092

# MLflow
curl http://localhost:5000/health
```

---

## Logs

```bash
# Follow logs for a service
docker compose logs -f backend
docker compose logs -f consumer
docker compose logs -f kafka

# Last 100 lines
docker compose logs --tail=100 backend
```

---

## Rotating Secrets

### Database password

1. Update `POSTGRES_PASSWORD` in `.env`
2. Update the password inside the database:
   ```bash
   docker compose exec timescaledb psql -U $POSTGRES_USER -d $POSTGRES_DB \
     -c "ALTER USER $POSTGRES_USER PASSWORD 'new-password';"
   ```
3. Restart dependent services:
   ```bash
   docker compose restart backend consumer training inference
   ```

### MLflow basic auth (production)

1. Generate a new hash:
   ```bash
   PASSWORD=$(openssl rand -base64 32)
   HASHED=$(openssl passwd -apr1 "$PASSWORD")
   echo "New password: $PASSWORD"
   echo "MLFLOW_BASIC_AUTH=admin:$HASHED"
   ```
2. Update `MLFLOW_BASIC_AUTH` in `.env`
3. Restart Traefik: `docker compose restart traefik`

---

## Kafka Consumer Lag

If the consumer is falling behind (data not appearing in the frontend):

```bash
# Check consumer group lag
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:29092 \
  --group test-group \
  --describe

# Restart the consumer
docker compose restart consumer

# If topics are missing, recreate them (data loss — only if db-init needs rerun)
docker compose exec kafka kafka-topics \
  --bootstrap-server localhost:29092 \
  --list
```

---

## MLflow Model Rollback

If a newly registered model produces bad forecasts:

```bash
# Open MLflow UI to find the previous good version
open https://mlflow.vpp.digital

# Or via CLI — list versions for a model
docker compose exec backend python -c "
import mlflow
client = mlflow.MlflowClient()
for v in client.search_model_versions(\"name='Best_solar_Model'\"):
    print(v.version, v.current_stage, v.run_id)
"
```

Then in the MLflow UI, transition the previous version back to "None" stage and archive the bad one. Re-run inference to regenerate forecasts from the older model.

---

## TimescaleDB Disk Full

```bash
# Check disk usage inside the container
docker compose exec timescaledb df -h /var/lib/postgresql/data

# Check table sizes
docker compose exec timescaledb psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
SELECT hypertable_name,
       pg_size_pretty(hypertable_size(format('%I', hypertable_name)::regclass)) AS size
FROM timescaledb_information.hypertables
ORDER BY hypertable_size(format('%I', hypertable_name)::regclass) DESC;
"

# Drop old chunks (data older than 90 days)
docker compose exec timescaledb psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
SELECT drop_chunks('solar', INTERVAL '90 days');
SELECT drop_chunks('wind', INTERVAL '90 days');
SELECT drop_chunks('load', INTERVAL '90 days');
SELECT drop_chunks('market', INTERVAL '90 days');
"
```

---

## Backup & Restore

### Backup

```bash
# Dump the full database
docker compose exec timescaledb pg_dump \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  --format=custom \
  --file=/var/lib/postgresql/data/backup_$(date +%Y%m%d).dump

# Copy dump out of container
docker cp timescaledb:/var/lib/postgresql/data/backup_$(date +%Y%m%d).dump ./backups/

# Backup MLflow artifacts
docker cp mlflow:/mlflow/artifacts ./backups/mlflow-artifacts-$(date +%Y%m%d)
```

### Restore

```bash
# Stop app services (keep DB running)
docker compose stop backend consumer training inference

# Restore
docker compose exec timescaledb pg_restore \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  --clean /var/lib/postgresql/data/backup_YYYYMMDD.dump

# Restart
docker compose start backend consumer
```

---

## Re-running ML Pipelines

```bash
# Retrain all models (takes several minutes)
docker compose --profile task up training

# Regenerate forecasts from latest models
docker compose --profile task up inference
```

---

## Full Reset (Development Only)

Wipes all data and starts fresh:

```bash
docker compose down -v                        # removes volumes (all data)
docker compose up -d timescaledb zookeeper kafka mlflow
docker compose up -d consumer
docker compose --profile init up db-init      # re-seed data
docker compose up -d backend frontend
```

---

## Updating the Application

```bash
git pull origin main

# Rebuild changed services
docker compose build backend frontend

# Rolling restart (one at a time to minimise downtime)
docker compose up -d --no-deps backend
docker compose up -d --no-deps frontend
```
