"""LLM provider selection — dummy credentials only, no live API calls."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.config import load_config
from src.generation.llm import (
    _azure_chat_url,
    generate_solution,
    get_hf_model_name,
    get_provider_name,
    reset_llm_cache,
)


DUMMY_TICKET = {
    "number": "INC999",
    "short_description": "dummy vpn issue",
}
DUMMY_HITS = [{"title": "Dummy KB", "chunk": "Restart dummy VPN client."}]


@pytest.fixture(autouse=True)
def _clear_llm_cache():
    reset_llm_cache()
    yield
    reset_llm_cache()


def test_provider_aliases():
    assert get_provider_name({"LLM_PROVIDER": "hf"}) == "huggingface"
    assert get_provider_name({"LLM_PROVIDER": "Azure"}) == "azure_openai"
    assert get_provider_name({"LLM_PROVIDER": "azure-openai"}) == "azure_openai"


def test_hf_model_from_config_aliases():
    cfg = load_config(
        config_path="missing-llm.yaml",
        env_file="",
        environ={"HF_MODEL_NAME": "dummy/org-model"},
        load_env_file=False,
    )
    assert get_hf_model_name(cfg) == "dummy/org-model"
    assert cfg["LLM_MODEL"] == "dummy/org-model"


def test_generate_solution_uses_injected_fn():
    cfg = {"LLM_PROVIDER": "huggingface", "LLM_MAX_NEW_TOKENS": "64"}
    fake = MagicMock(return_value="Dummy provider answer")
    out = generate_solution(
        DUMMY_TICKET, DUMMY_HITS, cfg=cfg, generate_fn=fake
    )
    assert out == "Dummy provider answer"
    fake.assert_called_once()
    prompt, tokens, passed_cfg = fake.call_args[0]
    assert "dummy vpn" in prompt.lower() or "VPN" in prompt
    assert tokens == 64
    assert passed_cfg["LLM_PROVIDER"] == "huggingface"


def test_unsupported_provider_raises():
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        generate_solution(
            DUMMY_TICKET,
            DUMMY_HITS,
            cfg={"LLM_PROVIDER": "not-a-real-provider"},
        )


def test_azure_requires_config():
    with pytest.raises(ValueError, match="Azure OpenAI requires"):
        generate_solution(
            DUMMY_TICKET,
            DUMMY_HITS,
            cfg={"LLM_PROVIDER": "azure_openai"},
        )


def test_azure_openai_http_path_uses_api_key_header():
    cfg = {
        "LLM_PROVIDER": "azure_openai",
        "AZURE_OPENAI_API_KEY": "dummy-azure-openai-api-key",
        "AZURE_OPENAI_ENDPOINT": "https://dummy.openai.azure.com",
        "AZURE_OPENAI_DEPLOYMENT": "dummy-deployment",
        "AZURE_OPENAI_API_VERSION": "2024-02-15-preview",
        "HTTP_TIMEOUT_SECONDS": "5",
        "LLM_MAX_NEW_TOKENS": "32",
    }

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {"message": {"content": "Dummy Azure answer"}}
                ]
            }

    with patch("src.generation.llm.requests.post", return_value=FakeResp()) as post:
        out = generate_solution(DUMMY_TICKET, DUMMY_HITS, cfg=cfg)

    assert out == "Dummy Azure answer"
    args, kwargs = post.call_args
    assert "chat/completions" in args[0]
    assert kwargs["headers"]["api-key"] == "dummy-azure-openai-api-key"
    assert "Authorization" not in kwargs["headers"]


def test_azure_chat_url_shape():
    url = _azure_chat_url(
        "https://dummy.openai.azure.com/",
        "dummy-deployment",
        "2024-02-15-preview",
    )
    assert url.startswith("https://dummy.openai.azure.com/openai/deployments/")
    assert "api-version=2024-02-15-preview" in url


def test_scheduler_renamed_file_exists():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert (root / "src" / "run_scheduler.py").is_file()
    text = (root / "src" / "run_schedular.py").read_text(encoding="utf-8")
    assert "deprecated" in text.lower()
    assert "run_scheduler" in text
