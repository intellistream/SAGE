# 我对架构的误解与纠正

## ❌ 我之前的错误理解

我误以为外迁模块应该：

1. **完全删除本地代码** → 只保留单文件兼容层（如 `agentic.py`）
1. **直接重导出** → `from isage_agentic import *`
1. **删除 interface/ 目录** → 认为接口也应该在外部包中

**这是完全错误的！**

## ✅ 正确的架构模式

SAGE 采用的是 **"接口/实现分离"** 模式：

### 核心原则

```
接口层（Interface Layer）
  ↓ 定义在 sage-libs
  ↓ 抽象基类 + 注册机制
  ↓
实现层（Implementation Layer）
  ↓ 在独立 PyPI 包（isage-*）
  ↓ 具体算法和实现
  ↓ 自动注册到接口层
```

### 具体示例：ANNS

**sage-libs 保留的接口层**：

```
packages/sage-libs/src/sage/libs/anns/
├── interface/                    # ✅ 保留（接口定义）
│   ├── __init__.py
│   ├── base.py                   # AnnIndex 抽象基类
│   └── factory.py                # register(), create() 工厂函数
└── __init__.py                   # 重导出接口
```

**isage-anns 独立包的实现层**：

```
isage-anns/src/isage_anns/
├── implementations/              # 具体实现
│   ├── faiss_hnsw.py            # 继承 AnnIndex
│   ├── vsag_hnsw.py             # 继承 AnnIndex
│   └── diskann.py               # 继承 AnnIndex
└── __init__.py                   # 导入时自动注册所有实现
```

**使用方式**：

```python
# SAGE 代码中
from sage.libs.anns.interface import create

# 创建实例（isage-anns 已注册实现）
index = create("faiss_hnsw", dimension=128)
```

## 🎯 你正在做的事情（完全正确！）

你在为每个外迁模块创建接口层：

```bash
packages/sage-libs/src/sage/libs/
├── agentic/interface/    # ✅ 你创建的
├── finetune/interface/   # ✅ 你创建的
├── sias/interface/       # ✅ 你创建的
└── intent/interface/     # ✅ 你创建的
```

这是**完全正确**的做法！

## 📋 接口层的职责

### interface/base.py

定义抽象基类：

```python
from abc import ABC, abstractmethod

class AgentRuntime(ABC):
    """Agent runtime interface."""

    @abstractmethod
    def execute(self, task: str) -> str:
        """Execute a task and return result."""
        pass

class PlanningStrategy(ABC):
    """Planning strategy interface."""

    @abstractmethod
    def plan(self, goal: str) -> list[str]:
        """Generate a plan as a list of steps."""
        pass
```

### interface/factory.py

提供注册和工厂函数：

```python
_RUNTIME_REGISTRY: dict[str, type[AgentRuntime]] = {}

def register_runtime(name: str, cls: type[AgentRuntime]) -> None:
    """Register an agent runtime implementation."""
    _RUNTIME_REGISTRY[name] = cls

def create_runtime(name: str, **kwargs) -> AgentRuntime:
    """Create an agent runtime instance."""
    return _RUNTIME_REGISTRY[name](**kwargs)
```

## 🏗️ 实现层如何工作

### isage-agentic 中的实现

```python
# isage-agentic/src/isage_agentic/agents/react_agent.py
from sage.libs.agentic.interface import AgentRuntime, register_runtime

class ReActAgent(AgentRuntime):
    """ReAct agent implementation."""

    def execute(self, task: str) -> str:
        # 具体实现逻辑
        result = self._react_loop(task)
        return result

    def _react_loop(self, task: str) -> str:
        # ReAct 算法实现
        pass

# 自动注册（在模块导入时）
register_runtime("react", ReActAgent)
```

### 用户使用方式

```python
# 用户代码
from sage.libs.agentic.interface import create_runtime

# 创建 ReAct agent（isage-agentic 已注册）
agent = create_runtime("react", llm="gpt-4")
result = agent.execute("Solve this problem...")
```

## 🔄 RAG 的特殊情况

### 当前问题

RAG 模块**没有接口/实现分离**，所有代码都在 sage-libs 中：

```
packages/sage-libs/src/sage/libs/rag/
├── document_loaders.py    # 完整实现（200+ 行）
├── chunk.py               # 完整实现（120 行）
└── types.py               # 完整实现（150+ 行）
```

### 应该如何处理

**选项 A**：创建接口层 + 外迁实现（推荐，保持一致性）

```
sage-libs/rag/
├── interface/
│   ├── base.py           # DocumentLoader, Chunker 抽象类
│   └── factory.py        # register_loader(), create_loader()
└── __init__.py

isage-rag/
└── implementations/
    ├── pdf_loader.py     # PDFLoader 实现
    ├── character_splitter.py  # CharacterSplitter 实现
    └── ...
```

**选项 B**：保留完整实现（简单但不一致）

保持当前结构，但与其他模块（agentic, anns）不一致。

## 🎯 工具支持

我创建了接口层生成器：

```bash
# 为任何模块生成接口层模板
./tools/dev/generate_interface_layer.sh agentic
./tools/dev/generate_interface_layer.sh finetune
./tools/dev/generate_interface_layer.sh rag
```

这会生成：

- `interface/__init__.py`
- `interface/base.py`（TODO: 定义抽象类）
- `interface/factory.py`（注册和工厂函数）

## 📝 下一步建议

1. **Agentic/Finetune 接口层**：我可以帮你设计具体的抽象类
1. **RAG 处理**：建议创建接口层（保持一致性）
1. **其他模块** (dataops/safety)：评估是否需要接口层

## ❓ 需要你的决策

1. **我是否应该帮你设计 agentic/finetune 的接口层**？
1. **RAG 是否采用接口/实现分离模式**？
1. **dataops/safety 等模块是否需要接口层**？

抱歉之前理解错误！现在我完全明白你的架构设计了。
