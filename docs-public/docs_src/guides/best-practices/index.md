# Best Practices

Recommended patterns and practices for SAGE development.

## Pipeline Design

### 1. Single Responsibility

Keep operators focused:

```python
# ❌ Bad: Operator does too much
class ProcessEverything(MapFunction):
    def map(self, record):
        # Load data, transform, validate, save...
        pass

# ✅ Good: Separate concerns
class LoadData(MapFunction):
    def map(self, record):
        return load_data(record)

class TransformData(MapFunction):
    def map(self, record):
        return transform(record)

class ValidateData(FilterFunction):
    def filter(self, record):
        return is_valid(record)
```

### 2. Stateless Operators

Avoid shared state:

```python
# ❌ Bad: Shared state between records
class StatefulOperator(MapFunction):
    def __init__(self):
        self.cache = {}  # Shared across records
    
    def map(self, record):
        if record.id in self.cache:
            return self.cache[record.id]
        result = process(record)
        self.cache[record.id] = result
        return result

# ✅ Good: Stateless processing
class StatelessOperator(MapFunction):
    def map(self, record):
        return process(record)
```

### 3. Clear Data Flow

Make pipelines readable:

```python
# ✅ Good: Clear, linear flow
stream = (env.from_source(source)
    .map(load_operator)
    .filter(validate_operator)
    .map(transform_operator)
    .map(enrich_operator)
    .to_sink(sink))

# Better: Named intermediate streams
loaded = env.from_source(source).map(load_operator)
validated = loaded.filter(validate_operator)
transformed = validated.map(transform_operator)
enriched = transformed.map(enrich_operator)
enriched.to_sink(sink)
```

### 4. Error Handling

Handle errors gracefully:

```python
class RobustOperator(MapFunction):
    def map(self, record):
        try:
            return process(record)
        except ValueError as e:
            # Log and skip invalid records
            logger.warning(f"Invalid record: {e}")
            return None
        except Exception as e:
            # Log and raise unexpected errors
            logger.error(f"Unexpected error: {e}")
            raise
```

## Performance Optimization

### 1. Batch Processing

Process records in batches:

```python
class BatchOperator(MapFunction):
    def __init__(self, batch_size=32):
        self.batch_size = batch_size
        self.buffer = []
    
    def map(self, record):
        self.buffer.append(record)
        if len(self.buffer) >= self.batch_size:
            results = process_batch(self.buffer)
            self.buffer = []
            return results
        return None
```

### 2. Parallel Execution

Use parallelism wisely:

```python
# CPU-bound operations
stream.map(cpu_intensive_op, parallelism=8)

# I/O-bound operations
stream.map(io_intensive_op, parallelism=16)

# GPU operations
stream.map(gpu_op, parallelism=1)  # Typically 1 per GPU
```

### 3. Resource Management

Manage resources carefully:

```python
class ResourceAwareOperator(MapFunction):
    def open(self, context):
        # Initialize expensive resources once
        self.model = load_model()
        self.db_connection = connect_db()
    
    def map(self, record):
        # Reuse resources
        return self.model.process(record)
    
    def close(self):
        # Clean up resources
        self.db_connection.close()
```

### 4. Caching

Cache expensive computations:

```python
from functools import lru_cache

class CachingOperator(MapFunction):
    @lru_cache(maxsize=1000)
    def expensive_computation(self, key):
        return compute(key)
    
    def map(self, record):
        return self.expensive_computation(record.key)
```

## Code Organization

### 1. Project Structure

Organize your SAGE project:

```
my-sage-app/
├── src/
│   ├── __init__.py
│   ├── operators/
│   │   ├── __init__.py
│   │   ├── load.py
│   │   ├── transform.py
│   │   └── validate.py
│   ├── pipelines/
│   │   ├── __init__.py
│   │   └── main_pipeline.py
│   ├── sources/
│   │   └── data_source.py
│   └── sinks/
│       └── output_sink.py
├── tests/
│   ├── test_operators.py
│   └── test_pipeline.py
├── config/
│   └── production.yaml
├── requirements.txt
└── main.py
```

### 2. Configuration Management

Separate code from configuration:

```python
# config/settings.py
from pydantic import BaseModel

class PipelineConfig(BaseModel):
    batch_size: int = 32
    parallelism: int = 4
    checkpoint_interval: float = 60.0

# main.py
from config.settings import PipelineConfig

config = PipelineConfig()
stream.map(operator, parallelism=config.parallelism)
```

### 3. Reusable Components

Create reusable operator libraries:

```python
# src/operators/base.py
class BaseOperator(MapFunction):
    def __init__(self, config):
        self.config = config
    
    def open(self, context):
        self.setup()
    
    def setup(self):
        """Override in subclasses"""
        pass

# src/operators/llm.py
class LLMOperator(BaseOperator):
    def setup(self):
        self.client = OpenAI(api_key=self.config.api_key)
    
    def map(self, record):
        return self.client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": record.text}]
        )
```

## Testing

### 1. Unit Tests

Test operators in isolation:

```python
import pytest
from src.operators.transform import TransformOperator

def test_transform_operator():
    operator = TransformOperator()
    
    # Test with valid input
    result = operator.map({"value": 10})
    assert result["value"] == 20
    
    # Test with invalid input
    with pytest.raises(ValueError):
        operator.map({"value": -1})
```

### 2. Integration Tests

Test pipelines end-to-end:

```python
def test_pipeline():
    env = LocalStreamEnvironment("test")
    
    # Create test data
    test_data = [{"id": 1}, {"id": 2}]
    source = ListSource(test_data)
    sink = CollectSink()
    
    # Build and execute pipeline
    stream = (env.from_source(source)
        .map(TransformOperator())
        .to_sink(sink))
    
    env.execute()
    
    # Verify results
    results = sink.get_results()
    assert len(results) == 2
```

### 3. Mock External Services

Mock LLMs and APIs:

```python
from unittest.mock import Mock, patch

def test_llm_operator():
    with patch('openai.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Test response"))]
        )
        
        operator = LLMOperator()
        result = operator.map({"text": "Test input"})
        assert result == "Test response"
```

### 4. Test Data Management

Use conftest.py for test fixtures:

```python
# tests/conftest.py
import pytest

@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("data")
    # Create test data
    (data_dir / "test.csv").write_text("id,value\n1,10\n2,20\n")
    return data_dir

# tests/test_pipeline.py
def test_with_real_data(test_data_dir):
    source = CSVSource(test_data_dir / "test.csv")
    # Test with real data structure
```

## Debugging

### 1. Logging

Use structured logging:

```python
import logging
logger = logging.getLogger(__name__)

class DebugOperator(MapFunction):
    def map(self, record):
        logger.info("Processing record", extra={
            "record_id": record.id,
            "stage": "transform"
        })
        try:
            result = process(record)
            logger.debug("Processed successfully", extra={
                "record_id": record.id,
                "output_size": len(result)
            })
            return result
        except Exception as e:
            logger.error("Processing failed", extra={
                "record_id": record.id,
                "error": str(e)
            }, exc_info=True)
            raise
```

### 2. Profiling

Profile performance:

```python
import cProfile
import pstats

def profile_pipeline():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run pipeline
    env.execute()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

### 3. Checkpointing

Enable checkpointing for debugging:

```python
env = LocalStreamEnvironment(
    "debug_app",
    config={
        "fault_tolerance": {
            "strategy": "checkpoint",
            "checkpoint_interval": 10.0,  # Checkpoint frequently
            "checkpoint_dir": "./checkpoints"
        }
    }
)
```

### 4. Incremental Development

Develop incrementally:

```python
# 1. Start with simple pipeline
stream = env.from_source(source).to_sink(sink)
env.execute()  # Verify data flow

# 2. Add one operator at a time
stream = env.from_source(source).map(op1).to_sink(sink)
env.execute()  # Verify op1

# 3. Continue adding operators
stream = (env.from_source(source)
    .map(op1)
    .map(op2)
    .to_sink(sink))
env.execute()  # Verify op1 + op2
```

## LLM Integration

### 1. Prompt Engineering

Structure prompts clearly:

```python
class LLMPromptOperator(MapFunction):
    PROMPT_TEMPLATE = """
Task: {task}

Context:
{context}

Input:
{input}

Instructions:
- Be concise
- Use examples
- Cite sources

Output:
"""
    
    def map(self, record):
        prompt = self.PROMPT_TEMPLATE.format(
            task=record.task,
            context=record.context,
            input=record.input
        )
        return self.llm.generate(prompt)
```

### 2. Rate Limiting

Respect API rate limits:

```python
import time
from threading import Lock

class RateLimitedOperator(MapFunction):
    def __init__(self, calls_per_second=10):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0
        self.lock = Lock()
    
    def map(self, record):
        with self.lock:
            elapsed = time.time() - self.last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_call = time.time()
        
        return self.llm.generate(record.text)
```

### 3. Cost Monitoring

Track API costs:

```python
class CostAwareOperator(MapFunction):
    def __init__(self):
        self.total_tokens = 0
        self.total_cost = 0.0
    
    def map(self, record):
        response = self.llm.generate(record.text)
        
        # Track usage
        tokens = response.usage.total_tokens
        cost = tokens * 0.000002  # $0.002 per 1K tokens
        
        self.total_tokens += tokens
        self.total_cost += cost
        
        if self.total_cost > 10.0:  # Alert if cost > $10
            logger.warning(f"High cost: ${self.total_cost:.2f}")
        
        return response.text
```

## See Also

- [Deployment Guide](../deployment/index.md)
- [Architecture](../../concepts/architecture/overview.md)
- [API Reference](../../api-reference/index.md)
