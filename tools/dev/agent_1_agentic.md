# Agent-1: Agentic Framework Refactoring (含 Intent/Reasoning/SIAS 合并)

## 🎯 任务目标

将 sage-libs 中的 agentic 模块重构为接口层，并**合并 Intent, Reasoning, SIAS** 功能到 isage-agentic 独立库。

## 🔍 合并策略

### 为什么合并？

1. **Intent（意图识别）** → Agentic 的输入理解层

   - Agent 需要理解用户意图来选择合适的工具和规划
   - 意图分类是 Agent 的第一步

1. **Reasoning（推理搜索）** → Agentic 的核心规划能力

   - ToT, ReAct, Beam Search 等是 Agent 规划的核心算法
   - 推理策略直接服务于 Agent 决策

1. **SIAS（流式重要性感知）** → Agentic 的高级特性

   - SIAS 是 Agent 的自我改进机制（学习、记忆、反思）
   - 作为可选安装：`pip install isage-agentic[sias]`

## 📂 当前结构

```
packages/sage-libs/src/sage/libs/
├── agentic.py                    # 临时兼容层
└── (待创建) agentic/interface/
```

外部仓库：`/home/shuhao/sage-agentic` (已存在)

## 📋 任务清单

### 1. 分析现有代码

查看 sage-libs 中的 agentic 相关代码：

```bash
cd /home/shuhao/SAGE
find packages/sage-libs/src/sage/libs -name "*agent*" -o -name "*agentic*"
grep -r "class.*Agent" packages/sage-libs/src/sage/libs/ --include="*.py"
```

### 2. 设计接口层

创建接口目录结构：

```
packages/sage-libs/src/sage/libs/agentic/
├── __init__.py              # 主入口 + deprecation warning
├── interface/
│   ├── __init__.py          # 接口层导出
│   ├── base.py              # 抽象基类
│   ├── factory.py           # 注册和工厂
│   └── protocols.py         # Protocol 定义
└── README.md                # 接口说明
```

### 3. 定义核心接口

**base.py** - 定义抽象基类：

```python
"""Base classes for agentic components."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass

@dataclass
class AgentAction:
    """Agent action result."""
    tool_name: str
    tool_input: dict[str, Any]
    thought: Optional[str] = None
    confidence: float = 1.0

@dataclass
class AgentResult:
    """Agent execution result."""
    output: Any
    intermediate_steps: list[tuple[AgentAction, str]]
    metadata: dict[str, Any]

class BaseAgent(ABC):
    """Abstract base class for all agents."""

    @abstractmethod
    def plan(self, task: str, context: dict[str, Any]) -> list[AgentAction]:
        """Plan actions for a given task."""
        pass

    @abstractmethod
    def execute(self, task: str, **kwargs) -> AgentResult:
        """Execute the agent on a task."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset agent state."""
        pass

class BasePlanner(ABC):
    """Abstract base class for planning strategies."""

    @abstractmethod
    def plan(
        self,
        goal: str,
        available_tools: list[str],
        context: dict[str, Any]
    ) -> list[str]:
        """Generate a plan as a sequence of tool calls."""
        pass

class BaseToolSelector(ABC):
    """Abstract base class for tool selection."""

    @abstractmethod
    def select_tools(
        self,
        query: str,
        available_tools: list[dict[str, Any]],
        top_k: int = 3
    ) -> list[str]:
        """Select top-k relevant tools for a query."""
        pass

    @abstractmethod
    def add_tool(self, tool_spec: dict[str, Any]) -> None:
        """Add a tool to the selector's knowledge."""
        pass

class BaseOrchestrator(ABC):
    """Abstract base class for multi-agent orchestration."""

    @abstractmethod
    def coordinate(
        self,
        task: str,
        agents: list[BaseAgent],
        **kwargs
    ) -> AgentResult:
        """Coordinate multiple agents to complete a task."""
        pass
```

**factory.py** - 注册和工厂模式：

```python
"""Factory and registry for agentic components."""

from typing import Any, Type

from .base import BaseAgent, BasePlanner, BaseToolSelector, BaseOrchestrator

_AGENT_REGISTRY: dict[str, Type[BaseAgent]] = {}
_PLANNER_REGISTRY: dict[str, Type[BasePlanner]] = {}
_TOOL_SELECTOR_REGISTRY: dict[str, Type[BaseToolSelector]] = {}
_ORCHESTRATOR_REGISTRY: dict[str, Type[BaseOrchestrator]] = {}

# ==================== Agent Registry ====================

def register_agent(name: str, cls: Type[BaseAgent]) -> None:
    """Register an agent implementation."""
    if name in _AGENT_REGISTRY:
        raise ValueError(f"Agent '{name}' already registered")
    if not issubclass(cls, BaseAgent):
        raise TypeError(f"Class must inherit from BaseAgent")
    _AGENT_REGISTRY[name] = cls

def create_agent(name: str, **kwargs: Any) -> BaseAgent:
    """Create an agent instance."""
    if name not in _AGENT_REGISTRY:
        available = ", ".join(_AGENT_REGISTRY.keys()) or "none"
        raise KeyError(
            f"Agent '{name}' not found. Available: {available}. "
            f"Did you install 'isage-agentic'?"
        )
    return _AGENT_REGISTRY[name](**kwargs)

def list_agents() -> list[str]:
    """List registered agents."""
    return list(_AGENT_REGISTRY.keys())

# ==================== Planner Registry ====================

def register_planner(name: str, cls: Type[BasePlanner]) -> None:
    """Register a planner implementation."""
    if name in _PLANNER_REGISTRY:
        raise ValueError(f"Planner '{name}' already registered")
    if not issubclass(cls, BasePlanner):
        raise TypeError(f"Class must inherit from BasePlanner")
    _PLANNER_REGISTRY[name] = cls

def create_planner(name: str, **kwargs: Any) -> BasePlanner:
    """Create a planner instance."""
    if name not in _PLANNER_REGISTRY:
        available = ", ".join(_PLANNER_REGISTRY.keys()) or "none"
        raise KeyError(
            f"Planner '{name}' not found. Available: {available}. "
            f"Did you install 'isage-agentic'?"
        )
    return _PLANNER_REGISTRY[name](**kwargs)

def list_planners() -> list[str]:
    """List registered planners."""
    return list(_PLANNER_REGISTRY.keys())

# ==================== Tool Selector Registry ====================

def register_tool_selector(name: str, cls: Type[BaseToolSelector]) -> None:
    """Register a tool selector implementation."""
    if name in _TOOL_SELECTOR_REGISTRY:
        raise ValueError(f"Tool selector '{name}' already registered")
    if not issubclass(cls, BaseToolSelector):
        raise TypeError(f"Class must inherit from BaseToolSelector")
    _TOOL_SELECTOR_REGISTRY[name] = cls

def create_tool_selector(name: str, **kwargs: Any) -> BaseToolSelector:
    """Create a tool selector instance."""
    if name not in _TOOL_SELECTOR_REGISTRY:
        available = ", ".join(_TOOL_SELECTOR_REGISTRY.keys()) or "none"
        raise KeyError(
            f"Tool selector '{name}' not found. Available: {available}. "
            f"Did you install 'isage-agentic'?"
        )
    return _TOOL_SELECTOR_REGISTRY[name](**kwargs)

def list_tool_selectors() -> list[str]:
    """List registered tool selectors."""
    return list(_TOOL_SELECTOR_REGISTRY.keys())

# ==================== Orchestrator Registry ====================

def register_orchestrator(name: str, cls: Type[BaseOrchestrator]) -> None:
    """Register an orchestrator implementation."""
    if name in _ORCHESTRATOR_REGISTRY:
        raise ValueError(f"Orchestrator '{name}' already registered")
    if not issubclass(cls, BaseOrchestrator):
        raise TypeError(f"Class must inherit from BaseOrchestrator")
    _ORCHESTRATOR_REGISTRY[name] = cls

def create_orchestrator(name: str, **kwargs: Any) -> BaseOrchestrator:
    """Create an orchestrator instance."""
    if name not in _ORCHESTRATOR_REGISTRY:
        available = ", ".join(_ORCHESTRATOR_REGISTRY.keys()) or "none"
        raise KeyError(
            f"Orchestrator '{name}' not found. Available: {available}. "
            f"Did you install 'isage-agentic'?"
        )
    return _ORCHESTRATOR_REGISTRY[name](**kwargs)

def list_orchestrators() -> list[str]:
    """List registered orchestrators."""
    return list(_ORCHESTRATOR_REGISTRY.keys())

__all__ = [
    # Agent
    "register_agent",
    "create_agent",
    "list_agents",
    # Planner
    "register_planner",
    "create_planner",
    "list_planners",
    # Tool Selector
    "register_tool_selector",
    "create_tool_selector",
    "list_tool_selectors",
    # Orchestrator
    "register_orchestrator",
    "create_orchestrator",
    "list_orchestrators",
]
```

### 4. 迁移实现到独立库

在 `/home/shuhao/sage-agentic` 中：

```bash
cd /home/shuhao/sage-agentic

# 创建目录结构
mkdir -p src/isage_agentic/{agents,planners,tool_selection,orchestration}

# 创建 pyproject.toml
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "isage-agentic"
version = "0.1.0"
description = "Agentic framework for SAGE - agents, planning, tool selection"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "Apache-2.0"}
authors = [
    {name = "IntelliStream Team", email = "shuhao_zhang@hust.edu.cn"}
]

dependencies = [
    "isage-libs>=0.2.0",  # For interface layer
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.8.0",
]
langchain = [
    "langchain>=0.1.0",
    "langchain-community>=0.0.10",
]

[tool.setuptools.packages.find]
where = ["src"]
EOF

# 提交到 main-dev
git add .
git commit -m "feat: add agentic interface and initial structure"
git push origin main-dev
```

### 5. 注册实现示例

在 isage-agentic 中创建注册代码：

```python
# src/isage_agentic/__init__.py
"""Agentic framework implementations."""

from sage.libs.agentic.interface import (
    register_agent,
    register_planner,
    register_tool_selector,
    register_orchestrator,
)

# Import implementations
from .agents import ReactAgent, ReflexionAgent
from .planners import ToTPlanner, ReActPlanner
from .tool_selection import KeywordSelector, EmbeddingSelector
from .orchestration import SimpleOrchestrator

# Register implementations
register_agent("react", ReactAgent)
register_agent("reflexion", ReflexionAgent)

register_planner("tot", ToTPlanner)
register_planner("react", ReActPlanner)

register_tool_selector("keyword", KeywordSelector)
register_tool_selector("embedding", EmbeddingSelector)

register_orchestrator("simple", SimpleOrchestrator)

__all__ = [
    "ReactAgent",
    "ReflexionAgent",
    "ToTPlanner",
    "ReActPlanner",
    "KeywordSelector",
    "EmbeddingSelector",
    "SimpleOrchestrator",
]
```

### 6. 更新 sage-libs 依赖

在 `packages/sage-libs/pyproject.toml` 中添加：

```toml
[project.optional-dependencies]
agentic = ["isage-agentic>=0.1.0"]
```

### 7. 测试集成

创建测试文件：

```python
# packages/sage-libs/tests/integration/test_agentic_integration.py
"""Test agentic interface integration."""

import pytest

def test_import_interface():
    """Test importing interface layer."""
    from sage.libs.agentic.interface import (
        BaseAgent,
        create_agent,
        register_agent,
    )
    assert BaseAgent is not None

def test_agent_not_found():
    """Test error when agent not found."""
    from sage.libs.agentic.interface import create_agent

    with pytest.raises(KeyError, match="Did you install 'isage-agentic'"):
        create_agent("nonexistent")

@pytest.mark.skipif(
    not _has_isage_agentic(),
    reason="isage-agentic not installed"
)
def test_create_agent():
    """Test creating agent with isage-agentic installed."""
    import isage_agentic  # Register implementations
    from sage.libs.agentic.interface import create_agent, list_agents

    agents = list_agents()
    assert "react" in agents

    agent = create_agent("react", llm=None)
    assert agent is not None

def _has_isage_agentic():
    try:
        import isage_agentic
        return True
    except ImportError:
        return False
```

## ✅ 完成标准

- [ ] sage-libs 中创建了 agentic/interface/ 目录
- [ ] base.py 定义了所有核心抽象基类
- [ ] factory.py 实现了注册和工厂模式
- [ ] sage-agentic 仓库更新了实现代码
- [ ] sage-agentic 实现了注册逻辑
- [ ] 集成测试通过
- [ ] 文档更新完成

## 📤 输出文件

1. `packages/sage-libs/src/sage/libs/agentic/interface/base.py`
1. `packages/sage-libs/src/sage/libs/agentic/interface/factory.py`
1. `/home/shuhao/sage-agentic/src/isage_agentic/__init__.py`
1. `/home/shuhao/sage-agentic/pyproject.toml`
1. `packages/sage-libs/tests/integration/test_agentic_integration.py`
