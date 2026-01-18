# isage-agentic Copilot Instructions

## Package Identity

| 属性          | 值                                              |
| ------------- | ----------------------------------------------- |
| **PyPI 包名** | `isage-agentic`                                 |
| **导入名**    | `sage_libs.sage_agentic`                        |
| **SAGE 层级** | L3 (Algorithms & Libraries)                     |
| **版本格式**  | `0.1.x.y` (四段式)                              |
| **仓库**      | `https://github.com/intellistream/sage-agentic` |

## 层级定位

### ✅ 允许的依赖

```
L3 及以下:
├── sage-common (L1)      # 基础工具、类型、配置
├── sage-platform (L2)    # 平台服务抽象
├── Python stdlib         # 标准库
├── pydantic              # 数据验证
├── jinja2                # 模板引擎
└── networkx              # 图算法 (用于 DAG 规划)
```

### ❌ 禁止的依赖

```
L4+ 组件 (绝对禁止):
├── sage-middleware       # ❌ 中间件层
├── isage-vdb / SageVDB   # ❌ 向量数据库
├── isage-neuromem        # ❌ 内存系统
├── FastAPI / uvicorn     # ❌ 网络服务
├── Redis / RocksDB       # ❌ 外部存储
├── vLLM / LMDeploy       # ❌ 推理引擎
└── isagellm              # ❌ LLM 客户端（通过注入）
```

**原则**: Agentic 库提供 Agent 框架和算法，LLM 调用通过依赖注入。

## 与 SAGE 主仓库的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                  SAGE 主仓库 (sage.libs.agentic)                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Interface Layer                         │  │
│  │  • BaseAgent (ABC)         • BasePlanner (ABC)            │  │
│  │  • BaseToolSelector (ABC)  • BaseOrchestrator (ABC)       │  │
│  │  • IntentRecognizer (ABC)  • BaseReasoningStrategy (ABC)  │  │
│  │  • AgentAction, AgentResult, Intent (数据类型)             │  │
│  │  • create_agent(), create_planner() (工厂函数)             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▲                                   │
│                              │ 注册                              │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                  isage-agentic (独立 PyPI 包)                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 Implementation Layer                       │  │
│  │  • ReActAgent, PlanExecuteAgent, ReflexAgent (Agent 实现) │  │
│  │  • DFSDTSelector, GorillaSelector (工具选择器)             │  │
│  │  • HierarchicalPlanner, DAGPlanner (规划器)                │  │
│  │  • RoundRobinOrchestrator (编排器)                         │  │
│  │  • MCTSReasoning, BeamSearchReasoning (推理策略)           │  │
│  │  • _register.py (自动注册到 SAGE 工厂)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 自动注册机制

```python
# sage_libs/sage_agentic/_register.py
from sage.libs.agentic.interface import (
    register_agent, register_planner, register_tool_selector
)

from .agents import ReActAgent, PlanExecuteAgent, ReflexAgent
from .planners import HierarchicalPlanner, DAGPlanner
from .selectors import DFSDTSelector, GorillaSelector

# 注册到 SAGE 工厂
register_agent("react", ReActAgent)
register_agent("plan_execute", PlanExecuteAgent)
register_agent("reflex", ReflexAgent)

register_planner("hierarchical", HierarchicalPlanner)
register_planner("dag", DAGPlanner)

register_tool_selector("dfsdt", DFSDTSelector)
register_tool_selector("gorilla", GorillaSelector)
```

## 功能模块

### 1. Agents (智能体)

```python
from sage.libs.agentic import create_agent, AgentResult

# ReAct Agent (推理-行动循环)
agent = create_agent("react",
    llm_client=client,
    tools=tool_list,
    max_iterations=10
)
result: AgentResult = agent.execute("分析这份财报")

# Plan-Execute Agent (先规划后执行)
agent = create_agent("plan_execute",
    llm_client=client,
    tools=tool_list,
    planner="hierarchical"
)
result = agent.execute("完成数据分析报告")

# Reflex Agent (反应式)
agent = create_agent("reflex",
    rules=rule_set,
    tools=tool_list
)
```

**支持的 Agent 类型**:

- `react`: ReAct (Reasoning + Acting)
- `plan_execute`: 规划-执行分离
- `reflex`: 基于规则的反应式
- `toolformer`: 自动工具调用
- `self_ask`: 自问自答式

### 2. Planners (规划器)

```python
from sage.libs.agentic import create_planner

# 层次化规划
planner = create_planner("hierarchical",
    llm_client=client,
    max_depth=3
)
plan = planner.plan(
    goal="完成季度报告",
    available_tools=["search", "calculate", "write"],
    context={"deadline": "2024-03-31"}
)

# DAG 规划 (支持并行)
planner = create_planner("dag",
    llm_client=client,
    enable_parallel=True
)
```

### 3. Tool Selectors (工具选择器)

```python
from sage.libs.agentic import create_tool_selector

# DFSDT 选择器 (深度优先搜索决策树)
selector = create_tool_selector("dfsdt",
    embedding_model="BAAI/bge-small-zh-v1.5"
)
selector.add_tool({
    "name": "search",
    "description": "搜索网页内容",
    "parameters": {...}
})

# 选择工具
selected = selector.select_tools(
    query="查找最新的 AI 新闻",
    available_tools=all_tools,
    top_k=3
)

# Gorilla 选择器 (基于 Gorilla 模型)
selector = create_tool_selector("gorilla",
    model="gorilla-llm/gorilla-openfunctions-v2"
)
```

### 4. Orchestrators (编排器)

```python
from sage.libs.agentic import create_orchestrator

# 轮询编排
orchestrator = create_orchestrator("round_robin")
result = orchestrator.coordinate(
    task="多步骤数据处理",
    agents=[data_agent, analysis_agent, report_agent]
)

# 层次编排 (manager-worker)
orchestrator = create_orchestrator("hierarchical",
    manager_agent=manager,
    worker_agents=[worker1, worker2]
)
```

### 5. Intent Recognition (意图识别)

```python
from sage.libs.agentic import create_intent_recognizer, Intent

# 基于 LLM 的意图识别
recognizer = create_intent_recognizer("llm",
    llm_client=client,
    intents=["search", "calculate", "summarize", "translate"]
)
intent: Intent = recognizer.recognize("帮我翻译这段话")
print(intent.name)  # "translate"
print(intent.confidence)  # 0.95

# 基于分类器的意图识别
recognizer = create_intent_recognizer("classifier",
    model="path/to/intent_classifier"
)
```

### 6. Reasoning Strategies (推理策略)

```python
from sage.libs.agentic import create_reasoning_strategy

# MCTS (蒙特卡洛树搜索)
strategy = create_reasoning_strategy("mcts",
    exploration_weight=1.0,
    max_iterations=100
)

# Beam Search
strategy = create_reasoning_strategy("beam_search",
    beam_width=5,
    max_depth=10
)

# 执行搜索
path = strategy.search(
    initial_state=start,
    goal_check=lambda s: s.is_goal,
    expand=lambda s: s.get_successors()
)
```

## 目录结构

```
sage-agentic/                       # 独立仓库根目录
├── pyproject.toml                  # 包配置 (name = "isage-agentic")
├── README.md
├── COPILOT_INSTRUCTIONS.md         # 本文件
├── LICENSE
├── src/
│   └── sage_libs/                  # 命名空间包
│       └── sage_agentic/
│           ├── __init__.py         # 主入口
│           ├── _version.py         # 版本信息
│           ├── _register.py        # 自动注册
│           ├── agents/             # Agent 实现
│           │   ├── __init__.py
│           │   ├── react.py        # ReAct Agent
│           │   ├── plan_execute.py # Plan-Execute Agent
│           │   ├── reflex.py       # Reflex Agent
│           │   └── toolformer.py   # Toolformer Agent
│           ├── planners/           # 规划器实现
│           │   ├── __init__.py
│           │   ├── hierarchical.py
│           │   ├── dag.py
│           │   └── iterative.py
│           ├── selectors/          # 工具选择器实现
│           │   ├── __init__.py
│           │   ├── dfsdt.py        # DFSDT 选择器
│           │   ├── gorilla.py      # Gorilla 选择器
│           │   └── semantic.py     # 语义相似度选择
│           ├── orchestrators/      # 编排器实现
│           │   ├── __init__.py
│           │   ├── round_robin.py
│           │   └── hierarchical.py
│           ├── intent/             # 意图识别实现
│           │   ├── __init__.py
│           │   ├── llm_recognizer.py
│           │   └── classifier.py
│           └── reasoning/          # 推理策略实现
│               ├── __init__.py
│               ├── mcts.py
│               └── beam_search.py
├── tests/
│   ├── conftest.py
│   ├── test_agents.py
│   ├── test_planners.py
│   ├── test_selectors.py
│   └── test_integration.py
└── examples/
    ├── react_agent.py
    ├── multi_agent.py
    └── tool_selection.py
```

## 常见问题修复指南

### 1. LLM 客户端注入

```python
# ❌ 错误：Agent 内部创建 LLM 客户端
class ReActAgent(BaseAgent):
    def __init__(self):
        from isagellm import UnifiedInferenceClient
        self.llm = UnifiedInferenceClient.create()  # ❌ 隐式依赖

# ✅ 正确：通过依赖注入
class ReActAgent(BaseAgent):
    def __init__(self, llm_client: LLMClientProtocol):
        self.llm = llm_client  # 注入的客户端

# 使用时
from isagellm import UnifiedInferenceClient
client = UnifiedInferenceClient.create()
agent = ReActAgent(llm_client=client)
```

### 2. 工具定义格式

```python
# ❌ 错误：工具定义不完整
tool = {"name": "search"}

# ✅ 正确：完整的工具定义
tool = {
    "name": "search",
    "description": "搜索互联网内容",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索查询"},
            "max_results": {"type": "integer", "default": 10}
        },
        "required": ["query"]
    }
}
```

### 3. 循环检测

```python
# ❌ 问题：Agent 陷入无限循环
agent = create_agent("react", max_iterations=None)  # 无限制

# ✅ 修复：设置最大迭代次数
agent = create_agent("react",
    max_iterations=10,
    timeout_seconds=60
)
```

### 4. 状态管理

```python
# ❌ 错误：忘记重置状态
agent.execute("任务1")
agent.execute("任务2")  # 可能受任务1状态影响

# ✅ 正确：显式重置
agent.execute("任务1")
agent.reset()  # 清除状态
agent.execute("任务2")
```

### 5. 内存依赖问题

```python
# ❌ 错误：在 Agent 中直接使用 NeuroMem
from isage_neuromem import NeuroMem  # ❌ L3 不应依赖 L4

# ✅ 正确：通过抽象接口
class ReActAgent(BaseAgent):
    def __init__(self, memory: MemoryProtocol = None):  # 可选的内存接口
        self.memory = memory

# 在 L4 middleware 层组合
from isage_neuromem import NeuroMem
from sage_libs.sage_agentic import ReActAgent

memory = NeuroMem(...)
agent = ReActAgent(llm_client=client, memory=memory)
```

## 关键设计原则

### 1. LLM 无关性

Agent 框架不绑定特定 LLM：

```python
class LLMClientProtocol(Protocol):
    """LLM 客户端协议 - 任何符合协议的客户端都可以使用"""
    def chat(self, messages: list[dict]) -> str: ...
    def generate(self, prompt: str) -> str: ...

class ReActAgent:
    def __init__(self, llm_client: LLMClientProtocol):
        self.llm = llm_client
```

### 2. 工具即数据

工具以数据结构描述，不是代码：

```python
# 工具定义是数据
tool_spec = {
    "name": "calculator",
    "description": "执行数学计算",
    "parameters": {...}
}

# 工具执行器在外部
def execute_tool(name: str, params: dict) -> Any:
    if name == "calculator":
        return eval(params["expression"])
```

### 3. 可观察性

所有 Agent 执行都可追踪：

```python
result = agent.execute("任务")

# 完整的执行轨迹
for action, observation in result.intermediate_steps:
    print(f"Action: {action.tool_name}({action.tool_input})")
    print(f"Thought: {action.thought}")
    print(f"Observation: {observation}")
```

### 4. 错误隔离

工具执行错误不应导致 Agent 崩溃：

```python
class ReActAgent:
    def _execute_tool(self, action: AgentAction) -> str:
        try:
            result = self.tool_executor(action.tool_name, action.tool_input)
            return str(result)
        except Exception as e:
            # 将错误作为观察返回给 LLM
            return f"Error: {type(e).__name__}: {str(e)}"
```

### 5. 无状态优先

优先设计无状态组件：

```python
# ✅ 好：无状态的工具选择器
class DFSDTSelector(BaseToolSelector):
    def select_tools(self, query: str, tools: list[dict]) -> list[str]:
        # 纯函数，无副作用
        return self._rank_tools(query, tools)[:self.top_k]

# ⚠️ 需要状态时明确管理
class StatefulAgent(BaseAgent):
    def __init__(self):
        self._history = []  # 明确的状态

    def reset(self):
        self._history.clear()  # 明确的重置
```

## 测试规范

```bash
# 运行单元测试
pytest tests/ -v

# 运行需要 LLM 的测试（使用 mock）
pytest tests/ -v -m "not integration"

# 运行集成测试（需要真实 LLM）
SAGE_TEST_LLM_ENABLED=1 pytest tests/test_integration.py -v
```

## 与其他 L3 库的协作

```python
# isage-agentic + isage-rag 协作
from sage_libs.sage_agentic import ReActAgent
from sage_libs.sage_rag import DenseRetriever

# RAG 作为工具
rag_tool = {
    "name": "search_documents",
    "description": "搜索知识库文档",
    "parameters": {...}
}

# 在外部定义工具执行器
retriever = DenseRetriever(...)
def tool_executor(name, params):
    if name == "search_documents":
        return retriever.retrieve(params["query"])

agent = ReActAgent(
    llm_client=client,
    tools=[rag_tool],
    tool_executor=tool_executor
)
```

## 发布流程

```bash
# 使用 sage-pypi-publisher
cd /path/to/sage-pypi-publisher
./publish.sh sage-agentic --auto-bump patch

# 或手动指定版本
./publish.sh sage-agentic --version 0.1.0.1
```
