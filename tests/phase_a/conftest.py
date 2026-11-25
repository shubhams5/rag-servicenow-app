"""Phase A fixtures — dummy credentials only. Never load real secret files for assertions."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# Explicit dummy values — not real credentials.
DUMMY_ENV = {
    "SERVICENOW_URL": "https://dummy-instance.service-now.com",
    "SERVICENOW_USER": "dummy-user",
    "SERVICENOW_PASS": "dummy-servicenow-password",
    "SERVICENOW_API_KEY": "dummy-servicenow-api-key",
    "AZURE_OPENAI_API_KEY": "dummy-azure-openai-api-key",
    "AZURE_OPENAI_ENDPOINT": "https://dummy.openai.azure.com",
    "AZURE_OPENAI_MODEL": "dummy-deployment",
    "ELASTICSEARCH_HOST": "localhost",
    "ELASTICSEARCH_PORT": "9200",
    "ELASTICSEARCH_USER": "dummy-elastic-user",
    "ELASTICSEARCH_PASSWORD": "dummy-elasticsearch-password",
    "ELASTICSEARCH_INDEX_NAME": "articles_test",
    "ELASTICSEARCH_FAILURE_INDEX": "article_failures_test",
    "ELASTICSEARCH_USE_SSL": "false",
    "API_KEY": "dummy-app-api-key",
    "CHUNK_OVERLAP": "50",
    "CHUNK_SIZE": "512",
    "LOG_LEVEL": "INFO",
}


@pytest.fixture
def dummy_env() -> dict[str, str]:
    return dict(DUMMY_ENV)


@pytest.fixture
def dummy_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "SERVICENOW_URL": "https://from-yaml.service-now.com",
                "SERVICENOW_PASS": "yaml-dummy-password",
                "ELASTICSEARCH_PASSWORD": "yaml-dummy-es-password",
                "CHUNK_SIZE": 256,
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def dummy_dotenv(tmp_path: Path) -> Path:
    path = tmp_path / ".env"
    path.write_text(
        "\n".join(
            [
                "SERVICENOW_PASS=dotenv-dummy-password",
                "AZURE_OPENAI_API_KEY=dotenv-dummy-azure-key",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path
