# sage-libs 接口层架构 - 正确理解

## 🎯 核心理解：接口层 vs 实现层分离

### ❌ 我之前的错误理解

我之前认为：

- 外迁后只需要 **单文件兼容层**（`agentic.py`, `finetune.py`）
- 删除所有本地代码，直接 `from isage_agentic import *`

### ✅ 正确的架构模式

**SAGE 采用的是"接口/实现分离"模式**：

```
sage-libs (本地)                      独立包 (PyPI)
├── anns/                            isage-anns
│   ├── interface/                   ├── implementations/
│   │   ├── base.py        ←────────┤   ├── faiss_hnsw.py
│   │   └── factory.py     (注册)   │   ├── vsag_hnsw.py
│   └── __init__.py                  │   └── diskann.py
│                                    └── __init__.py (register all)
```

**关键点**：

1. **接口定义** 保留在 `sage-libs/interface/`（`base.py`, `factory.py`）
1. **具体实现** 在独立包 `isage-anns`（`implementations/`）
1. **注册机制** 在接口层（`factory.py`），实现自动注册

## 📊 各模块的接口层分析

### 已完成的接口层（需要保留）

| 模块    | 接口层位置                  | 实现位置     | 状态          |
| ------- | --------------------------- | ------------ | ------------- |
| `anns/` | `sage-libs/anns/interface/` | `isage-anns` | ✅ 已有接口层 |
| `amms/` | `sage-libs/amms/interface/` | `isage-amms` | ✅ 已有接口层 |

### 需要创建的接口层

| 模块        | 接口层位置                      | 实现位置                | 状态          |
| ----------- | ------------------------------- | ----------------------- | ------------- |
| `agentic/`  | `sage-libs/agentic/interface/`  | `isage-agentic`         | 🔄 你正在创建 |
| `finetune/` | `sage-libs/finetune/interface/` | `isage-finetune`        | 🔄 你正在创建 |
| `sias/`     | `sage-libs/sias/interface/`     | `isage-sias` (future)   | 🔄 你正在创建 |
| `intent/`   | `sage-libs/intent/interface/`   | `isage-intent` (future) | 🔄 你正在创建 |

### RAG 的情况（特殊）

**当前状态**：

```
sage-libs/rag/
├── document_loaders.py    # 完整实现（200+ 行）
├── chunk.py               # 完整实现（120 行）
└── types.py               # 完整实现（150+ 行）
```

**问题**：RAG 没有"接口/实现"分离，而是完整实现都在 sage-libs 中！

**应该做**：

- **方案 A**：外迁 RAG，创建接口层（与 agentic/anns 保持一致）
- **方案 B**：保留 RAG 完整实现（但与其他模块不一致）

## 🏗️ 正确的接口层架构

### ANNS 示例（标准模式）

**sage-libs 接口层**：

```python
# packages/sage-libs/src/sage/libs/anns/interface/base.py
class AnnIndex(ABC):
    """Minimal ANN interface to standardize build/insert/search flows."""

    @abstractmethod
    def setup(self, dtype: str, max_points: int, dim: int) -> None:
        """Initialize the index with type, capacity, and dimension."""

    @abstractmethod
    def search(self, queries: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        """Search top-k nearest neighbors."""

# packages/sage-libs/src/sage/libs/anns/interface/factory.py
_REGISTRY: dict[str, type[AnnIndex]] = {}

def register(name: str, cls: type[AnnIndex]) -> None:
    """Register an ANN implementation."""
    _REGISTRY[name] = cls

def create(name: str, **kwargs) -> AnnIndex:
    """Create an ANN instance by name."""
    return _REGISTRY[name](**kwargs)
```

**isage-anns 实现层**：

```python
# isage-anns/src/isage_anns/implementations/faiss_hnsw.py
from sage.libs.anns.interface import AnnIndex, register

class FaissHNSW(AnnIndex):
    def setup(self, dtype: str, max_points: int, dim: int) -> None:
        # 具体实现
        pass

    def search(self, queries: np.ndarray, k: int) -> tuple:
        # 具体实现
        pass

# 自动注册
register("faiss_hnsw", FaissHNSW)
```

### Agentic 应该采用的模式

**sage-libs 接口层**（你正在创建）：

```python
# packages/sage-libs/src/sage/libs/agentic/interface/base.py
class AgentRuntime(ABC):
    """Agent runtime interface."""

    @abstractmethod
    def execute(self, task: str) -> str:
        """Execute a task."""

class PlanningStrategy(ABC):
    """Planning strategy interface."""

    @abstractmethod
    def plan(self, goal: str) -> list[str]:
        """Generate a plan."""

# packages/sage-libs/src/sage/libs/agentic/interface/factory.py
_RUNTIME_REGISTRY: dict[str, type[AgentRuntime]] = {}
_PLANNING_REGISTRY: dict[str, type[PlanningStrategy]] = {}

def register_runtime(name: str, cls: type[AgentRuntime]) -> None:
    _RUNTIME_REGISTRY[name] = cls

def create_runtime(name: str, **kwargs) -> AgentRuntime:
    return _RUNTIME_REGISTRY[name](**kwargs)
```

**isage-agentic 实现层**：

```python
# isage-agentic/src/isage_agentic/agents/react_agent.py
from sage.libs.agentic.interface import AgentRuntime, register_runtime

class ReActAgent(AgentRuntime):
    def execute(self, task: str) -> str:
        # 具体实现
        pass

# 自动注册
register_runtime("react", ReActAgent)
```

## 📋 正确的清理方案（修正版）

### ❌ 删除我之前建议的脚本

之前的 `cleanup_externalized_modules.sh` 是错误的！它会删除必要的接口层。

### ✅ 正确的目录结构

```
packages/sage-libs/src/sage/libs/
│
├── # 已外迁模块（保留接口层）
├── anns/
│   ├── interface/          # ✅ 保留（接口定义）
│   │   ├── __init__.py
│   │   ├── base.py         # AnnIndex, AnnIndexMeta
│   │   └── factory.py      # register, create
│   └── __init__.py         # 重导出接口 + 发出 deprecation warning
│
├── amms/
│   ├── interface/          # ✅ 保留（接口定义）
│   │   ├── __init__.py
│   │   ├── base.py         # AmmIndex
│   │   └── factory.py      # register, create
│   └── __init__.py
│
├── agentic/                # 🔄 你正在创建
│   ├── interface/          # ✅ 新建（接口定义）
│   │   ├── __init__.py
│   │   ├── base.py         # AgentRuntime, PlanningStrategy
│   │   └── factory.py      # register, create
│   └── __init__.py
│
├── finetune/               # 🔄 你正在创建
│   ├── interface/          # ✅ 新建（接口定义）
│   │   ├── __init__.py
│   │   ├── base.py         # FineTuner, TrainingConfig
│   │   └── factory.py      # register, create
│   └── __init__.py
│
├── # RAG 模块（需要重构）
├── rag/
│   ├── interface/          # ❓ 需要创建接口层
│   │   ├── base.py         # DocumentLoader, Chunker, RAGPipeline
│   │   └── factory.py      # register, create
│   ├── document_loaders.py # → 移到 isage-rag
│   ├── chunk.py            # → 移到 isage-rag
│   └── types.py            # → 移到 isage-rag (或保留在接口层)
│
└── # 完整实现的模块（保留）
    ├── foundation/         # ✅ 保留（基础工具）
    ├── dataops/           # ✅ 保留
    ├── safety/            # ✅ 保留
    ├── privacy/           # ✅ 保留
    └── integrations/      # ✅ 保留
```

## 🎯 RAG 的正确处理方式

### 选项 1：创建 RAG 接口层（推荐，与其他模块一致）

**接口层**（sage-libs）：

```python
# packages/sage-libs/src/sage/libs/rag/interface/base.py
class DocumentLoader(ABC):
    @abstractmethod
    def load(self, path: str) -> list[str]:
        """Load documents."""

class Chunker(ABC):
    @abstractmethod
    def split(self, text: str) -> list[str]:
        """Split text into chunks."""

# packages/sage-libs/src/sage/libs/rag/interface/factory.py
def register_loader(name: str, cls: type[DocumentLoader]) -> None:
    pass

def create_loader(name: str, **kwargs) -> DocumentLoader:
    pass
```

**实现层**（isage-rag）：

```python
# isage-rag/src/sagerag/loaders/pdf.py
from sage.libs.rag.interface import DocumentLoader, register_loader

class PDFLoader(DocumentLoader):
    def load(self, path: str) -> list[str]:
        # 具体实现
        pass

register_loader("pdf", PDFLoader)
```

### 选项 2：保留 RAG 完整实现（简单但不一致）

保持当前的 `document_loaders.py`, `chunk.py` 在 sage-libs 中。

## 💡 关键原则

1. **接口层保留在 sage-libs**：定义抽象基类、注册机制
1. **实现层在独立包**：具体算法、具体实现
1. **SAGE 通过接口使用**：`from sage.libs.anns.interface import create`
1. **独立包自动注册**：`from isage_anns import *` 时自动注册所有实现

## ❓ 你的决策

1. **Agentic/Finetune 接口层**：你已经创建了目录，需要我帮忙设计接口吗？
1. **RAG 处理方式**：
   - A. 创建接口层 + 外迁实现（与其他模块一致）✅ 推荐
   - B. 保留完整实现（简单但不一致）
1. **其他模块** (dataops/safety)：是否也需要接口层？

请告诉我你的决策，我可以帮你设计接口层的具体代码！
