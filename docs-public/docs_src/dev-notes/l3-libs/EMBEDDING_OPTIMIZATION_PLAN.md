# Embedding 管理优化方案

**Date**: 2024-09-20\
**Author**: SAGE Team\
**Summary**: Embedding 优化计划

______________________________________________________________________

## 📋 当前状态分析

### 现有架构

```
packages/sage-middleware/src/sage/middleware/utils/embedding/
├── embedding_api.py        # 工厂函数 apply_embedding_model()
├── embedding_model.py      # EmbeddingModel 主类
├── hf.py                   # HuggingFace wrapper
├── openai.py               # OpenAI wrapper
├── mockembedder.py         # Mock wrapper
├── jina.py, zhipu.py, ...  # 其他 provider wrappers
└── README.md
```

### 现有问题

#### 1. **重复实现** - sage chat 自己实现了 HashingEmbedder

```python
# packages/sage-tools/src/sage/tools/cli/commands/chat.py:104

class HashingEmbedder:
    """Lightweight embedding that hashes tokens into a fixed-length vector."""

    def __init__(self, dim: int = DEFAULT_FIXED_DIM) -> None:
        self._dim = max(64, int(dim))

    def embed(self, text: str) -> List[float]:
        # 实现哈希embedding...
```

**问题**: 这个应该统一到 middleware 的 embedding 模块中。

______________________________________________________________________

#### 2. **不一致的接口** - build_embedder 逻辑分散

```python
# packages/sage-tools/src/sage/tools/cli/commands/chat.py:222

def build_embedder(config: Dict[str, object]) -> Any:
    method = str(config.get("method", DEFAULT_EMBEDDING_METHOD))
    params = dict(config.get("params", {}))

    if method == "hash":
        return HashingEmbedder(dim)  # ← 特殊处理

    if method == "mockembedder" and "fixed_dim" not in params:
        params["fixed_dim"] = DEFAULT_FIXED_DIM

    embedder = EmbeddingModel(method=method, **params)  # ← 其他走标准接口
    return embedder
```

**问题**:

- `hash` 方法需要特殊处理
- 默认参数逻辑分散
- 类型不统一 (`HashingEmbedder` vs `EmbeddingModel`)

______________________________________________________________________

#### 3. **缺少模型发现能力** - 用户不知道有哪些模型可用

```python
# 当前没有这些功能：
# - list_embedding_models()
# - get_model_info(model_name)
# - check_model_availability(model_name)
```

**用户痛点**:

- 不知道支持哪些 embedding 方法
- 不知道某个模型是否需要 API Key
- 不知道模型是否已缓存到本地
- 不知道模型的维度信息

______________________________________________________________________

#### 4. **硬编码的模型信息** - dimension_mapping 不灵活

```python
# packages/sage-middleware/src/sage/middleware/utils/embedding/embedding_model.py:87

dimension_mapping = {
    "mistral_embed": 1024,
    "embed-multilingual-v3.0": 1024,
    "BAAI/bge-m3": 1024,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "mockembedder": 128,
}
```

**问题**:

- 新模型需要手动添加
- 无法动态查询 HuggingFace 模型的维度
- 错误提示不友好：`<UNK> embedding <UNK>{model_name}`

______________________________________________________________________

#### 5. **缺少统一的抽象层** - 每个 wrapper 接口不一致

```python
# hf.py
def hf_embed_sync(text: str, tokenizer, embed_model) -> list[float]:
    ...

# openai.py  
def openai_embed_sync(text: str, model: str, api_key: str, base_url: str) -> list[float]:
    ...

# mockembedder.py
class MockTextEmbedder:
    def encode(self, text: str) -> list[float]:
        ...
```

**问题**: 参数传递方式不一致，难以扩展。

______________________________________________________________________

## 🎯 优化目标

### 目标 1: 统一接口抽象

所有 embedding 方法提供一致的接口：

- `embed(text: str) -> List[float]` - 单文本 embedding
- `embed_batch(texts: List[str]) -> List[List[float]]` - 批量 embedding
- `get_dim() -> int` - 获取维度
- `method_name` - 获取方法名

### 目标 2: 模型注册与发现

提供统一的模型管理：

- `list_embedding_models()` - 列出所有可用模型
- `get_embedding_model(name, **kwargs)` - 获取模型实例
- `check_model_status(name)` - 检查模型状态（需要 API Key / 已缓存 / 可用）

### 目标 3: 清晰的分层架构

```
┌─────────────────────────────────────────────────────┐
│  Application Layer (sage chat, pipeline builder)    │
│  - 使用 get_embedding_model() 获取模型               │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Embedding Manager (NEW)                            │
│  - EmbeddingRegistry: 模型注册表                     │
│  - EmbeddingFactory: 创建模型实例                    │
│  - list_models(), get_model(), check_status()       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Base Wrapper (NEW)                                 │
│  - BaseEmbedding: 抽象基类                           │
│  - 统一接口: embed(), embed_batch(), get_dim()      │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Provider Wrappers (REFACTORED)                     │
│  - HFEmbedding, OpenAIEmbedding, ...                │
│  - 继承 BaseEmbedding                                │
└─────────────────────────────────────────────────────┘
```

______________________________________________________________________

## 🚀 优化方案

### Phase 1: 创建抽象基类和统一接口 ✅

**文件**: `packages/sage-middleware/src/sage/middleware/utils/embedding/base.py`

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class BaseEmbedding(ABC):
    """所有 Embedding 模型的抽象基类"""

    def __init__(self, **kwargs):
        self.config = kwargs

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """单文本 embedding"""
        pass

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量 embedding（默认实现：逐个调用）"""
        return [self.embed(text) for text in texts]

    @abstractmethod
    def get_dim(self) -> int:
        """获取 embedding 维度"""
        pass

    @property
    @abstractmethod
    def method_name(self) -> str:
        """返回方法名（如 'hf', 'openai'）"""
        pass

    @classmethod
    def get_model_info(cls) -> Dict[str, Any]:
        """返回模型元信息（子类可选实现）"""
        return {
            "method": cls.__name__,
            "requires_api_key": False,
            "requires_model_download": False,
            "default_dimension": None,
        }
```

______________________________________________________________________

### Phase 2: 模型注册表 ✅

**文件**: `packages/sage-middleware/src/sage/middleware/utils/embedding/registry.py`

```python
from typing import Dict, List, Type, Optional, Any
from dataclasses import dataclass
from enum import Enum

class ModelStatus(Enum):
    """模型可用状态"""
    AVAILABLE = "available"           # 直接可用
    NEEDS_API_KEY = "needs_api_key"   # 需要 API Key
    NEEDS_DOWNLOAD = "needs_download" # 需要下载模型
    CACHED = "cached"                 # 已缓存到本地
    UNAVAILABLE = "unavailable"       # 不可用


@dataclass
class ModelInfo:
    """模型元信息"""
    method: str                      # 方法名：hf, openai, mockembedder, hash
    display_name: str                # 显示名称
    description: str                 # 描述
    requires_api_key: bool           # 是否需要 API Key
    requires_model_download: bool    # 是否需要下载模型
    default_dimension: Optional[int] # 默认维度
    example_models: List[str]        # 示例模型名称
    wrapper_class: Type              # Wrapper 类


class EmbeddingRegistry:
    """Embedding 模型注册表"""

    _registry: Dict[str, ModelInfo] = {}

    @classmethod
    def register(
        cls,
        method: str,
        display_name: str,
        description: str,
        wrapper_class: Type,
        requires_api_key: bool = False,
        requires_model_download: bool = False,
        default_dimension: Optional[int] = None,
        example_models: List[str] = None,
    ) -> None:
        """注册 embedding 方法"""
        cls._registry[method] = ModelInfo(
            method=method,
            display_name=display_name,
            description=description,
            requires_api_key=requires_api_key,
            requires_model_download=requires_model_download,
            default_dimension=default_dimension,
            example_models=example_models or [],
            wrapper_class=wrapper_class,
        )

    @classmethod
    def list_methods(cls) -> List[str]:
        """列出所有已注册的方法"""
        return list(cls._registry.keys())

    @classmethod
    def get_model_info(cls, method: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        return cls._registry.get(method)

    @classmethod
    def check_status(cls, method: str, **kwargs) -> ModelStatus:
        """检查模型状态"""
        info = cls.get_model_info(method)
        if not info:
            return ModelStatus.UNAVAILABLE

        # API Key 检查
        if info.requires_api_key:
            api_key = kwargs.get("api_key") or os.getenv(f"{method.upper()}_API_KEY")
            if not api_key:
                return ModelStatus.NEEDS_API_KEY

        # 本地模型缓存检查
        if info.requires_model_download:
            model_name = kwargs.get("model")
            if model_name and is_model_cached(model_name):
                return ModelStatus.CACHED
            return ModelStatus.NEEDS_DOWNLOAD

        return ModelStatus.AVAILABLE

    @classmethod
    def get_wrapper_class(cls, method: str) -> Optional[Type]:
        """获取 Wrapper 类"""
        info = cls.get_model_info(method)
        return info.wrapper_class if info else None


def is_model_cached(model_name: str) -> bool:
    """检查 HuggingFace 模型是否已缓存"""
    from pathlib import Path
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    # 简化检查：存在 models-- 开头的目录
    model_slug = model_name.replace("/", "--")
    cached = any(cache_dir.glob(f"models--{model_slug}*"))
    return cached
```

______________________________________________________________________

### Phase 3: Embedding 工厂 ✅

**文件**: `packages/sage-middleware/src/sage/middleware/utils/embedding/factory.py`

```python
import os
from typing import Optional, Dict, Any
from .base import BaseEmbedding
from .registry import EmbeddingRegistry, ModelStatus


class EmbeddingFactory:
    """Embedding 模型工厂"""

    @staticmethod
    def create(method: str, **kwargs) -> BaseEmbedding:
        """
        创建 Embedding 实例

        Args:
            method: embedding 方法名 (hf, openai, hash, mockembedder, ...)
            **kwargs: 方法特定参数
                - model: 模型名称 (hf, openai 等需要)
                - api_key: API 密钥 (openai, jina 等需要)
                - base_url: API 端点 (openai 可选)
                - fixed_dim: 固定维度 (mockembedder, hash 需要)

        Returns:
            BaseEmbedding 实例

        Raises:
            ValueError: 不支持的方法或缺少必要参数
            RuntimeError: 模型不可用

        Examples:
            >>> # HuggingFace 模型
            >>> emb = EmbeddingFactory.create(
            ...     method="hf",
            ...     model="BAAI/bge-small-zh-v1.5"
            ... )

            >>> # OpenAI API
            >>> emb = EmbeddingFactory.create(
            ...     method="openai",
            ...     model="text-embedding-3-small",
            ...     api_key=os.getenv("OPENAI_API_KEY")
            ... )

            >>> # Mock embedder (测试)
            >>> emb = EmbeddingFactory.create(
            ...     method="mockembedder",
            ...     fixed_dim=384
            ... )
        """
        # 获取注册信息
        wrapper_class = EmbeddingRegistry.get_wrapper_class(method)
        if not wrapper_class:
            available = ", ".join(EmbeddingRegistry.list_methods())
            raise ValueError(
                f"不支持的 embedding 方法: {method}\n"
                f"可用方法: {available}"
            )

        # 检查状态
        status = EmbeddingRegistry.check_status(method, **kwargs)
        if status == ModelStatus.NEEDS_API_KEY:
            raise RuntimeError(
                f"{method} 方法需要 API Key。\n"
                f"请设置环境变量 {method.upper()}_API_KEY 或传递 api_key 参数。"
            )

        # 创建实例
        try:
            return wrapper_class(**kwargs)
        except Exception as e:
            raise RuntimeError(
                f"创建 {method} embedding 实例失败: {e}"
            ) from e

    @staticmethod
    def list_models() -> Dict[str, Dict[str, Any]]:
        """
        列出所有可用的 embedding 方法

        Returns:
            Dict[method_name, model_info]
        """
        result = {}
        for method in EmbeddingRegistry.list_methods():
            info = EmbeddingRegistry.get_model_info(method)
            if info:
                result[method] = {
                    "display_name": info.display_name,
                    "description": info.description,
                    "requires_api_key": info.requires_api_key,
                    "requires_download": info.requires_model_download,
                    "default_dimension": info.default_dimension,
                    "examples": info.example_models,
                }
        return result

    @staticmethod
    def check_availability(method: str, **kwargs) -> Dict[str, Any]:
        """
        检查特定方法的可用性

        Returns:
            {
                "status": "available|needs_api_key|needs_download|unavailable",
                "message": "详细说明",
                "action": "建议操作"
            }
        """
        status = EmbeddingRegistry.check_status(method, **kwargs)

        messages = {
            ModelStatus.AVAILABLE: ("✅ 可用", "可以直接使用"),
            ModelStatus.CACHED: ("✅ 已缓存", "模型已下载到本地"),
            ModelStatus.NEEDS_API_KEY: (
                "⚠️ 需要 API Key",
                f"设置环境变量 {method.upper()}_API_KEY"
            ),
            ModelStatus.NEEDS_DOWNLOAD: (
                "⚠️ 需要下载模型",
                f"首次使用将从 HuggingFace 下载模型: {kwargs.get('model', '?')}"
            ),
            ModelStatus.UNAVAILABLE: ("❌ 不可用", "方法未注册"),
        }

        message, action = messages.get(status, ("❓ 未知", ""))

        return {
            "status": status.value,
            "message": message,
            "action": action,
        }
```

______________________________________________________________________

### Phase 4: 重构 Wrapper 类 ✅

**示例**: `packages/sage-middleware/src/sage/middleware/utils/embedding/wrappers/hash_wrapper.py`

```python
import hashlib
import re
from typing import List
from ..base import BaseEmbedding


class HashEmbedding(BaseEmbedding):
    """基于哈希的轻量级 Embedding（用于快速测试）"""

    def __init__(self, dim: int = 384, **kwargs):
        super().__init__(dim=dim, **kwargs)
        self._dim = max(64, int(dim))

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

        # 归一化
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]

    def get_dim(self) -> int:
        return self._dim

    @property
    def method_name(self) -> str:
        return "hash"

    @classmethod
    def get_model_info(cls):
        return {
            "method": "hash",
            "requires_api_key": False,
            "requires_model_download": False,
            "default_dimension": 384,
        }
```

**示例**: `packages/sage-middleware/src/sage/middleware/utils/embedding/wrappers/hf_wrapper.py`

```python
from typing import List
from ..base import BaseEmbedding
from ..hf import hf_embed_sync  # 复用现有实现


class HFEmbedding(BaseEmbedding):
    """HuggingFace Embedding Wrapper"""

    def __init__(self, model: str, **kwargs):
        super().__init__(model=model, **kwargs)

        from transformers import AutoModel, AutoTokenizer

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model)
            self.embed_model = AutoModel.from_pretrained(
                model, trust_remote_code=True
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to load HuggingFace model '{model}': {e}"
            ) from e

        # 推断维度
        self._dim = self._infer_dimension()

    def embed(self, text: str) -> List[float]:
        return hf_embed_sync(text, self.tokenizer, self.embed_model)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """优化的批量 embedding"""
        # TODO: 实现真正的批量处理
        return [self.embed(text) for text in texts]

    def get_dim(self) -> int:
        return self._dim

    @property
    def method_name(self) -> str:
        return "hf"

    def _infer_dimension(self) -> int:
        """通过 embedding 一个示例文本推断维度"""
        try:
            sample = self.embed("test")
            return len(sample)
        except:
            return 768  # 默认维度

    @classmethod
    def get_model_info(cls):
        return {
            "method": "hf",
            "requires_api_key": False,
            "requires_model_download": True,
            "default_dimension": None,  # 动态推断
        }
```

______________________________________________________________________

### Phase 5: 注册所有 Wrapper ✅

**文件**: `packages/sage-middleware/src/sage/middleware/utils/embedding/__init__.py`

```python
from .base import BaseEmbedding
from .registry import EmbeddingRegistry, ModelStatus, ModelInfo
from .factory import EmbeddingFactory

# 导入所有 wrapper
from .wrappers.hash_wrapper import HashEmbedding
from .wrappers.mock_wrapper import MockEmbedding
from .wrappers.hf_wrapper import HFEmbedding
from .wrappers.openai_wrapper import OpenAIEmbedding
# ... 其他 wrappers

# 注册所有方法
def _register_all():
    """注册所有 embedding 方法"""

    EmbeddingRegistry.register(
        method="hash",
        display_name="Hash Embedding",
        description="轻量级哈希 embedding（测试用）",
        wrapper_class=HashEmbedding,
        default_dimension=384,
        example_models=["hash-384", "hash-768"],
    )

    EmbeddingRegistry.register(
        method="mockembedder",
        display_name="Mock Embedder",
        description="随机 embedding（测试用）",
        wrapper_class=MockEmbedding,
        default_dimension=128,
        example_models=["mock-128", "mock-384"],
    )

    EmbeddingRegistry.register(
        method="hf",
        display_name="HuggingFace Models",
        description="本地 Transformer 模型",
        wrapper_class=HFEmbedding,
        requires_model_download=True,
        example_models=[
            "BAAI/bge-small-zh-v1.5",
            "BAAI/bge-base-zh-v1.5",
            "sentence-transformers/all-MiniLM-L6-v2",
        ],
    )

    EmbeddingRegistry.register(
        method="openai",
        display_name="OpenAI Embedding API",
        description="OpenAI 官方或兼容 API",
        wrapper_class=OpenAIEmbedding,
        requires_api_key=True,
        example_models=[
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ],
    )

    # ... 注册其他方法

_register_all()

# 统一导出接口
def get_embedding_model(method: str, **kwargs) -> BaseEmbedding:
    """
    获取 Embedding 模型实例（推荐使用）

    Examples:
        >>> emb = get_embedding_model("hf", model="BAAI/bge-small-zh-v1.5")
        >>> vec = emb.embed("hello world")
        >>> dim = emb.get_dim()
    """
    return EmbeddingFactory.create(method, **kwargs)


def list_embedding_models():
    """列出所有可用的 embedding 方法"""
    return EmbeddingFactory.list_models()


def check_model_availability(method: str, **kwargs):
    """检查模型可用性"""
    return EmbeddingFactory.check_availability(method, **kwargs)


__all__ = [
    "BaseEmbedding",
    "EmbeddingRegistry",
    "EmbeddingFactory",
    "ModelStatus",
    "get_embedding_model",
    "list_embedding_models",
    "check_model_availability",
]
```

______________________________________________________________________

## 📝 使用示例

### 示例 1: Sage Chat 简化后的代码

```python
# packages/sage-tools/src/sage/tools/cli/commands/chat.py

from sage.common.components.sage_embedding import get_embedding_model

def build_embedder(config: Dict[str, object]) -> BaseEmbedding:
    """构建 embedder（简化版）"""
    method = str(config.get("method", "hash"))
    params = dict(config.get("params", {}))

    # 一行搞定，不需要特殊处理！
    return get_embedding_model(method, **params)
```

### 示例 2: 用户查询可用模型

```python
from sage.common.components.sage_embedding import list_embedding_models

models = list_embedding_models()
for method, info in models.items():
    print(f"{method}: {info['description']}")
    if info['requires_api_key']:
        print("  ⚠️ 需要 API Key")
    if info['examples']:
        print(f"  示例: {', '.join(info['examples'][:2])}")
```

输出：

```
hash: 轻量级哈希 embedding（测试用）
  示例: hash-384, hash-768

hf: 本地 Transformer 模型
  ⚠️ 需要下载模型
  示例: BAAI/bge-small-zh-v1.5, BAAI/bge-base-zh-v1.5

openai: OpenAI 官方或兼容 API
  ⚠️ 需要 API Key
  示例: text-embedding-3-small, text-embedding-3-large
```

### 示例 3: 检查模型状态

```python
from sage.common.components.sage_embedding import check_model_availability

# 检查 HuggingFace 模型
status = check_model_availability("hf", model="BAAI/bge-small-zh-v1.5")
print(status)
# {"status": "cached", "message": "✅ 已缓存", "action": "模型已下载到本地"}

# 检查 OpenAI（无 API Key）
status = check_model_availability("openai")
print(status)
# {"status": "needs_api_key", "message": "⚠️ 需要 API Key", "action": "设置环境变量 OPENAI_API_KEY"}
```

### 示例 4: CLI 命令

```bash
# 列出所有可用方法
sage embedding list

# 检查特定方法状态
sage embedding check hf --model BAAI/bge-small-zh-v1.5

# 测试 embedding
sage embedding test hf --model BAAI/bge-small-zh-v1.5 --text "测试文本"
```

______________________________________________________________________

## 🎯 迁移计划

### Step 1: 创建新架构（不破坏现有代码）✅

```
packages/sage-middleware/src/sage/middleware/utils/embedding/
├── base.py                 # NEW
├── registry.py             # NEW
├── factory.py              # NEW
├── wrappers/               # NEW
│   ├── __init__.py
│   ├── hash_wrapper.py     # 迁移 sage chat 的 HashingEmbedder
│   ├── mock_wrapper.py     # 迁移 mockembedder.py
│   ├── hf_wrapper.py       # 包装 hf.py
│   ├── openai_wrapper.py   # 包装 openai.py
│   └── ...
├── embedding_model.py      # KEEP (向后兼容)
├── embedding_api.py        # KEEP (向后兼容)
└── 现有 provider 文件       # KEEP (被 wrapper 调用)
```

### Step 2: 向后兼容层 ✅

```python
# embedding_model.py - 添加兼容层

class EmbeddingModel(BaseEmbedding):
    """向后兼容的 EmbeddingModel 类"""

    def __init__(self, method: str = "openai", **kwargs):
        # 内部使用新架构
        self._impl = get_embedding_model(method, **kwargs)

    def embed(self, text: str) -> list[float]:
        return self._impl.embed(text)

    def get_dim(self):
        return self._impl.get_dim()

    # ... 其他方法委托给 _impl
```

### Step 3: 逐步迁移 sage chat ✅

```python
# 阶段 1: 使用新接口，保持功能不变
from sage.common.components.sage_embedding import get_embedding_model

def build_embedder(config):
    return get_embedding_model(**config)

# 阶段 2: 删除 HashingEmbedder 类定义
# 阶段 3: 简化 ingest 命令参数处理
```

______________________________________________________________________

## ✅ 验收标准

### 功能完整性

- [ ] 所有现有 embedding 方法正常工作
- [ ] sage chat 功能不受影响
- [ ] 新增 `list_embedding_models()` API
- [ ] 新增 `check_model_availability()` API
- [ ] 统一的 `get_embedding_model()` 接口

### 代码质量

- [ ] 所有 wrapper 继承 `BaseEmbedding`
- [ ] 接口一致性：`embed()`, `embed_batch()`, `get_dim()`, `method_name`
- [ ] 完整的类型注解
- [ ] 详细的文档字符串

### 用户体验

- [ ] 清晰的错误提示（缺少 API Key、模型不存在等）
- [ ] CLI 命令支持模型发现
- [ ] README 更新使用示例

### 测试覆盖

- [ ] 单元测试覆盖所有 wrapper
- [ ] 集成测试覆盖 sage chat
- [ ] 向后兼容性测试

______________________________________________________________________

## 🤔 需要决策的问题

### Q1: 是否保留 `EmbeddingModel` 类？

**选项 A**: 完全废弃，只使用新架构

- ✅ 代码更清晰
- ❌ 破坏现有代码

**选项 B**: 作为向后兼容层保留（推荐）

- ✅ 平滑迁移
- ❌ 多一层抽象

**建议**: 选项 B，保留 `EmbeddingModel` 作为兼容层。

______________________________________________________________________

### Q2: dimension_mapping 如何处理？

**选项 A**: 硬编码在 Registry

```python
DIMENSION_MAPPING = {
    "text-embedding-3-small": 1536,
    "BAAI/bge-small-zh-v1.5": 512,
}
```

**选项 B**: 动态推断（推荐）

```python
def _infer_dimension(self):
    sample = self.embed("test")
    return len(sample)
```

**建议**: 选项 B + fallback 到硬编码表。

______________________________________________________________________

### Q3: 是否需要 EmbeddingManager？

**当前设计**: Factory + Registry（静态方法）

**Manager 设计**: 实例化的管理器

```python
manager = EmbeddingManager()
manager.register_model(...)
emb = manager.get_model(...)
```

**建议**: 当前的 Factory + Registry 已足够，暂不需要 Manager。

______________________________________________________________________

## 📊 工作量估算

| 任务                    | 工作量 | 优先级 |
| ----------------------- | ------ | ------ |
| 创建 base.py            | 1h     | P0     |
| 创建 registry.py        | 2h     | P0     |
| 创建 factory.py         | 2h     | P0     |
| 创建 hash_wrapper.py    | 1h     | P0     |
| 创建 mock_wrapper.py    | 1h     | P0     |
| 创建 hf_wrapper.py      | 2h     | P0     |
| 创建 openai_wrapper.py  | 1h     | P1     |
| 创建其他 wrappers (8个) | 8h     | P1     |
| 更新 __init__.py        | 1h     | P0     |
| 迁移 sage chat          | 2h     | P0     |
| 添加 CLI 命令           | 3h     | P2     |
| 编写单元测试            | 4h     | P1     |
| 更新文档                | 2h     | P1     |

**总计**: ~30 小时

**P0 (核心)**: ~12 小时 **P1 (重要)**: ~16 小时\
**P2 (增强)**: ~3 小时

______________________________________________________________________

## 🎓 总结

### 当前问题

1. ❌ HashingEmbedder 重复实现
1. ❌ 接口不统一
1. ❌ 缺少模型发现能力
1. ❌ 硬编码的模型信息
1. ❌ Wrapper 接口不一致

### 优化后

1. ✅ 统一的 `BaseEmbedding` 抽象
1. ✅ `EmbeddingRegistry` 模型注册表
1. ✅ `EmbeddingFactory` 统一创建接口
1. ✅ 所有 wrapper 继承 `BaseEmbedding`
1. ✅ `list_embedding_models()` 发现能力
1. ✅ `check_model_availability()` 状态检查
1. ✅ 向后兼容现有代码

### 核心 API

```python
# 简单直接的接口
from sage.common.components.sage_embedding import get_embedding_model

emb = get_embedding_model("hf", model="BAAI/bge-small-zh-v1.5")
vec = emb.embed("hello world")
```

______________________________________________________________________

**建议**: 先实现 P0 核心功能（~12h），验证可行性后再推进 P1/P2。
