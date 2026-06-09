from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def reference_batch() -> list[dict]:
    path = Path(__file__).parent / "reference_batch.json"
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def query_annots(reference_batch: list[dict]) -> list[dict]:
    return [a for a in reference_batch if a["is_query"]]


@pytest.fixture(scope="session")
def db_annots(reference_batch: list[dict]) -> list[dict]:
    return [a for a in reference_batch if not a["is_query"]]


@pytest.fixture(scope="session")
def ml_service_url() -> str:
    return os.environ.get("ML_SERVICE_URL", "http://ml-service:6050")


@pytest.fixture(scope="session")
def wbia_core_url() -> str:
    return os.environ.get("WBIA_CORE_URL", "http://wbia-core:5000")


@pytest.fixture(scope="session")
def wbia_url() -> str:
    return os.environ.get("WBIA_URL", "http://wbia:5000")


@pytest.fixture(scope="session")
def predict_model_id() -> str:
    return os.environ.get("PREDICT_MODEL_ID", "yolo11n")


@pytest.fixture(scope="session")
def extract_model_id() -> str:
    return os.environ.get("EXTRACT_MODEL_ID", "miewid-hf-v3")


@pytest.fixture(scope="session")
def identify_config() -> dict:
    return {
        "pipeline_root": "vsmany",
        "K": 4,
        "Knorm": 1,
        "Kpad": 0,
        "score_method": "nsum",
        "fg_on": False,
        "sv_on": False,
        "flann_algorithm": "kdtree",
    }


@pytest.fixture(scope="session")
def predict_params() -> dict:
    return {"conf": 0.25}


def requires_service(url: str, timeout: float = 5.0):
    try:
        import requests

        requests.get(f"{url}/", timeout=timeout)
    except Exception:
        pytest.skip(f"Service not available: {url}")
