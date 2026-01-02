# sage-libs API

Algorithm libraries: agents, RAG, tools, workflow optimization, and I/O utilities.

**Layer**: L3 (Core Libraries)

## Overview

`sage-libs` provides reusable algorithm libraries and tools:

- **Agentic**: Intelligent agent framework with planning, tool selection, and timing decision
- **RAG**: Retrieval-Augmented Generation components
- **Tools**: Utility tools (search, image processing, web scraping)
- **I/O**: Data sources and sinks
- **Context**: Context management for agents and RAG
- **Workflow**: Workflow optimization framework
- **Unlearning**: Machine unlearning algorithms

## Modules

### Agentic Framework ⭐ NEW

The `sage.libs.agentic` module provides comprehensive agent capabilities:

#### Tool Selection

::: sage.libs.agentic.agents.action.tool_selection
    options:
      show_root_heading: true
      members:
        - BaseToolSelector
        - KeywordSelector
        - EmbeddingSelector
        - HybridSelector
        - GorillaSelector
        - DFSDTSelector
        - SelectorRegistry

**Available Tool Selectors:**

| Selector | Description | Use Case |
|----------|-------------|----------|
| `KeywordSelector` | Keyword-based matching | Simple, fast selection |
| `EmbeddingSelector` | Semantic similarity | Context-aware selection |
| `HybridSelector` | Keyword + Embedding | Balanced accuracy |
| `GorillaSelector` | Gorilla-style API retrieval | API-heavy tasks |
| `DFSDTSelector` | Depth-First Search with Decision Tree | Complex multi-tool tasks |

```python
from sage.libs.agentic.agents.action.tool_selection import (
    SelectorRegistry,
    get_selector,
    HybridSelector,
    HybridSelectorConfig
)

# Use registry
selector = get_selector("hybrid")

# Or create directly
config = HybridSelectorConfig(
    keyword_weight=0.3,
    embedding_weight=0.7
)
selector = HybridSelector(config)

# Select tools for query
tools = selector.select(
    query="Search for news about AI",
    available_tools=[tool1, tool2, tool3],
    top_k=3
)
```

#### Planning

::: sage.libs.agentic.agents.planning
    options:
      show_root_heading: true
      members:
        - BasePlanner
        - HierarchicalPlanner
        - ReActPlanner
        - TreeOfThoughtsPlanner
        - PlanRequest
        - PlanResult
        - PlanStep
        - PlannerConfig

**Available Planners:**

| Planner | Description | Use Case |
|---------|-------------|----------|
| `HierarchicalPlanner` | Multi-step decomposition | Complex multi-step tasks |
| `ReActPlanner` | Reasoning + Acting | Interactive tasks |
| `TreeOfThoughtsPlanner` | Tree search exploration | Creative problem-solving |

```python
from sage.libs.agentic.agents.planning import (
    HierarchicalPlanner,
    PlanRequest,
    PlannerConfig
)

config = PlannerConfig(min_steps=3, max_steps=10)
planner = HierarchicalPlanner.from_config(
    config=config,
    llm_client=your_llm_client,
    tool_selector=your_tool_selector
)

request = PlanRequest(
    goal="Deploy application to production",
    tools=[...],
    constraints=["No downtime", "Rollback capability"]
)
result = planner.plan(request)
```

#### Timing Decision

::: sage.libs.agentic.agents.planning.timing_decider
    options:
      show_root_heading: true
      members:
        - BaseTimingDecider
        - RuleBasedTimingDecider
        - LLMBasedTimingDecider
        - HybridTimingDecider
        - TimingMessage
        - TimingDecision
        - TimingConfig

**Available Timing Deciders:**

| Decider | Description | Use Case |
|---------|-------------|----------|
| `RuleBasedTimingDecider` | Pattern matching rules | Deterministic decisions |
| `LLMBasedTimingDecider` | LLM-powered judgment | Complex context |
| `HybridTimingDecider` | Rules + LLM fallback | Production recommended |

```python
from sage.libs.agentic.agents.planning import (
    HybridTimingDecider,
    TimingMessage,
    TimingConfig
)

config = TimingConfig(decision_threshold=0.8)
decider = HybridTimingDecider(config, llm_client=your_llm)

message = TimingMessage(user_message="What's the weather in Beijing?")
decision = decider.decide(message)

if decision.should_respond:
    # Generate response
    pass
```

#### Agent Runtime

::: sage.libs.agentic.agents.runtime
    options:
      show_root_heading: true
      members:
        - AgentRuntime
        - runtime

::: sage.libs.agentic.agents.profile
    options:
      show_root_heading: true
      members:
        - BaseProfile

::: sage.libs.agentic.agents.action
    options:
      show_root_heading: true
      members:
        - MCPRegistry

### RAG (Retrieval-Augmented Generation)

#### Generator

::: sage.libs.rag.generator
    options:
      show_root_heading: true
      members:
        - OpenAIGenerator
        - VLLMGenerator

#### Retriever

::: sage.libs.rag.retriever
    options:
      show_root_heading: true
      members:
        - ChromaRetriever
        - MilvusRetriever

#### Promptor

::: sage.libs.rag.promptor
    options:
      show_root_heading: true
      members:
        - QAPromptor
        - ChatPromptor

### I/O Utilities

#### Sources

::: sage.libs.io.source
    options:
      show_root_heading: true
      members:
        - FileSource
        - SocketSource
        - JSONFileSource
        - CSVFileSource
        - KafkaSource

#### Sinks

::: sage.libs.io.sink
    options:
      show_root_heading: true
      members:
        - TerminalSink
        - FileSink
        - PrintSink

### Tools

::: sage.libs.tools
    options:
      show_root_heading: true
      members:
        - SearcherTool
        - ImageCaptioner
        - ArxivPaperSearcher

### Workflow Optimization

::: sage.libs.workflow
    options:
      show_root_heading: true
      members:
        - WorkflowGraph
        - BaseOptimizer
        - WorkflowEvaluator

## Quick Examples

### Complete Agent Setup

```python
from sage.libs.agentic.agents.profile.profile import BaseProfile
from sage.libs.agentic.agents.runtime.agent import AgentRuntime
from sage.libs.agentic.agents.planning import HierarchicalPlanner, PlannerConfig
from sage.libs.agentic.agents.action.mcp_registry import MCPRegistry
from sage.libs.agentic.agents.action.tool_selection import get_selector

# 1. Create profile
profile = BaseProfile(name="assistant", role="research helper")

# 2. Register tools
registry = MCPRegistry()
registry.register(search_tool)
registry.register(calculator_tool)

# 3. Create tool selector
selector = get_selector("hybrid")

# 4. Create planner
config = PlannerConfig(min_steps=3, max_steps=10)
planner = HierarchicalPlanner.from_config(
    config=config,
    llm_client=your_llm_client,
    tool_selector=selector
)

# 5. Create runtime
runtime = AgentRuntime(
    profile=profile,
    planner=planner,
    tools=registry
)

# 6. Execute
result = runtime.execute({"query": "Search for AI news and summarize"})
```

### RAG Pipeline

```python
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import ChromaRetriever
from sage.libs.rag.generator import OpenAIGenerator

# Build RAG pipeline
promptor = QAPromptor()
retriever = ChromaRetriever(collection_name="docs")
generator = OpenAIGenerator(model="gpt-4")

# Use in SAGE pipeline
stream = (env
    .from_source(questions)
    .map(promptor)
    .map(retriever)
    .map(generator)
    .sink(output)
)
```

### I/O Sources and Sinks

```python
from sage.libs.io import FileSource, TerminalSink

# Create pipeline with I/O
stream = (env
    .from_source(FileSource, {"file_path": "data.txt"})
    .map(process_function)
    .sink(TerminalSink, {})
)
```

## Component Guides

### Agentic (NEW)

- [Agents 概述](../../guides/packages/sage-libs/agents.md) - Agent 框架核心组件
- [Planner 组件](../../guides/packages/sage-libs/agents/components/planner.md) - 规划器
- [Action 组件](../../guides/packages/sage-libs/agents/components/action.md) - 行动组件

### RAG

- [RAG Overview](../../guides/packages/sage-libs/rag/README.md)
- [RAG Components](../../guides/packages/sage-libs/rag/api_reference.md)

### Agents

- [Agents Guide](../../guides/packages/sage-libs/agents.md)

### Tools

- [Tools Introduction](../../guides/packages/sage-libs/tools_intro.md)

## Module Organization

```
sage.libs/
├── agentic/                    # Agent framework (NEW)
│   ├── agents/
│   │   ├── action/
│   │   │   ├── tool_selection/ # Tool selectors
│   │   │   └── mcp_registry.py # MCP tool registry
│   │   ├── planning/           # Planners & timing
│   │   ├── profile/            # Agent profiles
│   │   └── runtime/            # Agent runtime
│   └── workflow/               # Workflow optimization
├── rag/                        # RAG components
│   ├── generator/
│   ├── retriever/
│   └── promptor/
├── io/                         # I/O utilities
│   ├── source/
│   └── sink/
├── tools/                      # Tool implementations
└── context/                    # Context management
```

## See Also

- [Libraries Guide](../../guides/packages/sage-libs/README.md)
- [Benchmark 概览](../../guides/packages/sage-benchmark/index.md)
- [Design Decisions](../../concepts/architecture/design-decisions/sage-libs-restructuring.md)
