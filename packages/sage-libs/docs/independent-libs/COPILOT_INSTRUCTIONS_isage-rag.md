# isage-rag Copilot Instructions

## Package Identity

| 属性          | 值                                          |
| ------------- | ------------------------------------------- |
| **PyPI 包名** | `isage-rag`                                 |
| **导入名**    | `sage_libs.sage_rag`                        |
| **SAGE 层级** | L3 (Algorithms & Libraries)                 |
| **版本格式**  | `0.1.x.y` (四段式)                          |
| **仓库**      | `https://github.com/intellistream/sage-rag` |

## 层级定位

### ✅ 允许的依赖

```
L3 及以下:
├── sage-common (L1)      # 基础工具、类型、配置
├── sage-platform (L2)    # 平台服务抽象
├── Python stdlib         # 标准库
├── numpy, scipy          # 科学计算
├── transformers          # HuggingFace 模型
├── sentence-transformers # Embedding 模型
└── pypdf, docx, etc.     # 文档解析库
```

### ❌ 禁止的依赖

```
L4+ 组件 (绝对禁止):
├── sage-middleware       # ❌ 中间件层
├── isage-vdb / SageVDB   # ❌ 向量数据库
├── isage-neuromem        # ❌ 内存系统
├── isage-refiner         # ❌ 上下文压缩
├── FastAPI / uvicorn     # ❌ 网络服务
├── Redis / RocksDB       # ❌ 外部存储
└── vLLM / LMDeploy       # ❌ 推理引擎
```

**原则**: RAG 库提供纯算法实现，不依赖运行时服务。向量存储、内存管理等应在 L4 middleware 层组合。

## 与 SAGE 主仓库的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                    SAGE 主仓库 (sage.libs.rag)                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Interface Layer                         │  │
│  │  • DocumentLoader (ABC)    • TextChunker (ABC)            │  │
│  │  • Retriever (ABC)         • Reranker (ABC)               │  │
│  │  • QueryRewriter (ABC)     • RAGPipeline (ABC)            │  │
│  │  • Document, Chunk, RetrievalResult (数据类型)             │  │
│  │  • create_loader(), create_retriever() (工厂函数)          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▲                                   │
│                              │ 注册                              │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                    isage-rag (独立 PyPI 包)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 Implementation Layer                       │  │
│  │  • TextLoader, PDFLoader, DocxLoader (具体加载器)          │  │
│  │  • CharacterSplitter, TokenSplitter (具体分块器)           │  │
│  │  • DenseRetriever, BM25Retriever (具体检索器)              │  │
│  │  • CrossEncoderReranker (具体重排器)                       │  │
│  │  • HyDERewriter, MultiQueryRewriter (查询重写器)           │  │
│  │  • _register.py (自动注册到 SAGE 工厂)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 自动注册机制

```python
# sage_libs/sage_rag/_register.py
from sage.libs.rag import register_loader, register_chunker, register_retriever

from .loaders import TextLoader, PDFLoader, DocxLoader
from .chunkers import CharacterSplitter, TokenSplitter
from .retrievers import DenseRetriever, BM25Retriever

# 注册到 SAGE 工厂
register_loader("text", TextLoader)
register_loader("pdf", PDFLoader)
register_loader("docx", DocxLoader)

register_chunker("character", CharacterSplitter)
register_chunker("token", TokenSplitter)

register_retriever("dense", DenseRetriever)
register_retriever("bm25", BM25Retriever)
```

## 功能模块

### 1. Document Loaders (文档加载器)

```python
from sage.libs.rag import create_loader, Document

# 通过工厂创建（推荐）
loader = create_loader("pdf")
doc = loader.load("/path/to/document.pdf")

# 批量加载
docs = loader.load_batch(["/path/1.pdf", "/path/2.pdf"])

# 直接导入实现
from sage_libs.sage_rag.loaders import PDFLoader
loader = PDFLoader(extract_images=True)
```

**支持的格式**:

- `text`: `.txt`, `.md`, `.json`, `.yaml`
- `pdf`: `.pdf` (支持 OCR)
- `docx`: `.docx`, `.doc`
- `html`: `.html`, `.htm`, URL
- `csv`: `.csv`, `.tsv`

### 2. Text Chunkers (文本分块器)

```python
from sage.libs.rag import create_chunker, Chunk

# 字符分块
chunker = create_chunker("character", chunk_size=1000, overlap=100)
chunks = chunker.chunk(text)

# Token 分块（使用 tokenizer）
chunker = create_chunker("token", chunk_size=512, tokenizer="gpt2")
chunks = chunker.chunk_document(document)

# 语义分块
chunker = create_chunker("semantic", model="sentence-transformers/all-MiniLM-L6-v2")
```

### 3. Retrievers (检索器)

```python
from sage.libs.rag import create_retriever, RetrievalResult

# Dense Retriever (向量检索)
retriever = create_retriever("dense",
    embedding_model="BAAI/bge-small-zh-v1.5",
    index_path="/path/to/index"
)

# BM25 Retriever (关键词检索)
retriever = create_retriever("bm25", k1=1.2, b=0.75)

# Hybrid Retriever (混合检索)
retriever = create_retriever("hybrid",
    dense_weight=0.7,
    sparse_weight=0.3
)

# 检索
results: list[RetrievalResult] = retriever.retrieve("查询问题", top_k=10)
```

### 4. Rerankers (重排器)

```python
from sage.libs.rag import create_reranker

# Cross-Encoder 重排
reranker = create_reranker("cross_encoder",
    model="BAAI/bge-reranker-base"
)

# 重排结果
reranked = reranker.rerank(query, results, top_k=5)
```

### 5. Query Rewriters (查询重写器)

```python
from sage.libs.rag import create_query_rewriter

# HyDE (假设文档嵌入)
rewriter = create_query_rewriter("hyde", llm_client=client)
expanded_query = rewriter.rewrite("原始查询")

# Multi-Query (多查询扩展)
rewriter = create_query_rewriter("multi_query", num_queries=3)
queries = rewriter.expand("原始查询")
```

## 目录结构

```
sage-rag/                           # 独立仓库根目录
├── pyproject.toml                  # 包配置 (name = "isage-rag")
├── README.md
├── COPILOT_INSTRUCTIONS.md         # 本文件
├── LICENSE
├── src/
│   └── sage_libs/                  # 命名空间包
│       └── sage_rag/
│           ├── __init__.py         # 主入口，导出所有实现
│           ├── _version.py         # 版本信息
│           ├── _register.py        # 自动注册到 SAGE 工厂
│           ├── loaders/            # 文档加载器实现
│           │   ├── __init__.py
│           │   ├── text.py
│           │   ├── pdf.py
│           │   ├── docx.py
│           │   ├── html.py
│           │   └── csv.py
│           ├── chunkers/           # 文本分块器实现
│           │   ├── __init__.py
│           │   ├── character.py
│           │   ├── token.py
│           │   ├── sentence.py
│           │   └── semantic.py
│           ├── retrievers/         # 检索器实现
│           │   ├── __init__.py
│           │   ├── dense.py
│           │   ├── bm25.py
│           │   └── hybrid.py
│           ├── rerankers/          # 重排器实现
│           │   ├── __init__.py
│           │   └── cross_encoder.py
│           └── rewriters/          # 查询重写器实现
│               ├── __init__.py
│               ├── hyde.py
│               └── multi_query.py
├── tests/
│   ├── conftest.py
│   ├── test_loaders.py
│   ├── test_chunkers.py
│   ├── test_retrievers.py
│   └── test_integration.py
└── examples/
    ├── simple_rag.py
    ├── hybrid_retrieval.py
    └── document_processing.py
```

## 常见问题修复指南

### 1. 导入错误

```python
# ❌ 错误：直接从 sage.libs.rag 导入实现
from sage.libs.rag import DenseRetriever  # ImportError

# ✅ 正确：从独立包导入实现
from sage_libs.sage_rag.retrievers import DenseRetriever

# ✅ 正确：通过工厂创建（推荐）
from sage.libs.rag import create_retriever
retriever = create_retriever("dense", ...)
```

### 2. 实现未注册

```python
# ❌ 错误：忘记安装独立包
from sage.libs.rag import create_loader
loader = create_loader("pdf")  # RAGRegistryError: 'pdf' not registered

# ✅ 修复：安装独立包
# pip install isage-rag
```

### 3. 向量存储依赖

```python
# ❌ 错误：在 RAG 库中直接使用向量数据库
from sage_libs.sage_rag.retrievers import DenseRetriever
from sagevdb import SageVDB  # ❌ L3 不应依赖 L4

# ✅ 正确：检索器接受抽象索引接口
class DenseRetriever:
    def __init__(self, index: VectorIndex):  # 抽象接口
        self.index = index

# ✅ 正确：在 L4 middleware 中组合
from sage.middleware.components.sage_db import SageVDB
from sage_libs.sage_rag.retrievers import DenseRetriever

index = SageVDB(dimension=768)
retriever = DenseRetriever(index=index)  # 在 middleware 层组合
```

### 4. LLM 调用问题

```python
# ❌ 错误：RAG 库内部创建 LLM 客户端
class HyDERewriter:
    def __init__(self):
        from sage.llm import UnifiedInferenceClient
        self.client = UnifiedInferenceClient.create()  # ❌ 隐式依赖

# ✅ 正确：通过依赖注入
class HyDERewriter:
    def __init__(self, llm_client: LLMClient):  # 接口类型
        self.client = llm_client
```

### 5. 版本冲突

```bash
# 检查版本兼容性
pip show isage-rag isage-libs

# 升级到兼容版本
pip install "isage-rag>=0.1.0,<0.2.0"
```

## 关键设计原则

### 1. 纯算法实现

RAG 库只提供算法实现，不包含：

- 网络服务 (HTTP API)
- 持久化存储 (数据库连接)
- 进程管理 (后台任务)
- 外部服务客户端

### 2. 依赖注入

所有外部依赖通过构造函数注入：

```python
class DenseRetriever(Retriever):
    def __init__(
        self,
        embedding_fn: Callable[[str], list[float]],  # 注入 embedding 函数
        index: VectorIndex,  # 注入向量索引
    ):
        self.embedding_fn = embedding_fn
        self.index = index
```

### 3. 接口隔离

每个组件遵循单一职责：

- `DocumentLoader`: 只负责加载文档
- `TextChunker`: 只负责分块
- `Retriever`: 只负责检索
- `Reranker`: 只负责重排

### 4. 无 Fallback 原则

```python
# ❌ 错误：静默 fallback
def load(self, path):
    try:
        return self._load_pdf(path)
    except ImportError:
        return self._load_text(path)  # 静默降级

# ✅ 正确：明确失败
def load(self, path):
    if not HAS_PYPDF:
        raise ImportError(
            "PDF loading requires pypdf. Install with: pip install isage-rag[pdf]"
        )
    return self._load_pdf(path)
```

### 5. 类型安全

所有公开 API 使用类型注解：

```python
def retrieve(
    self,
    query: str,
    top_k: int = 10,
    filter_fn: Optional[Callable[[Document], bool]] = None,
) -> list[RetrievalResult]:
    ...
```

## 测试规范

```bash
# 运行单元测试
pytest tests/ -v

# 运行集成测试（需要模型）
pytest tests/test_integration.py -v --run-integration

# 检查覆盖率
pytest tests/ --cov=sage_libs.sage_rag --cov-report=html
```

## 发布流程

```bash
# 使用 sage-pypi-publisher
cd /path/to/sage-pypi-publisher
./publish.sh sage-rag --auto-bump patch

# 或手动指定版本
./publish.sh sage-rag --version 0.1.0.1
```
