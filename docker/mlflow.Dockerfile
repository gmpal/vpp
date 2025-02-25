FROM python:3.9-slim
RUN pip install mlflow psycopg2-binary boto3
ENV MLFLOW_BACKEND_STORE_URI="file:///mlflow/mlruns"
ENV MLFLOW_DEFAULT_ARTIFACT_ROOT="s3://mlflow-artifacts-production"
CMD mlflow server --backend-store-uri "$MLFLOW_BACKEND_STORE_URI" --default-artifact-root "$MLFLOW_DEFAULT_ARTIFACT_ROOT" --host 0.0.0.0 --port 5000
