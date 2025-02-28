# inference.Dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y libpq-dev gcc git netcat-openbsd

WORKDIR /app

COPY ./requirements/requirements-forecasting.txt .
RUN pip install --no-cache-dir -r requirements-forecasting.txt

COPY ./backend ./backend
COPY ./entrypoints/inference.sh /app/inference.sh

RUN chmod +x /app/inference.sh
ENTRYPOINT ["/app/inference.sh"]
