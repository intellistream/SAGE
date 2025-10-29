"""Knowledge base utilities for the SAGE pipeline builder."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import urllib.request
import zipfile
from collections.abc import Mapping, MutableSequence, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from sage.cli.commands.apps.pipeline_domain import load_domain_contexts
from sage.common.components.sage_embedding.factory import EmbeddingFactory
from sage.common.config.output_paths import get_sage_paths

GITHUB_DOCS_ZIP_URL = "https://github.com/intellistream/SAGE-Pub/archive/refs/heads/main.zip"
DOCS_CACHE_SUBDIR = "pipeline-builder/docs"

CHUNK_SIZE = 600
CHUNK_OVERLAP = 120
TOP_K_DEFAULT = 6

_PYTHON_COMMENT_RE = re.compile(r"\s*#.*")
_DOCSTRING_RE = re.compile(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')', re.DOTALL)


@dataclass
class KnowledgeChunk:
    text: str
    source: str
    kind: str
    score: float = 0.0
    vector: list[float] | None = None


def _should_download_docs() -> bool:
    flag = os.getenv("SAGE_PIPELINE_DOWNLOAD_DOCS", "1").lower()
    return flag not in {"0", "false", "no"}


def _docs_cache_root() -> Path:
    return get_sage_paths().cache_dir / DOCS_CACHE_SUBDIR


def _download_docs(cache_root: Path) -> Path | None:
    if not _should_download_docs():
        return None

    cache_root.mkdir(parents=True, exist_ok=True)
    url = os.getenv("SAGE_PIPELINE_DOCS_URL", GITHUB_DOCS_ZIP_URL)
    fd, tmp_path = tempfile.mkstemp(prefix="sage_docs_", suffix=".zip")
    os.close(fd)
    tmp_file = Path(tmp_path)

    try:
        urllib.request.urlretrieve(url, tmp_file)
        with zipfile.ZipFile(tmp_file, "r") as zf:
            zf.extractall(cache_root)
    except Exception as exc:  # pragma: no cover - network error
        if tmp_file.exists():
            tmp_file.unlink()
        raise RuntimeError(f"下载 docs-public 文档失败: {exc}") from exc
    finally:
        if tmp_file.exists():
            tmp_file.unlink()

    extracted_docs: Path | None = None
    for candidate in cache_root.glob("**/docs_src"):
        if candidate.is_dir():
            extracted_docs = candidate
            break

    if extracted_docs is None:
        raise RuntimeError("下载的文档包中未找到 docs_src 目录")

    target = cache_root / "docs_src"
    if target.exists() and target != extracted_docs:
        shutil.rmtree(target, ignore_errors=True)

    if extracted_docs != target:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(extracted_docs), target)

    return target


def _resolve_docs_dir(project_root: Path, allow_download: bool) -> Path | None:
    local_docs = project_root / "docs-public" / "docs_src"
    if local_docs.exists():
        return local_docs

    cache_root = _docs_cache_root()
    cached_docs = cache_root / "docs_src"
    if cached_docs.exists():
        return cached_docs

    if not allow_download:
        return None

    return _download_docs(cache_root)


def _normalize_whitespace(value: str) -> str:
    value = value.replace("\r", "\n")
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]+", " ", value)
    return value.strip()


def _chunk_text(
    content: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    normalized = _normalize_whitespace(content)
    if not normalized:
        return []

    chunks: list[str] = []
    length = len(normalized)
    start = 0
    step = max(1, chunk_size - overlap)

    while start < length:
        end = min(length, start + chunk_size)
        chunk = normalized[start:end]
        if end < length:
            boundary = max(chunk.rfind("\n"), chunk.rfind("。"), chunk.rfind("."))
            if boundary >= 0 and boundary > len(chunk) * 0.4:
                end = start + boundary
                chunk = normalized[start:end]
        chunks.append(chunk.strip())
        start += step

    return [chunk for chunk in chunks if chunk]


class _HashingEmbedder:
    """Lightweight embedder mirroring the chat CLI's hashing strategy."""

    def __init__(self, dim: int = 384) -> None:
        self._dim = max(64, dim)

    def embed(self, text: str) -> list[float]:
        if not text:
            return [0.0] * self._dim

        vector = [0.0] * self._dim
        tokens = re.findall(r"[\w\u4e00-\u9fa5]+", text.lower())
        if not tokens:
            tokens = [text.lower()]

        for token in tokens:
            digest = _stable_hash(token)
            for offset in range(0, len(digest), 4):
                chunk = digest[offset : offset + 4]
                if len(chunk) < 4:
                    chunk = chunk.ljust(4, b"\0")
                idx = int.from_bytes(chunk, "little") % self._dim
                vector[idx] += 1.0

        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


@lru_cache(maxsize=1024)
def _stable_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    return float(sum(a * b for a, b in zip(vec_a, vec_b, strict=False)))


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _summarize_yaml(path: Path) -> str:
    try:
        data = yaml.safe_load(_read_file(path))
    except Exception:
        return ""
    if not isinstance(data, Mapping):
        return ""
    pipeline = data.get("pipeline") or {}
    name = pipeline.get("name") or path.stem
    description = pipeline.get("description", "")
    summary_lines = [f"Pipeline: {name}"]
    if description:
        summary_lines.append(description)
    stages = data.get("stages") or []
    if isinstance(stages, list):
        summary_lines.append("Stages:")
        for stage in stages[:6]:
            if not isinstance(stage, Mapping):
                continue
            stage_id = stage.get("id", "stage")
            stage_class = stage.get("class", "")
            stage_summary = stage.get("summary", "")
            summary_lines.append(
                f"- {stage_id}: {stage_class} {'- ' + stage_summary if stage_summary else ''}"
            )
    sink = data.get("sink") or {}
    if isinstance(sink, Mapping) and sink.get("class"):
        summary_lines.append(f"Sink: {sink['class']}")
    return "\n".join(summary_lines)


def _summarize_python(path: Path) -> str:
    text = _read_file(path)
    text = re.sub(_PYTHON_COMMENT_RE, "", text)
    docstrings = "\n".join(match.group(0) for match in _DOCSTRING_RE.finditer(text))
    return docstrings or text[:1200]


def _discover_documents(
    project_root: Path, allow_download: bool
) -> MutableSequence[KnowledgeChunk]:
    chunks: MutableSequence[KnowledgeChunk] = []

    docs_dir = _resolve_docs_dir(project_root, allow_download=allow_download)
    if docs_dir is not None and docs_dir.exists():
        for md in docs_dir.rglob("*.md"):
            if md.is_file():
                content = _read_file(md)
                for chunk in _chunk_text(content):
                    rel = md.relative_to(docs_dir)
                    chunks.append(
                        KnowledgeChunk(
                            text=f"{chunk}\n\n(Source: docs/{rel})",
                            source=str(md),
                            kind="docs",
                        )
                    )

    examples_dir = project_root / "examples" / "config"
    if examples_dir.exists():
        for config in examples_dir.glob("*.yaml"):
            summary = _summarize_yaml(config)
            if summary:
                chunks.append(
                    KnowledgeChunk(
                        text=f"{summary}\n\n(Source: {config.relative_to(project_root)})",
                        source=str(config),
                        kind="example",
                    )
                )

    libs_dir = project_root / "packages" / "sage-libs" / "src" / "sage" / "libs"
    if libs_dir.exists():
        for py_file in libs_dir.rglob("*.py"):
            if py_file.is_file() and "tests" not in py_file.parts:
                summary = _summarize_python(py_file)
                for chunk in _chunk_text(summary, chunk_size=400, overlap=80):
                    chunks.append(
                        KnowledgeChunk(
                            text=f"{chunk}\n\n(Source: {py_file.relative_to(project_root)})",
                            source=str(py_file),
                            kind="code",
                        )
                    )

    tools_dir = project_root / "packages" / "sage-tools" / "src" / "sage" / "tools"
    if tools_dir.exists():
        for py_file in tools_dir.rglob("*.py"):
            if py_file.is_file() and "tests" not in py_file.parts:
                summary = _summarize_python(py_file)
                for chunk in _chunk_text(summary, chunk_size=400, overlap=80):
                    chunks.append(
                        KnowledgeChunk(
                            text=f"{chunk}\n\n(Source: {py_file.relative_to(project_root)})",
                            source=str(py_file),
                            kind="code",
                        )
                    )

    # Append curated summaries to ensure familiar structure remains available.
    for context in load_domain_contexts(limit=6):
        chunks.append(
            KnowledgeChunk(
                text=context,
                source="pipeline_domain",
                kind="summary",
            )
        )

    return chunks


class PipelineKnowledgeBase:
    """Lightweight retrieval over SAGE docs and code, kept in memory."""

    def __init__(
        self,
        project_root: Path | None = None,
        max_chunks: int = 2000,
        allow_download: bool = True,
        embedding_method: str = "hash",
        embedding_model: str | None = None,
        embedding_params: Mapping[str, object] | None = None,
    ) -> None:
        root = project_root or getattr(get_sage_paths(), "project_root", None)
        self.project_root = Path(root) if root else Path.cwd()

        # Use the new unified embedding system
        self.embedding_method = embedding_method
        try:
            params = dict(embedding_params or {})
            if embedding_model:
                params["model"] = embedding_model
            self._embedder = EmbeddingFactory.create(embedding_method, **params)
        except Exception as exc:
            # Fallback to hash embedding if the requested method fails
            print(f"⚠️  无法创建 {embedding_method} embedding，使用 hash 作为后备: {exc}")
            self._embedder = EmbeddingFactory.create("hash", dimension=384)

        all_chunks = _discover_documents(self.project_root, allow_download=allow_download)
        if max_chunks and len(all_chunks) > max_chunks:
            all_chunks = all_chunks[:max_chunks]
        for chunk in all_chunks:
            chunk.vector = self._embedder.embed(chunk.text)
        self._chunks = list(all_chunks)

    def search(self, query: str, top_k: int = TOP_K_DEFAULT) -> list[KnowledgeChunk]:
        if not query.strip():
            return []
        vector = self._embedder.embed(query)
        scored: list[KnowledgeChunk] = []
        for chunk in self._chunks:
            if chunk.vector is None:
                continue
            score = _cosine_similarity(vector, chunk.vector)
            scored.append(
                KnowledgeChunk(
                    text=chunk.text,
                    source=chunk.source,
                    kind=chunk.kind,
                    score=score,
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]


@lru_cache(maxsize=1)
def get_default_knowledge_base(
    max_chunks: int = 2000,
    allow_download: bool = True,
    embedding_method: str | None = None,
    embedding_model: str | None = None,
) -> PipelineKnowledgeBase:
    """Get or create the default knowledge base.

    Args:
        max_chunks: Maximum number of chunks to keep
        allow_download: Whether to download docs if not found locally
        embedding_method: Which embedding method to use (hash, openai, hf, etc.)
        embedding_model: Specific model to use for the embedding method
    """
    method = embedding_method or os.getenv("SAGE_PIPELINE_EMBEDDING_METHOD", "hash")
    model = embedding_model or os.getenv("SAGE_PIPELINE_EMBEDDING_MODEL")

    return PipelineKnowledgeBase(
        max_chunks=max_chunks,
        allow_download=allow_download,
        embedding_method=method,
        embedding_model=model,
    )


def build_query_payload(
    requirements: Mapping[str, object],
    previous_plan: Mapping[str, object] | None = None,
    feedback: str | None = None,
) -> str:
    hints: list[str] = [json.dumps(requirements, ensure_ascii=False)]
    if previous_plan:
        pipeline = previous_plan.get("pipeline") or {}
        if pipeline:
            hints.append(json.dumps(pipeline, ensure_ascii=False))
        stages = previous_plan.get("stages") or []
        if isinstance(stages, Sequence):
            stage_info = [
                f"{stage.get('id', stage.get('class', 'stage'))}:{stage.get('class', '')}"
                for stage in stages
                if isinstance(stage, Mapping)
            ]
            if stage_info:
                hints.append("; ".join(stage_info))
    if feedback:
        hints.append(feedback)
    return "\n".join(hints)


__all__ = [
    "PipelineKnowledgeBase",
    "build_query_payload",
    "get_default_knowledge_base",
]
