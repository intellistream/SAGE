#!/usr/bin/env python3
"""SAGE Chat CLI - Embedded programming assistant backed by SageVDB."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import textwrap
import urllib.request
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# 延迟导入 sage_db 以允许 CLI 在没有 C++ 扩展的情况下启动
# from sage.middleware.components.sage_db.python.sage_db import SageDB, SageDBException
from sage.cli.commands.apps import pipeline as pipeline_builder
from sage.cli.commands.apps.pipeline_domain import load_domain_contexts
from sage.cli.commands.apps.pipeline_knowledge import get_default_knowledge_base
from sage.common.components.sage_embedding import get_embedding_model
from sage.common.components.sage_embedding.embedding_model import EmbeddingModel
from sage.common.config.output_paths import find_sage_project_root
from sage.common.config.ports import SagePorts

# Import document processing utilities from sage-common (L1)
from sage.common.utils.document_processing import (
    iter_markdown_files,
    parse_markdown_sections,
    slugify,
)

console = Console()

# sage_db 需要 C++ 扩展，使用延迟导入
SAGE_DB_AVAILABLE = False
SAGE_DB_IMPORT_ERROR: Exception | None = None
SageDB = None  # type: ignore
SageDBException = Exception  # type: ignore


def _lazy_import_sage_db():
    """延迟导入 sage_db，只在需要时导入"""
    global SageDB, SageDBException, SAGE_DB_AVAILABLE, SAGE_DB_IMPORT_ERROR

    if SAGE_DB_AVAILABLE:
        return  # 已经成功导入

    try:
        from sage.middleware.components.sage_db.python.sage_db import SageDB as _SageDB
        from sage.middleware.components.sage_db.python.sage_db import (
            SageDBException as _SageDBException,
        )

        SageDB = _SageDB
        SageDBException = _SageDBException
        SAGE_DB_AVAILABLE = True
        SAGE_DB_IMPORT_ERROR = None
    except (ImportError, ModuleNotFoundError) as e:
        SAGE_DB_AVAILABLE = False
        SAGE_DB_IMPORT_ERROR = e


DEFAULT_INDEX_NAME = "docs-public"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 160
DEFAULT_TOP_K = 4
DEFAULT_BACKEND = "auto"  # 自动检测本地 LLM 服务，若无则回退 mock
# 默认使用本地 embedding server（与 sage-gateway 统一）
DEFAULT_EMBEDDING_METHOD = "openai"  # 使用 OpenAI 兼容接口连接本地 embedding server
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"  # 默认 embedding 模型
DEFAULT_FIXED_DIM = 384  # 仅用于 hash 方法的回退
DEFAULT_FINETUNE_MODEL = "sage_code_expert"
DEFAULT_FINETUNE_PORT = SagePorts.GATEWAY_DEFAULT

# Note: SUPPORTED_MARKDOWN_SUFFIXES now imported from sage.common.utils.document_processing

METHODS_REQUIRE_MODEL = {
    "hf",
    "openai",
    "jina",
    "cohere",
    "zhipu",
    "bedrock",
    "ollama",
    "siliconcloud",
    "nvidia_openai",
    "lollms",
}

GITHUB_DOCS_ZIP_URL = "https://github.com/intellistream/SAGE-Pub/archive/refs/heads/main.zip"

app = typer.Typer(
    help="🧭 嵌入式 SAGE 编程助手 (Docs + SageDB + LLM)",
    invoke_without_command=True,
)


@dataclass
class ChatManifest:
    """Metadata describing a built knowledge index."""

    index_name: str
    db_path: Path
    created_at: str
    source_dir: str
    embedding: dict[str, object]
    chunk_size: int
    chunk_overlap: int
    num_documents: int
    num_chunks: int

    @property
    def embed_config(self) -> dict[str, object]:
        return self.embedding


def ensure_sage_db() -> None:
    """确保 SageDB 扩展可用，如果不可用则提前退出。"""
    # 尝试延迟导入
    _lazy_import_sage_db()

    if SAGE_DB_AVAILABLE:
        return

    message = (
        "[red]SageDB C++ 扩展不可用，无法使用 `sage chat`。[/red]\n"
        "请先通过命令 `sage extensions install sage_db` 构建 SageDB 组件（如需重新安装可加上 --force）。"
    )
    if SAGE_DB_IMPORT_ERROR:
        message += f"\n原始错误: {SAGE_DB_IMPORT_ERROR}"
    console.print(message)
    raise typer.Exit(code=1)


def resolve_index_root(index_root: str | None) -> Path:
    """解析索引存储根目录。

    用户数据缓存（聊天索引）始终使用用户目录 ~/.sage/cache/chat/，
    确保 sage-chat 和 sage-gateway 使用同一份索引。
    """
    if index_root:
        root = Path(index_root).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root
    # 始终使用用户目录，确保与 sage-gateway 共享同一份索引
    cache_dir = Path.home() / ".sage" / "cache" / "chat"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def default_source_dir() -> Path:
    project_root = find_sage_project_root()
    if not project_root:
        project_root = Path.cwd()
    candidate = project_root / "docs-public" / "docs_src"
    return candidate


def manifest_path(index_root: Path, index_name: str) -> Path:
    # 使用下划线格式，与 sage-gateway 保持一致
    return index_root / f"{index_name}_manifest.json"


def db_file_path(index_root: Path, index_name: str) -> Path:
    return index_root / f"{index_name}.sagedb"


def load_manifest(index_root: Path, index_name: str) -> ChatManifest:
    path = manifest_path(index_root, index_name)
    if not path.exists():
        # 兼容旧格式：尝试读取 .manifest.json
        old_path = index_root / f"{index_name}.manifest.json"
        if old_path.exists():
            path = old_path
        else:
            raise FileNotFoundError(f"未找到索引 manifest: {path}. 请先运行 `sage chat ingest`.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    manifest = ChatManifest(
        index_name=index_name,
        db_path=Path(payload["db_path"]),
        created_at=payload["created_at"],
        source_dir=payload["source_dir"],
        embedding=payload["embedding"],
        chunk_size=payload["chunk_size"],
        chunk_overlap=payload["chunk_overlap"],
        num_documents=payload.get("num_documents", 0),
        num_chunks=payload.get("num_chunks", 0),
    )
    return manifest


def save_manifest(
    index_root: Path,
    index_name: str,
    manifest: ChatManifest,
) -> None:
    path = manifest_path(index_root, index_name)
    payload = {
        "index_name": manifest.index_name,
        "db_path": str(manifest.db_path),
        "created_at": manifest.created_at,
        "source_dir": manifest.source_dir,
        "embedding": manifest.embedding,
        "chunk_size": manifest.chunk_size,
        "chunk_overlap": manifest.chunk_overlap,
        "num_documents": manifest.num_documents,
        "num_chunks": manifest.num_chunks,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_embedder(config: dict[str, object]) -> Any:
    """构建 embedder 实例（使用新的统一接口）

    Args:
        config: embedding 配置
            - method: 方法名 (hash, hf, openai, mockembedder, ...)
            - params: 方法特定参数

    Returns:
        BaseEmbedding 实例

    Examples:
        >>> config = {"method": "hash", "params": {"dim": 384}}
        >>> emb = build_embedder(config)
        >>> vec = emb.embed("test")
    """
    method = str(config.get("method", DEFAULT_EMBEDDING_METHOD))
    params_raw = config.get("params", {})
    params = dict(params_raw) if isinstance(params_raw, dict) else {}  # type: ignore[arg-type]

    # 统一使用新接口，不需要特殊处理！
    return get_embedding_model(method, **params)


# Note: Document processing functions now imported from sage.common.utils.document_processing
# - iter_markdown_files
# - parse_markdown_sections
# - chunk_text
# - slugify
# - truncate_text
# - sanitize_metadata_value


def ensure_docs_corpus(index_root: Path) -> Path:
    """Ensure we have a docs-public/docs_src directory available."""

    local_source = default_source_dir()
    if local_source.exists():
        return local_source

    cache_root = index_root / "remote_docs"
    docs_path = cache_root / "docs_src"
    if docs_path.exists():
        return docs_path

    cache_root.mkdir(parents=True, exist_ok=True)
    console.print(
        "🌐 未检测到本地 docs-public/docs_src，正在下载官方文档包...",
        style="cyan",
    )

    fd, tmp_path = tempfile.mkstemp(prefix="sage_docs_", suffix=".zip")
    os.close(fd)
    tmp_file = Path(tmp_path)
    try:
        urllib.request.urlretrieve(GITHUB_DOCS_ZIP_URL, tmp_file)
        with zipfile.ZipFile(tmp_file, "r") as zf:
            zf.extractall(cache_root)
    except Exception as exc:
        if tmp_file.exists():
            tmp_file.unlink()
        raise RuntimeError(f"下载 docs-public 文档失败: {exc}") from exc

    if tmp_file.exists():
        tmp_file.unlink()

    extracted_docs: Path | None = None
    for candidate in cache_root.glob("**/docs_src"):
        if candidate.is_dir():
            extracted_docs = candidate
            break

    if extracted_docs is None:
        raise RuntimeError("下载的文档包中未找到 docs_src 目录")

    if docs_path.exists() and docs_path == extracted_docs:
        return docs_path

    if not docs_path.exists():
        docs_path.mkdir(parents=True, exist_ok=True)
        for item in extracted_docs.iterdir():
            shutil.move(str(item), docs_path / item.name)
    return docs_path


def bootstrap_default_index(index_root: Path, index_name: str) -> ChatManifest | None:
    try:
        source_dir = ensure_docs_corpus(index_root)
    except Exception as exc:
        console.print(f"[red]无法准备文档语料: {exc}[/red]")
        return None

    # 检测本地 embedding server 是否可用
    from sage.common.config.ports import SagePorts

    embedding_port = SagePorts.EMBEDDING_DEFAULT
    embedding_available = False

    try:
        import requests

        # 使用 /v1/models 端点检测（OpenAI 兼容接口）
        response = requests.get(f"http://localhost:{embedding_port}/v1/models", timeout=2)
        embedding_available = response.status_code == 200
    except Exception:
        pass

    if embedding_available:
        console.print(f"[green]✅ 检测到本地 Embedding 服务 (端口 {embedding_port})[/green]")
        embedding_config: dict[str, object] = {
            "method": "openai",
            "params": {
                "model": DEFAULT_EMBEDDING_MODEL,
                "base_url": f"http://localhost:{embedding_port}/v1",
                "api_key": "local",  # 本地服务不需要真实 key  # pragma: allowlist secret
            },
        }
    else:
        console.print(
            f"[yellow]⚠️  未检测到本地 Embedding 服务 (端口 {embedding_port})，使用 hash 方法[/yellow]\n"
            "[dim]提示: 运行 `sage llm serve` 启动 Embedding 服务以获得更好的检索效果[/dim]"
        )
        embedding_config = {
            "method": "hash",
            "params": {"dim": DEFAULT_FIXED_DIM},
        }

    console.print(
        f"🚀 正在导入 [cyan]{source_dir}[/cyan] 以初始化 `{index_name}` 索引...",
        style="green",
    )
    manifest = ingest_source(
        source_dir=source_dir,
        index_root=index_root,
        index_name=index_name,
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        embedding_config=embedding_config,
        max_files=None,
    )
    return manifest


def load_or_bootstrap_manifest(index_root: Path, index_name: str) -> ChatManifest:
    try:
        return load_manifest(index_root, index_name)
    except FileNotFoundError:
        console.print(
            "🔍 检测到尚未为 `sage chat` 初始化索引。",
            style="yellow",
        )
        if not typer.confirm("是否立即导入 docs-public 文档？", default=True):
            console.print(
                "💡 可使用 `sage chat ingest` 手动导入后再重试。",
                style="cyan",
            )
            raise typer.Exit(code=1)

        manifest = bootstrap_default_index(index_root, index_name)
        if manifest is None:
            raise typer.Exit(code=1)
        return manifest


def _create_markdown_processor(
    source_dir: Path, max_files: int | None = None, show_progress: bool = True
):
    """Create a custom document processor for Markdown files.

    This processor handles SAGE-specific Markdown processing with:
    - Section splitting by headings
    - Metadata extraction (doc_path, title, heading, anchor)
    - Text preview generation

    Note: Progress display is handled by IndexBuilder's Rich progress bar.
    This processor shows live progress during document processing.
    """

    def process_markdown(src: Path) -> list[dict[str, Any]]:
        chunks = []
        total_docs = 0
        skipped_docs = []  # Track skipped documents

        # Count total files first for progress display
        all_files = list(iter_markdown_files(src))
        total_files = len(all_files) if max_files is None else min(len(all_files), max_files)

        if show_progress:
            from rich.live import Live
            from rich.text import Text

            # Use Rich Live for real-time progress updates
            with Live(
                Text(f"📄 处理文档 0/{total_files}, 已生成 0 个片段", style="cyan"),
                refresh_per_second=10,
                transient=True,
            ) as live:
                for idx, file_path in enumerate(all_files, start=1):
                    if max_files is not None and idx > max_files:
                        break

                    rel_path = file_path.relative_to(src)
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                    sections = parse_markdown_sections(text)

                    if not sections:
                        skipped_docs.append(
                            (rel_path, "无法解析出有效章节（可能为空或格式不支持）")
                        )
                        continue

                    doc_title = sections[0]["heading"] if sections else file_path.stem

                    for section in sections:
                        chunks.append(
                            {
                                "content": section["content"],
                                "metadata": {
                                    "doc_path": str(rel_path),
                                    "title": doc_title,
                                    "heading": section["heading"],
                                    "anchor": slugify(section["heading"]),
                                },
                            }
                        )

                    total_docs += 1
                    # Update live progress after each document
                    live.update(
                        Text(
                            f"📄 处理文档 {total_docs}/{total_files}, 已生成 {len(chunks)} 个片段",
                            style="cyan",
                        )
                    )

            # Print final summary
            console.print(
                f"[green]✓ 文档处理完成: {total_docs}/{total_files} 个文档, {len(chunks)} 个片段[/green]"
            )

            # Report skipped documents
            if skipped_docs:
                console.print(f"[yellow]⚠ 跳过 {len(skipped_docs)} 个文档:[/yellow]")
                for doc_path, reason in skipped_docs:
                    console.print(f"[dim]  - {doc_path}: {reason}[/dim]")
        else:
            # Quiet mode - no progress display
            for idx, file_path in enumerate(all_files, start=1):
                if max_files is not None and idx > max_files:
                    break

                rel_path = file_path.relative_to(src)
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                sections = parse_markdown_sections(text)

                if not sections:
                    skipped_docs.append((rel_path, "无法解析出有效章节"))
                    continue

                doc_title = sections[0]["heading"] if sections else file_path.stem

                for section in sections:
                    chunks.append(
                        {
                            "content": section["content"],
                            "metadata": {
                                "doc_path": str(rel_path),
                                "title": doc_title,
                                "heading": section["heading"],
                                "anchor": slugify(section["heading"]),
                            },
                        }
                    )

                total_docs += 1

        return chunks

    return process_markdown


def ingest_source(
    source_dir: Path,
    index_root: Path,
    index_name: str,
    chunk_size: int,
    chunk_overlap: int,
    embedding_config: dict[str, object],
    max_files: int | None = None,
    show_progress: bool = True,
) -> ChatManifest:
    """Build RAG index from source documents using IndexBuilder.

    This function now uses the unified IndexBuilder from sage-middleware,
    allowing code sharing with sage-gateway and other components.
    """
    ensure_sage_db()

    if not source_dir.exists():
        raise FileNotFoundError(f"文档目录不存在: {source_dir}")

    # Build embedder
    embedder = build_embedder(embedding_config)

    # Prepare database path
    db_path = db_file_path(index_root, index_name)
    if db_path.exists():
        db_path.unlink()

    # Import IndexBuilder and SageDBBackend
    try:
        from sage.middleware.components.sage_db.backend import SageDBBackend
        from sage.middleware.operators.rag.index_builder import IndexBuilder
    except ImportError as e:
        raise RuntimeError(
            f"Failed to import IndexBuilder or SageDBBackend: {e}\n"
            "Ensure sage-middleware is installed with --dev option"
        ) from e

    # Create backend factory for SageDB
    def backend_factory(persist_path: Path, dim: int):
        return SageDBBackend(persist_path, dim)

    # Create document processor for Markdown
    document_processor = _create_markdown_processor(source_dir, max_files, show_progress)

    # Build index using IndexBuilder
    if show_progress:
        console.print("🔨 Building index using IndexBuilder...", style="cyan")
    builder = IndexBuilder(backend_factory=backend_factory)

    index_manifest = builder.build_from_docs(
        source_dir=source_dir,
        persist_path=db_path,
        embedding_model=embedder,
        index_name=index_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        document_processor=document_processor,
        show_progress=show_progress,
    )

    # Convert IndexManifest to ChatManifest for compatibility
    manifest = ChatManifest(
        index_name=index_name,
        db_path=db_path,
        created_at=index_manifest.created_at,
        source_dir=str(source_dir),
        embedding=embedding_config,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        num_documents=index_manifest.num_documents,
        num_chunks=index_manifest.num_chunks,
    )

    save_manifest(index_root, index_name, manifest)
    if show_progress:
        console.print(Panel.fit(f"✅ 索引已更新 -> {db_path}", title="INGEST", style="green"))
        console.print(
            f"📊 Documents: {manifest.num_documents}, Chunks: {manifest.num_chunks}", style="green"
        )

    return manifest


def open_database(manifest: ChatManifest) -> Any:
    ensure_sage_db()
    if not manifest.db_path.exists():
        prefix = manifest.db_path
        siblings = list(prefix.parent.glob(prefix.name + "*"))
        if not siblings:
            raise FileNotFoundError(
                f"未找到数据库文件 {manifest.db_path}。请重新运行 `sage chat ingest`."
            )
    embedder = build_embedder(manifest.embed_config)
    if not SageDB:
        raise RuntimeError("SageDB not available - sage-middleware not installed")
    db = SageDB(embedder.get_dim())
    db.load(str(manifest.db_path))
    return db


def build_prompt(question: str, contexts: Sequence[str]) -> list[dict[str, str]]:
    """构建对话 prompt。

    针对小模型优化：
    1. 简短清晰的指令
    2. 明确区分闲聊和技术问题
    3. 只在真正相关时使用上下文
    """
    # 检测是否是简单闲聊（不需要检索上下文）
    casual_patterns = [
        "你好",
        "hi",
        "hello",
        "嗨",
        "hey",
        "谢谢",
        "thanks",
        "thank you",
        "再见",
        "bye",
        "拜拜",
        "test",
        "测试",
        "试试",
        "ok",
        "好的",
        "嗯",
    ]
    question_lower = question.strip().lower()
    is_casual = (
        any(
            question_lower == p
            or question_lower.startswith(p + " ")
            or question_lower.endswith(" " + p)
            for p in casual_patterns
        )
        and len(question.strip()) < 20
    )

    if is_casual:
        # 简单闲聊：不使用检索上下文，避免干扰
        system_instructions = (
            "你是 SAGE 智能助手。用户在和你打招呼或闲聊，请自然友好地回应，不要输出代码。"
        )
        return [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": question.strip()},
        ]

    # 技术问题：使用检索上下文
    context_block = "\n\n".join(
        f"[{idx}] {textwrap.dedent(ctx).strip()}"
        for idx, ctx in enumerate(contexts, start=1)
        if ctx
    )
    system_instructions = textwrap.dedent(
        """
        你是 SAGE 智能助手。根据用户问题和提供的文档上下文回答。

        规则：
        - 依据上下文回答，引用时用 [编号] 标注
        - 可以给出示例代码
        - 如果上下文不足，坦诚说明
        """
    ).strip()

    if context_block:
        system_instructions += f"\n\n参考文档:\n{context_block}"

    return [
        {"role": "system", "content": system_instructions},
        {"role": "user", "content": question.strip()},
    ]


class ResponseGenerator:
    def __init__(
        self,
        backend: str,
        model: str,
        base_url: str | None,
        api_key: str | None,
        temperature: float = 0.2,
        finetune_model: str | None = None,
        finetune_port: int = DEFAULT_FINETUNE_PORT,
    ) -> None:
        self.backend = backend.lower()
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.finetune_model = finetune_model
        self.finetune_port = finetune_port
        self._llm_server = None  # 用于追踪 sageLLM 服务

        if self.backend == "mock":
            self.client = None
        elif self.backend == "auto":
            # 自动检测本地 LLM 服务
            self._setup_auto_backend()
        elif self.backend == "finetune":
            # 使用微调模型
            self._setup_finetune_backend()
        else:
            try:
                from sage.llm import UnifiedInferenceClient

                if base_url and api_key:
                    # Explicit configuration — use factory and inject API key via env
                    old_key = os.environ.get("SAGE_UNIFIED_API_KEY")
                    try:
                        os.environ["SAGE_UNIFIED_API_KEY"] = api_key
                        self.client = UnifiedInferenceClient.create(
                            control_plane_url=base_url,
                            default_llm_model=model,
                        )
                    finally:
                        if old_key is None:
                            os.environ.pop("SAGE_UNIFIED_API_KEY", None)
                        else:
                            os.environ["SAGE_UNIFIED_API_KEY"] = old_key
                elif base_url:
                    # Only base_url provided
                    self.client = UnifiedInferenceClient.create(
                        control_plane_url=base_url,
                        default_llm_model=model,
                    )
                else:
                    # Auto-detection mode
                    self.client = UnifiedInferenceClient.create()
            except Exception as exc:  # pragma: no cover - runtime check
                raise RuntimeError(f"无法初始化 UnifiedInferenceClient: {exc}") from exc

    def _setup_auto_backend(self) -> None:
        """自动检测并配置最佳可用的 LLM 后端。

        优先级: 本地 LLM 服务 → 云端 API → mock 回退
        """
        import os

        import requests

        from sage.common.config.ports import SagePorts

        # 1. 尝试本地 LLM 服务
        local_ports = [SagePorts.BENCHMARK_LLM, SagePorts.LLM_DEFAULT]
        for port in local_ports:
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=2)
                if response.status_code == 200:
                    # 获取本地服务的实际模型名
                    models_response = requests.get(f"http://localhost:{port}/v1/models", timeout=2)
                    local_model = self.model
                    if models_response.status_code == 200:
                        models_data = models_response.json()
                        if models_data.get("data"):
                            local_model = models_data["data"][0].get("id", self.model)

                    console.print(
                        f"[green]✅ 检测到本地 LLM 服务 (端口 {port}, 模型: {local_model})[/green]"
                    )
                    from sage.llm import UnifiedInferenceClient

                    self.client = UnifiedInferenceClient.create(
                        control_plane_url=f"http://localhost:{port}/v1",
                        default_llm_model=local_model,
                    )
                    self.model = local_model
                    self.backend = "local"
                    return
            except Exception:  # noqa: S110
                pass

        # 2. 尝试云端 API（检查环境变量）
        api_key = os.getenv("SAGE_CHAT_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from sage.llm import UnifiedInferenceClient

                # 使用 create 会自动检测配置
                self.client = UnifiedInferenceClient.create()
                status = self.client.get_status()
                if status.get("llm_available"):
                    console.print("[green]✅ 使用云端 API 服务[/green]")
                    self.backend = "api"
                    return
            except Exception as e:
                console.print(f"[yellow]⚠️  云端 API 初始化失败: {e}[/yellow]")

        # 3. 回退到 mock 模式
        console.print(
            "[yellow]⚠️  未检测到可用的 LLM 服务，使用 mock 模式[/yellow]\n"
            "[dim]提示: 启动本地服务 `sage llm serve` 或配置 SAGE_CHAT_API_KEY/OPENAI_API_KEY 环境变量[/dim]"
        )
        self.client = None
        self.backend = "mock"

    def _setup_finetune_backend(self) -> None:
        """设置微调模型 backend（通过 sageLLM LLMAPIServer）"""
        from pathlib import Path

        import requests

        model_name = self.finetune_model or DEFAULT_FINETUNE_MODEL
        port = self.finetune_port

        # 使用 SAGE 配置目录
        sage_config_dir = Path.home() / ".sage"
        finetune_output_dir = sage_config_dir / "finetune_output"

        # 检查微调模型是否存在
        finetune_dir = finetune_output_dir / model_name
        merged_path = finetune_dir / "merged_model"
        checkpoint_path = finetune_dir / "checkpoints"

        if not finetune_dir.exists():
            raise FileNotFoundError(
                f"微调模型不存在: {model_name}\n"
                f"路径: {finetune_dir}\n"
                f"请先运行微调或指定其他模型:\n"
                f"  sage finetune quickstart {model_name}"
            )

        # 检查服务是否已运行
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=1)
            service_running = response.status_code == 200
        except Exception:  # noqa: S110
            service_running = False

        if service_running:
            console.print(f"[green]✅ LLM 服务已在端口 {port} 运行[/green]")
            model_to_use = self.model if self.model != "qwen-max" else None
        else:
            console.print("[yellow]⏳ 正在启动微调模型服务（通过 sageLLM）...[/yellow]")

            # 检查是否有合并模型
            if not merged_path.exists():
                console.print("[yellow]⚠️  未找到合并模型，正在自动合并 LoRA 权重...[/yellow]")

                # 检查是否有 checkpoint
                if not checkpoint_path.exists():
                    raise FileNotFoundError(
                        f"未找到模型或 checkpoint: {model_name}\n"
                        f"请确保已完成训练或运行: sage finetune merge {model_name}"
                    )

                # 尝试自动合并
                try:
                    console.print("[cyan]正在合并 LoRA 权重...[/cyan]")
                    from sage.libs.finetune.service import merge_lora_weights

                    # 读取 meta 获取基础模型
                    meta_file = finetune_dir / "finetune_meta.json"
                    if meta_file.exists():
                        import json

                        with open(meta_file) as f:
                            meta = json.load(f)
                        base_model = meta.get("model", "")
                    else:
                        raise RuntimeError("未找到 meta 信息文件")

                    # 找到最新的 checkpoint
                    checkpoints = sorted(checkpoint_path.glob("checkpoint-*"))
                    if not checkpoints:
                        raise RuntimeError("未找到 checkpoint")

                    latest_checkpoint = checkpoints[-1]
                    merge_lora_weights(latest_checkpoint, base_model, merged_path)
                    console.print("[green]✅ 权重合并完成[/green]")
                except Exception as merge_exc:
                    raise RuntimeError(
                        f"自动合并失败: {merge_exc}\n请手动运行: sage finetune merge {model_name}"
                    ) from merge_exc

            # 使用 sageLLM LLMAPIServer 启动服务
            try:
                from sage.llm import LLMAPIServer, LLMServerConfig

                config = LLMServerConfig(
                    model=str(merged_path),
                    backend="vllm",
                    host="0.0.0.0",
                    port=port,
                    gpu_memory_utilization=0.9,
                )

                self._llm_server = LLMAPIServer(config)
                success = self._llm_server.start(background=True)

                if not success:
                    raise RuntimeError("LLM 服务启动失败")

                console.print("[green]✅ LLM 服务启动成功（sageLLM）[/green]\n")

            except ImportError:
                raise RuntimeError("sageLLM 不可用，请确保已安装 sage-common")
            except Exception as exc:
                raise RuntimeError(f"启动 LLM 服务失败: {exc}") from exc

            # 读取实际的模型名称
            meta_file = finetune_dir / "finetune_meta.json"
            if meta_file.exists():
                import json

                with open(meta_file) as f:
                    meta = json.load(f)
                model_to_use = meta.get("model", str(merged_path))
            else:
                model_to_use = str(merged_path)

        # 设置 LLM 客户端连接到本地服务
        try:
            from sage.llm import UnifiedInferenceClient

            # Connect to local finetune LLM via factory
            self.client = UnifiedInferenceClient.create(
                control_plane_url=f"http://localhost:{port}/v1",
                default_llm_model=model_to_use or str(merged_path),
            )
            self.model = model_to_use or str(merged_path)
            console.print(f"[green]✅ 已连接到微调模型: {model_name}[/green]\n")
        except Exception as exc:
            if hasattr(self, "_llm_server") and self._llm_server:
                self._llm_server.stop()
            raise RuntimeError(f"无法连接到 LLM 服务: {exc}") from exc

    def cleanup(self) -> None:
        """清理资源（如果启动了 LLM 服务）"""
        if hasattr(self, "_llm_server") and self._llm_server:
            try:
                console.print("\n[yellow]⏳ 正在关闭 LLM 服务...[/yellow]")
                self._llm_server.stop()
                console.print("[green]✅ LLM 服务已关闭[/green]")
            except Exception:  # noqa: S110
                pass
            self._llm_server = None

    def answer(
        self,
        question: str,
        contexts: Sequence[str],
        references: Sequence[dict[str, str]],
        stream: bool = False,
    ) -> str:
        if self.backend == "mock":
            return self._mock_answer(question, contexts, references)

        if not self.client:
            raise RuntimeError("Client not initialized")
        messages = build_prompt(question, contexts)
        try:
            response = self.client.chat(
                messages,
                max_tokens=768,
                temperature=self.temperature,
                stream=stream,
            )
            if isinstance(response, str):
                return response
            # Non-streaming ensures string; streaming not yet supported.
            return str(response)
        except Exception as exc:
            raise RuntimeError(f"调用语言模型失败: {exc}") from exc

    @staticmethod
    def _mock_answer(
        question: str,
        contexts: Sequence[str],
        references: Sequence[dict[str, str]],
    ) -> str:
        if not contexts:
            return (
                "暂时没有从知识库检索到答案。请尝试改写提问，或运行 `sage chat ingest` 更新索引。"
            )
        top_ref = references[0] if references else {"title": "资料", "heading": ""}
        snippet = contexts[0].strip().replace("\n", " ")
        citation = top_ref.get("label", top_ref.get("title", "Docs"))
        return (
            f"根据 {citation} 的说明：{snippet[:280]}...\n\n"
            "[Mock 模式] 启动本地服务 `sage llm serve` 或配置 SAGE_CHAT_API_KEY 以获得完整回答。"
        )


PIPELINE_TRIGGER_VERBS = (
    "构建",
    "生成",
    "搭建",
    "创建",
    "设计",
    "build",
    "create",
    "design",
    "orchestrate",
)

PIPELINE_TRIGGER_TERMS = (
    "pipeline",
    "工作流",
    "流程",
    "图谱",
    "大模型应用",
    "应用",
    "app",
    "application",
    "workflow",
    "agent",
    "agents",
)

# 常见场景模板
COMMON_SCENARIOS = {
    "qa": {
        "name": "问答助手",
        "goal": "构建基于文档的问答系统",
        "data_sources": ["文档知识库"],
        "latency_budget": "实时响应优先",
        "constraints": "",
    },
    "rag": {
        "name": "RAG检索增强生成",
        "goal": "结合向量检索和大模型生成的智能问答",
        "data_sources": ["向量数据库", "文档库"],
        "latency_budget": "实时响应优先",
        "constraints": "",
    },
    "chat": {
        "name": "对话机器人",
        "goal": "支持多轮对话的智能助手",
        "data_sources": ["用户输入", "历史对话"],
        "latency_budget": "实时响应优先",
        "constraints": "支持流式输出",
    },
    "batch": {
        "name": "批量处理",
        "goal": "批量处理文档或数据",
        "data_sources": ["文件系统", "数据库"],
        "latency_budget": "批处理可接受",
        "constraints": "",
    },
    "agent": {
        "name": "智能代理",
        "goal": "具有工具调用能力的AI代理",
        "data_sources": ["工具API", "知识库"],
        "latency_budget": "实时响应优先",
        "constraints": "支持函数调用",
    },
}


def _get_scenario_template(scenario_key: str) -> dict[str, str] | None:
    """获取场景模板"""
    return COMMON_SCENARIOS.get(scenario_key.lower())


def _show_scenario_templates() -> None:
    """显示可用的场景模板"""
    console.print("\n[bold cyan]📚 可用场景模板：[/bold cyan]\n")
    for key, template in COMMON_SCENARIOS.items():
        console.print(f"  [yellow]{key:10}[/yellow] - {template['name']}: {template['goal']}")
    console.print()


def _looks_like_pipeline_request(message: str) -> bool:
    text = message.strip()
    if not text:
        return False

    lowered = text.lower()
    if lowered.startswith("pipeline:") or lowered.startswith("workflow:"):
        return True

    has_verb = any(token in text for token in PIPELINE_TRIGGER_VERBS)
    has_term = any(token in text for token in PIPELINE_TRIGGER_TERMS)
    if has_verb and has_term:
        return True

    if "llm" in lowered and "build" in lowered and ("app" in lowered or "application" in lowered):
        return True

    return False


def _default_pipeline_name(seed: str) -> str:
    headline = seed.strip().splitlines()[0] if seed.strip() else "LLM 应用"
    headline = re.sub(r"[。！？.!?]", " ", headline)
    tokens = [tok for tok in re.split(r"\s+", headline) if tok]
    if not tokens:
        return "LLM 应用"
    if len(tokens) == 1:
        word = tokens[0]
        return f"{word} 应用" if len(word) <= 10 else word[:10]
    trimmed = " ".join(tokens[:4])
    return trimmed[:32] if len(trimmed) > 32 else trimmed


def _normalize_list_field(raw_value: str) -> list[str]:
    if not raw_value.strip():
        return []
    return [item.strip() for item in re.split(r"[,，/；;]", raw_value) if item.strip()]


def _validate_pipeline_config(plan: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    验证生成的 Pipeline 配置是否合法

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    # 检查必需的顶层字段
    if "pipeline" not in plan:
        errors.append("缺少 'pipeline' 字段")
    else:
        pipeline = plan["pipeline"]
        if not isinstance(pipeline, dict):
            errors.append("'pipeline' 必须是字典类型")
        else:
            for required in ["name", "type"]:
                if required not in pipeline:
                    errors.append(f"'pipeline' 缺少必需字段 '{required}'")

    # 检查 source
    if "source" not in plan:
        errors.append("缺少 'source' 字段")
    elif not isinstance(plan["source"], dict):
        errors.append("'source' 必须是字典类型")
    elif "class" not in plan["source"]:
        errors.append("'source' 缺少 'class' 字段")

    # 检查 sink
    if "sink" not in plan:
        errors.append("缺少 'sink' 字段")
    elif not isinstance(plan["sink"], dict):
        errors.append("'sink' 必须是字典类型")
    elif "class" not in plan["sink"]:
        errors.append("'sink' 缺少 'class' 字段")

    # 检查 stages（可选但如果存在需要是列表）
    if "stages" in plan:
        stages = plan["stages"]
        if not isinstance(stages, list):
            errors.append("'stages' 必须是列表类型")
        else:
            for idx, stage in enumerate(stages):
                if not isinstance(stage, dict):
                    errors.append(f"stages[{idx}] 必须是字典类型")
                else:
                    for required in ["id", "kind", "class"]:
                        if required not in stage:
                            errors.append(f"stages[{idx}] 缺少必需字段 '{required}'")

    return (len(errors) == 0, errors)


def _check_class_imports(plan: dict[str, Any]) -> list[str]:
    """
    检查配置中的类是否可以导入

    Returns:
        List of import warnings
    """
    warnings = []
    classes_to_check = []

    # 收集所有类名
    if "source" in plan and isinstance(plan["source"], dict):
        if "class" in plan["source"]:
            classes_to_check.append(("source", plan["source"]["class"]))

    if "sink" in plan and isinstance(plan["sink"], dict):
        if "class" in plan["sink"]:
            classes_to_check.append(("sink", plan["sink"]["class"]))

    if "stages" in plan and isinstance(plan["stages"], list):
        for idx, stage in enumerate(plan["stages"]):
            if isinstance(stage, dict) and "class" in stage:
                classes_to_check.append((f"stages[{idx}]", stage["class"]))

    # 尝试导入每个类
    for location, class_path in classes_to_check:
        if not class_path or not isinstance(class_path, str):
            continue

        try:
            # 分割模块路径和类名
            parts = class_path.rsplit(".", 1)
            if len(parts) != 2:
                warnings.append(f"{location}: 类路径格式不正确 '{class_path}'")
                continue

            module_path, class_name = parts

            # 尝试导入（但不实际执行，只是检查语法）
            # 注意：这里只做基本检查，不执行真实导入以避免副作用
            if not module_path or not class_name:
                warnings.append(f"{location}: 类路径 '{class_path}' 无效")

        except Exception as exc:
            warnings.append(f"{location}: 类 '{class_path}' 可能无法导入 - {exc}")

    return warnings


class PipelineChatCoordinator:
    def __init__(
        self,
        backend: str,
        model: str,
        base_url: str | None,
        api_key: str | None,
    ) -> None:
        self.backend = backend
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.knowledge_top_k = 5
        self.show_knowledge = False
        self._domain_contexts: tuple[str, ...] | None = None
        self._knowledge_base: Any | None = None

    def detect(self, message: str) -> bool:
        return _looks_like_pipeline_request(message)

    def _ensure_api_key(self) -> bool:
        if self.backend == "mock":
            return True
        if self.api_key:
            return True

        console.print("[yellow]当前使用真实模型后端，需要提供 API Key 才能生成 pipeline。[/yellow]")
        provided = typer.prompt("请输入 LLM API Key (留空取消)", default="")
        if not provided.strip():
            console.print("已取消 pipeline 构建流程。", style="yellow")
            return False

        self.api_key = provided.strip()
        return True

    def _ensure_contexts(self) -> tuple[str, ...]:
        if self._domain_contexts is None:
            try:
                self._domain_contexts = tuple(load_domain_contexts(limit=4))
            except Exception as exc:  # pragma: no cover - defensive
                console.print(f"[yellow]加载默认上下文失败: {exc}[/yellow]")
                self._domain_contexts = ()
        return self._domain_contexts

    def _ensure_knowledge_base(self) -> Any | None:
        if self._knowledge_base is None:
            try:
                self._knowledge_base = get_default_knowledge_base()
            except Exception as exc:  # pragma: no cover - defensive
                console.print(f"[yellow]初始化 pipeline 知识库失败，将跳过检索: {exc}[/yellow]")
                self._knowledge_base = None
        return self._knowledge_base

    def _collect_requirements(self, initial_request: str) -> dict[str, Any]:
        console.print("\n[bold cyan]📋 需求收集[/bold cyan]", style="bold")
        console.print("请提供以下信息以生成最适合的 Pipeline 配置：\n", style="dim")

        # 询问是否使用模板
        use_template = typer.confirm("是否使用预设场景模板？", default=False)
        template_data = None

        if use_template:
            _show_scenario_templates()
            template_key = (
                typer.prompt("选择场景模板 (输入关键字，如 'qa', 'rag', 'chat' 等)", default="qa")
                .strip()
                .lower()
            )
            template_data = _get_scenario_template(template_key)
            if template_data:
                console.print(f"\n✅ 已加载 [green]{template_data['name']}[/green] 模板\n")
            else:
                console.print(
                    f"\n⚠️  未找到模板 '{template_key}'，将使用自定义配置\n",
                    style="yellow",
                )

        default_name = _default_pipeline_name(initial_request)

        # 提示用户可以简化输入
        console.print("💡 [dim]提示：直接回车将使用默认值（基于您的描述自动推断）[/dim]\n")

        # 如果有模板，使用模板的默认值
        if template_data:
            name = typer.prompt("📛 Pipeline 名称", default=template_data["name"])
            goal = typer.prompt("🎯 Pipeline 目标描述", default=template_data["goal"])
            default_sources = ", ".join(template_data["data_sources"])
            default_latency = template_data["latency_budget"]
            default_constraints = template_data["constraints"]
        else:
            name = typer.prompt("📛 Pipeline 名称", default=default_name)
            goal = typer.prompt(
                "🎯 Pipeline 目标描述", default=initial_request.strip() or default_name
            )
            default_sources = "文档知识库"
            default_latency = "实时响应优先"
            default_constraints = ""

        # 提供更详细的说明
        console.print("\n[dim]数据来源示例：文档知识库、用户输入、数据库、API 等[/dim]")
        data_sources = typer.prompt("📦 主要数据来源 (逗号分隔)", default=default_sources)

        console.print("\n[dim]延迟需求示例：实时响应优先、批处理可接受、高吞吐量优先[/dim]")
        latency = typer.prompt("⚡ 延迟/吞吐需求", default=default_latency)

        console.print("\n[dim]约束条件示例：仅使用本地模型、内存限制 4GB、必须支持流式输出[/dim]")
        constraints = typer.prompt("⚙️  特殊约束 (可留空)", default=default_constraints)

        requirements: dict[str, Any] = {
            "name": name.strip() or default_name,
            "goal": goal.strip() or initial_request.strip() or default_name,
            "data_sources": _normalize_list_field(data_sources),
            "latency_budget": latency.strip(),
            "constraints": constraints.strip(),
            "initial_prompt": initial_request.strip(),
        }

        # 显示收集到的需求摘要
        console.print("\n[bold green]✅ 需求收集完成[/bold green]")
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_row("名称:", f"[cyan]{requirements['name']}[/cyan]")
        summary_table.add_row("目标:", f"[yellow]{requirements['goal']}[/yellow]")
        summary_table.add_row(
            "数据源:", f"[magenta]{', '.join(requirements['data_sources'])}[/magenta]"
        )
        if requirements["latency_budget"]:
            summary_table.add_row("延迟需求:", requirements["latency_budget"])
        if requirements["constraints"]:
            summary_table.add_row("约束条件:", requirements["constraints"])
        console.print(summary_table)
        console.print()

        return requirements

    def _build_config(self) -> pipeline_builder.BuilderConfig:
        domain_contexts = self._ensure_contexts() or ()
        knowledge_base = self._ensure_knowledge_base()
        return pipeline_builder.BuilderConfig(
            backend=self.backend,
            model=self.model,
            base_url=self.base_url,
            api_key=self.api_key,
            domain_contexts=domain_contexts,
            knowledge_base=knowledge_base,
            knowledge_top_k=self.knowledge_top_k,
            show_knowledge=self.show_knowledge,
        )

    def _generate_plan(self, requirements: dict[str, Any]) -> dict[str, Any] | None:
        console.print("\n[bold magenta]🤖 正在生成 Pipeline 配置...[/bold magenta]\n")

        config = self._build_config()
        generator = pipeline_builder.PipelinePlanGenerator(config)

        plan: dict[str, Any] | None = None
        feedback: str | None = None

        for round_num in range(1, 7):  # 最多 6 轮
            console.print(f"[dim]>>> 第 {round_num} 轮生成...[/dim]")

            try:
                plan = generator.generate(requirements, plan, feedback)
                console.print("[green]✓[/green] 生成成功\n")
            except pipeline_builder.PipelineBuilderError as exc:
                console.print(f"[red]✗ 生成失败: {exc}[/red]\n")

                # 提供更详细的错误处理建议
                if "API" in str(exc) or "key" in str(exc).lower():
                    console.print("[yellow]💡 建议：检查 API Key 是否正确配置[/yellow]")
                elif "timeout" in str(exc).lower():
                    console.print("[yellow]💡 建议：网络可能不稳定，可以重试[/yellow]")
                elif "JSON" in str(exc) or "parse" in str(exc).lower():
                    console.print("[yellow]💡 建议：模型输出格式异常，尝试简化需求描述[/yellow]")

                if not typer.confirm("\n是否尝试重新生成？", default=True):
                    return None

                feedback = typer.prompt(
                    "请提供更多需求或修改建议（直接回车使用原需求重试）", default=""
                )
                if not feedback or not feedback.strip():
                    feedback = None
                continue

            # 显示生成的配置
            console.print("[bold cyan]📄 生成的 Pipeline 配置：[/bold cyan]")
            pipeline_builder.render_pipeline_plan(plan)
            pipeline_builder.preview_pipeline_plan(plan)

            # 验证配置
            console.print("\n[dim]>>> 正在验证配置...[/dim]")
            is_valid, errors = _validate_pipeline_config(plan)

            if not is_valid:
                console.print("[red]⚠️  配置验证发现问题：[/red]")
                for error in errors:
                    console.print(f"  • [red]{error}[/red]")
                console.print("\n[yellow]建议：在反馈中说明这些问题，让模型重新生成[/yellow]")

                if not typer.confirm("是否继续使用此配置（可能无法正常运行）？", default=False):
                    feedback = typer.prompt(
                        "请描述需要修正的问题或提供额外要求",
                        default="请修复配置验证中发现的问题",
                    )
                    continue
            else:
                console.print("[green]✓[/green] 配置验证通过")

                # 检查类导入（警告级别）
                import_warnings = _check_class_imports(plan)
                if import_warnings:
                    console.print("\n[yellow]⚠️  检测到以下潜在问题：[/yellow]")
                    for warning in import_warnings[:5]:  # 最多显示5个
                        console.print(f"  • [yellow]{warning}[/yellow]")
                    if len(import_warnings) > 5:
                        console.print(f"  [dim]... 还有 {len(import_warnings) - 5} 个警告[/dim]")
                    console.print("[dim]提示：这些警告不一定导致运行失败，但建议检查[/dim]")

            if typer.confirm("\n✨ 对该配置满意吗？", default=True):
                console.print("\n[bold green]🎉 Pipeline 配置已确认！[/bold green]\n")
                return plan

            console.print("\n[yellow]⚙️  进入优化模式...[/yellow]")
            feedback = typer.prompt(
                "请输入需要调整的地方（例如：使用流式输出、改用本地模型、添加监控）\n留空结束",
                default="",
            )
            if not feedback or not feedback.strip():
                console.print("[yellow]未提供调整意见，保持当前版本。[/yellow]")
                return plan

        # 达到最大轮数
        console.print("\n[yellow]⚠️  已达到最大优化轮数（6 轮）[/yellow]")
        if plan and typer.confirm("是否使用最后一次生成的配置？", default=True):
            return plan

        return plan

    def handle(self, message: str) -> bool:
        if not self.detect(message):
            return False

        if not self._ensure_api_key():
            return True

        # 显示欢迎信息和功能说明
        console.print("\n" + "=" * 70)
        console.print("[bold magenta]🚀 SAGE Pipeline Builder - 智能编排助手[/bold magenta]")
        console.print("=" * 70)
        console.print(
            """
[dim]功能说明：
  • 基于您的描述自动生成 SAGE Pipeline 配置
  • 使用 RAG 技术检索相关文档和示例
  • 支持多轮对话优化配置
  • 可直接运行生成的 Pipeline
[/dim]
        """
        )

        console.print("🎯 [cyan]检测到 Pipeline 构建请求[/cyan]")
        console.print(f"📝 您的需求: [yellow]{message}[/yellow]\n")

        # 收集需求
        requirements = self._collect_requirements(message)

        # 生成配置
        plan = self._generate_plan(requirements)
        if plan is None:
            console.print("[yellow]⚠️  未生成可用的 Pipeline 配置。[/yellow]")
            return True

        # 保存配置
        console.print("[bold cyan]💾 保存配置文件[/bold cyan]")
        destination = typer.prompt("保存到文件 (直接回车使用默认输出目录)", default="").strip()
        output_path: Path | None = Path(destination).expanduser() if destination else None
        overwrite = False
        if output_path and output_path.exists():
            overwrite = typer.confirm("⚠️  目标文件已存在，是否覆盖？", default=False)
            if not overwrite:
                console.print("[yellow]已取消保存，结束本次构建。[/yellow]")
                return True

        saved_path = pipeline_builder.save_pipeline_plan(plan, output_path, overwrite)
        console.print(f"\n✅ Pipeline 配置已保存至 [green]{saved_path}[/green]\n")

        # 询问是否运行
        if not typer.confirm("▶️  是否立即运行该 Pipeline？", default=True):
            console.print("\n[dim]提示：稍后可使用以下命令运行：[/dim]")
            console.print(f"[cyan]  sage pipeline run {saved_path}[/cyan]\n")
            return True

        # 配置运行参数
        console.print("\n[bold cyan]⚙️  配置运行参数[/bold cyan]")
        autostop = typer.confirm("提交后等待执行完成 (autostop)?", default=True)

        pipeline_type = (plan.get("pipeline", {}).get("type") or "local").lower()
        host: str | None = None
        port_value: int | None = None

        if pipeline_type == "remote":
            console.print("\n[yellow]检测到远程 Pipeline，需要配置 JobManager 连接信息[/yellow]")
            host = typer.prompt("远程 JobManager host", default="127.0.0.1").strip() or None
            port_text = typer.prompt("远程 JobManager 端口", default="19001").strip()
            try:
                port_value = int(port_text)
            except ValueError:
                console.print("[yellow]端口格式不合法，使用默认 19001。[/yellow]")
                port_value = 19001

        # 运行 Pipeline
        console.print("\n[bold green]🚀 正在启动 Pipeline...[/bold green]\n")
        try:
            job_id = pipeline_builder.execute_pipeline_plan(
                plan,
                autostop=autostop,
                host=host,
                port=port_value,
                console_override=console,
            )
            if job_id:
                console.print(f"\n[bold green]✅ Pipeline 已提交，Job ID: {job_id}[/bold green]")
            else:
                console.print("\n[bold green]✅ Pipeline 执行完成[/bold green]")
        except Exception as exc:
            console.print(f"\n[red]❌ Pipeline 执行失败: {exc}[/red]")
            console.print("\n[dim]提示：请检查配置文件和依赖项是否正确[/dim]")

        console.print("\n" + "=" * 70 + "\n")
        return True


def render_references(references: Sequence[dict[str, str]]) -> Table:
    table = Table(title="知识引用", show_header=True, header_style="bold cyan")
    table.add_column("#", justify="right", width=3)
    table.add_column("文档")
    table.add_column("节")
    table.add_column("得分", justify="right", width=7)

    for idx, ref in enumerate(references, start=1):
        # score 可能是字符串，需要转换为浮点数
        score = ref.get("score", 0.0)
        try:
            score_float = float(score)
        except (ValueError, TypeError):
            score_float = 0.0
        table.add_row(
            str(idx),
            ref.get("title", "未知"),
            ref.get("heading", "-"),
            f"{score_float:.4f}",
        )
    return table


def retrieve_context(
    db: Any,
    embedder: EmbeddingModel,
    question: str,
    top_k: int,
    show_progress: bool = True,
) -> dict[str, object]:
    """检索相关上下文。

    Args:
        db: SageDB 数据库实例
        embedder: Embedding 模型
        question: 用户问题
        top_k: 返回的文档数量
        show_progress: 是否显示进度
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn

    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]正在检索相关文档...[/cyan]"),
            transient=True,
        ) as progress:
            progress.add_task("embedding", total=None)
            query_vector = embedder.embed(question)
            results = db.search(query_vector, top_k, True)
    else:
        query_vector = embedder.embed(question)
        results = db.search(query_vector, top_k, True)

    contexts: list[str] = []
    references: list[dict[str, str]] = []
    for item in results:
        metadata = dict(item.metadata) if hasattr(item, "metadata") else {}
        contexts.append(metadata.get("text", ""))
        references.append(
            {
                "title": metadata.get("title", metadata.get("doc_path", "未知")),
                "heading": metadata.get("heading", ""),
                "path": metadata.get("doc_path", ""),
                "anchor": metadata.get("anchor", ""),
                "score": str(float(getattr(item, "score", 0.0))),
                "label": f"[{metadata.get('doc_path', '?')}]",
            }
        )
    return {"contexts": contexts, "references": references}


def interactive_chat(
    manifest: ChatManifest,
    index_root: Path,
    top_k: int,
    backend: str,
    model: str,
    base_url: str | None,
    api_key: str | None,
    ask: str | None,
    stream: bool,
    finetune_model: str | None = None,
    finetune_port: int = DEFAULT_FINETUNE_PORT,
) -> None:
    embedder: Any | None = None
    db: Any | None = None
    generator = ResponseGenerator(
        backend,
        model,
        base_url,
        api_key,
        finetune_model=finetune_model,
        finetune_port=finetune_port,
    )
    pipeline_coordinator = PipelineChatCoordinator(backend, model, base_url, api_key)

    console.print(
        Panel(
            f"索引: [cyan]{manifest.index_name}[/cyan]\n"
            f"来源: [green]{manifest.source_dir}[/green]\n"
            f"文档数: {manifest.num_documents}  Chunk数: {manifest.num_chunks}\n"
            f"Embedding: {manifest.embed_config}",
            title="SAGE Chat 准备就绪",
        )
    )

    def ensure_retriever() -> tuple[Any, Any]:
        nonlocal embedder, db
        if embedder is None:
            embedder = build_embedder(manifest.embed_config)
        if db is None:
            db = open_database(manifest)
        return db, embedder

    def answer_once(query: str) -> None:
        # 检测是否是简单闲聊（不需要检索）
        casual_patterns = [
            "你好",
            "hi",
            "hello",
            "嗨",
            "hey",
            "谢谢",
            "thanks",
            "thank you",
            "再见",
            "bye",
            "拜拜",
            "test",
            "测试",
            "试试",
            "ok",
            "好的",
            "嗯",
        ]
        query_lower = query.strip().lower()
        is_casual = (
            any(
                query_lower == p or query_lower.startswith(p + " ") or query_lower.endswith(" " + p)
                for p in casual_patterns
            )
            and len(query.strip()) < 20
        )

        if is_casual:
            # 闲聊模式：跳过检索，直接生成回答
            contexts: Sequence[str] = []
            references: Sequence[dict[str, str]] = []
        else:
            # 技术问题：执行检索
            current_db, current_embedder = ensure_retriever()
            payload = retrieve_context(current_db, current_embedder, query, top_k)
            contexts = payload["contexts"]  # type: ignore[assignment]
            references = payload["references"]  # type: ignore[assignment]

        try:
            reply = generator.answer(query, contexts, references, stream=stream)
        except Exception as exc:
            console.print(f"[red]生成回答失败: {exc}[/red]")
            return

        # 只在有引用时显示引用表
        if references:
            context_table = render_references(references)
            console.print(context_table)

        if stream:
            text = Text()
            with Live(Panel(text, title="回答"), auto_refresh=False) as live:
                text.append(reply)
                live.refresh()
        else:
            console.print(Panel(Markdown(reply), title="回答", style="bold green"))

    if ask:
        if pipeline_coordinator.handle(ask):
            return
        answer_once(ask)
        return

    # 显示帮助信息
    console.print("\n[bold cyan]🧭 SAGE Chat 使用指南[/bold cyan]")

    # 显示当前配置
    if backend == "finetune":
        console.print(f"[green]✅ 使用微调模型: {finetune_model or DEFAULT_FINETUNE_MODEL}[/green]")
        console.print(f"[dim]端口: {finetune_port}[/dim]\n")

    console.print(
        """
[dim]基本命令：
  • 直接输入问题获取文档相关回答
  • 输入包含 'pipeline'、'构建应用' 等关键词触发 Pipeline 构建模式
  • 输入 'help' 显示帮助信息
  • 输入 'templates' 查看可用场景模板
  • 输入 'exit'、'quit' 或 'q' 退出对话
[/dim]
    """
    )

    try:
        while True:
            try:
                question = typer.prompt("🤖 你的问题")
            except (EOFError, KeyboardInterrupt):
                console.print("\n再见 👋", style="cyan")
                break
            if not question.strip():
                continue

            question_lower = question.lower().strip()

            # 处理特殊命令
            if question_lower in {"exit", "quit", "q"}:
                console.print("再见 👋", style="cyan")
                break
            elif question_lower in {"help", "帮助", "?"}:
                console.print("\n[bold cyan]📚 帮助信息[/bold cyan]")
                console.print(
                    """
[dim]功能说明：
  1. 文档问答：直接提问关于 SAGE 的问题
  2. Pipeline 构建：描述你想要的应用场景

示例问题：
  • "SAGE 如何配置 RAG？"
  • "请帮我构建一个问答应用"
  • "如何使用向量数据库？"
  • "build a chat pipeline with streaming"

特殊命令：
  • help      - 显示此帮助信息
  • templates - 查看可用场景模板
  • exit/quit - 退出对话
[/dim]
                """
                )
                continue
            elif question_lower in {"templates", "模板"}:
                _show_scenario_templates()
                console.print("[dim]提示：在 Pipeline 构建流程中可以选择使用这些模板[/dim]\n")
                continue

            # 处理 Pipeline 构建请求
            if pipeline_coordinator.handle(question):
                continue

            # 处理普通问答
            answer_once(question)
    finally:
        # 清理资源
        generator.cleanup()


@app.callback()
def main(
    ctx: typer.Context,
    index_name: str = typer.Option(
        DEFAULT_INDEX_NAME,
        "--index",
        "-i",
        help="索引名称，用于读取 manifest 和 SageDB 文件",
    ),
    ask: str | None = typer.Option(
        None,
        "--ask",
        "-q",
        help="直接提问并退出，而不是进入交互模式",
    ),
    top_k: int = typer.Option(
        DEFAULT_TOP_K,
        "--top-k",
        "-k",
        min=1,
        max=20,
        help="检索时返回的参考文档数量",
    ),
    backend: str = typer.Option(
        DEFAULT_BACKEND,
        "--backend",
        help="回答生成后端: mock / openai / compatible / finetune / vllm / ollama",
    ),
    model: str = typer.Option(
        "qwen-max",
        "--model",
        help="回答生成模型名称（finetune backend 会自动从配置读取）",
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="LLM API base_url (例如 vLLM 或兼容 OpenAI 的接口)",
    ),
    api_key: str | None = typer.Option(
        lambda: os.environ.get("TEMP_GENERATOR_API_KEY"),
        "--api-key",
        help="LLM API Key (默认读取环境变量 TEMP_GENERATOR_API_KEY)",
    ),
    finetune_model: str | None = typer.Option(
        DEFAULT_FINETUNE_MODEL,
        "--finetune-model",
        help="使用 finetune backend 时的微调模型名称（~/.sage/finetune_output/ 下的目录名）",
    ),
    finetune_port: int = typer.Option(
        DEFAULT_FINETUNE_PORT,
        "--finetune-port",
        help="finetune backend 使用的 vLLM 服务端口",
    ),
    index_root: str | None = typer.Option(
        None,
        "--index-root",
        help="索引输出目录 (未提供则使用 ~/.sage/cache/chat)",
    ),
    stream: bool = typer.Option(False, "--stream", help="启用流式输出 (仅当后端支持)"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    ensure_sage_db()
    root = resolve_index_root(index_root)
    manifest = load_or_bootstrap_manifest(root, index_name)

    interactive_chat(
        manifest=manifest,
        index_root=root,
        top_k=top_k,
        backend=backend,
        model=model,
        base_url=base_url,
        api_key=api_key,
        ask=ask,
        stream=stream,
        finetune_model=finetune_model,
        finetune_port=finetune_port,
    )


@app.command("ingest")
def ingest(
    source_dir: Path | None = typer.Option(
        None,
        "--source",
        "-s",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="文档来源目录 (默认 docs-public/docs_src)",
    ),
    index_name: str = typer.Option(DEFAULT_INDEX_NAME, "--index", "-i", help="索引名称"),
    chunk_size: int = typer.Option(
        DEFAULT_CHUNK_SIZE,
        "--chunk-size",
        help="chunk 字符长度",
        min=128,
        max=4096,
    ),
    chunk_overlap: int = typer.Option(
        DEFAULT_CHUNK_OVERLAP,
        "--chunk-overlap",
        help="chunk 之间的重叠字符数",
        min=0,
        max=1024,
    ),
    embedding_method: str = typer.Option(
        DEFAULT_EMBEDDING_METHOD,
        "--embedding-method",
        help="Embedding 方法 (mockembedder/hf/openai/...)",
    ),
    embedding_model: str | None = typer.Option(
        None,
        "--embedding-model",
        help="Embedding 模型名称 (方法需要时提供)",
    ),
    fixed_dim: int = typer.Option(
        DEFAULT_FIXED_DIM,
        "--fixed-dim",
        help="mockembedder 使用的维度",
        min=64,
        max=2048,
    ),
    max_files: int | None = typer.Option(
        None,
        "--max-files",
        help="仅处理指定数量的文件 (测试/调试用)",
    ),
    index_root: str | None = typer.Option(
        None,
        "--index-root",
        help="索引输出目录 (未提供则使用 ~/.sage/cache/chat)",
    ),
    embedding_base_url: str | None = typer.Option(
        None,
        "--embedding-base-url",
        help="Embedding 服务 API 端点 (用于连接本地 embedding server，如 http://localhost:8090/v1)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="静默模式，只显示进度条不打印详细日志",
    ),
) -> None:
    ensure_sage_db()
    root = resolve_index_root(index_root)
    target_source = source_dir or default_source_dir()

    needs_model = embedding_method in METHODS_REQUIRE_MODEL
    if needs_model and not embedding_model:
        raise typer.BadParameter(f"{embedding_method} 方法需要指定 --embedding-model")

    # 构建 embedding 配置（新接口会自动处理默认值）
    embedding_config: dict[str, Any] = {"method": embedding_method, "params": {}}

    # 设置方法特定参数
    if embedding_method == "mockembedder":
        embedding_config["params"]["fixed_dim"] = fixed_dim
    elif embedding_method == "hash":
        embedding_config["params"]["dim"] = fixed_dim

    # 设置模型名称（如果提供）
    if embedding_model:
        embedding_config["params"]["model"] = embedding_model

    # 设置 base_url（如果提供，用于连接本地 embedding 服务）
    if embedding_base_url:
        embedding_config["params"]["base_url"] = embedding_base_url
        # 本地服务不需要 API key，设置一个占位符
        if "api_key" not in embedding_config["params"]:
            embedding_config["params"]["api_key"] = "local"  # pragma: allowlist secret

    if not quiet:
        console.print(
            Panel(
                f"索引名称: [cyan]{index_name}[/cyan]\n"
                f"文档目录: [green]{target_source}[/green]\n"
                f"索引目录: [magenta]{root}[/magenta]\n"
                f"Embedding: {embedding_config}",
                title="SAGE Chat Ingest",
            )
        )

    ingest_source(
        source_dir=target_source,
        index_root=root,
        index_name=index_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_config=embedding_config,
        max_files=max_files,
        show_progress=not quiet,
    )


@app.command("show")
def show_manifest(
    index_name: str = typer.Option(DEFAULT_INDEX_NAME, "--index", "-i"),
    index_root: str | None = typer.Option(None, "--index-root", help="索引所在目录"),
) -> None:
    ensure_sage_db()
    root = resolve_index_root(index_root)
    try:
        manifest = load_manifest(root, index_name)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    table = Table(title=f"SAGE Chat 索引: {index_name}")
    table.add_column("属性", style="cyan")
    table.add_column("值", style="green")
    table.add_row("索引路径", str(manifest.db_path))
    table.add_row("创建时间", manifest.created_at)
    table.add_row("文档目录", manifest.source_dir)
    table.add_row("文档数量", str(manifest.num_documents))
    table.add_row("Chunk 数量", str(manifest.num_chunks))
    table.add_row("Embedding", json.dumps(manifest.embedding, ensure_ascii=False))
    table.add_row("Chunk 配置", f"size={manifest.chunk_size}, overlap={manifest.chunk_overlap}")
    console.print(table)


__all__ = ["app"]
