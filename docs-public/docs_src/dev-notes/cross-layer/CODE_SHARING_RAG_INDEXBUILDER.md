# SAGE 代码共享架构实现总结

## 🎯 目标

解决 `sage chat` 和 `sage-llm-gateway` 之间的代码重复问题，实现 RAG 索引构建逻辑的共享。

## ✅ 已完成的工作

### 1. 创建共享的文档处理工具 (L1)

**位置**: `packages/sage-common/src/sage/common/utils/document_processing.py`

**功能**:

- `iter_markdown_files()` - 遍历 Markdown 文件
- `parse_markdown_sections()` - 解析 Markdown 章节
- `chunk_text()` - 智能文本分块（支持自然边界检测）
- `sanitize_metadata_value()` - 清理元数据值
- `slugify()` - URL 安全化
- `truncate_text()` - 文本截断

**优势**: 纯 Python 标准库实现，无依赖，可在所有层级使用

### 2. 创建统一的 IndexBuilder (L4)

**位置**: `packages/sage-middleware/src/sage/middleware/operators/rag/index_builder/`

**组件**:

#### `manifest.py` - 索引元数据

```python
@dataclass
class IndexManifest:
    index_name: str
    backend_type: str
    persist_path: Path
    source_dir: str
    embedding_config: dict
    chunk_size: int
    chunk_overlap: int
    num_documents: int
    num_chunks: int
    created_at: str
```

#### `storage.py` - VectorStore Protocol

```python
@runtime_checkable
class VectorStore(Protocol):
    def add(self, vector: list[float], metadata: dict) -> None: ...
    def build_index(self) -> None: ...
    def save(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...
    def search(self, query_vector, top_k, filter_dict) -> list[dict]: ...
    def get_dim(self) -> int: ...
    def count(self) -> int: ...
```

#### `builder.py` - 索引构建器

```python
class IndexBuilder:
    def __init__(self, backend_factory: Callable[[Path, int], VectorStore]):
        self.backend_factory = backend_factory

    def build_from_docs(
        self,
        source_dir: Path,
        persist_path: Path,
        embedding_model: Any,
        chunk_size: int = 800,
        chunk_overlap: int = 160,
        document_processor: Callable | None = None,
    ) -> IndexManifest:
        # 1. 处理文档
        # 2. 分块
        # 3. 生成嵌入
        # 4. 存储向量
        # 5. 构建索引
        # 6. 返回 manifest
```

**设计模式**: 依赖注入 + Protocol（接口抽象）

### 3. 创建 VectorStore 适配器

#### SageDBBackend (L4)

**位置**: `packages/sage-middleware/src/sage/middleware/components/sage_db/backend.py`

实现 `VectorStore` Protocol，包装 SageDB C++ 扩展。

#### ChromaVectorStoreAdapter (L3)

**位置**: `packages/sage-libs/src/sage/libs/integrations/chroma_adapter.py`

实现 `VectorStore` Protocol，包装 ChromaBackend。

### 4. 重构 sage-cli (L6)

**修改**: `packages/sage-cli/src/sage/cli/commands/apps/chat.py`

**变更**:

- ✅ 删除重复的文档处理函数（72行）
- ✅ 导入 `sage.common.utils.document_processing`
- ✅ 重构 `ingest_source()` 使用 `IndexBuilder`
- ✅ 创建 `_create_markdown_processor()` 工厂函数
- ✅ 使用 `SageDBBackend` 作为存储后端

**代码简化**: ~120 行 → ~80 行（减少 33%）

### 5. 增强 sage-llm-gateway (L6)

**修改**: `packages/sage-llm-gateway/src/sage/gateway/adapters/openai.py`

**新增功能**:

- ✅ `_ensure_index_ready()` - 启动时自动检查/构建索引
- ✅ `_build_index_from_docs()` - 使用 IndexBuilder 构建索引
- ✅ 自动检测文档源路径
- ✅ 使用 ChromaVectorStoreAdapter

**修改**: `packages/sage-llm-gateway/src/sage/gateway/server.py`

**新增 API**:

- ✅ `GET /admin/index/status` - 查看索引状态
- ✅ `POST /admin/index/build` - 触发索引构建
- ✅ `DELETE /admin/index` - 删除索引

## 📊 架构对比

### 之前 (代码重复)

```
sage-cli/chat.py               sage-llm-gateway/openai.py
     ├── iter_markdown_files       ├── (缺失)
     ├── parse_markdown_sections   ├── (缺失)
     ├── chunk_text                ├── (缺失)
     ├── ingest_source()           ├── (缺失)
     └── 直接使用 SageDB            └── 使用 ChromaDB
```

### 之后 (代码共享)

```
L1: sage-common/utils/document_processing.py
    ├── iter_markdown_files
    ├── parse_markdown_sections
    ├── chunk_text
    └── sanitize_metadata_value
           ↑
           │ (import)
           │
L4: sage-middleware/operators/rag/index_builder/
    ├── VectorStore (Protocol)
    ├── IndexBuilder
    ├── IndexManifest
    ├── SageDBBackend (adapter)
    └── ChromaVectorStoreAdapter (adapter)
           ↑
           │ (import)
           │
L6: sage-cli/chat.py + sage-llm-gateway/openai.py
    └── 使用 IndexBuilder + 注入 backend
```

## 🎨 关键设计决策

### 1. 为什么放在 L4 (sage-middleware/operators/rag)?

❌ **L2 (sage-platform)**: 不合适 - L2 是基础设施层（queue, storage, service）

- "rag_index这个名字放在L2就不太对，和同级的 queue, service, storage不是一个级别的"

❌ **L3 (sage-libs)**: 不合适 - L3 是算法层

- sage-libs/rag 只包含纯算法：`chunk.py`, `document_loaders.py`, `types.py`
- IndexBuilder 是编排逻辑，不是算法

✅ **L4 (sage-middleware/operators/rag)**: 正确！

- 已有 `RAGPipeline` 在此层（编排组件）
- IndexBuilder 也是编排逻辑（文档处理→分块→嵌入→存储）
- 遵循现有模式

### 2. 为什么使用 Protocol 而非继承？

✅ **Protocol (Duck Typing)**:

- 解耦 - L4 定义接口，L3/L4 各自实现
- 灵活 - 无需修改现有类
- Python 惯用 - runtime_checkable

❌ **继承 (ABC)**:

- 强耦合 - 需要修改 SageDB/ChromaDB
- 不符合 Python 哲学

### 3. 为什么使用依赖注入？

✅ **Factory Pattern**:

```python
# L6 注入 SageDB
def backend_factory(path: Path, dim: int):
    return SageDBBackend(path, dim)

builder = IndexBuilder(backend_factory=backend_factory)
```

**优势**:

- L4 不直接依赖具体实现
- L6 可选择任意后端（SageDB, Chroma, Milvus...）
- 便于测试（Mock backend）

## 📈 收益

### 代码维护性

- ✅ 单一数据源（Single Source of Truth）
- ✅ DRY 原则（Don't Repeat Yourself）
- ✅ 减少 bug 表面积

### 功能增强

- ✅ Gateway 获得自动索引构建能力
- ✅ Gateway 新增索引管理 API
- ✅ 统一的索引元数据格式

### 可扩展性

- ✅ 轻松添加新的 VectorStore 后端（只需实现 Protocol）
- ✅ 可自定义 document_processor
- ✅ 可复用于其他组件

## 🔧 下一步

### 必须完成

1. **重新安装包**: `./quickstart.sh --dev --yes`

   - 确保 `chroma_adapter.py` 被正确安装

1. **测试 sage-cli**:

   ```bash
   sage chat ingest --help
   sage chat ingest --source docs-public/docs_src
   ```

1. **测试 sage-llm-gateway**:

   ```bash
   sage-llm-gateway start
   curl http://localhost:8000/admin/index/status
   curl -X POST http://localhost:8000/admin/index/build
   ```

### 可选增强

1. **添加进度回调**: IndexBuilder 支持进度显示
1. **批量嵌入**: 优化大文档集的处理速度
1. **增量索引**: 只处理新增/修改的文档
1. **并行处理**: 多进程/多线程加速

## 📝 文件清单

### 新建文件

1. `packages/sage-common/src/sage/common/utils/document_processing.py` (240 行)
1. `packages/sage-middleware/src/sage/middleware/operators/rag/index_builder/__init__.py` (42 行)
1. `packages/sage-middleware/src/sage/middleware/operators/rag/index_builder/manifest.py` (100 行)
1. `packages/sage-middleware/src/sage/middleware/operators/rag/index_builder/storage.py` (130 行)
1. `packages/sage-middleware/src/sage/middleware/operators/rag/index_builder/builder.py` (260 行)
1. `packages/sage-middleware/src/sage/middleware/components/sage_db/backend.py` (180 行)
1. `packages/sage-libs/src/sage/libs/integrations/chroma_adapter.py` (200 行)

### 修改文件

1. `packages/sage-common/src/sage/common/utils/__init__.py` (+15 行)
1. `packages/sage-cli/src/sage/cli/commands/apps/chat.py` (-72 行重复代码, +80 行使用 IndexBuilder)
1. `packages/sage-llm-gateway/src/sage/gateway/adapters/openai.py` (+140 行)
1. `packages/sage-llm-gateway/src/sage/gateway/server.py` (+130 行 API)
1. `packages/sage-libs/src/sage/libs/integrations/__init__.py` (+2 行导出)

### 总计

- **新增代码**: ~1,200 行
- **删除重复代码**: ~72 行
- **净增**: ~1,130 行
- **新增功能**: 索引管理 API, 自动索引构建, 统一索引框架

## 🏆 架构原则验证

✅ **遵循 SAGE 层级依赖规则**:

- L6 (cli/gateway) → L4 (IndexBuilder) → L3 (ChromaDB) → L1 (document_processing)
- 无向上依赖

✅ **遵循现有模式**:

- RAGPipeline 在 L4 → IndexBuilder 也在 L4
- sage-libs/rag 只含算法 → 编排逻辑在 L4

✅ **设计模式应用**:

- Protocol (接口抽象)
- Factory (依赖注入)
- Adapter (适配现有类)

## 📚 参考

- SAGE Architecture: `docs/dev-notes/package-architecture.md`
- Layer Dependencies: L6→L5→L4→L3→L2→L1
- 用户反馈: "rag的内容是否应该放在sage-middleware/operators里面更合适？"
