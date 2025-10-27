# sage-libs API

Algorithm libraries: agents, RAG, tools, workflow optimization, and I/O utilities.

**Layer**: L3 (Core Libraries)

## Overview

`sage-libs` provides reusable algorithm libraries and tools:

- **Agents**: Intelligent agent framework with planning and action
- **RAG**: Retrieval-Augmented Generation components
- **Tools**: Utility tools (search, image processing, web scraping)
- **I/O**: Data sources and sinks
- **Context**: Context management for agents and RAG
- **Workflow**: Workflow optimization framework
- **Unlearning**: Machine unlearning algorithms

## Modules

### Agents

::: sage.libs.agents
    options:
      show_root_heading: true
      members:
        - Agent
        - AgentRuntime
        - Planner
        - ActionExecutor

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

### Agent Framework

```python
from sage.libs.agents import Agent, AgentRuntime

# Define agent
agent = Agent(
    name="assistant",
    tools=[search_tool, calculator_tool],
    planner=ReActPlanner()
)

# Run agent
runtime = AgentRuntime()
result = runtime.run(agent, "What is 2+2 and search for AI news?")
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

### RAG

- [RAG Overview](../../guides/packages/sage-libs/rag/README.md)
- [RAG Components](../../guides/packages/sage-libs/rag/api_reference.md)

### Agents

- [Agents Guide](../../guides/packages/sage-libs/agents.md)
- [Agent Components](../../guides/packages/sage-libs/agents/components/)

### Tools

- [Tools Introduction](../../guides/packages/sage-libs/tools_intro.md)
- [Individual Tool Docs](../../guides/packages/sage-libs/tools/)

## Design Decisions

- [sage-libs Restructuring](../../concepts/architecture/design-decisions/sage-libs-restructuring.md)

## See Also

- [Libraries Guide](../../guides/packages/sage-libs/README.md)
- [RAG Examples](../../guides/packages/sage-libs/rag/examples/)
- [Agent Examples](../../guides/packages/sage-libs/agents/examples/)
