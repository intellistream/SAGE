# Task 2: Knowledge Manager (知识库管理器)

## 任务概述

实现知识库管理器，负责管理、加载和检索多种知识源。这是 Multi-Agent 架构中 Knowle    async def ensure_source_loaded(self, source_name: str) -> bool:
        """确保指定知识源已加载并索引

        如果尚未加载，则触发加载流程：
        1. 读取源文件
        2. 切分文档
        3. 生成 Embedding
        4. 存入向量库

        对于 user_uploads 类型，每次调用可能需要检查新文件。
        """
        ...

    async def add_document(self, file_path: str | Path, source_name: str = "user_uploads") -> bool:
        """添加单个文档到知识库 (用于文件上传后立即索引)"""
        ...

    async def search(
        self,
        query: str,
        sources: List[str] | None = None,
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[SearchResult]:
        """在指定知识源中检索"""
        ...

    async def get_memory_context(self, session_id: str, query: str) -> str:
        """获取记忆上下文 (集成 sage-memory)

        结合长期记忆(向量库)和短期记忆(对话历史)
        """
        ...优先级**: P0 (高)  
**预计工时**: 3-4 天  
**可并行**: 是（依赖 sage-common, sage-middleware）

## 目标

1. **按需加载**: 只有在需要时才加载和索引知识源，避免启动慢
2. **多源支持**: 支持 SAGE 官方文档、示例代码、API 文档、用户自定义文档
3. **统一检索**: 提供统一的语义检索接口
4. **持久化**: 支持向量索引的持久化和增量更新

## 文件位置

```
packages/sage-studio/src/sage/studio/services/knowledge_manager.py
packages/sage-studio/src/sage/studio/config/knowledge_sources.yaml
packages/sage-studio/tests/unit/test_knowledge_manager.py
```

## 接口设计

```python
"""
Knowledge Manager for SAGE Studio

Layer: L6 (sage-studio)
Dependencies: sage-common (embedding), sage-middleware (sage-db)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, List, Dict

from sage.common.components.sage_embedding.service import EmbeddingService
# 注意：sage-db 可能需要根据实际安装情况导入
# from sage.middleware.components.sage_db.python.micro_service.sage_db_service import SageDBService


class SourceType(Enum):
    MARKDOWN = "markdown"
    PYTHON_CODE = "python_code"
    JSON = "json"
    PDF = "pdf"
    USER_UPLOAD = "user_upload"  # 新增：用户上传


@dataclass
class KnowledgeSource:
    """知识源定义"""
    name: str
    type: SourceType
    path: str | Path
    description: str = ""
    enabled: bool = True
    auto_load: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 新增：支持动态路径（如用户上传目录）
    is_dynamic: bool = False


@dataclass
class SearchResult:
    """检索结果"""
    content: str
    score: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeManager:
    """知识库管理器

    负责管理向量数据库连接、Embedding 服务以及文档的加载和检索。
    """

    def __init__(self, config_path: str | Path | None = None):
        """
        Args:
            config_path: 配置文件路径，默认使用 studio 内置配置
        """
        self.sources: Dict[str, KnowledgeSource] = {}
        self.loaded_sources: set[str] = set()
        self._embedding_service = None
        self._vector_db = None

        # 初始化时只加载配置，不连接服务
        self._load_config(config_path)

    async def ensure_source_loaded(self, source_name: str) -> bool:
        """确保指定知识源已加载并索引

        如果尚未加载，则触发加载流程：
        1. 读取源文件
        2. 切分文档
        3. 生成 Embedding
        4. 存入向量库
        """
        ...

    async def search(
        self,
        query: str,
        sources: List[str] | None = None,
        top_k: int = 5,
        score_threshold: float = 0.6
    ) -> List[SearchResult]:
        """在指定知识源中检索

        Args:
            query: 用户查询
            sources: 指定检索的源列表，None 表示检索所有已加载的源
            top_k: 返回结果数量
            score_threshold: 相似度阈值

        Returns:
            SearchResult 列表
        """
        ...

    def list_sources(self) -> List[Dict[str, Any]]:
        """列出所有可用知识源及其状态"""
        ...

    def add_custom_source(self, name: str, path: str, type: str) -> bool:
        """添加用户自定义知识源"""
        ...
```

## 配置文件设计

`packages/sage-studio/src/sage/studio/config/knowledge_sources.yaml`

```yaml
sources:
  sage_docs:
    type: markdown
    path: "${SAGE_ROOT}/docs-public/docs_src"
    description: "SAGE 框架官方文档，包含架构、安装、使用指南"
    enabled: true
    auto_load: false
    chunk_size: 500
    chunk_overlap: 50

  examples:
    type: python_code
    path: "${SAGE_ROOT}/examples"
    description: "SAGE 使用示例代码"
    enabled: true
    auto_load: false
    chunk_size: 1000
    chunk_overlap: 100

  api_reference:
    type: python_code
    path: "${SAGE_ROOT}/packages/sage-common/src/sage/common"
    description: "SAGE 核心组件 API 参考"
    enabled: true
    auto_load: false
```

## 实现细节

### 1. 服务初始化

KnowledgeManager 应该采用**懒加载**模式初始化 EmbeddingService 和 VectorDB。

```python
    @property
    def embedding_service(self):
        if self._embedding_service is None:
            # 使用 sage.common.components.sage_embedding
            from sage.common.components.sage_embedding.service import EmbeddingService
            # 尝试连接现有服务或启动新实例
            # 建议复用 sage-studio 启动时可能已经存在的服务连接
            self._embedding_service = EmbeddingService(...)
        return self._embedding_service

    @property
    def vector_db(self):
        if self._vector_db is None:
            # 使用 sage-db 或简单的内存向量库（如 ChromaDB/FAISS）作为后备
            # 考虑到 studio 的轻量级需求，如果 sage-db 不可用，可以考虑使用简单的本地向量库
            try:
                from sage.middleware.components.sage_db.python.micro_service.sage_db_service import SageDBService
                self._vector_db = SageDBService(...)
            except ImportError:
                # Fallback implementation
                pass
        return self._vector_db
```

### 2. 文档处理

需要实现不同类型文件的加载器和切分器：

- **MarkdownLoader**: 解析 Markdown 结构，按标题切分（可复用 `docs_processor.py` 中的逻辑）。
- **PythonLoader**: 解析 Python 代码，提取类、函数 docstring 和签名。

### 3. 向量存储策略

- **Collection 管理**: 每个 KnowledgeSource 对应一个 Collection 还是所有源在一个 Collection 中通过 metadata 区分？
  - *建议*: 使用 metadata 区分 `source_name`，这样可以灵活支持跨源检索。
- **持久化**: 索引应保存在 `~/.local/share/sage/studio/knowledge_base/`。
- **缓存**: 记录文件哈希，避免重复索引未修改的文件。

## 测试计划

```python
# tests/unit/test_knowledge_manager.py

import pytest
from sage.studio.services.knowledge_manager import KnowledgeManager

class TestKnowledgeManager:

    @pytest.fixture
    def manager(self):
        return KnowledgeManager(config_path="tests/data/test_sources.yaml")

    def test_load_config(self, manager):
        assert "sage_docs" in manager.sources
        assert manager.sources["sage_docs"].enabled is True

    @pytest.mark.asyncio
    async def test_ensure_source_loaded(self, manager):
        # Mock embedding and db
        success = await manager.ensure_source_loaded("sage_docs")
        assert success
        assert "sage_docs" in manager.loaded_sources

    @pytest.mark.asyncio
    async def test_search(self, manager):
        results = await manager.search("如何创建 Pipeline", sources=["sage_docs"])
        assert len(results) > 0
        assert results[0].source == "sage_docs"
```

## 提示词（复制使用）

```
请在 SAGE 项目中实现 KnowledgeManager 知识库管理器。

## 背景
SAGE Studio 需要一个按需加载的知识库管理组件，支持多种数据源，用于 Multi-Agent 系统的 RAG 功能。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/services/knowledge_manager.py
2. 配置文件: packages/sage-studio/src/sage/studio/config/knowledge_sources.yaml
3. 实现 KnowledgeManager 类，支持懒加载 EmbeddingService 和 VectorDB
4. 实现 Markdown 和 Python 代码的文档加载与切分逻辑（可参考 docs_processor.py）
5. 实现 ensure_source_loaded 方法，支持增量更新（基于文件哈希）
6. 实现 search 方法，支持按源过滤

## 依赖
- sage.common.components.sage_embedding
- sage.middleware.components.sage_db (可选，需提供 fallback)

## 注意
- 优先复用现有代码
- 索引数据存储在 ~/.local/share/sage/studio/knowledge_base/
- 保持接口异步 (async/await)
```
