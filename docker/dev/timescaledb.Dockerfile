# timescaledb.Dockerfile
FROM timescale/timescaledb:latest-pg14

# Expose the default PostgreSQL port
EXPOSE 5432

# Volume for persistent data (managed by docker-compose or run command)
VOLUME /var/lib/postgresql/data