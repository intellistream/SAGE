# Agent-2: RAG Toolkit Refactoring

## 🎯 任务目标

将 sage-libs 中的 rag 模块重构为接口层，实现代码迁移到 isage-rag 独立库。

## 📂 当前结构

```
packages/sage-libs/src/sage/libs/rag/
├── interface/
│   ├── __init__.py
│   ├── base.py      # 已有部分接口
│   └── factory.py   # 已有部分工厂
```

外部仓库：`/home/shuhao/sage-rag` (已存在)

## 📋 任务清单

### 1. 完善接口层

**base.py** - RAG 核心接口：

```python
"""Base classes for RAG components."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Document:
    """Document representation."""
    content: str
    metadata: dict[str, Any]
    id: Optional[str] = None
    source: Optional[str] = None

@dataclass
class Chunk:
    """Document chunk."""
    content: str
    metadata: dict[str, Any]
    doc_id: Optional[str] = None
    chunk_index: int = 0
    overlap_with_prev: int = 0

@dataclass
class RetrievalResult:
    """Retrieval result with score."""
    chunk: Chunk
    score: float
    metadata: dict[str, Any]

class BaseLoader(ABC):
    """Abstract base class for document loaders."""

    @abstractmethod
    def load(self, source: str | Path, **kwargs) -> list[Document]:
        """Load documents from source."""
        pass

    @abstractmethod
    def supported_formats(self) -> list[str]:
        """Return supported file formats."""
        pass

class BaseChunker(ABC):
    """Abstract base class for text chunking."""

    @abstractmethod
    def chunk(self, document: Document, **kwargs) -> list[Chunk]:
        """Chunk a document into smaller pieces."""
        pass

    @abstractmethod
    def chunk_batch(self, documents: list[Document], **kwargs) -> list[list[Chunk]]:
        """Chunk multiple documents."""
        pass

class BaseRetriever(ABC):
    """Abstract base class for retrievers."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[dict[str, Any]] = None,
        **kwargs
    ) -> list[RetrievalResult]:
        """Retrieve relevant chunks for a query."""
        pass

    @abstractmethod
    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Add chunks to the retriever's index."""
        pass

class BaseReranker(ABC):
    """Abstract base class for rerankers."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: Optional[int] = None
    ) -> list[RetrievalResult]:
        """Rerank retrieval results."""
        pass

class BaseQueryRewriter(ABC):
    """Abstract base class for query rewriting."""

    @abstractmethod
    def rewrite(self, query: str, context: Optional[dict[str, Any]] = None) -> str:
        """Rewrite query for better retrieval."""
        pass

    @abstractmethod
    def rewrite_multi(self, query: str, num_variants: int = 3) -> list[str]:
        """Generate multiple query variants."""
        pass
```

**factory.py** - 注册和工厂：

```python
"""Factory and registry for RAG components."""

from typing import Any, Type

from .base import (
    BaseLoader,
    BaseChunker,
    BaseRetriever,
    BaseReranker,
    BaseQueryRewriter,
)

_LOADER_REGISTRY: dict[str, Type[BaseLoader]] = {}
_CHUNKER_REGISTRY: dict[str, Type[BaseChunker]] = {}
_RETRIEVER_REGISTRY: dict[str, Type[BaseRetriever]] = {}
_RERANKER_REGISTRY: dict[str, Type[BaseReranker]] = {}
_QUERY_REWRITER_REGISTRY: dict[str, Type[BaseQueryRewriter]] = {}

# ==================== Loader Registry ====================

def register_loader(name: str, cls: Type[BaseLoader]) -> None:
    """Register a document loader."""
    if name in _LOADER_REGISTRY:
        raise ValueError(f"Loader '{name}' already registered")
    if not issubclass(cls, BaseLoader):
        raise TypeError("Class must inherit from BaseLoader")
    _LOADER_REGISTRY[name] = cls

def create_loader(name: str, **kwargs: Any) -> BaseLoader:
    """Create a loader instance."""
    if name not in _LOADER_REGISTRY:
        available = ", ".join(_LOADER_REGISTRY.keys()) or "none"
        raise KeyError(
            f"Loader '{name}' not found. Available: {available}. "
            "Did you install 'isage-rag'?"
        )
    return _LOADER_REGISTRY[name](**kwargs)

def list_loaders() -> list[str]:
    """List registered loaders."""
    return list(_LOADER_REGISTRY.keys())

# ==================== Chunker Registry ====================

def register_chunker(name: str, cls: Type[BaseChunker]) -> None:
    """Register a chunker."""
    if name in _CHUNKER_REGISTRY:
        raise ValueError(f"Chunker '{name}' already registered")
    if not issubclass(cls, BaseChunker):
        raise TypeError("Class must inherit from BaseChunker")
    _CHUNKER_REGISTRY[name] = cls

def create_chunker(name: str, **kwargs: Any) -> BaseChunker:
    """Create a chunker instance."""
    if name not in _CHUNKER_REGISTRY:
        available = ", ".join(_CHUNKER_REGISTRY.keys()) or "none"
        raise KeyError(
            f"Chunker '{name}' not found. Available: {available}. "
            "Did you install 'isage-rag'?"
        )
    return _CHUNKER_REGISTRY[name](**kwargs)

def list_chunkers() -> list[str]:
    """List registered chunkers."""
    return list(_CHUNKER_REGISTRY.keys())

# ==================== Retriever Registry ====================

def register_retriever(name: str, cls: Type[BaseRetriever]) -> None:
    """Register a retriever."""
    if name in _RETRIEVER_REGISTRY:
        raise ValueError(f"Retriever '{name}' already registered")
    if not issubclass(cls, BaseRetriever):
        raise TypeError("Class must inherit from BaseRetriever")
    _RETRIEVER_REGISTRY[name] = cls

def create_retriever(name: str, **kwargs: Any) -> BaseRetriever:
    """Create a retriever instance."""
    if name not in _RETRIEVER_REGISTRY:
        available = ", ".join(_RETRIEVER_REGISTRY.keys()) or "none"
        raise KeyError(
            f"Retriever '{name}' not found. Available: {available}. "
            "Did you install 'isage-rag'?"
        )
    return _RETRIEVER_REGISTRY[name](**kwargs)

def list_retrievers() -> list[str]:
    """List registered retrievers."""
    return list(_RETRIEVER_REGISTRY.keys())

# ==================== Reranker Registry ====================

def register_reranker(name: str, cls: Type[BaseReranker]) -> None:
    """Register a reranker."""
    if name in _RERANKER_REGISTRY:
        raise ValueError(f"Reranker '{name}' already registered")
    if not issubclass(cls, BaseReranker):
        raise TypeError("Class must inherit from BaseReranker")
    _RERANKER_REGISTRY[name] = cls

def create_reranker(name: str, **kwargs: Any) -> BaseReranker:
    """Create a reranker instance."""
    if name not in _RERANKER_REGISTRY:
        available = ", ".join(_RERANKER_REGISTRY.keys()) or "none"
        raise KeyError(
            f"Reranker '{name}' not found. Available: {available}. "
            "Did you install 'isage-rag'?"
        )
    return _RERANKER_REGISTRY[name](**kwargs)

def list_rerankers() -> list[str]:
    """List registered rerankers."""
    return list(_RERANKER_REGISTRY.keys())

# ==================== Query Rewriter Registry ====================

def register_query_rewriter(name: str, cls: Type[BaseQueryRewriter]) -> None:
    """Register a query rewriter."""
    if name in _QUERY_REWRITER_REGISTRY:
        raise ValueError(f"Query rewriter '{name}' already registered")
    if not issubclass(cls, BaseQueryRewriter):
        raise TypeError("Class must inherit from BaseQueryRewriter")
    _QUERY_REWRITER_REGISTRY[name] = cls

def create_query_rewriter(name: str, **kwargs: Any) -> BaseQueryRewriter:
    """Create a query rewriter instance."""
    if name not in _QUERY_REWRITER_REGISTRY:
        available = ", ".join(_QUERY_REWRITER_REGISTRY.keys()) or "none"
        raise KeyError(
            f"Query rewriter '{name}' not found. Available: {available}. "
            "Did you install 'isage-rag'?"
        )
    return _QUERY_REWRITER_REGISTRY[name](**kwargs)

def list_query_rewriters() -> list[str]:
    """List registered query rewriters."""
    return list(_QUERY_REWRITER_REGISTRY.keys())

__all__ = [
    # Loaders
    "register_loader",
    "create_loader",
    "list_loaders",
    # Chunkers
    "register_chunker",
    "create_chunker",
    "list_chunkers",
    # Retrievers
    "register_retriever",
    "create_retriever",
    "list_retrievers",
    # Rerankers
    "register_reranker",
    "create_reranker",
    "list_rerankers",
    # Query Rewriters
    "register_query_rewriter",
    "create_query_rewriter",
    "list_query_rewriters",
]
```

### 2. isage-rag 仓库结构

```bash
cd /home/shuhao/sage-rag

# 目录结构
mkdir -p src/isage_rag/{loaders,chunkers,retrievers,rerankers,query_rewrite}

# pyproject.toml
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "isage-rag"
version = "0.1.0"
description = "RAG toolkit for SAGE - loaders, chunkers, retrievers, rerankers"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "Apache-2.0"}

dependencies = [
    "isage-libs>=0.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.8.0",
]
full = [
    "pypdf>=3.17.0",
    "python-docx>=1.0.0",
    "beautifulsoup4>=4.12.0",
    "markdown>=3.5.0",
    "sentence-transformers>=2.2.0",
]

[tool.setuptools.packages.find]
where = ["src"]
EOF

# 提交
git add .
git commit -m "feat: add RAG interface and structure"
git push origin main-dev
```

### 3. 实现注册

```python
# src/isage_rag/__init__.py
"""RAG toolkit implementations."""

from sage.libs.rag.interface import (
    register_loader,
    register_chunker,
    register_retriever,
    register_reranker,
    register_query_rewriter,
)

# Loaders
from .loaders import PDFLoader, DOCXLoader, MarkdownLoader, HTMLLoader

register_loader("pdf", PDFLoader)
register_loader("docx", DOCXLoader)
register_loader("markdown", MarkdownLoader)
register_loader("html", HTMLLoader)

# Chunkers
from .chunkers import FixedSizeChunker, SemanticChunker, SentenceChunker

register_chunker("fixed", FixedSizeChunker)
register_chunker("semantic", SemanticChunker)
register_chunker("sentence", SentenceChunker)

# Retrievers
from .retrievers import DenseRetriever, SparseRetriever, HybridRetriever

register_retriever("dense", DenseRetriever)
register_retriever("sparse", SparseRetriever)
register_retriever("hybrid", HybridRetriever)

# Rerankers
from .rerankers import CrossEncoderReranker, LLMReranker

register_reranker("cross_encoder", CrossEncoderReranker)
register_reranker("llm", LLMReranker)

# Query Rewriters
from .query_rewrite import TemplateRewriter, LLMRewriter

register_query_rewriter("template", TemplateRewriter)
register_query_rewriter("llm", LLMRewriter)
```

## ✅ 完成标准

- [ ] sage-libs rag/interface/ 完善（5 个组件接口）
- [ ] sage-rag 仓库更新实现代码
- [ ] 所有组件注册到工厂
- [ ] 集成测试通过
- [ ] 文档更新

## 📤 输出文件

1. `packages/sage-libs/src/sage/libs/rag/interface/base.py`（完善）
1. `packages/sage-libs/src/sage/libs/rag/interface/factory.py`（完善）
1. `/home/shuhao/sage-rag/src/isage_rag/__init__.py`
1. `/home/shuhao/sage-rag/pyproject.toml`
1. `packages/sage-libs/tests/integration/test_rag_integration.py`
