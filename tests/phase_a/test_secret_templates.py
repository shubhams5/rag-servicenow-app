"""Phase A: committed templates must stay placeholders; gitignore must block secret files."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

PLACEHOLDER_HINTS = (
    "your-",
    "your_",
    "<your",
    "example",
    "changeme",
    "dummy-",
    "localhost",
)

SECRET_NAME_RE = re.compile(
    r"(PASS|PASSWORD|API_KEY|SECRET|TOKEN|AZURE_OPENAI_KEY)\s*[=:]\s*[\"']?([^\s\"']+)",
    re.IGNORECASE,
)


def _is_placeholder(value: str) -> bool:
    low = value.strip().strip("\"'").lower()
    if not low:
        return True
    return any(hint in low for hint in PLACEHOLDER_HINTS)


@pytest.mark.parametrize(
    "relative",
    [".env.example", "config.example.yaml"],
)
def test_example_secret_values_are_placeholders(relative: str):
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")
    matches = SECRET_NAME_RE.findall(text)
    assert matches, f"Expected secret-like keys in {relative}"
    for _name, value in matches:
        assert _is_placeholder(value), (
            f"{relative} has non-placeholder value for a secret-like key. "
            "Replace with your-* placeholder. Do not commit real credentials."
        )


def test_gitignore_blocks_secret_files():
    ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in (".env", "config.yaml", "!.env.example", "secrets/"):
        assert pattern in ignore


def test_security_doc_exists():
    path = REPO_ROOT / "SECURITY.md"
    assert path.is_file()
    body = path.read_text(encoding="utf-8").lower()
    assert "never commit" in body
    assert "rotate" in body


def test_tests_do_not_embed_provider_shaped_keys():
    """Guard: phase_a tests must not contain live provider key prefixes."""
    phase_a = REPO_ROOT / "tests" / "phase_a"
    # Built without embedding banned prefixes as contiguous literals in this file.
    parts = ["sk" + chr(45), "sk" + "_", "AIza", "ghp" + "_", "xox[baprs]" + chr(45)]
    banned = re.compile(r"\b(" + "|".join(parts) + r")", re.IGNORECASE)
    for path in phase_a.rglob("*.py"):
        if path.name == "test_secret_templates.py":
            continue
        text = path.read_text(encoding="utf-8")
        assert not banned.search(text), f"Banned key-shaped token found in {path}"
