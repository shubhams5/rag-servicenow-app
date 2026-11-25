"""Phase D fixtures — dummy API_KEY only. No live provider keys."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import reload_config

DUMMY_API_KEY = "dummy-app-api-key-phase-d"


@pytest.fixture
def dummy_api_key() -> str:
    return DUMMY_API_KEY


@pytest.fixture
def secured_config(dummy_api_key):
    reload_config(
        config_path="nonexistent-phase-d-config.yaml",
        env_file="",
        environ={
            "API_KEY": dummy_api_key,
            "ELASTICSEARCH_HOST": "localhost",
            "ELASTICSEARCH_INDEX_NAME": "articles_test",
            "ENVIRONMENT": "development",
            "DISABLE_API_DOCS": "false",
            "HTTP_TIMEOUT_SECONDS": "5",
        },
        load_env_file=False,
    )
    return dummy_api_key


@pytest.fixture
def client(secured_config):
    # Import after config reload so auth sees dummy key.
    from src.api.main import app

    with TestClient(app) as test_client:
        yield test_client
