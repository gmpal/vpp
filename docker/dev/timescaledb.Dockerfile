# timescaledb.Dockerfile
FROM timescale/timescaledb:latest-pg14

# Environment variables for PostgreSQL/TimescaleDB
ENV POSTGRES_USER=gmpal
ENV POSTGRES_PASSWORD=postgresso
ENV POSTGRES_DB=postgres

# Expose the default PostgreSQL port
EXPOSE 5432

# Volume for persistent data (managed by docker-compose or run command)
VOLUME /var/lib/postgresql/data