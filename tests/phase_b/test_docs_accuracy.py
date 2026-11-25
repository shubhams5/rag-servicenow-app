"""Phase B: docs must match implemented API/entrypoints (no secret values)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
README = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
GEMINI = (REPO_ROOT / "GEMINI.md").read_text(encoding="utf-8")
MAIN_PY = REPO_ROOT / "src" / "api" / "main.py"
LLM_PY = REPO_ROOT / "src" / "generation" / "llm.py"


def _route_paths_from_main() -> set[str]:
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))
    paths: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for deco in node.decorator_list:
                if (
                    isinstance(deco, ast.Call)
                    and isinstance(deco.func, ast.Attribute)
                    and deco.func.attr in {"get", "post", "put", "delete", "patch"}
                    and deco.args
                    and isinstance(deco.args[0], ast.Constant)
                    and isinstance(deco.args[0].value, str)
                ):
                    paths.add(deco.args[0].value)
    return paths


def test_readme_documents_real_api_routes():
    routes = _route_paths_from_main()
    assert "/retrieve" in routes
    assert "/rag" in routes
    assert "/retrieve" in README
    assert "/rag" in README
    # Must not list obsolete path as a live endpoint
    assert re.search(r"(?m)^\s*\|?\s*POST\s*\|?\s*`?/rag_ticket", README) is None
    assert "`/rag_ticket`" not in README


def test_gemini_documents_real_api_routes():
    assert "/retrieve" in GEMINI
    assert "/rag" in GEMINI
    assert "`/rag_ticket`" not in GEMINI
    assert "POST /rag_ticket" not in GEMINI


def test_readme_uvicorn_module_path():
    assert "uvicorn src.api.main:app" in README
    assert "uvicorn src/api/main:app" not in README


def test_gemini_uvicorn_module_path():
    assert "uvicorn src.api.main:app" in GEMINI


def test_docs_do_not_claim_removed_test_clis():
    banned = (
        "elasticsearch.py --test-connection",
        "llm.py --test",
    )
    for phrase in banned:
        assert phrase not in README
        assert phrase not in GEMINI


def test_docs_do_not_claim_active_azure_or_mistral_generation():
    # Soft claims that misled operators
    assert "Supports Hugging Face models (Flan-T5, Mistral) and Azure OpenAI" not in README
    assert "Hugging Face Transformers & Azure OpenAI" not in GEMINI
    # loguru may appear only as an explicit non-claim
    if "loguru" in GEMINI.lower():
        assert "not" in GEMINI.lower().split("loguru")[0][-40:]
    # Must not claim rotating logs as a current feature
    assert "Logging is enabled with rotating file handlers" not in README
    assert "logs are configured" not in GEMINI.lower() or "not" in GEMINI.lower()


def test_readme_points_at_security_and_dummy_tests():
    assert "SECURITY.md" in README
    assert "dummy" in README.lower()
    assert "tests/phase_a" in README
    assert "tests/phase_b" in README
    assert "tests/phase_d" in README
    assert "tests/phase_e" in README
    assert "X-API-Key" in README
    assert "/healthz" in README
    assert "Dockerfile" in README


def test_readme_mentions_configurable_llm():
    llm_src = LLM_PY.read_text(encoding="utf-8")
    assert "LLM_PROVIDER" in llm_src
    assert "azure_openai" in llm_src
    assert "huggingface" in llm_src
    assert "LLM_PROVIDER" in README
    assert "flan-t5" in README.lower()
    assert "azure_openai" in README.lower() or "Azure OpenAI" in README


def test_readme_elser_endpoint_id_matches_code():
    kb_fields = (REPO_ROOT / "src" / "rag" / "kb_fields.py").read_text(encoding="utf-8")
    embed = (REPO_ROOT / "src" / "embeddings" / "chunk_and_embed.py").read_text(
        encoding="utf-8"
    )
    assert "elser-model-2-endpoint" in kb_fields
    assert "ELSER_INFERENCE_ID" in embed
    assert "elser-model-2-endpoint" in README
    # Old incorrect deploy-only story should not be the primary instruction
    assert ".elser_model_1/_deploy" not in README


def test_key_source_files_exist_as_documented():
    for rel in (
        "src/api/main.py",
        "src/config.py",
        "src/run_pipeline.py",
        "src/run_scheduler.py",
        "src/rag/pipeline.py",
        "src/generation/llm.py",
        "src/storage/elasticsearch.py",
        "SECURITY.md",
        ".env.example",
        "config.example.yaml",
    ):
        assert (REPO_ROOT / rel).is_file(), f"missing {rel}"


def test_docs_contain_no_provider_shaped_live_keys():
    parts = ["sk" + chr(45), "sk" + "_", "AIza", "ghp" + "_"]
    banned = re.compile(r"\b(" + "|".join(parts) + r")")
    for name, text in (("README.md", README), ("GEMINI.md", GEMINI)):
        assert not banned.search(text), f"Banned key-shaped token in {name}"
