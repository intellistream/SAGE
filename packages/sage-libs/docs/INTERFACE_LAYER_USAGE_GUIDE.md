# 接口层使用指南

## 🚀 快速开始

### 基本使用（接口定义）

无需安装外部包，即可使用接口定义：

```python
from sage.libs.agentic import Agent, Planner
from sage.libs.finetune import Trainer, FinetuneConfig
from sage.libs.sias import ContinualLearner, CoresetSelector
from sage.libs.intent import IntentRecognizer, IntentClassifier

# 自定义实现
class MyAgent(Agent):
    def run(self, task: str, **kwargs) -> str:
        return f"Processing: {task}"

    def reset(self) -> None:
        pass

agent = MyAgent()
result = agent.run("Hello")
```

### 使用外部包实现

安装外部包后，可以直接创建实例：

```python
from sage.libs.agentic import create_agent, list_agents

# 查看可用的 agent
print(list_agents())  # ['react', 'reflexion', ...]

# 创建实例
agent = create_agent("react", llm="gpt-4", temperature=0.7)
result = agent.run("What is the weather today?")
```

## 📦 安装方式

### 方式 1：通过 sage-libs extras（推荐）

```bash
# 安装特定功能
pip install -e packages/sage-libs[agentic]    # Agent 框架
pip install -e packages/sage-libs[finetune]   # 模型微调
pip install -e packages/sage-libs[sias]       # 持续学习
pip install -e packages/sage-libs[intent]     # 意图识别
pip install -e packages/sage-libs[anns]       # ANN 算法
pip install -e packages/sage-libs[amms]       # 近似矩阵乘

# 安装所有功能
pip install -e packages/sage-libs[all]
```

### 方式 2：直接安装外部包

```bash
pip install isage-agentic
pip install isage-finetune
pip install isage-sias
pip install isage-intent
pip install isage-anns
pip install isage-amms
```

## 🔧 注册自定义实现

### 注册到全局注册表

```python
from sage.libs.agentic import register_agent, Agent

class MyCustomAgent(Agent):
    def run(self, task: str, **kwargs) -> str:
        return f"Custom: {task}"

    def reset(self) -> None:
        pass

# 注册
register_agent("my_agent", MyCustomAgent)

# 使用
from sage.libs.agentic import create_agent
agent = create_agent("my_agent")
```

### 在外部包中注册（推荐）

如果你开发自己的 agent 包，在 `__init__.py` 中注册：

```python
# my_agents/__init__.py
from sage.libs.agentic import register_agent
from .my_agent import MyAgent

register_agent("my_agent", MyAgent)

__all__ = ["MyAgent"]
```

用户安装你的包后，实现自动可用：

```bash
pip install my-agents
```

```python
from sage.libs.agentic import list_agents, create_agent
print(list_agents())  # 包含 'my_agent'
agent = create_agent("my_agent")
```

## 📖 完整示例

### Agentic 模块

```python
from sage.libs.agentic import (
    # 接口
    Agent, Planner, ToolSelector, WorkflowEngine,
    # 注册
    register_agent, register_planner,
    # 工厂
    create_agent, create_planner,
    # 发现
    list_agents, list_planners,
)

# 查看可用实现
print("Available agents:", list_agents())
print("Available planners:", list_planners())

# 创建实例
agent = create_agent("react", llm="gpt-4")
result = agent.run("Analyze the data")

planner = create_planner("tree_of_thought")
plan = planner.plan("Book a flight", context={})
```

### Finetune 模块

```python
from sage.libs.finetune import (
    # 接口
    Trainer, FinetuneConfig, DataFormatter,
    # 注册
    register_trainer, register_config,
    # 工厂
    create_trainer, create_config,
    # 发现
    list_trainers, list_configs,
)

# 查看可用实现
print("Available trainers:", list_trainers())

# 创建实例
trainer = create_trainer("lora", rank=8, alpha=16)
config = create_config("default", learning_rate=1e-4)

results = trainer.train(model, train_data, val_data)
```

### SIAS 模块

```python
from sage.libs.sias import (
    # 接口
    ContinualLearner, CoresetSelector,
    # 工厂
    create_learner, create_selector,
    # 发现
    list_learners, list_selectors,
)

# 创建实例
learner = create_learner("incremental")
learner.update(new_data)
predictions = learner.predict(test_data)

selector = create_selector("greedy", diversity_weight=0.5)
coreset = selector.select(full_data, budget=100)
```

### Intent 模块

```python
from sage.libs.intent import (
    # 接口
    IntentRecognizer, IntentClassifier, IntentCatalog,
    # 工厂
    create_recognizer, create_classifier, create_catalog,
    # 发现
    list_recognizers, list_classifiers,
)

# 创建实例
recognizer = create_recognizer("llm", model="gpt-4")
result = recognizer.recognize("Book a flight to Paris")
print(result["intent"], result["confidence"])

classifier = create_classifier("bert", model_path="./models/intent-bert")
intent = classifier.classify("What's the weather?")
```

## 🔍 错误处理

### 实现未安装

```python
from sage.libs.agentic import create_agent

try:
    agent = create_agent("react")
except AgenticRegistryError as e:
    print(e)
    # Agent 'react' not registered. Available: [].
    # Install 'isage-agentic' package for implementations.
```

### 未知实现名称

```python
from sage.libs.agentic import create_agent

try:
    agent = create_agent("unknown_agent")
except AgenticRegistryError as e:
    print(e)
    # Agent 'unknown_agent' not registered. Available: ['react', 'reflexion'].
    # Install 'isage-agentic' package for implementations.
```

## 🧪 测试你的实现

```python
import pytest
from sage.libs.agentic import Agent, register_agent, create_agent

class TestCustomAgent:
    def test_custom_agent(self):
        # 定义自定义 agent
        class TestAgent(Agent):
            def run(self, task: str, **kwargs) -> str:
                return f"Test: {task}"

            def reset(self) -> None:
                pass

        # 注册
        register_agent("test_agent", TestAgent)

        # 创建
        agent = create_agent("test_agent")

        # 测试
        result = agent.run("Hello")
        assert result == "Test: Hello"
```

## 📚 更多资源

- **架构文档**: `packages/sage-libs/docs/INTERFACE_LAYER_ARCHITECTURE.md`
- **重构总结**: `packages/sage-libs/docs/INTERFACE_LAYER_REFACTOR_COMPLETED.md`
- **外部包仓库**:
  - https://github.com/intellistream/sage-agentic
  - https://github.com/intellistream/sage-finetune
  - https://github.com/intellistream/sage-sias
  - https://github.com/intellistream/sage-intent
  - https://github.com/intellistream/sage-anns
  - https://github.com/intellistream/sage-amms

## 💡 最佳实践

1. **优先使用工厂函数**: `create_agent()` 而非直接实例化
1. **检查可用实现**: 使用 `list_agents()` 等函数
1. **捕获注册表错误**: 提供友好的错误提示
1. **使用 extras 安装**: `pip install sage-libs[agentic]` 而非单独安装
1. **在外部包注册**: 实现应该在 `__init__.py` 中自动注册
