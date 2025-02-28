# reset-db.Dockerfile is used to create a docker image that will reset the database to its initial state.
FROM python:3.10-slim
WORKDIR /app

RUN pip install --no-cache-dir pandas psycopg2-binary kafka-python
COPY backend ./backend

COPY ./entrypoints/reset_db.sh ./reset_db.sh
RUN chmod +x ./reset_db.sh
ENTRYPOINT ["./reset_db.sh"]
