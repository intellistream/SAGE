# Embedding 模块

SAGE 提供了统一的 Embedding 接口，支持多种嵌入方法将文本转换为向量表示。这些嵌入可用于语义搜索、聚类、分类、RAG 等任务。

## 架构概览

SAGE 提供三层 Embedding API：

| 层级           | API                      | 用途                               |
| -------------- | ------------------------ | ---------------------------------- |
| **统一客户端** | `UnifiedInferenceClient` | LLM + Embedding 混合场景（推荐）   |
| **工厂模式**   | `EmbeddingFactory`       | 本地模型或单一 Embedding 场景      |
| **服务模式**   | `EmbeddingService`       | Pipeline 集成，支持 setup/teardown |

______________________________________________________________________

## 快速开始

### 方式 1: UnifiedInferenceClient（推荐）

适用于需要同时使用 LLM 和 Embedding 的场景：

```python
from sage.llm import UnifiedInferenceClient

# 自动检测本地服务或使用云端 API
client = UnifiedInferenceClient.create_auto()

# 批量 Embedding
vectors = client.embed(["Hello, world.", "SAGE is awesome."])
print(f"Embedding dimension: {len(vectors[0])}")

# 同时支持 LLM 调用
response = client.chat([{"role": "user", "content": "What is SAGE?"}])
```

### 方式 2: EmbeddingFactory + EmbeddingClientAdapter

适用于只需要 Embedding，不需要 LLM 的场景：

```python
from sage.common.components.sage_embedding import (
    EmbeddingFactory,
    EmbeddingClientAdapter,
)

# 创建单文本 Embedding 接口
raw_embedder = EmbeddingFactory.create("hf", model="BAAI/bge-small-zh-v1.5")

# 单文本嵌入
vec = raw_embedder.embed("Hello, world.")
dim = raw_embedder.get_dim()
print(f"Dimension: {dim}")

# 转换为批量接口
client = EmbeddingClientAdapter(raw_embedder)
vectors = client.embed(["Text 1", "Text 2", "Text 3"])
```

______________________________________________________________________

## 支持的 Embedding 方法

使用 `list_embedding_models()` 查看所有可用方法：

```python
from sage.common.components.sage_embedding import list_embedding_models

for method, info in list_embedding_models().items():
    print(f"{method}: {info['description']}")
```

### 本地模型（无需 API Key）

| 方法           | 描述                           | 示例模型                                     |
| -------------- | ------------------------------ | -------------------------------------------- |
| `hash`         | 轻量级哈希 embedding（测试用） | `hash-384`, `hash-768`                       |
| `mockembedder` | 随机 embedding（单元测试用）   | `mock-128`, `mock-384`                       |
| `hf`           | HuggingFace 本地模型           | `BAAI/bge-small-zh-v1.5`, `all-MiniLM-L6-v2` |
| `ollama`       | Ollama 本地部署                | `nomic-embed-text`, `mxbai-embed-large`      |

### 云端 API（需要 API Key）

| 方法            | 描述                  | 示例模型                                           |
| --------------- | --------------------- | -------------------------------------------------- |
| `openai`        | OpenAI API            | `text-embedding-3-small`, `text-embedding-ada-002` |
| `jina`          | Jina AI 多语言        | `jina-embeddings-v3`                               |
| `zhipu`         | 智谱 AI（国内访问快） | `embedding-3`                                      |
| `cohere`        | Cohere 多语言         | `embed-multilingual-v3.0`                          |
| `siliconcloud`  | 硅基流动（国内）      | `netease-youdao/bce-embedding-base_v1`             |
| `bedrock`       | AWS Bedrock           | `amazon.titan-embed-text-v2:0`                     |
| `nvidia_openai` | NVIDIA NIM            | `nvidia/llama-3.2-nv-embedqa-1b-v1`                |

______________________________________________________________________

## 详细用法

### HuggingFace 本地模型

```python
from sage.common.components.sage_embedding import EmbeddingFactory, EmbeddingClientAdapter

# 创建 HuggingFace embedding（首次使用会自动下载模型）
embedder = EmbeddingFactory.create("hf", model="BAAI/bge-small-zh-v1.5")
client = EmbeddingClientAdapter(embedder)

# 批量嵌入
texts = ["什么是 SAGE?", "SAGE 是一个流式处理框架"]
vectors = client.embed(texts)
```

### OpenAI API

```python
from sage.common.components.sage_embedding import EmbeddingFactory, EmbeddingClientAdapter

# 使用环境变量 OPENAI_API_KEY
embedder = EmbeddingFactory.create(
    "openai",
    model="text-embedding-3-small",
)
client = EmbeddingClientAdapter(embedder)

vectors = client.embed(["Hello", "World"])
```

### Jina AI

```python
from sage.common.components.sage_embedding import EmbeddingFactory, EmbeddingClientAdapter

# 使用环境变量 JINA_API_KEY
embedder = EmbeddingFactory.create(
    "jina",
    model="jina-embeddings-v3",
)
client = EmbeddingClientAdapter(embedder)

vectors = client.embed(["Hello", "World"])
```

### 硅基流动 (SiliconCloud)

```python
from sage.common.components.sage_embedding import EmbeddingFactory, EmbeddingClientAdapter

# 使用环境变量 SILICONCLOUD_API_KEY
embedder = EmbeddingFactory.create(
    "siliconcloud",
    model="BAAI/bge-large-zh-v1.5",
)
client = EmbeddingClientAdapter(embedder)

vectors = client.embed(["你好", "世界"])
```

### Hash Embedding（测试用）

```python
from sage.common.components.sage_embedding import EmbeddingFactory, EmbeddingClientAdapter

# 轻量级，无需下载模型或 API Key
embedder = EmbeddingFactory.create("hash", dim=384)
client = EmbeddingClientAdapter(embedder)

# 确定性：相同文本总是得到相同向量
v1 = client.embed(["test"])
v2 = client.embed(["test"])
assert v1 == v2  # True
```

______________________________________________________________________

## 接口对比

### BaseEmbedding（单文本接口）

`EmbeddingFactory.create()` 返回的对象：

```python
embedder = EmbeddingFactory.create("hash", dim=64)

# 单文本嵌入
vec: list[float] = embedder.embed("hello")

# 获取维度
dim: int = embedder.get_dim()
```

### EmbeddingProtocol（批量接口）

通过 `EmbeddingClientAdapter` 适配后的接口：

```python
from sage.common.components.sage_embedding import EmbeddingClientAdapter

client = EmbeddingClientAdapter(embedder)

# 批量嵌入
vectors: list[list[float]] = client.embed(["hello", "world"])
```

⚠️ **注意**: 直接对 `EmbeddingFactory.create()` 返回值使用批量参数会报错：

```python
# ❌ 错误用法
embedder = EmbeddingFactory.create("hash", dim=64)
embedder.embed(texts=["a", "b"])  # TypeError: unexpected keyword argument 'texts'

# ✅ 正确用法
client = EmbeddingClientAdapter(embedder)
client.embed(["a", "b"])  # OK
```

______________________________________________________________________

## 检查模型可用性

```python
from sage.common.components.sage_embedding import check_model_availability

# 检查 HuggingFace 模型是否已下载
status = check_model_availability("hf", model="BAAI/bge-small-zh-v1.5")
print(status)
# {'status': 'cached', 'message': '✅ 已缓存', 'action': '...'}

# 检查 API 配置
status = check_model_availability("openai")
print(status)
# {'status': 'needs_api_key', 'message': '⚠️ 需要 API Key', 'action': '...'}
```

______________________________________________________________________

## 在 Pipeline 中使用

### EmbeddingService（推荐）

```python
from sage.kernel.api.local_environment import LocalStreamEnvironment
from sage.common.components.sage_embedding import EmbeddingService, EmbeddingServiceConfig

env = LocalStreamEnvironment("embedding_pipeline")

# 创建 Embedding 服务
service = EmbeddingService(EmbeddingServiceConfig(
    method="hf",
    model="BAAI/bge-small-zh-v1.5",
))

# 在 pipeline 中使用
stream = env.from_source(text_source).map(service)

env.execute()
```

______________________________________________________________________

## 启动 Embedding 服务器

SAGE 提供 OpenAI 兼容的 Embedding 服务器：

```bash
# 启动 Embedding 服务（端口 8090）
python -m sage.common.components.sage_embedding.embedding_server \
    --model BAAI/bge-m3 \
    --port 8090

# 或使用 sage llm serve 命令同时启动 LLM + Embedding
sage llm serve --with-embedding --embedding-model BAAI/bge-m3
```

然后使用 `UnifiedInferenceClient` 连接：

```python
# 推荐：使用 create() 工厂方法
client = UnifiedInferenceClient.create(
    control_plane_url="http://localhost:8090/v1",
    default_embedding_model="BAAI/bge-m3",
)
vectors = client.embed(["Hello", "World"])
```

______________________________________________________________________

## 环境变量配置

为安全使用 API 密钥，建议使用环境变量或 `.env` 文件：

```bash
# .env 文件
OPENAI_API_KEY=sk-xxx
JINA_API_KEY=jina_xxx
SILICONCLOUD_API_KEY=sk-xxx
ZHIPU_API_KEY=xxx
COHERE_API_KEY=xxx

# HuggingFace 镜像（中国用户）
HF_ENDPOINT=https://hf-mirror.com
```

______________________________________________________________________

## 配置参数说明

| 参数       | 描述                                    | 默认值   |
| ---------- | --------------------------------------- | -------- |
| `method`   | Embedding 方法（hf, openai, hash, ...） | 必需     |
| `model`    | 模型名称                                | 方法依赖 |
| `api_key`  | API 密钥（云端方法需要）                | 环境变量 |
| `dim`      | 嵌入维度（hash, mock 需要）             | 384      |
| `base_url` | 自定义 API 端点                         | 方法默认 |

______________________________________________________________________

## 最佳实践

1. **选择合适的 API 层级**:

   - 需要 LLM + Embedding → `UnifiedInferenceClient`
   - 只需 Embedding → `EmbeddingFactory` + `EmbeddingClientAdapter`
   - Pipeline 集成 → `EmbeddingService`

1. **本地 vs 云端**:

   - 开发测试用 `hash` 或 `mockembedder`
   - 生产环境推荐 HuggingFace 本地模型（数据隐私）
   - 高质量要求选择 OpenAI 或 Jina API

1. **批量处理**: 对于大量文本，使用批量接口可显著提高效率

1. **缓存嵌入**: 对于不变的文本，考虑缓存结果避免重复计算

1. **维度一致性**: 确保同一应用中使用相同维度的嵌入

______________________________________________________________________

## 迁移指南

如果你使用的是旧版 `sage.utils.embedding_methods` API，请按以下方式迁移：

```python
# 旧版 API (已弃用)
from sage.utils.embedding_methods.embedding_api import apply_embedding_model
model = apply_embedding_model("hf", model="BAAI/bge-small-zh-v1.5")

# 新版 API (推荐)
from sage.common.components.sage_embedding import EmbeddingFactory
model = EmbeddingFactory.create("hf", model="BAAI/bge-small-zh-v1.5")
```

旧版 API 仍可使用（向后兼容），但建议尽快迁移到新版 API。
