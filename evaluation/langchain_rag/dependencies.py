from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
SHARED_WORKLOAD_REPO_ROOT = REPO_ROOT.parent / "llm-serving-workloads"
SHARED_WORKLOAD_SRC_DIR = SHARED_WORKLOAD_REPO_ROOT / "src"


def bootstrap_paths() -> None:
    for candidate in (REPO_ROOT, SRC_DIR, SHARED_WORKLOAD_SRC_DIR):
        if not candidate.exists():
            continue
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


bootstrap_paths()


class _MissingRuntimeDependency:
    def __init__(self, *args, **kwargs) -> None:
        raise RuntimeError("Optional runtime dependency is not available in this environment.")

    @classmethod
    def from_messages(cls, *args, **kwargs):
        raise RuntimeError("Optional runtime dependency is not available in this environment.")


class _FallbackMessage:
    def __init__(self, content: str = "") -> None:
        self.content = content


class _FallbackChatHistory:
    def __init__(self) -> None:
        self.messages: list[_FallbackMessage] = []

    def add_user_message(self, content: str) -> None:
        self.messages.append(HumanMessage(content))

    def add_ai_message(self, content: str) -> None:
        self.messages.append(AIMessage(content))


class _FallbackDocument:
    def __init__(self, page_content: str, metadata: dict[str, Any] | None = None) -> None:
        self.page_content = page_content
        self.metadata = dict(metadata or {})


try:
    from langchain.chat_models import init_chat_model
    from langchain_core.chat_history import InMemoryChatMessageHistory
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnableLambda
    from langchain_core.vectorstores import InMemoryVectorStore
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError as exc:  # pragma: no cover - exercised by CLI/runtime only
    LANGCHAIN_IMPORT_ERROR: ImportError | None = exc
    init_chat_model = None
    InMemoryChatMessageHistory = _FallbackChatHistory
    Document = _FallbackDocument

    class Embeddings:  # pragma: no cover - only used when LangChain is unavailable
        pass

    BaseMessage = _FallbackMessage
    HumanMessage = _FallbackMessage
    AIMessage = _FallbackMessage
    ChatPromptTemplate = _MissingRuntimeDependency
    RunnableLambda = _MissingRuntimeDependency
    InMemoryVectorStore = _MissingRuntimeDependency
    RecursiveCharacterTextSplitter = _MissingRuntimeDependency
else:
    LANGCHAIN_IMPORT_ERROR = None


try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - exercised by CLI/runtime only
    OPENAI_IMPORT_ERROR: ImportError | None = exc
    OpenAI = None
else:
    OPENAI_IMPORT_ERROR = None


try:
    import faiss
except ImportError as exc:  # pragma: no cover - exercised by CLI/runtime only
    FAISS_IMPORT_ERROR: ImportError | None = exc
    faiss = None
else:
    FAISS_IMPORT_ERROR = None


try:
    from llm_serving_workloads import (
        DEFAULT_WORKLOAD_DATASET_ORDER,
        WORKLOAD_BENCHMARK_SHAPE_CATALOG,
        WORKLOAD_FAMILY_SPECS,
        WORKLOAD_PRESET_CATALOG,
        generate_repo_local_workload_requests,
        normalize_repo_local_metadata,
        summarize_repo_local_workload,
    )
    from llm_serving_workloads.metadata import RepoLocalDatasetRow
except ImportError as exc:  # pragma: no cover - exercised by CLI/runtime only
    SHARED_WORKLOAD_IMPORT_ERROR: ImportError | None = exc
    DEFAULT_WORKLOAD_DATASET_ORDER = ()
    WORKLOAD_BENCHMARK_SHAPE_CATALOG: dict[str, dict[str, Any]] = {}
    WORKLOAD_FAMILY_SPECS: dict[str, Any] = {}
    WORKLOAD_PRESET_CATALOG: dict[str, dict[str, Any]] = {}
    generate_repo_local_workload_requests = None
    normalize_repo_local_metadata = None
    summarize_repo_local_workload = None
    RepoLocalDatasetRow = Any
else:
    SHARED_WORKLOAD_IMPORT_ERROR = None


def require_langchain() -> None:
    if LANGCHAIN_IMPORT_ERROR is None:
        return
    raise RuntimeError(
        "This evaluation requires optional LangChain packages. Install langchain and "
        "langchain-text-splitters in the active environment before running it."
    ) from LANGCHAIN_IMPORT_ERROR


def require_shared_workloads() -> None:
    if SHARED_WORKLOAD_IMPORT_ERROR is None:
        return
    raise RuntimeError(
        "This evaluation requires the sibling llm-serving-workloads repository. Keep "
        "llm-serving-workloads cloned next to SAGE or install its package into the active environment."
    ) from SHARED_WORKLOAD_IMPORT_ERROR


def require_openai() -> None:
    if OPENAI_IMPORT_ERROR is None:
        return
    raise RuntimeError(
        "This evaluation requires the openai Python package for OpenAI-compatible generation or embedding endpoints."
    ) from OPENAI_IMPORT_ERROR


def require_faiss() -> None:
    if FAISS_IMPORT_ERROR is None:
        return
    raise RuntimeError(
        "This evaluation requires the faiss Python package for offline FAISS retrieval indexes."
    ) from FAISS_IMPORT_ERROR


def dependency_status() -> dict[str, Any]:
    return {
        "repo_root": str(REPO_ROOT),
        "src_dir": str(SRC_DIR),
        "shared_workload_repo_root": str(SHARED_WORKLOAD_REPO_ROOT),
        "shared_workload_src_dir": str(SHARED_WORKLOAD_SRC_DIR),
        "langchain_available": LANGCHAIN_IMPORT_ERROR is None,
        "openai_available": OPENAI_IMPORT_ERROR is None,
        "faiss_available": FAISS_IMPORT_ERROR is None,
        "shared_workloads_available": SHARED_WORKLOAD_IMPORT_ERROR is None,
    }


__all__ = [
    "AIMessage",
    "BaseMessage",
    "ChatPromptTemplate",
    "DEFAULT_WORKLOAD_DATASET_ORDER",
    "Document",
    "Embeddings",
    "faiss",
    "HumanMessage",
    "InMemoryChatMessageHistory",
    "InMemoryVectorStore",
    "OpenAI",
    "REPO_ROOT",
    "RecursiveCharacterTextSplitter",
    "RepoLocalDatasetRow",
    "RunnableLambda",
    "SHARED_WORKLOAD_REPO_ROOT",
    "WORKLOAD_BENCHMARK_SHAPE_CATALOG",
    "WORKLOAD_FAMILY_SPECS",
    "WORKLOAD_PRESET_CATALOG",
    "bootstrap_paths",
    "dependency_status",
    "generate_repo_local_workload_requests",
    "init_chat_model",
    "normalize_repo_local_metadata",
    "require_faiss",
    "require_openai",
    "require_langchain",
    "require_shared_workloads",
    "summarize_repo_local_workload",
]
