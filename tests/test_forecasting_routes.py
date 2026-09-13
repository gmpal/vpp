"""Unit tests for forecasting pipeline triggers and status (no database, no subprocesses)."""
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api import main
from backend.api.routes import forecasting


@pytest.fixture(autouse=True)
def reset_status():
    saved = dict(forecasting.training_status)
    for key in forecasting.training_status:
        forecasting.training_status[key] = False if key.startswith("is_") else None
    yield
    forecasting.training_status.update(saved)


def _completed(returncode, stderr="", stdout=""):
    return SimpleNamespace(returncode=returncode, stderr=stderr, stdout=stdout)


def test_pipeline_runs_module_with_current_interpreter_from_repo_root():
    with patch.object(forecasting.subprocess, "run", return_value=_completed(0)) as run:
        assert forecasting.run_training() is True

    args, kwargs = run.call_args
    assert args[0] == [sys.executable, "-m", "backend.src.pipelines.training"]
    assert kwargs["cwd"] == forecasting.REPO_ROOT
    assert (forecasting.REPO_ROOT / "backend" / "src" / "pipelines" / "training.py").exists()
    status = forecasting.training_status
    assert status["last_training_ok"] is True
    assert status["last_training_error"] is None
    assert status["last_training"] is not None
    assert status["is_training"] is False


def test_failed_pipeline_is_reported_with_stderr_tail():
    stderr = "x" * 5000 + "\nConnectionError: mlflow unreachable"
    with patch.object(forecasting.subprocess, "run", return_value=_completed(1, stderr=stderr)):
        assert forecasting.run_inference() is False

    status = forecasting.training_status
    assert status["last_inference_ok"] is False
    assert status["last_inference_error"].startswith("exit code 1: ")
    assert status["last_inference_error"].endswith("ConnectionError: mlflow unreachable")
    assert len(status["last_inference_error"]) <= forecasting.ERROR_TAIL_CHARS + len("exit code 1: ")
    assert status["last_inference"] is not None  # finish time is still recorded


def test_timeout_is_reported_as_failure():
    with patch.object(forecasting.subprocess, "run", side_effect=subprocess.TimeoutExpired("python", 600)):
        assert forecasting.run_training() is False
    assert forecasting.training_status["last_training_ok"] is False
    assert forecasting.training_status["last_training_error"] == "timed out after 600 s"


def test_status_endpoint_exposes_outcomes():
    with patch.object(forecasting.subprocess, "run", return_value=_completed(2, stderr="boom")):
        forecasting.run_training()

    body = TestClient(main.app).get("/api/forecasting/status").json()
    assert body["last_training_ok"] is False
    assert body["last_training_error"] == "exit code 2: boom"
    assert body["last_inference_ok"] is None


@pytest.mark.parametrize("path, task_name, running_key", [
    ("/api/forecasting/train", "run_training", "is_training"),
    ("/api/forecasting/inference", "run_inference", "is_running_inference"),
])
def test_second_trigger_is_rejected_while_running(path, task_name, running_key):
    client = TestClient(main.app)
    with patch.object(forecasting, task_name, lambda: None):  # the background task never finishes the run
        first = client.post(path)
        second = client.post(path)

    assert first.status_code == 200
    assert first.json()["status"][running_key] is True
    assert second.status_code == 400
    assert "already in progress" in second.json()["detail"]

