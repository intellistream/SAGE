# SageFlow Integration with SAGE Pipeline

## Overview

This document describes how to integrate SageFlow as a component within SAGE's DataStream pipeline.
SageFlow provides high-performance C++ vector stream processing, while SAGE handles the overall
pipeline orchestration.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SAGE Pipeline                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌──────────────┐    ┌──────────────────┐    ┌────────────────────────┐    │
│   │ SAGE Source  │───►│ SAGE Map/Filter  │───►│ SageFlowOperator       │    │
│   │ (DataStream) │    │ (embedding, etc) │    │ (MapFunction wrapper)  │    │
│   └──────────────┘    └──────────────────┘    └──────────┬─────────────┘    │
│                                                           │                   │
│                                                           ▼                   │
│                       ┌─────────────────────────────────────────────┐        │
│                       │           SageFlow Engine (C++)             │        │
│                       ├─────────────────────────────────────────────┤        │
│                       │  SimpleStreamSource → Join → Sink           │        │
│                       │  (query stream)       ↑                     │        │
│                       │                       │                     │        │
│                       │  SimpleStreamSource ──┘                     │        │
│                       │  (doc stream - pre-indexed)                 │        │
│                       └─────────────────────────────────────────────┘        │
│                                                           │                   │
│                                                           ▼                   │
│   ┌────────────────────────┐    ┌──────────────────┐    ┌──────────────┐    │
│   │ SageFlow Output        │───►│ SAGE Map         │───►│ SAGE Sink    │    │
│   │ (via callback → queue) │    │ (post-process)   │    │ (output)     │    │
│   └────────────────────────┘    └──────────────────┘    └──────────────┘    │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Install SageFlow
pip install isage-flow

# Install SAGE (if not already installed)
pip install isage-middleware isage-kernel isage-common
```

## Quick Start

### Basic Usage

```python
from sage.kernel.api import LocalEnvironment
from sage.middleware.components.sage_flow import SageFlowJoinOperator

# Pre-compute document embeddings
doc_vectors = compute_embeddings(documents)  # Your embedding function
doc_ids = [doc["id"] for doc in documents]

# Create SageFlow join operator
sageflow_join = SageFlowJoinOperator(
    dim=128,
    doc_vectors=doc_vectors,
    doc_ids=doc_ids,
    similarity_threshold=0.7,
    join_method="bruteforce_lazy",
)

# Build SAGE pipeline with SageFlow as middle component
env = LocalEnvironment()
(
    env.from_collection(queries)
    .map(EmbeddingFunction)          # SAGE upstream: compute embeddings
    .map(sageflow_join)              # SageFlow: vector join
    .map(ContextAggregator)          # SAGE downstream: aggregate results
    .sink(ResponseSink)              # SAGE sink: output
)

env.execute()
```

## Available Operators

### SageFlowJoinOperator

Wraps SageFlow's vector join capability as a SAGE MapFunction.

**Use Case**: Real-time document retrieval for RAG pipelines

```python
from sage.middleware.components.sage_flow import SageFlowJoinOperator

join_op = SageFlowJoinOperator(
    dim=128,                      # Vector dimension
    doc_vectors=doc_embeddings,   # Pre-computed document vectors (N x dim)
    doc_ids=doc_ids,              # Document IDs
    similarity_threshold=0.7,     # Minimum similarity for match
    join_method="bruteforce_lazy", # Join algorithm
    window_size_ms=10000,         # Time window for streaming
    parallelism=1,                # SageFlow parallelism
)
```

**Input**: `dict` with keys:

- `id`: Query ID (int or str)
- `embedding`: Query vector (list or numpy array)
- Other fields passed through

**Output**: `dict` with keys:

- All input fields (passed through)
- `matched_docs`: List of matched document IDs
- `matched_vectors`: List of matched document vectors
- `similarity_scores`: List of similarity scores
- `join_timestamp`: Timestamp of join operation

### SageFlowAggregationOperator

Groups semantically similar queries together.

**Use Case**: Reduce redundant LLM calls by processing similar queries once

```python
from sage.middleware.components.sage_flow import SageFlowAggregationOperator

aggregation_op = SageFlowAggregationOperator(
    dim=128,                      # Vector dimension
    similarity_threshold=0.85,    # Threshold for grouping
    aggregation_window_ms=5000,   # Time window for aggregation
    min_group_size=1,             # Minimum queries to form a group
)
```

**Input**: `dict` with keys:

- `id`: Query ID
- `embedding`: Query vector
- `query`: Query text

**Output**: `dict` with keys:

- All input fields
- `is_representative`: True if this query is group representative
- `group_ids`: List of query IDs in the same group
- `group_queries`: List of query texts in the group
- `group_size`: Number of queries in the group

### SageFlowContextSource

Wraps SageFlow output as a SAGE SourceFunction.

**Use Case**: SageFlow as upstream source for SAGE pipeline

```python
from sage.middleware.components.sage_flow import SageFlowContextSource

source = SageFlowContextSource(dim=128, output_format="dict")

# Push data to SageFlow
source.push(uid=1, vec=embedding_vector)

# Use as SAGE source
env.from_source(source).map(...).sink(...)
```

## Scenarios

### Scenario 1: Streaming RAG

Real-time document retrieval for LLM context augmentation.

```python
# Pre-compute document embeddings
doc_vectors = np.array([embed(doc) for doc in documents])
doc_ids = [doc["id"] for doc in documents]

# Create join operator
join_op = SageFlowJoinOperator(
    dim=128,
    doc_vectors=doc_vectors,
    doc_ids=doc_ids,
    similarity_threshold=0.7,
)

# Pipeline
(
    env.from_source(QuerySource)
    .map(EmbeddingOperator)    # Embed queries
    .map(join_op)              # SageFlow retrieval
    .map(ContextBuilder)       # Build LLM context
    .map(LLMOperator)          # Generate response
    .sink(ResponseSink)
)
```

### Scenario 2: Similar Query Aggregation

Group similar queries to reduce LLM calls.

```python
aggregation_op = SageFlowAggregationOperator(
    dim=128,
    similarity_threshold=0.85,
    aggregation_window_ms=5000,
)

(
    env.from_source(QuerySource)
    .map(EmbeddingOperator)
    .map(aggregation_op)       # Group similar queries
    .map(GroupProcessor)       # Only process representatives
    .sink(ResponseSink)
)
```

### Scenario 3: Session Semantic State

Maintain conversation context via semantic similarity.

```python
class SessionContextBuilder(MapFunction):
    def __init__(self, dim=128, **kwargs):
        super().__init__(**kwargs)
        self.dim = dim
        self._history = []
        self._join_op = None

    def execute(self, data):
        # Update history and create join operator
        self._history.append(data)
        self._update_join_operator()

        # Find semantically related turns
        result = self._join_op.execute(data)
        return {**data, "context": result["matched_docs"]}

(
    env.from_source(ConversationSource)
    .map(SessionContextBuilder)
    .map(ResponseGenerator)
    .sink(SessionSink)
)
```

## Data Format

### SAGE → SageFlow

SAGE operators pass data as `dict[str, Any]`. SageFlow operators expect:

| Field       | Type                          | Required | Description                 |
| ----------- | ----------------------------- | -------- | --------------------------- |
| `id`        | `int` or `str`                | Yes      | Unique identifier           |
| `embedding` | `np.ndarray` or `list[float]` | Yes      | Vector embedding            |
| `query`     | `str`                         | No       | Original query text         |
| `*`         | `Any`                         | No       | Other fields passed through |

### SageFlow → SAGE

SageFlow operators return enriched `dict[str, Any]`:

| Field               | Type                | Description                 |
| ------------------- | ------------------- | --------------------------- |
| `matched_docs`      | `list[int]`         | Matched document IDs        |
| `matched_vectors`   | `list[list[float]]` | Matched document vectors    |
| `similarity_scores` | `list[float]`       | Similarity scores           |
| `join_timestamp`    | `int`               | Timestamp of join operation |

## Join Methods

SageFlow supports multiple join algorithms:

| Method             | Description         | Use Case                         |
| ------------------ | ------------------- | -------------------------------- |
| `bruteforce_lazy`  | Lazy brute force    | Small datasets, highest accuracy |
| `bruteforce_eager` | Eager brute force   | Medium datasets                  |
| `ivf`              | Inverted file index | Large datasets                   |
| `hnsw`             | Hierarchical NSW    | Very large datasets              |

## Performance Considerations

1. **Pre-compute embeddings**: Document embeddings should be computed once and reused
1. **Adjust similarity threshold**: Higher threshold = fewer matches but faster
1. **Use appropriate join method**: `bruteforce_lazy` for \<10K docs, `ivf`/`hnsw` for larger
1. **Window size**: Larger windows can improve join quality but increase latency

## Example Files

- Full demo: `examples/tutorials/L4-middleware/sage_sageflow_integrated_demo.py`
- Operator definitions: `sage/middleware/components/sage_flow/operators.py`
- SageFlow service: `sage/middleware/components/sage_flow/python/micro_service/sage_flow_service.py`

## See Also

- [SageFlow C++ Documentation](https://github.com/intellistream/sageFlow)
- [SAGE DataStream API](../../../l3-kernel/datastream.md)
- [SageFlow Independence Migration](./sageflow-independence-migration.md)
