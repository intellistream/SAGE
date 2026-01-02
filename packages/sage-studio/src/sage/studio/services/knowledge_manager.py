"""
Knowledge Manager for SAGE Studio

This module provides the data structures and manager class for handling
multiple knowledge sources in the SAGE Studio Multi-Agent architecture.

Layer: L6 (sage-studio)
Dependencies: sage-common (embedding), sage-middleware (sage-db)
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from sage.studio.services.vector_store import VectorStore

from sage.studio.services.vector_store import DocumentChunk

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """知识源类型枚举

    定义 SAGE Studio 支持的所有知识源类型。
    """

    MARKDOWN = "markdown"
    PYTHON_CODE = "python_code"
    JSON = "json"
    YAML = "yaml"
    PDF = "pdf"
    USER_UPLOAD = "user_upload"


@dataclass
class KnowledgeSource:
    """知识源定义

    描述一个知识源的所有配置信息，包括路径、类型、加载策略等。

    Attributes:
        name: 知识源的唯一标识符
        type: 知识源类型，参见 SourceType 枚举
        path: 知识源的文件或目录路径，支持 ~ 展开
        description: 知识源的描述信息
        enabled: 是否启用该知识源
        auto_load: 是否在启动时自动加载（默认 False，按需加载）
        is_dynamic: 是否为动态知识源（如用户上传目录，内容可能随时变化）
        file_patterns: 文件匹配模式列表，使用 glob 语法
        metadata: 额外的元数据配置
    """

    name: str
    type: SourceType
    path: str | Path
    description: str = ""
    enabled: bool = True
    auto_load: bool = False
    is_dynamic: bool = False
    file_patterns: list[str] = field(default_factory=lambda: ["*"])
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化后处理：展开路径中的 ~ 和环境变量"""
        if isinstance(self.path, str):
            expanded_path = os.path.expandvars(self.path)
            self.path = Path(expanded_path).expanduser()
        elif isinstance(self.path, Path):
            expanded_path = os.path.expandvars(str(self.path))
            self.path = Path(expanded_path).expanduser()


@dataclass
class SearchResult:
    """检索结果

    表示从知识库中检索到的单条结果。

    Attributes:
        content: 匹配的文本内容
        score: 相似度分数，范围 0-1，越高越相关
        source: 来源知识源的名称
        file_path: 原始文件路径（可选）
        chunk_id: 分块 ID，用于定位具体片段（可选）
        metadata: 额外的元数据，如行号、标题等
    """

    content: str
    score: float
    source: str
    file_path: str | None = None
    chunk_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """验证 score 范围"""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be between 0 and 1, got {self.score}")


@dataclass
class ChunkConfig:
    """文档分块配置

    定义如何将文档切分为更小的块以便于向量检索。

    Attributes:
        chunk_size: 每个块的目标字符数
        chunk_overlap: 相邻块之间的重叠字符数
        separator: 分块时优先使用的分隔符列表
    """

    chunk_size: int = 500
    chunk_overlap: int = 50
    separator: list[str] = field(default_factory=lambda: ["\n\n", "\n", " ", ""])


@dataclass
class VectorStoreConfig:
    """向量存储配置

    Attributes:
        type: 向量存储类型 (chroma, milvus, faiss)
        persist_dir: 持久化目录路径
        collection_prefix: Collection 名称前缀
    """

    type: str = "chroma"
    persist_dir: str | Path = "~/.local/share/sage/studio/vector_db/"
    collection_prefix: str = "studio_kb_"

    def __post_init__(self) -> None:
        """初始化后处理：展开路径中的 ~ 和环境变量"""
        if isinstance(self.persist_dir, str):
            expanded_path = os.path.expandvars(self.persist_dir)
            self.persist_dir = Path(expanded_path).expanduser()
        elif isinstance(self.persist_dir, Path):
            expanded_path = os.path.expandvars(str(self.persist_dir))
            self.persist_dir = Path(expanded_path).expanduser()


@dataclass
class EmbeddingConfig:
    """Embedding 服务配置

    Attributes:
        model: Embedding 模型名称
        dim: 向量维度
        batch_size: 批处理大小
        max_length: 最大序列长度
    """

    model: str = "BAAI/bge-m3"
    dim: int = 1024
    batch_size: int = 32
    max_length: int = 512


@dataclass
class KnowledgeManagerConfig:
    """知识库管理器配置

    Attributes:
        vector_store: 向量存储配置
        embedding: Embedding 配置
        chunking: 分块配置
    """

    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    chunking: ChunkConfig = field(default_factory=ChunkConfig)


class KnowledgeManager:
    """知识库管理器

    负责管理多个知识源，实现按需加载、统一检索和持久化。
    作为 Studio 的核心服务之一，它协调 DocumentLoader 和 VectorStore 工作。
    """

    def __init__(self, config_path: str | Path | None = None):
        """初始化知识库管理器

        Args:
            config_path: 配置文件路径，默认使用 studio 内置配置
        """
        self.sources: dict[str, KnowledgeSource] = {}
        self._loaded_sources: set[str] = set()
        self._vector_stores: dict[str, VectorStore] = {}

        # 延迟导入以避免循环依赖
        from sage.studio.services.document_loader import DocumentLoader

        self._doc_loader = DocumentLoader()

        self.config = KnowledgeManagerConfig()
        self._load_config(config_path)

    def _load_config(self, config_path: str | Path | None) -> None:
        """加载 YAML 配置"""
        if config_path is None:
            # 默认配置路径: packages/sage-studio/src/sage/studio/config/knowledge_sources.yaml
            current_dir = Path(__file__).parent
            config_path = current_dir.parent / "config" / "knowledge_sources.yaml"

        config_path = Path(config_path).expanduser()
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return

        try:
            with open(config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # 解析知识源配置
            for name, source_config in config_data.get("knowledge_sources", {}).items():
                try:
                    self.sources[name] = KnowledgeSource(
                        name=name,
                        type=SourceType(source_config.get("type", "markdown")),
                        path=source_config.get("path", ""),
                        description=source_config.get("description", ""),
                        enabled=source_config.get("enabled", True),
                        auto_load=source_config.get("auto_load", False),
                        is_dynamic=source_config.get("is_dynamic", False),
                        file_patterns=source_config.get("file_patterns", ["*"]),
                        metadata=source_config.get("metadata", {}),
                    )
                except Exception as e:
                    logger.error(f"Failed to parse source config '{name}': {e}")

            # 解析组件配置
            if "vector_store" in config_data:
                vs_config = config_data["vector_store"]
                self.config.vector_store = VectorStoreConfig(
                    type=vs_config.get("type", "chroma"),
                    persist_dir=vs_config.get(
                        "persist_dir", "~/.local/share/sage/studio/vector_db/"
                    ),
                    collection_prefix=vs_config.get("collection_prefix", "studio_kb_"),
                )

            if "embedding" in config_data:
                emb_config = config_data["embedding"]
                self.config.embedding = EmbeddingConfig(
                    model=emb_config.get("model", "BAAI/bge-m3"),
                    dim=emb_config.get("dim", 1024),
                    batch_size=emb_config.get("batch_size", 32),
                    max_length=emb_config.get("max_length", 512),
                )

        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")

    async def ensure_source_loaded(self, source_name: str) -> bool:
        """确保指定知识源已加载

        这是"按需加载"的核心方法:
        1. 检查是否已加载
        2. 如未加载，调用 DocumentLoader
        3. 将 chunks 添加到 VectorStore
        """
        if source_name in self._loaded_sources:
            return True

        source = self.sources.get(source_name)
        if not source:
            logger.warning(f"Source not found: {source_name}")
            return False

        if not source.enabled:
            logger.info(f"Source is disabled: {source_name}")
            return False

        logger.info(f"Loading knowledge source: {source_name} from {source.path}")

        try:
            # 获取或创建向量存储
            vs = self._get_or_create_vector_store(source_name)

            # 加载文档
            chunks = list(
                self._doc_loader.load_directory(
                    source.path,
                    source.file_patterns,
                    source.type,
                )
            )

            if not chunks:
                logger.warning(f"No documents found for source: {source_name}")
                # 即使没有文档也标记为已加载，避免重复尝试
                self._loaded_sources.add(source_name)
                return True

            logger.info(f"Generated {len(chunks)} chunks for {source_name}")

            # 添加到向量存储
            count = await vs.add_documents(chunks, batch_size=self.config.embedding.batch_size)
            logger.info(f"Indexed {count} chunks for {source_name}")

            self._loaded_sources.add(source_name)
            return True

        except Exception as e:
            logger.error(f"Failed to load source {source_name}: {e}", exc_info=True)
            return False

    def _get_or_create_vector_store(self, source_name: str) -> VectorStore:
        """获取或创建指定源的向量存储实例"""
        if source_name in self._vector_stores:
            return self._vector_stores[source_name]

        from sage.studio.services.vector_store import VectorStore

        collection_name = f"{self.config.vector_store.collection_prefix}{source_name}"

        vs = VectorStore(
            collection_name=collection_name,
            embedding_model=self.config.embedding.model,
            embedding_dim=self.config.embedding.dim,
            persist_dir=self.config.vector_store.persist_dir,
        )

        self._vector_stores[source_name] = vs
        return vs

    async def add_document(self, file_path: str | Path, source_name: str = "user_uploads") -> bool:
        """添加单个文档（用于文件上传）"""
        file_path = Path(file_path).expanduser()
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        # 确保源已初始化
        if source_name not in self.sources:
            # 如果是未定义的源，创建一个临时的动态源配置
            self.sources[source_name] = KnowledgeSource(
                name=source_name,
                type=SourceType.USER_UPLOAD,
                path=file_path.parent,
                description="User uploaded documents",
                is_dynamic=True,
            )

        # 获取向量存储
        vs = self._get_or_create_vector_store(source_name)

        try:
            # 确定源类型
            source_type = self.sources[source_name].type

            chunks = self._doc_loader.load_file(file_path, source_type)
            if not chunks:
                return False

            await vs.add_documents(chunks, batch_size=self.config.embedding.batch_size)

            # 标记源为已加载
            self._loaded_sources.add(source_name)
            return True

        except Exception as e:
            logger.error(f"Failed to add document {file_path}: {e}")
            return False

    async def ingest_texts(
        self,
        texts: list[str],
        *,
        source_name: str = "agentic_evidence",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """将内存/检索得到的片段增量写入向量库（用于 agentic/聊天证据）。

        Args:
            texts: 待索引的纯文本列表
            source_name: 逻辑来源名称（用于 collection 前缀）
            metadata: 附带的上下文元数据（如 session_id、route）

        Returns:
            实际写入的 chunk 数量
        """

        if not texts:
            return 0

        vs = self._get_or_create_vector_store(source_name)
        meta = metadata or {}

        chunks = [
            DocumentChunk(
                content=text,
                source_file=source_name,
                chunk_index=idx,
                metadata={**meta},
            )
            for idx, text in enumerate(texts)
            if text
        ]

        if not chunks:
            return 0

        added = await vs.add_documents(chunks, batch_size=self.config.embedding.batch_size)
        self._loaded_sources.add(source_name)
        return added

    async def search(
        self,
        query: str,
        sources: list[str] | None = None,
        limit: int = 5,
        score_threshold: float = 0.6,
    ) -> list[SearchResult]:
        """在指定知识源中检索

        Args:
            query: 检索查询
            sources: 指定检索源，None 表示所有已加载的源
            limit: 返回结果数量
            score_threshold: 最低分数阈值
        """
        # 确定要检索的源
        if sources is None:
            # 如果未指定，检索所有已加载的源
            target_sources = list(self._loaded_sources)
            if not target_sources:
                # 如果没有加载任何源，尝试加载默认的（如 sage_docs）
                if "sage_docs" in self.sources and self.sources["sage_docs"].enabled:
                    target_sources = ["sage_docs"]
        else:
            target_sources = sources

        # 并行确保源已加载
        load_tasks = []
        for source_name in target_sources:
            if source_name not in self._loaded_sources:
                load_tasks.append(self.ensure_source_loaded(source_name))

        if load_tasks:
            await asyncio.gather(*load_tasks)

        # 在各源中检索
        search_tasks = []
        for source_name in target_sources:
            if source_name in self._vector_stores:
                vs = self._vector_stores[source_name]
                search_tasks.append(vs.search(query, top_k=limit, score_threshold=score_threshold))

        if not search_tasks:
            return []

        results_lists = await asyncio.gather(*search_tasks)

        # 合并结果
        all_results = []
        for results in results_lists:
            all_results.extend(results)

        # 按分数排序，取 top-k
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:limit]

    def get_loaded_sources(self) -> list[str]:
        """获取已加载的知识源列表"""
        return list(self._loaded_sources)

    def get_source_stats(self, source_name: str) -> dict[str, Any]:
        """获取知识源统计信息"""
        if source_name not in self._vector_stores:
            return {"status": "not_loaded"}

        stats = self._vector_stores[source_name].get_stats()
        stats["status"] = "loaded"
        return stats

    def list_sources(self) -> list[dict[str, Any]]:
        """列出所有可用知识源及其状态

        Returns:
            包含每个知识源信息的列表，每项包含:
            - name: 知识源名称
            - description: 描述
            - enabled: 是否启用
            - loaded: 是否已加载
            - type: 知识源类型
        """
        result = []
        for name, source in self.sources.items():
            result.append(
                {
                    "name": name,
                    "description": source.description,
                    "enabled": source.enabled,
                    "loaded": name in self._loaded_sources,
                    "type": source.type.value,
                    "path": str(source.path),
                    "is_dynamic": source.is_dynamic,
                }
            )
        return result
