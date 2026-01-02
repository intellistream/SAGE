# IndexBuilder - RAG 索引构建器

## 概述

`IndexBuilder` 是 SAGE 框架中用于构建 RAG（检索增强生成）向量索引的核心服务。它位于 L4 层（sage-middleware），采用依赖注入模式支持多种向量存储后端。

______________________________________________________________________

## 架构设计

### 层级定位

```
L6: sage-cli, sage-llm-gateway    # 使用 IndexBuilder
    │
    ▼
L4: sage-middleware           # IndexBuilder 定义
    ├── operators/rag/index_builder/
    │   ├── builder.py        # IndexBuilder 类
    │   ├── manifest.py       # IndexManifest 数据结构
    │   └── storage.py        # VectorStore 协议
    │
    ▼
L3: sage-libs                 # 提供分块算法
    └── rag/chunk.py
```

### 设计模式

IndexBuilder 使用**工厂注入模式**，将向量存储后端的创建逻辑与索引构建逻辑解耦：

```python
# 后端工厂函数签名
Callable[[Path, int], VectorStore]
#         │      │
#         │      └── 向量维度
#         └── 持久化路径
```

______________________________________________________________________

## 快速开始

### 基本用法

```python
from pathlib import Path
from sage.middleware.operators.rag.index_builder import IndexBuilder
from sage.middleware.components.sage_db.backend import SageDBBackend
from sage.common.components.sage_embedding import get_embedding_model

# 1. 准备后端工厂
def backend_factory(path: Path, dim: int):
    return SageDBBackend(path, dim)

# 2. 准备 Embedding 模型
embedder = get_embedding_model("openai", model="BAAI/bge-m3")

# 3. 创建 IndexBuilder
builder = IndexBuilder(backend_factory=backend_factory)

# 4. 构建索引
manifest = builder.build_from_docs(
    source_dir=Path("docs/"),
    persist_path=Path(".sage/index.sagedb"),
    embedding_model=embedder,
    index_name="my-docs",
    chunk_size=800,
    chunk_overlap=160,
)

print(f"索引构建完成: {manifest.num_chunks} 个片段")
```

______________________________________________________________________

## API 参考

### IndexBuilder

```python
class IndexBuilder:
    def __init__(self, backend_factory: Callable[[Path, int], VectorStore]):
        """初始化 IndexBuilder。

        Args:
            backend_factory: 创建 VectorStore 实例的工厂函数
        """

    def build_from_docs(
        self,
        source_dir: Path,
        persist_path: Path,
        embedding_model: Any,
        index_name: str = "default",
        chunk_size: int = 800,
        chunk_overlap: int = 160,
        document_processor: Callable[[Path], list[dict]] | None = None,
        max_documents: int | None = None,
        show_progress: bool = True,
    ) -> IndexManifest:
        """从文档目录构建向量索引。

        Args:
            source_dir: 源文档目录
            persist_path: 索引持久化路径
            embedding_model: Embedding 模型（需实现 embed() 和 get_dim()）
            index_name: 索引唯一标识
            chunk_size: 文本分块大小（字符数）
            chunk_overlap: 相邻分块重叠大小
            document_processor: 自定义文档处理函数
            max_documents: 最大处理文档数（用于测试）
            show_progress: 是否显示进度条

        Returns:
            IndexManifest: 包含构建统计信息的清单
        """
```

### IndexManifest

```python
@dataclass
class IndexManifest:
    """索引构建清单"""
    index_name: str       # 索引名称
    created_at: str       # 创建时间 (ISO 格式)
    num_documents: int    # 文档数量
    num_chunks: int       # 分块数量
    embedding_dim: int    # 向量维度
    chunk_size: int       # 分块大小
    chunk_overlap: int    # 分块重叠
```

### VectorStore 协议

```python
class VectorStore(Protocol):
    """向量存储后端协议"""

    def add(self, uid: int, vector: list[float], metadata: dict) -> None:
        """添加向量"""

    def build_index(self) -> None:
        """构建/优化索引"""

    def save(self, path: Path) -> None:
        """持久化索引"""
```

______________________________________________________________________

## 自定义文档处理器

默认文档处理器仅支持简单文本提取。对于复杂文档（如 Markdown、代码文件），建议提供自定义处理器：

```python
def custom_markdown_processor(source_dir: Path) -> list[dict]:
    """自定义 Markdown 处理器"""
    chunks = []

    for md_file in source_dir.glob("**/*.md"):
        content = md_file.read_text(encoding="utf-8")
        relative_path = md_file.relative_to(source_dir)

        # 按标题分割章节
        for section in parse_sections(content):
            chunks.append({
                "content": section["text"],
                "metadata": {
                    "doc_path": str(relative_path),
                    "title": section.get("title", ""),
                    "heading": section.get("heading", ""),
                },
            })

    return chunks

# 使用自定义处理器
manifest = builder.build_from_docs(
    source_dir=docs_path,
    persist_path=index_path,
    embedding_model=embedder,
    document_processor=custom_markdown_processor,
)
```

______________________________________________________________________

## 支持的后端

### SageDB (默认)

高性能 C++ 向量数据库，适用于生产环境：

```python
from sage.middleware.components.sage_db.backend import SageDBBackend

def factory(path, dim):
    return SageDBBackend(path, dim)
```

### ChromaDB

基于 Chroma 的后端，适用于快速原型开发：

```python
from sage.libs.integrations.chroma import ChromaBackend

def factory(path, dim):
    return ChromaBackend(path, dim)
```

______________________________________________________________________

## 工作流程

```
┌─────────────────┐
│   源文档目录     │
└────────┬────────┘
         │ document_processor
         ▼
┌─────────────────┐
│   文档解析       │  提取文本 + 元数据
└────────┬────────┘
         │ chunk_text()
         ▼
┌─────────────────┐
│   文本分块       │  按 chunk_size 分割
└────────┬────────┘
         │ embedding_model.embed()
         ▼
┌─────────────────┐
│   向量化        │  生成 embedding
└────────┬────────┘
         │ store.add()
         ▼
┌─────────────────┐
│   存储入库       │  写入 VectorStore
└────────┬────────┘
         │ store.build_index()
         ▼
┌─────────────────┐
│   索引优化       │  构建 HNSW 等索引
└────────┬────────┘
         │ store.save()
         ▼
┌─────────────────┐
│   持久化        │  保存到磁盘
└─────────────────┘
```

______________________________________________________________________

## 最佳实践

1. **选择合适的分块大小**：通常 512-1024 字符效果较好
1. **设置适当的重叠**：建议 10-20% 的重叠以保持上下文连贯性
1. **使用高质量 Embedding**：推荐使用 `BAAI/bge-m3` 等多语言模型
1. **增量更新**：对于大型文档库，考虑实现增量索引更新
1. **监控构建进度**：使用 `show_progress=True` 监控长时间构建任务

______________________________________________________________________

## 相关文档

- [RAG 模块概览](../rag.md)
- [SageDB 后端](../../sage-middleware/components/sage_db.md)
- [Embedding 服务](../../sage-common/embedding.md)
