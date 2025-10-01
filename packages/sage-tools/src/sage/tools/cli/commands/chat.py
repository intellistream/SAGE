#!/usr/bin/env python3
"""SAGE Chat CLI - Embedded programming assistant backed by SageDB."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import textwrap
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from sage.common.config.output_paths import (
    find_sage_project_root,
    get_sage_paths,
)
from sage.middleware.utils.embedding.embedding_model import EmbeddingModel

console = Console()

try:  # pragma: no cover - runtime check
    from sage.middleware.components.sage_db.python.sage_db import (
        SageDB,
        SageDBException,
    )

    SAGE_DB_AVAILABLE = True
    SAGE_DB_IMPORT_ERROR: Optional[Exception] = None
except Exception as exc:  # pragma: no cover - runtime check
    SageDB = None  # type: ignore
    SageDBException = Exception  # type: ignore
    SAGE_DB_AVAILABLE = False
    SAGE_DB_IMPORT_ERROR = exc


DEFAULT_INDEX_NAME = "docs-public"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 160
DEFAULT_TOP_K = 4
DEFAULT_BACKEND = "mock"
DEFAULT_EMBEDDING_METHOD = "hash"
DEFAULT_FIXED_DIM = 384
SUPPORTED_MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}

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

GITHUB_DOCS_ZIP_URL = (
    "https://github.com/intellistream/SAGE-Pub/archive/refs/heads/main.zip"
)

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
    embedding: Dict[str, object]
    chunk_size: int
    chunk_overlap: int
    num_documents: int
    num_chunks: int

    @property
    def embed_config(self) -> Dict[str, object]:
        return self.embedding


class HashingEmbedder:
    """Lightweight embedding that hashes tokens into a fixed-length vector."""

    def __init__(self, dim: int = DEFAULT_FIXED_DIM) -> None:
        self._dim = max(64, int(dim))

    def get_dim(self) -> int:
        return self._dim

    @property
    def method_name(self) -> str:
        return "hash"

    def embed(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self._dim

        vector = [0.0] * self._dim
        tokens = re.findall(r"[\w\u4e00-\u9fa5]+", text.lower())
        if not tokens:
            tokens = [text.lower()]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, len(digest), 4):
                chunk = digest[offset : offset + 4]
                if len(chunk) < 4:
                    chunk = chunk.ljust(4, b"\0")
                idx = int.from_bytes(chunk, "little") % self._dim
                vector[idx] += 1.0

        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]


def ensure_sage_db() -> None:
    """Exit early if the SageDB extension is unavailable."""

    if SAGE_DB_AVAILABLE:
        return
    message = (
        "[red]SageDB C++ 扩展不可用，无法使用 `sage chat`。[/red]\n"
        "请先构建 SageDB 组件：`cd packages/sage-middleware && bash build.sh`."
    )
    if SAGE_DB_IMPORT_ERROR:
        message += f"\n原始错误: {SAGE_DB_IMPORT_ERROR}"
    console.print(message)
    raise typer.Exit(code=1)


def resolve_index_root(index_root: Optional[str]) -> Path:
    if index_root:
        root = Path(index_root).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root
    paths = get_sage_paths()
    cache_dir = paths.cache_dir / "chat"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def default_source_dir() -> Path:
    project_root = find_sage_project_root()
    if not project_root:
        project_root = Path.cwd()
    candidate = project_root / "docs-public" / "docs_src"
    return candidate


def manifest_path(index_root: Path, index_name: str) -> Path:
    return index_root / f"{index_name}.manifest.json"


def db_file_path(index_root: Path, index_name: str) -> Path:
    return index_root / f"{index_name}.sagedb"


def load_manifest(index_root: Path, index_name: str) -> ChatManifest:
    path = manifest_path(index_root, index_name)
    if not path.exists():
        raise FileNotFoundError(
            f"未找到索引 manifest: {path}. 请先运行 `sage chat ingest`."
        )
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


def build_embedder(config: Dict[str, object]) -> Any:
    method = str(config.get("method", DEFAULT_EMBEDDING_METHOD))
    params = dict(config.get("params", {}))
    if method == "hash":
        dim = int(params.get("dim", params.get("fixed_dim", DEFAULT_FIXED_DIM)))
        return HashingEmbedder(dim)
    if method == "mockembedder" and "fixed_dim" not in params:
        params["fixed_dim"] = DEFAULT_FIXED_DIM
    embedder = EmbeddingModel(method=method, **params)
    return embedder


def iter_markdown_files(source: Path) -> Iterable[Path]:
    for path in sorted(source.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_MARKDOWN_SUFFIXES:
            yield path


_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(?P<title>.+?)\s*$")


def parse_markdown_sections(content: str) -> List[Dict[str, str]]:
    sections: List[Dict[str, str]] = []
    current_title = "Introduction"
    current_lines: List[str] = []

    for raw_line in content.splitlines():
        match = _HEADING_PATTERN.match(raw_line.strip())
        if match:
            if current_lines:
                sections.append(
                    {
                        "heading": current_title,
                        "content": "\n".join(current_lines).strip(),
                    }
                )
                current_lines = []
            current_title = match.group("title").strip()
        else:
            current_lines.append(raw_line)

    if current_lines:
        sections.append(
            {"heading": current_title, "content": "\n".join(current_lines).strip()}
        )

    return [section for section in sections if section["content"]]


def chunk_text(content: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    normalized = re.sub(r"\n{3,}", "\n\n", content).strip()
    if not normalized:
        return []

    start = 0
    length = len(normalized)
    step = max(1, chunk_size - chunk_overlap)
    chunks: List[str] = []

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

    return [c for c in chunks if c]


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\-]+", "-", text.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug or "section"


def truncate_text(text: str, limit: int = 480) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def sanitize_metadata_value(value: str) -> str:
    cleaned = value.replace("\r", " ").replace("\n", " ")
    cleaned = cleaned.replace('"', "'")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


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

    extracted_docs: Optional[Path] = None
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


def bootstrap_default_index(
    index_root: Path, index_name: str
) -> Optional[ChatManifest]:
    try:
        source_dir = ensure_docs_corpus(index_root)
    except Exception as exc:
        console.print(f"[red]无法准备文档语料: {exc}[/red]")
        return None

    embedding_config: Dict[str, object] = {
        "method": DEFAULT_EMBEDDING_METHOD,
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


def ingest_source(
    source_dir: Path,
    index_root: Path,
    index_name: str,
    chunk_size: int,
    chunk_overlap: int,
    embedding_config: Dict[str, object],
    max_files: Optional[int] = None,
) -> ChatManifest:
    ensure_sage_db()

    if not source_dir.exists():
        raise FileNotFoundError(f"文档目录不存在: {source_dir}")

    embedder = build_embedder(embedding_config)
    db_path = db_file_path(index_root, index_name)
    if db_path.exists():
        db_path.unlink()

    db = SageDB(embedder.get_dim())
    total_chunks = 0
    total_docs = 0

    for idx, file_path in enumerate(iter_markdown_files(source_dir), start=1):
        if max_files is not None and idx > max_files:
            break

        rel_path = file_path.relative_to(source_dir)
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        sections = parse_markdown_sections(text)
        if not sections:
            continue

        doc_title = sections[0]["heading"] if sections else file_path.stem

        for section_idx, section in enumerate(sections):
            section_chunks = chunk_text(section["content"], chunk_size, chunk_overlap)
            for chunk_idx, chunk in enumerate(section_chunks):
                vector = embedder.embed(chunk)
                metadata = {
                    "doc_path": sanitize_metadata_value(str(rel_path)),
                    "title": sanitize_metadata_value(doc_title),
                    "heading": sanitize_metadata_value(section["heading"]),
                    "anchor": sanitize_metadata_value(slugify(section["heading"])),
                    "chunk": str(chunk_idx),
                    "text": sanitize_metadata_value(truncate_text(chunk, limit=1200)),
                }
                db.add(vector, metadata)
                total_chunks += 1

        total_docs += 1
        console.print(
            f"📄 处理文档 {idx}: {rel_path} (sections={len(sections)})", style="cyan"
        )

    if total_chunks == 0:
        raise RuntimeError("未在文档中生成任何 chunk，检查源目录或 chunk 参数。")

    console.print(f"🧱 共写入向量: {total_chunks}")
    db.build_index()
    db.save(str(db_path))

    manifest = ChatManifest(
        index_name=index_name,
        db_path=db_path,
        created_at=datetime.utcnow().isoformat(),
        source_dir=str(source_dir),
        embedding=embedding_config,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        num_documents=total_docs,
        num_chunks=total_chunks,
    )
    save_manifest(index_root, index_name, manifest)
    console.print(
        Panel.fit(f"✅ 索引已更新 -> {db_path}", title="INGEST", style="green")
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
    db = SageDB(embedder.get_dim())
    db.load(str(manifest.db_path))
    return db


def build_prompt(question: str, contexts: Sequence[str]) -> List[Dict[str, str]]:
    context_block = "\n\n".join(
        f"[{idx}] {textwrap.dedent(ctx).strip()}"
        for idx, ctx in enumerate(contexts, start=1)
        if ctx
    )
    system_instructions = textwrap.dedent(
        """
        You are SAGE 内嵌编程助手。回答用户关于 SAGE 的问题，依据提供的上下文进行解释。
        - 如果上下文不足以回答，请坦诚说明并给出下一步建议。
        - 引用时使用 [编号] 表示。
        - 回答保持简洁，直接给出步骤或示例代码。
        """
    ).strip()

    if context_block:
        system_instructions += f"\n\n已检索上下文:\n{context_block}"

    return [
        {"role": "system", "content": system_instructions},
        {"role": "user", "content": question.strip()},
    ]


class ResponseGenerator:
    def __init__(
        self,
        backend: str,
        model: str,
        base_url: Optional[str],
        api_key: Optional[str],
        temperature: float = 0.2,
    ) -> None:
        self.backend = backend.lower()
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature

        if self.backend == "mock":
            self.client = None
        else:
            try:
                from sage.libs.utils.openaiclient import OpenAIClient

                kwargs = {"seed": 42}
                if base_url:
                    kwargs["base_url"] = base_url
                if api_key:
                    kwargs["api_key"] = api_key
                self.client = OpenAIClient(model_name=model, **kwargs)
            except Exception as exc:  # pragma: no cover - runtime check
                raise RuntimeError(f"无法初始化 OpenAIClient: {exc}") from exc

    def answer(
        self,
        question: str,
        contexts: Sequence[str],
        references: Sequence[Dict[str, str]],
        stream: bool = False,
    ) -> str:
        if self.backend == "mock":
            return self._mock_answer(question, contexts, references)

        messages = build_prompt(question, contexts)
        try:
            response = self.client.generate(
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
        references: Sequence[Dict[str, str]],
    ) -> str:
        if not contexts:
            return "暂时没有从知识库检索到答案。请尝试改写提问，或运行 `sage chat ingest` 更新索引。"
        top_ref = references[0] if references else {"title": "资料", "heading": ""}
        snippet = contexts[0].strip().replace("\n", " ")
        citation = top_ref.get("label", top_ref.get("title", "Docs"))
        return (
            f"根据 {citation} 的说明：{snippet[:280]}...\n\n"
            "如需更多细节，可以输入 `more` 再次检索，或使用 `--backend openai` 启用真实模型。"
        )


def render_references(references: Sequence[Dict[str, str]]) -> Table:
    table = Table(title="知识引用", show_header=True, header_style="bold cyan")
    table.add_column("#", justify="right", width=3)
    table.add_column("文档")
    table.add_column("节")
    table.add_column("得分", justify="right", width=7)

    for idx, ref in enumerate(references, start=1):
        table.add_row(
            str(idx),
            ref.get("title", "未知"),
            ref.get("heading", "-"),
            f"{ref.get('score', 0.0):.4f}",
        )
    return table


def retrieve_context(
    db: Any,
    embedder: EmbeddingModel,
    question: str,
    top_k: int,
) -> Dict[str, object]:
    query_vector = embedder.embed(question)
    results = db.search(query_vector, top_k, True)

    contexts: List[str] = []
    references: List[Dict[str, str]] = []
    for item in results:
        metadata = dict(item.metadata) if hasattr(item, "metadata") else {}
        contexts.append(metadata.get("text", ""))
        references.append(
            {
                "title": metadata.get("title", metadata.get("doc_path", "未知")),
                "heading": metadata.get("heading", ""),
                "path": metadata.get("doc_path", ""),
                "anchor": metadata.get("anchor", ""),
                "score": float(getattr(item, "score", 0.0)),
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
    base_url: Optional[str],
    api_key: Optional[str],
    ask: Optional[str],
    stream: bool,
) -> None:
    embedder = build_embedder(manifest.embed_config)
    db = open_database(manifest)
    generator = ResponseGenerator(backend, model, base_url, api_key)

    console.print(
        Panel(
            f"索引: [cyan]{manifest.index_name}[/cyan]\n"
            f"来源: [green]{manifest.source_dir}[/green]\n"
            f"文档数: {manifest.num_documents}  Chunk数: {manifest.num_chunks}\n"
            f"Embedding: {manifest.embed_config}",
            title="SAGE Chat 准备就绪",
        )
    )

    def answer_once(query: str) -> None:
        payload = retrieve_context(db, embedder, query, top_k)
        contexts = payload["contexts"]
        references = payload["references"]

        try:
            reply = generator.answer(query, contexts, references, stream=stream)
        except Exception as exc:
            console.print(f"[red]生成回答失败: {exc}[/red]")
            return

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
        answer_once(ask)
        return

    console.print("输入 `exit` 或 `quit` 结束对话。", style="dim")
    while True:
        try:
            question = typer.prompt("🤖 你的问题")
        except (EOFError, KeyboardInterrupt):
            console.print("\n再见 👋", style="cyan")
            break
        if not question.strip():
            continue
        if question.lower().strip() in {"exit", "quit", "q"}:
            console.print("再见 👋", style="cyan")
            break
        answer_once(question)


@app.callback()
def main(
    ctx: typer.Context,
    index_name: str = typer.Option(
        DEFAULT_INDEX_NAME,
        "--index",
        "-i",
        help="索引名称，用于读取 manifest 和 SageDB 文件",
    ),
    ask: Optional[str] = typer.Option(
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
        help="回答生成后端: mock / openai / compatible",
    ),
    model: str = typer.Option(
        "qwen-max",
        "--model",
        help="回答生成模型名称",
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="LLM API base_url (例如 vLLM 或兼容 OpenAI 的接口)",
    ),
    api_key: Optional[str] = typer.Option(
        lambda: os.environ.get("SAGE_CHAT_API_KEY"),
        "--api-key",
        help="LLM API Key (默认读取环境变量 SAGE_CHAT_API_KEY)",
    ),
    index_root: Optional[str] = typer.Option(
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
    )


@app.command("ingest")
def ingest(
    source_dir: Optional[Path] = typer.Option(
        None,
        "--source",
        "-s",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="文档来源目录 (默认 docs-public/docs_src)",
    ),
    index_name: str = typer.Option(
        DEFAULT_INDEX_NAME, "--index", "-i", help="索引名称"
    ),
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
    embedding_model: Optional[str] = typer.Option(
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
    max_files: Optional[int] = typer.Option(
        None,
        "--max-files",
        help="仅处理指定数量的文件 (测试/调试用)",
    ),
    index_root: Optional[str] = typer.Option(
        None,
        "--index-root",
        help="索引输出目录 (未提供则使用 ~/.sage/cache/chat)",
    ),
) -> None:
    ensure_sage_db()
    root = resolve_index_root(index_root)
    target_source = source_dir or default_source_dir()

    needs_model = embedding_method in METHODS_REQUIRE_MODEL
    if needs_model and not embedding_model:
        raise typer.BadParameter(f"{embedding_method} 方法需要指定 --embedding-model")

    embedding_config: Dict[str, object] = {"method": embedding_method, "params": {}}
    if embedding_method == "mockembedder":
        embedding_config["params"] = {"fixed_dim": fixed_dim}
    elif embedding_method == "hash":
        embedding_config["params"] = {"dim": fixed_dim}
    if embedding_model:
        embedding_config.setdefault("params", {})["model"] = embedding_model

    console.print(
        Panel(
            f"索引名称: [cyan]{index_name}[/cyan]\n"
            f"文档目录: [green]{target_source}[/green]\n"
            f"索引目录: [magenta]{root}[/magenta]\n"
            f"Embedding: {embedding_config}",
            title="SAGE Chat Ingest",
        )
    )

    manifest = ingest_source(
        source_dir=target_source,
        index_root=root,
        index_name=index_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_config=embedding_config,
        max_files=max_files,
    )


@app.command("show")
def show_manifest(
    index_name: str = typer.Option(DEFAULT_INDEX_NAME, "--index", "-i"),
    index_root: Optional[str] = typer.Option(None, "--index-root", help="索引所在目录"),
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
    table.add_row(
        "Chunk 配置", f"size={manifest.chunk_size}, overlap={manifest.chunk_overlap}"
    )
    console.print(table)


__all__ = ["app"]
