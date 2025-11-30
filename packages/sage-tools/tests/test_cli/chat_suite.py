"""Test cases for ``sage chat`` command group."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from .helpers import CLITestCase

CHAT_MODULE = "sage.cli.commands.apps.chat"


def _patch_noop(name: str):
    return lambda: patch(f"{CHAT_MODULE}.{name}", return_value=None)


def _patch_resolve_index_root():
    temp_dir = Path(tempfile.mkdtemp(prefix="sage_chat_cli_index_"))
    return patch(f"{CHAT_MODULE}.resolve_index_root", return_value=temp_dir)


def _patch_default_source_dir():
    temp_dir = Path(tempfile.mkdtemp(prefix="sage_chat_cli_docs_"))
    return patch(f"{CHAT_MODULE}.default_source_dir", return_value=temp_dir)


def _patch_load_manifest():
    fake = SimpleNamespace(
        db_path=Path("/tmp/fake.sagedb"),
        created_at="2025-01-01T00:00:00Z",
        source_dir="/tmp/docs",
        num_documents=10,
        num_chunks=120,
        embedding={"method": "hash", "params": {"dim": 384}},
        chunk_size=800,
        chunk_overlap=160,
    )
    return patch(f"{CHAT_MODULE}.load_manifest", return_value=fake)


def _patch_ingest_source():
    return patch(f"{CHAT_MODULE}.ingest_source", return_value=None)


def collect_cases() -> list[CLITestCase]:
    def check_missing_model(result):
        assert result.exit_code == 2
        assert "--embedding-model" in result.stderr

    return [
        CLITestCase("sage chat --help", ["chat", "--help"]),
        CLITestCase(
            "sage chat ingest default",
            ["chat", "ingest", "--index", "ci-test"],
            patch_factories=[
                _patch_noop("ensure_sage_db"),
                _patch_default_source_dir(),
                _patch_resolve_index_root(),
                _patch_ingest_source(),
            ],
        ),
        CLITestCase(
            "sage chat ingest needs model",
            ["chat", "ingest", "--embedding-method", "openai"],
            patch_factories=[
                _patch_noop("ensure_sage_db"),
                _patch_default_source_dir(),
                _patch_resolve_index_root(),
            ],
            expected_exit_code=2,
            check=check_missing_model,
        ),
        CLITestCase(
            "sage chat show manifest",
            ["chat", "show", "--index", "ci-test"],
            patch_factories=[
                _patch_noop("ensure_sage_db"),
                _patch_resolve_index_root(),
                _patch_load_manifest(),
            ],
        ),
    ]
