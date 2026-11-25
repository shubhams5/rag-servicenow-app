"""Application configuration.

Precedence (highest wins):
  1. Process environment variables
  2. Optional .env file (via python-dotenv)
  3. Optional YAML file (config.yaml)

Never hardcode secrets here. Use placeholders in committed examples only.
Paths can be overridden with RAG_CONFIG_PATH and RAG_ENV_FILE (useful for tests).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is a declared dependency
    def load_dotenv(*_args, **_kwargs):  # type: ignore[misc]
        return False


# Canonical keys used across the app. Keep examples and docs aligned with this list.
CONFIG_KEYS = (
    "SERVICENOW_URL",
    "SERVICENOW_USER",
    "SERVICENOW_PASS",
    "SERVICENOW_API_KEY",
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_MODEL",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "LLM_PROVIDER",
    "LLM_MODEL",
    "HF_MODEL_NAME",
    "LLM_MAX_NEW_TOKENS",
    "ELASTICSEARCH_HOST",
    "ELASTICSEARCH_PORT",
    "ELASTICSEARCH_USER",
    "ELASTICSEARCH_PASSWORD",
    "ELASTICSEARCH_INDEX_NAME",
    "ELASTICSEARCH_FAILURE_INDEX",
    "ELASTICSEARCH_USE_SSL",
    "CHUNK_OVERLAP",
    "CHUNK_SIZE",
    "LOG_LEVEL",
    "API_KEY",
    "API_HOST",
    "API_PORT",
    "ENVIRONMENT",
    "DISABLE_API_DOCS",
    "HTTP_TIMEOUT_SECONDS",
    "TESSERACT_CMD",
)

# Legacy / alternate names mapped onto canonical keys.
ENV_ALIASES = {
    "SERVICENOW_BASE_URL": "SERVICENOW_URL",
    "SERVICENOW_USERNAME": "SERVICENOW_USER",
    "SERVICENOW_PASSWORD": "SERVICENOW_PASS",
}

SECRET_KEYS = frozenset(
    {
        "SERVICENOW_PASS",
        "SERVICENOW_API_KEY",
        "AZURE_OPENAI_KEY",
        "AZURE_OPENAI_API_KEY",
        "ELASTICSEARCH_PASSWORD",
        "API_KEY",
    }
)


def _read_yaml(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must be a mapping: {config_path}")
    return {str(key): value for key, value in data.items()}


def _apply_aliases(data: MutableMapping[str, Any]) -> None:
    for alias, canonical in ENV_ALIASES.items():
        if alias in data and canonical not in data:
            data[canonical] = data[alias]

    # Prefer explicit AZURE_OPENAI_API_KEY; fall back to AZURE_OPENAI_KEY.
    if not data.get("AZURE_OPENAI_API_KEY") and data.get("AZURE_OPENAI_KEY"):
        data["AZURE_OPENAI_API_KEY"] = data["AZURE_OPENAI_KEY"]
    if not data.get("AZURE_OPENAI_KEY") and data.get("AZURE_OPENAI_API_KEY"):
        data["AZURE_OPENAI_KEY"] = data["AZURE_OPENAI_API_KEY"]

    # HF model aliases
    if not data.get("LLM_MODEL") and data.get("HF_MODEL_NAME"):
        data["LLM_MODEL"] = data["HF_MODEL_NAME"]
    if not data.get("HF_MODEL_NAME") and data.get("LLM_MODEL"):
        data["HF_MODEL_NAME"] = data["LLM_MODEL"]

    # Azure deployment name aliases
    if not data.get("AZURE_OPENAI_DEPLOYMENT") and data.get("AZURE_OPENAI_MODEL"):
        data["AZURE_OPENAI_DEPLOYMENT"] = data["AZURE_OPENAI_MODEL"]
    if not data.get("AZURE_OPENAI_MODEL") and data.get("AZURE_OPENAI_DEPLOYMENT"):
        data["AZURE_OPENAI_MODEL"] = data["AZURE_OPENAI_DEPLOYMENT"]

    # Defaults for generation
    data.setdefault("LLM_PROVIDER", "huggingface")
    data.setdefault("LLM_MODEL", "google/flan-t5-base")
    data.setdefault("HF_MODEL_NAME", data.get("LLM_MODEL", "google/flan-t5-base"))
    data.setdefault("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    data.setdefault("LLM_MAX_NEW_TOKENS", "512")


def _overlay_environ(data: MutableMapping[str, Any], environ: Mapping[str, str]) -> None:
    for key in CONFIG_KEYS:
        if key in environ and environ[key] != "":
            data[key] = environ[key]
    for alias, canonical in ENV_ALIASES.items():
        if alias in environ and environ[alias] != "":
            # Alias env wins only when canonical env is unset.
            if canonical not in environ or environ[canonical] == "":
                data[canonical] = environ[alias]
            data[alias] = environ[alias]


def load_config(
    config_path: Optional[str] = None,
    env_file: Optional[str] = None,
    environ: Optional[Mapping[str, str]] = None,
    load_env_file: bool = True,
) -> dict[str, Any]:
    """Load config from YAML + .env + process env.

    Args:
        config_path: YAML path. Defaults to RAG_CONFIG_PATH or config.yaml.
        env_file: dotenv path. Defaults to RAG_ENV_FILE or .env. Pass "" to skip.
        environ: Mapping used instead of os.environ (tests).
        load_env_file: When False, skip dotenv entirely.
    """
    yaml_path = Path(
        config_path
        if config_path is not None
        else os.environ.get("RAG_CONFIG_PATH", "config.yaml")
    )

    if load_env_file:
        dotenv_path = (
            env_file
            if env_file is not None
            else os.environ.get("RAG_ENV_FILE", ".env")
        )
        if dotenv_path:
            load_dotenv(dotenv_path, override=False)

    data: dict[str, Any] = _read_yaml(yaml_path)
    _overlay_environ(data, environ if environ is not None else os.environ)
    _apply_aliases(data)
    return data


def get_secret(cfg: Mapping[str, Any], key: str, default: Optional[str] = None) -> Optional[str]:
    """Fetch a secret-like value. Returns default when missing/empty."""
    value = cfg.get(key, default)
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def redacted(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Copy of config with secret values masked (safe for logs)."""
    out: dict[str, Any] = {}
    for key, value in cfg.items():
        if key in SECRET_KEYS and value not in (None, ""):
            out[key] = "***REDACTED***"
        else:
            out[key] = value
    return out


def reload_config(
    config_path: Optional[str] = None,
    env_file: Optional[str] = None,
    environ: Optional[Mapping[str, str]] = None,
    load_env_file: bool = True,
) -> dict[str, Any]:
    """Reload and replace the module-level config dict in place."""
    global config
    fresh = load_config(
        config_path=config_path,
        env_file=env_file,
        environ=environ,
        load_env_file=load_env_file,
    )
    config.clear()
    config.update(fresh)
    return config


# Module-level config used by existing imports: `from src.config import config`
config: dict[str, Any] = load_config()
