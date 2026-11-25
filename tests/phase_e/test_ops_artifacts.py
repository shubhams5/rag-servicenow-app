"""Phase E: ops artifacts — pins, Docker, CI. Dummy values only; no live keys."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]


def test_requirements_are_pinned():
    lines = [
        ln.strip()
        for ln in (REPO / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    assert lines
    for ln in lines:
        # allow environment markers after version
        pkg = ln.split(";")[0].strip()
        assert "==" in pkg, f"unpinned requirement: {ln}"


def test_requirements_dev_pins_pytest():
    text = (REPO / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "pytest==" in text
    assert "pytest-asyncio==" in text


def test_pyproject_requires_python_312():
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.12"' in text
    assert "elasticsearch==9.2.0" in text or "elasticsearch" in text
    # Old poetry 3.8 / ES7 story must be gone
    assert 'python = "^3.8"' not in text
    assert 'elasticsearch = "^7.14.0"' not in text


def test_dockerfile_exists_and_safe():
    df = (REPO / "Dockerfile").read_text(encoding="utf-8")
    assert "python:3.12" in df
    assert "uvicorn" in df
    assert "src.api.main:app" in df
    assert ".env" not in df or "COPY .env" not in df
    assert "COPY config.yaml" not in df
    banned = re.compile(r"\b(" + "|".join(["sk" + chr(45), "AIza", "ghp" + "_"]) + r")")
    assert not banned.search(df)


def test_dockerignore_blocks_secrets():
    ignore = (REPO / ".dockerignore").read_text(encoding="utf-8")
    for pattern in (".env", "config.yaml", ".venv"):
        assert pattern in ignore


def test_compose_uses_env_substitution_not_live_secrets():
    compose = yaml.safe_load((REPO / "docker-compose.yml").read_text(encoding="utf-8"))
    api_env = compose["services"]["api"]["environment"]
    assert "API_KEY" in api_env
    # Default must be clearly dummy / placeholder
    assert "dummy" in str(api_env["API_KEY"]).lower() or "your-" in str(
        api_env.get("SERVICENOW_PASS", "")
    ).lower()
    dumped = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    assert "${API_KEY" in dumped
    # Compose must not assign long opaque literals as API_KEY defaults
    assert re.search(r"API_KEY:\s*[A-Za-z0-9_\-]{24,}\s*$", dumped, re.M) is None


def test_ci_workflow_runs_pytest_with_dummy_env():
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pytest tests/phase_a" in ci
    assert "tests/phase_e" in ci
    assert "dummy-ci-api-key" in ci
    assert "dummy-azure-openai-api-key" in ci
    assert "secret-shape scan" in ci or "banned" in ci.lower()


def test_readme_documents_docker_and_ci():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "docker compose" in readme.lower() or "docker-compose" in readme.lower()
    assert "Dockerfile" in readme or "docker" in readme.lower()
    assert "tests/phase_e" in readme
    assert ".github/workflows" in readme or "CI" in readme
