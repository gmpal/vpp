FROM python:3.8-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir pandas psycopg2-binary
COPY data ./data
COPY src ./src
COPY config.ini .

COPY 01_filldb.py . 
CMD ["python", "01_filldb.py"]
