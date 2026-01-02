# Agent 框架

SAGE 提供了完整的 Agent 框架，支持构建具有规划、工具调用、记忆能力的智能代理。

## 架构概览

```
┌──────────────────────────────────────────────────────────────────┐
│                       AgentRuntime (执行主循环)                   │
├───────────────┬──────────────┬───────────────┬──────────────────┤
│   Profile     │   Planner    │  MCP Registry │    Memory        │
│  (人格/目标)   │  (LLM 规划)   │  (工具注册表)  │  (可选记忆模块)   │
└───────────────┴──────────────┴───────────────┴──────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    Pre-built Bots (预置 Bot)                      │
├──────────────┬──────────────┬───────────────┬───────────────────┤
│  AnswerBot   │  QuestionBot │  SearcherBot  │    CriticBot      │
└──────────────┴──────────────┴───────────────┴───────────────────┘
```

______________________________________________________________________

## 核心组件

### 1. Profile (人格配置)

定义 Agent 的身份、目标和约束：

```python
from sage.libs.agentic.agents.profile.profile import BaseProfile

profile = BaseProfile.from_dict({
    "name": "ResearchAssistant",
    "role": "researcher",
    "language": "zh",
    "goals": [
        "准确回答用户问题",
        "引用可靠来源",
    ],
    "constraints": [
        "保持客观中立",
        "不生成虚假信息",
    ],
    "persona": {
        "style": "professional",
    }
})
```

### 2. Planner (规划器)

使用 LLM 生成执行计划：

```python
from sage.libs.agentic.agents.planning.simple_llm_planner import SimpleLLMPlanner
from sage.libs.rag.generator import OpenAIGenerator

generator = OpenAIGenerator({
    "method": "openai",
    "model_name": "gpt-4o-mini",
    "base_url": "http://localhost:8001/v1",
})

planner = SimpleLLMPlanner(
    generator=generator,
    max_steps=6,           # 最大规划步数
    enable_repair=True,    # 自动修复无效 JSON
    topk_tools=6,          # 最多使用的工具数
)
```

### 3. MCP Registry (工具注册表)

管理和注册 MCP (Model Context Protocol) 工具：

```python
from sage.libs.agentic.agents.action.mcp_registry import MCPRegistry
import importlib

# 创建注册表
registry = MCPRegistry()

# 动态注册工具
tools_config = [
    {"module": "sage.tools.arxiv", "class": "ArxivSearchTool"},
    {"module": "sage.tools.calculator", "class": "CalculatorTool"},
]

for item in tools_config:
    mod = importlib.import_module(item["module"])
    cls = getattr(mod, item["class"])
    registry.register(cls())
```

**MCP 工具规范**:

```python
class MyTool:
    name: str = "my_tool"
    description: str = "工具描述"
    input_schema: dict = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "查询内容"}
        },
        "required": ["query"]
    }

    def call(self, arguments: dict) -> Any:
        """执行工具调用"""
        return {"result": "..."}
```

### 4. AgentRuntime (运行时)

驱动完整的 Agent 执行循环：

```python
from sage.libs.agentic.agents.runtime.agent import AgentRuntime

agent = AgentRuntime(
    profile=profile,
    planner=planner,
    tools=registry,
    summarizer=generator,  # 用于汇总结果
    max_steps=6,
)

# 执行查询
result = agent.execute({"query": "搜索最新的 LLM 论文并总结"})
```

______________________________________________________________________

## 预置 Bots

SAGE 提供多种预置 Bot 用于常见任务：

| Bot           | 用途           | 位置                                         |
| ------------- | -------------- | -------------------------------------------- |
| `AnswerBot`   | 生成答案       | `sage.libs.agentic.agents.bots.answer_bot`   |
| `QuestionBot` | 生成澄清问题   | `sage.libs.agentic.agents.bots.question_bot` |
| `SearcherBot` | 信息检索       | `sage.libs.agentic.agents.bots.searcher_bot` |
| `CriticBot`   | 评估和批判输出 | `sage.libs.agentic.agents.bots.critic_bot`   |

______________________________________________________________________

## 快速开始示例

```python
import os
from sage.libs.agentic.agents.profile.profile import BaseProfile
from sage.libs.agentic.agents.planning.simple_llm_planner import SimpleLLMPlanner
from sage.libs.agentic.agents.action.mcp_registry import MCPRegistry
from sage.libs.agentic.agents.runtime.agent import AgentRuntime
from sage.libs.rag.generator import OpenAIGenerator

# 1. 配置 LLM Generator
generator = OpenAIGenerator({
    "method": "openai",
    "model_name": "gpt-4o-mini",
    "base_url": "http://localhost:8001/v1",
    "api_key": os.getenv("OPENAI_API_KEY", "not-needed"),
})

# 2. 创建 Profile
profile = BaseProfile.from_dict({
    "name": "Assistant",
    "role": "helper",
    "goals": ["帮助用户完成任务"],
})

# 3. 创建 Planner
planner = SimpleLLMPlanner(generator=generator, max_steps=6)

# 4. 注册工具 (可选)
registry = MCPRegistry()
# registry.register(YourTool())

# 5. 创建 Agent
agent = AgentRuntime(
    profile=profile,
    planner=planner,
    tools=registry,
    summarizer=generator,
)

# 6. 执行
result = agent.execute({"query": "你好，请介绍一下自己"})
print(result)
```

______________________________________________________________________

## 与 LLM 服务集成

Agent 需要 LLM 服务进行规划和生成。推荐使用 `UnifiedInferenceClient`：

```python
from sage.llm import UnifiedInferenceClient
from sage.libs.rag.generator import OpenAIGenerator

# 方式 1: 使用 UnifiedInferenceClient 检测服务
client = UnifiedInferenceClient.create_auto()
status = client.get_status()
print(f"LLM available: {status['llm_available']}")

# 方式 2: 直接配置 OpenAIGenerator
generator = OpenAIGenerator({
    "method": "openai",
    "model_name": "Qwen/Qwen2.5-7B-Instruct",
    "base_url": "http://localhost:8901/v1",
})
```

______________________________________________________________________

## 与 Memory 集成

Agent 可以接入记忆模块实现多轮对话和知识累积：

```python
from sage.libs.agentic.agents.runtime.agent import AgentRuntime

# 配置带 Memory 的 Agent
agent = AgentRuntime(
    profile=profile,
    planner=planner,
    tools=registry,
    summarizer=generator,
    # memory=memory_adapter,  # 接入 MemoryServiceAdapter
)
```

详见 [Memory 组件](agents/components/memory.md) 文档。

______________________________________________________________________

## 配置文件示例

```yaml
# config_agent.yaml
pipeline:
  name: "sage-agent"
  version: "0.1.0"

profile:
  name: "ResearchOrchestrator"
  role: "planner"
  language: "zh"
  goals:
    - "以最少步骤完成用户意图"
    - "优先使用 MCP 工具"
  constraints:
    - "工具参数必须符合 JSONSchema"

planner:
  max_steps: 6
  enable_repair: true
  topk_tools: 6

generator:
  method: "openai"
  model_name: "gpt-4o-mini"
  base_url: "http://localhost:8001/v1"
  api_key: "${OPENAI_API_KEY}"

tools:
  - module: "sage.tools.arxiv"
    class: "ArxivSearchTool"
  - module: "sage.tools.calculator"
    class: "CalculatorTool"

runtime:
  max_steps: 6
  summarizer: "reuse_generator"
```

______________________________________________________________________

## 执行流程

```
User Query
    │
    ▼
┌──────────┐
│  Profile │ → 生成 system prompt
└────┬─────┘
     │
     ▼
┌──────────┐
│ Planner  │ → 生成 JSON 执行计划
└────┬─────┘
     │
     ▼
┌──────────┐
│  Tools   │ → 逐步执行工具调用
└────┬─────┘
     │
     ▼
┌──────────┐
│Summarizer│ → 汇总结果生成回复
└────┬─────┘
     │
     ▼
Final Answer
```

______________________________________________________________________

## 相关文档

- [Memory 组件](agents/components/memory.md) - 记忆系统设计
- [Planner 组件](agents/components/planner.md) - 规划器详解
- [Action 组件](agents/components/action.md) - 动作执行
- [MCP Server](agents/components/mcp_server.md) - MCP 服务端
- [最小示例](agents/examples/agent_min.md) - 完整运行示例
