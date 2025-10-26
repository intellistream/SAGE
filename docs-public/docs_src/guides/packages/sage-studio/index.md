# sage-studio

Visual pipeline builder and management interface for SAGE.

**Layer**: L6 (Interface)

## Overview

`sage-studio` provides a web-based interface for building, managing, and monitoring SAGE pipelines:

- **Visual Pipeline Builder**: Drag-and-drop pipeline construction
- **Node Registry**: Catalog of available operators and services
- **Pipeline Management**: Save, load, and version pipelines
- **Execution Monitoring**: Real-time pipeline monitoring
- **Configuration UI**: Visual configuration of operators

## Features

### Visual Pipeline Builder

Build SAGE pipelines visually without writing code:

- Drag nodes from palette to canvas
- Connect nodes to define data flow
- Configure node parameters via UI
- Validate pipeline before execution
- Export to Python code

### Node Registry

Centralized registry of available components:

- **RAG Operators**: Retriever, Generator, Promptor, Refiner
- **LLM Services**: OpenAI, vLLM, custom models
- **I/O Components**: Sources (file, socket, Kafka) and Sinks
- **Custom Operators**: Register your own operators

### Pipeline Templates

Pre-built pipeline templates:

- RAG pipelines (simple, multi-stage, with reranking)
- Agent workflows
- Data processing pipelines
- Custom templates

## Installation

Install sage-studio:

```bash
pip install -e packages/sage-studio
```

With all dependencies:

```bash
pip install -e packages/sage-studio[all]
```

## Usage

### Starting Studio

```bash
# Using CLI
sage studio start

# Or directly
python -m sage.studio.app
```

The web interface will be available at `http://localhost:8501`.

### Programmatic Access

```python
from sage.studio.services.pipeline_builder import PipelineBuilder
from sage.studio.models import VisualPipeline, VisualNode

# Create visual pipeline
pipeline = VisualPipeline(
    id="my_pipeline",
    name="RAG Pipeline"
)

# Add nodes
retriever_node = VisualNode(
    id="retriever",
    type="rag.retriever",
    config={
        "collection_name": "documents",
        "top_k": 3
    }
)
pipeline.nodes.append(retriever_node)

# Build executable SAGE pipeline
builder = PipelineBuilder()
env = builder.build(pipeline)

# Execute
env.execute()
```

## Architecture

### Components

```
sage-studio/
├── models/              # Data models (VisualNode, VisualPipeline)
├── services/            # Business logic
│   ├── node_registry.py    # Node catalog
│   └── pipeline_builder.py # Pipeline conversion
└── app.py              # Web application
```

### Node Registry

Maps visual node types to SAGE operators:

```python
from sage.studio.services.node_registry import get_node_registry

registry = get_node_registry()

# Register custom operator
registry.register(
    node_type="my.custom.operator",
    operator_class=MyOperator,
    metadata={
        "label": "My Operator",
        "description": "Does something cool",
        "category": "processing"
    }
)
```

### Pipeline Builder

Converts visual pipelines to executable SAGE pipelines:

```python
from sage.studio.services.pipeline_builder import PipelineBuilder

builder = PipelineBuilder()

# Convert visual pipeline to SAGE environment
env = builder.build(visual_pipeline)

# The env can be executed like any SAGE pipeline
result = env.execute()
```

## Configuration

### Source and Sink Configuration

Studio supports various data sources and sinks:

**Sources**:
- File (JSON, CSV, text)
- Socket
- Kafka
- Database
- API
- Memory (for testing)

**Sinks**:
- Terminal
- File
- Print (with formatting)
- Memory (for testing)

See [Source/Sink Configuration Guide](../../../sage-studio/docs/SOURCE_SINK_CONFIG.md) for details.

### Node Configuration

Each node type has specific configuration parameters:

```json
{
  "node_type": "rag.retriever",
  "config": {
    "collection_name": "documents",
    "top_k": 3,
    "embedding_model": "text-embedding-3-small",
    "distance_metric": "cosine"
  }
}
```

## API Reference

### Models

#### VisualNode

Represents a node in the visual pipeline.

```python
@dataclass
class VisualNode:
    id: str
    type: str  # "rag.generator", "rag.retriever", etc.
    label: str
    position: Dict[str, float]  # {x, y}
    config: Dict[str, Any]
```

#### VisualConnection

Represents a connection between nodes.

```python
@dataclass
class VisualConnection:
    source_node: str
    source_port: str
    target_node: str
    target_port: str
```

#### VisualPipeline

Represents a complete visual pipeline.

```python
@dataclass
class VisualPipeline:
    id: str
    name: str
    nodes: List[VisualNode]
    connections: List[VisualConnection]
    
    def to_sage_pipeline(self) -> Environment:
        """Convert to executable SAGE pipeline"""
```

### Services

#### NodeRegistry

```python
class NodeRegistry:
    def register(self, node_type: str, operator_class: Type, metadata: Dict)
    def get_operator(self, node_type: str) -> Type
    def list_types(self) -> List[str]
```

#### PipelineBuilder

```python
class PipelineBuilder:
    def build(self, pipeline: VisualPipeline) -> BaseEnvironment
```

## Examples

### Building a RAG Pipeline

```python
from sage.studio.models import VisualPipeline, VisualNode, VisualConnection

# Create pipeline
pipeline = VisualPipeline(id="rag_001", name="Simple RAG")

# Add nodes
pipeline.nodes = [
    VisualNode(id="source", type="file", config={"file_path": "questions.txt"}),
    VisualNode(id="promptor", type="rag.promptor", config={}),
    VisualNode(id="retriever", type="rag.retriever", config={"collection_name": "docs"}),
    VisualNode(id="generator", type="rag.generator", config={"model": "gpt-4"}),
    VisualNode(id="sink", type="terminal", config={})
]

# Connect nodes
pipeline.connections = [
    VisualConnection("source", "out", "promptor", "in"),
    VisualConnection("promptor", "out", "retriever", "in"),
    VisualConnection("retriever", "out", "generator", "in"),
    VisualConnection("generator", "out", "sink", "in")
]

# Build and execute
from sage.studio.services.pipeline_builder import PipelineBuilder
builder = PipelineBuilder()
env = builder.build(pipeline)
env.execute()
```

## Development

### Adding Custom Nodes

1. Implement your operator (in sage-libs or sage-middleware)
2. Register it in Studio:

```python
from sage.studio.services.node_registry import get_node_registry

registry = get_node_registry()
registry.register(
    "custom.my_operator",
    MyOperator,
    {
        "label": "My Operator",
        "description": "Custom processing",
        "category": "processing",
        "inputs": ["text"],
        "outputs": ["processed_text"],
        "config_schema": {
            "param1": {"type": "string", "default": "value"},
            "param2": {"type": "integer", "default": 10}
        }
    }
)
```

### Testing

```bash
cd packages/sage-studio
pytest tests/ -v
```

## See Also

- [SAGE Architecture](../../concepts/architecture/overview.md)
- [Pipeline Builder](sage-tools/pipeline_builder.md)
- [Getting Started](../../getting-started/quickstart.md)

## Contributing

Contributions to sage-studio are welcome:

- Add new node types
- Improve UI/UX
- Add pipeline templates
- Enhance visualization

See [Community Guide](../../community/community.md) for details.
