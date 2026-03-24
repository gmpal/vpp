# Development Consumer Dockerfile: docker/dev/consumer.Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy only the requirements file to leverage Docker cache
COPY requirements/requirements-consumer.txt .
# Install only the necessary system dependencies for psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev netcat-openbsd && \
    # Now, install the minimal python dependencies
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-consumer.txt && \
    # Finally, clean up the apt cache
    rm -rf /var/lib/apt/lists/*

COPY ./backend ./backend
COPY ./entrypoints/consume.sh /app/consume.sh
RUN chmod +x /app/consume.sh

ENTRYPOINT ["/app/consume.sh"]
