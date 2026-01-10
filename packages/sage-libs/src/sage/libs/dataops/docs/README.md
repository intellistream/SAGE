# Dataflow Helpers

**Location**: `sage.libs.dataops`\
**Layer**: L3 (Algorithm Library)\
**Dependencies**: Pure Python, no engine dependencies

## Overview

This module provides reusable operators for data transformations used by pipelines. These are
pure-Python utilities with no runtime engine dependencies, making them lightweight and composable.

## Components

### 1. Text Operations (`text.py`)

Text processing and manipulation utilities:

- **normalize_whitespace**: Collapse multiple spaces, trim
- **truncate_text**: Truncate with suffix
- **extract_keywords**: Simple keyword extraction
- **split_sentences**: Sentence segmentation
- **deduplicate_lines**: Remove duplicate lines
- **apply_template**: Template variable substitution
- **batch_transform**: Apply transformation to list of texts

**Usage**:

```python
from sage.libs.dataops.text import normalize_whitespace, extract_keywords

text = "  Hello    world  "
normalized = normalize_whitespace(text)  # "Hello world"

keywords = extract_keywords(
    "Machine learning is transforming AI",
    stopwords={"is", "the"},
    min_length=3
)  # ["machine", "learning", "transforming"]
```

### 2. Table Operations (`table.py`)

Tabular data operations:

- **filter_rows**: Filter based on predicate
- **select_columns**: Column selection
- **aggregate**: Group by and aggregate
- **sort_rows**: Sort by column
- **pivot**: Simple pivot operation

**Usage**:

```python
from sage.libs.dataops.table import filter_rows, aggregate

data = [
    {"name": "Alice", "age": 30, "score": 85},
    {"name": "Bob", "age": 25, "score": 92},
    {"name": "Charlie", "age": 30, "score": 88},
]

# Filter
adults = filter_rows(data, lambda row: row["age"] >= 25)

# Aggregate
avg_by_age = aggregate(data, "age", "score", lambda scores: sum(scores) / len(scores))
```

### 3. JSON Operations (`json_ops.py`)

JSON schema validation and transformation:

- **validate_schema**: Simple type schema validation
- **extract_fields**: Extract specific fields (supports nested paths)
- **flatten_json**: Flatten nested JSON
- **merge_json**: Deep merge of JSON objects

**Usage**:

```python
from sage.libs.dataops.json_ops import validate_schema, flatten_json

# Validate
schema = {"name": str, "age": int}
is_valid, errors = validate_schema({"name": "Alice", "age": "30"}, schema)

# Flatten
nested = {"user": {"name": "Alice", "address": {"city": "NYC"}}}
flat = flatten_json(nested)  # {"user.name": "Alice", "user.address.city": "NYC"}
```

### 4. Sampling & Filtering (`sampling.py`)

Sampling and filtering utilities:

- **random_sample**: Random sampling with seed control
- **stratified_sample**: Stratified sampling by key
- **reservoir_sample**: Reservoir sampling for streaming
- **bucket_by**: Group items into buckets
- **filter_outliers**: Outlier detection (IQR or Z-score)

**Usage**:

```python
from sage.libs.dataops.sampling import random_sample, stratified_sample

# Random sampling
items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
sample = random_sample(items, k=5, seed=42)

# Stratified sampling
data = [("A", 1), ("B", 2), ("A", 3), ("B", 4)]
stratified = stratified_sample(data, k=2, key_fn=lambda x: x[0], seed=42)
```

## Design Principles

1. **Pure Python**: No compiled dependencies
1. **No Engine Deps**: No dataflow runtime dependencies
1. **Composable**: Functions can be chained
1. **Type Hints**: Full type annotations
1. **Fail Fast**: No silent fallbacks

## Used By

- `sage.middleware.operators` - Dataflow operators
- `sage.libs.rag` - RAG pipeline preprocessing
- `sage.libs.agentic` - Agent data transformations
- Custom pipelines and workflows

## Future Enhancements

- Feature extractors (TF-IDF, embeddings integration)
- Schema inference from data
- More advanced text processing (NER, tokenization)
- DataFrame-style operations (if needed)

## Migration Notes

This module consolidates data transformation utilities previously scattered across:

- `sage.libs.foundation.io` (batch operations)
- Various adhoc implementations in middleware operators
- Text processing utils from RAG components

All utilities now follow consistent naming and interfaces.
