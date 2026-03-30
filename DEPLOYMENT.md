# Deployment Guide — vpp.digital

Assumes a VPS with Docker and Docker Compose already installed.

---

## 1. DNS Configuration

At your domain registrar, add the following A records pointing to your server's public IP:

```
A    vpp.digital          →  <server-ip>
A    api.vpp.digital      →  <server-ip>
```

DNS propagation can take up to 1 hour.

---

## 2. Clone the Repository

```bash
cd ~
git clone https://github.com/gmpal/vpp_forecasting_optimization.git
cd vpp_forecasting_optimization
```

---

## 3. Create `.env` File

```bash
PASSWORD=$(openssl rand -base64 32)
echo "MLflow password: $PASSWORD"  # save this somewhere safe
HASHED=$(openssl passwd -apr1 "$PASSWORD")

cat > .env << EOF
DOMAIN=vpp.digital
LETSENCRYPT_EMAIL=your-email@example.com
POSTGRES_DB=vpp
POSTGRES_USER=vpp_user
POSTGRES_PASSWORD=$(openssl rand -base64 32)
MLFLOW_BASIC_AUTH=admin:$HASHED
EOF
```

Never commit `.env` to git.

---

## 4. Reverse Proxy + SSL

Traefik is configured in `docker-compose.prod.yaml`. It automatically provisions Let's Encrypt certificates and routes traffic:

- `vpp.digital` → `frontend:80`
- `api.vpp.digital` → `backend:8000`
- `mlflow.vpp.digital` → `mlflow:5000` (protected by basic auth)

No manual configuration needed — Traefik reads Docker labels on each service.

---

## 5. Service Startup Order

```bash
# 1. Infrastructure
docker compose -f docker-compose.prod.yaml up -d timescaledb zookeeper kafka mlflow
sleep 60

# 2. Consumer (must be running before db-init produces data)
docker compose -f docker-compose.prod.yaml up -d consumer

# 3. Initialize database and stream synthetic data (run once)
docker compose -f docker-compose.prod.yaml --profile init up db-init

# 4. Application + reverse proxy
docker compose -f docker-compose.prod.yaml up -d traefik backend frontend
sleep 30

# 5. ML pipelines (run once, then on schedule)
docker compose -f docker-compose.prod.yaml --profile task up training
sleep 60
docker compose -f docker-compose.prod.yaml --profile task up inference
```

---

## 6. Security

| Risk | Fix |
|---|---|
| TimescaleDB/Kafka/ZooKeeper exposed | No external port mappings in prod compose |
| MLflow has no authentication | Protected by Traefik basic auth (`MLFLOW_BASIC_AUTH`) |
| `.env` in git | Confirmed in `.gitignore` |
| Weak DB password | Use `openssl rand -base64 32` (see step 3) |
| CORS set to `*` | Restrict `allow_origins` in `backend/api/main.py` to `https://vpp.digital` |

### Firewall (UFW)

Only expose ports 22, 80, and 443:

```bash
ufw allow 22
ufw allow 80
ufw allow 443
ufw enable
```

---

## 7. Backups

Docker volumes store all stateful data. Back them up regularly:

| Volume | Contents |
|---|---|
| `timescaledb-data` | All time-series data |
| `mlflow-artifacts` | Trained ML models |

Daily TimescaleDB backup script:

```bash
#!/bin/bash
docker exec timescaledb pg_dump -U vpp_user vpp | gzip > /backups/vpp_$(date +%F).sql.gz
```

Schedule with cron (`crontab -e`):
```
0 2 * * * /opt/vpp/backup.sh
```

---

## 8. Deployment Checklist

- [ ] DNS A records created for `vpp.digital` and `api.vpp.digital`
- [ ] Repository cloned to server
- [ ] `.env` file created with production values
- [ ] Firewall configured (ports 22, 80, 443 only)
- [ ] Services started in order (section 5)
- [ ] `db-init` run once to initialize schema and seed data
- [ ] `training` run at least once to register models in MLflow
- [ ] `inference` run to generate initial forecasts
- [ ] Frontend loads at `https://vpp.digital`
- [ ] API responds at `https://api.vpp.digital/docs`
- [ ] Backup script scheduled

---

## 9. Access Points

- **Frontend**: https://vpp.digital
- **API docs**: https://api.vpp.digital/docs
- **MLflow**: https://mlflow.vpp.digital (username: `admin`, password from step 3)

---

## 10. Useful Commands

```bash
# View logs
docker compose -f docker-compose.prod.yaml logs -f <service_name>

# Check running services
docker compose -f docker-compose.prod.yaml ps

# Restart a service
docker compose -f docker-compose.prod.yaml restart <service_name>

# Stop everything
docker compose -f docker-compose.prod.yaml down

# Full reset (deletes all data)
docker compose -f docker-compose.prod.yaml down -v
```
