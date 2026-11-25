"""Phase A: config loader behaviour with dummy credentials only."""

from __future__ import annotations

import os
from pathlib import Path

from src.config import (
    SECRET_KEYS,
    get_secret,
    load_config,
    redacted,
    reload_config,
)


def test_env_overrides_yaml(dummy_yaml: Path, dummy_env: dict[str, str]):
    cfg = load_config(
        config_path=str(dummy_yaml),
        env_file="",
        environ=dummy_env,
        load_env_file=False,
    )
    assert cfg["SERVICENOW_URL"] == dummy_env["SERVICENOW_URL"]
    assert cfg["SERVICENOW_PASS"] == "dummy-servicenow-password"
    assert cfg["ELASTICSEARCH_PASSWORD"] == "dummy-elasticsearch-password"


def test_yaml_used_when_env_missing(dummy_yaml: Path):
    cfg = load_config(
        config_path=str(dummy_yaml),
        env_file="",
        environ={},
        load_env_file=False,
    )
    assert cfg["SERVICENOW_URL"] == "https://from-yaml.service-now.com"
    assert cfg["SERVICENOW_PASS"] == "yaml-dummy-password"
    assert cfg["CHUNK_SIZE"] == 256


def test_missing_yaml_ok_with_env_only(tmp_path: Path, dummy_env: dict[str, str]):
    missing = tmp_path / "nope.yaml"
    cfg = load_config(
        config_path=str(missing),
        env_file="",
        environ=dummy_env,
        load_env_file=False,
    )
    assert cfg["API_KEY"] == "dummy-app-api-key"
    assert "SERVICENOW_USER" in cfg


def test_legacy_servicenow_aliases():
    environ = {
        "SERVICENOW_BASE_URL": "https://alias.service-now.com",
        "SERVICENOW_USERNAME": "alias-user",
        "SERVICENOW_PASSWORD": "alias-dummy-password",
    }
    cfg = load_config(
        config_path="nonexistent-config-phase-a.yaml",
        env_file="",
        environ=environ,
        load_env_file=False,
    )
    assert cfg["SERVICENOW_URL"] == "https://alias.service-now.com"
    assert cfg["SERVICENOW_USER"] == "alias-user"
    assert cfg["SERVICENOW_PASS"] == "alias-dummy-password"


def test_azure_key_aliases_from_api_key():
    cfg = load_config(
        config_path="nonexistent-config-phase-a.yaml",
        env_file="",
        environ={"AZURE_OPENAI_API_KEY": "dummy-azure-only"},
        load_env_file=False,
    )
    assert cfg["AZURE_OPENAI_API_KEY"] == "dummy-azure-only"
    assert cfg["AZURE_OPENAI_KEY"] == "dummy-azure-only"


def test_azure_key_aliases_from_legacy_key():
    cfg = load_config(
        config_path="nonexistent-config-phase-a.yaml",
        env_file="",
        environ={"AZURE_OPENAI_KEY": "dummy-legacy-azure"},
        load_env_file=False,
    )
    assert cfg["AZURE_OPENAI_KEY"] == "dummy-legacy-azure"
    assert cfg["AZURE_OPENAI_API_KEY"] == "dummy-legacy-azure"


def test_redacted_masks_secrets(dummy_env: dict[str, str]):
    cfg = load_config(
        config_path="nonexistent-config-phase-a.yaml",
        env_file="",
        environ=dummy_env,
        load_env_file=False,
    )
    safe = redacted(cfg)
    for key in SECRET_KEYS:
        if key in cfg and cfg[key]:
            assert safe[key] == "***REDACTED***"
            assert safe[key] != cfg[key]
    assert safe["SERVICENOW_URL"] == dummy_env["SERVICENOW_URL"]
    # Ensure redacted output never contains raw dummy secret strings for password keys
    assert "dummy-servicenow-password" not in str(safe.get("SERVICENOW_PASS"))
    assert "dummy-elasticsearch-password" not in str(safe.get("ELASTICSEARCH_PASSWORD"))


def test_get_secret_empty_returns_default():
    assert get_secret({"SERVICENOW_PASS": "  "}, "SERVICENOW_PASS", default="fallback") == "fallback"
    assert get_secret({}, "SERVICENOW_PASS", default="fallback") == "fallback"
    assert get_secret({"SERVICENOW_PASS": "dummy-x"}, "SERVICENOW_PASS") == "dummy-x"


def test_reload_config_updates_module_global(dummy_env: dict[str, str], tmp_path: Path):
    yaml_path = tmp_path / "reload.yaml"
    yaml_path.write_text("CHUNK_SIZE: 99\n", encoding="utf-8")
    reload_config(
        config_path=str(yaml_path),
        env_file="",
        environ=dummy_env,
        load_env_file=False,
    )
    from src import config as config_mod

    assert config_mod.config["CHUNK_SIZE"] == "512" or config_mod.config["CHUNK_SIZE"] == 512
    # env overlay wins for CHUNK_SIZE when present in dummy_env
    assert str(config_mod.config["CHUNK_SIZE"]) == "512"
    assert config_mod.config["API_KEY"] == "dummy-app-api-key"


def test_dotenv_does_not_override_existing_process_env(
    dummy_yaml: Path, dummy_dotenv: Path, monkeypatch
):
    monkeypatch.setenv("SERVICENOW_PASS", "process-dummy-password")
    # Clear unrelated noise; load_dotenv(override=False) must keep process value
    cfg = load_config(
        config_path=str(dummy_yaml),
        env_file=str(dummy_dotenv),
        environ=None,
        load_env_file=True,
    )
    assert cfg["SERVICENOW_PASS"] == "process-dummy-password"
    # Cleanup so later tests in same process are not polluted
    monkeypatch.delenv("SERVICENOW_PASS", raising=False)
    if "AZURE_OPENAI_API_KEY" in os.environ and os.environ["AZURE_OPENAI_API_KEY"].startswith(
        "dotenv-dummy"
    ):
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
