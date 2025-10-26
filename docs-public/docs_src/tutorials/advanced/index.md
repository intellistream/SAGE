# Advanced Tutorials

Advanced topics for experienced SAGE users.

## Distributed Pipeline

Build scalable distributed pipelines.

### Setup Distributed Environment

```python
from sage.kernel.api.local_environment import LocalStreamEnvironment

# Create distributed environment
env = LocalStreamEnvironment(
    "distributed_app",
    config={
        "execution_mode": "distributed",
        "ray": {
            "address": "ray://cluster-head:10001",
            "num_cpus": 16,
            "num_gpus": 2
        }
    }
)
```

### Distributed RAG Pipeline

```python
from sage.libs.io.sources import ChunkedFileSource
from sage.middleware.rag.operators import (
    VLLMEmbeddingOperator,
    ChromaUpsertOperator
)

# Distributed embedding and indexing
stream = (env.from_source(ChunkedFileSource("large_docs/"))
    .map(VLLMEmbeddingOperator(
        model="sentence-transformers/all-MiniLM-L6-v2"
    ), parallelism=8)  # Parallel embedding
    .to_sink(ChromaUpsertOperator(
        collection="distributed_docs"
    )))

env.execute()
```

### Multi-Node Processing

```python
# Process data across multiple nodes
from sage.kernel.api.datastream import DataStream

def create_distributed_pipeline(env):
    # Node 1: Data loading
    loaded = env.from_source(large_source).map(
        LoadOperator(),
        parallelism=4
    )
    
    # Node 2: Heavy computation
    processed = loaded.map(
        HeavyComputeOperator(),
        parallelism=8,
        resources={"num_cpus": 4, "memory": "8GB"}
    )
    
    # Node 3: GPU inference
    predicted = processed.map(
        GPUInferenceOperator(),
        parallelism=2,
        resources={"num_gpus": 1}
    )
    
    # Node 4: Aggregation
    aggregated = predicted.reduce(
        AggregateOperator()
    )
    
    return aggregated
```

## Custom Operators

Create reusable custom operators.

### Base Custom Operator

```python
from sage.kernel.api.function import MapFunction, RuntimeContext

class CustomOperator(MapFunction):
    """
    Template for custom operators.
    """
    
    def __init__(self, config: dict):
        """Initialize with configuration."""
        self.config = config
        self.state = None
    
    def open(self, context: RuntimeContext):
        """
        Initialize resources.
        Called once per parallel instance.
        """
        self.context = context
        self.state = self._initialize_state()
    
    def map(self, record):
        """
        Process a single record.
        Called for each record.
        """
        return self._process(record)
    
    def close(self):
        """
        Clean up resources.
        Called once when operator terminates.
        """
        if self.state:
            self.state.cleanup()
    
    def _initialize_state(self):
        """Override to initialize custom state."""
        return {}
    
    def _process(self, record):
        """Override to implement custom logic."""
        return record
```

### LLM Operator Example

```python
from openai import OpenAI

class CustomLLMOperator(MapFunction):
    """
    Custom LLM operator with retry logic and caching.
    """
    
    def __init__(self, model="gpt-4", max_retries=3):
        self.model = model
        self.max_retries = max_retries
        self.cache = {}
    
    def open(self, context):
        self.client = OpenAI()
        self.logger = context.get_logger()
    
    def map(self, record):
        prompt = record.get("prompt")
        
        # Check cache
        if prompt in self.cache:
            self.logger.info("Cache hit")
            return self.cache[prompt]
        
        # Generate with retries
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                result = response.choices[0].message.content
                
                # Cache result
                self.cache[prompt] = result
                return result
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
```

### Filter Operator Example

```python
from sage.kernel.api.function import FilterFunction

class CustomFilterOperator(FilterFunction):
    """
    Custom filter with complex conditions.
    """
    
    def __init__(self, min_score=0.5, required_fields=None):
        self.min_score = min_score
        self.required_fields = required_fields or []
    
    def filter(self, record) -> bool:
        # Check required fields
        for field in self.required_fields:
            if field not in record:
                return False
        
        # Check score threshold
        if record.get("score", 0) < self.min_score:
            return False
        
        # Custom validation logic
        return self._validate(record)
    
    def _validate(self, record):
        """Override for custom validation."""
        return True
```

### Stateful Operator Example

```python
class WindowAggregateOperator(MapFunction):
    """
    Aggregate records over a time window.
    """
    
    def __init__(self, window_size=10, aggregate_fn=None):
        self.window_size = window_size
        self.aggregate_fn = aggregate_fn or (lambda x: sum(x) / len(x))
        self.window = []
    
    def map(self, record):
        self.window.append(record)
        
        if len(self.window) >= self.window_size:
            result = self.aggregate_fn(self.window)
            self.window = []
            return result
        
        return None  # No output until window is full
```

## Complex Workflows

Build sophisticated multi-stage workflows.

### Multi-Branch Pipeline

```python
def create_branching_pipeline(env):
    # Main stream
    main_stream = env.from_source(source)
    
    # Branch 1: NLP processing
    nlp_stream = (main_stream
        .filter(lambda r: r.type == "text")
        .map(TokenizeOperator())
        .map(NEROperator())
        .to_sink(nlp_sink))
    
    # Branch 2: Vision processing
    vision_stream = (main_stream
        .filter(lambda r: r.type == "image")
        .map(ResizeOperator())
        .map(ObjectDetectionOperator())
        .to_sink(vision_sink))
    
    # Branch 3: Audio processing
    audio_stream = (main_stream
        .filter(lambda r: r.type == "audio")
        .map(TranscribeOperator())
        .map(SentimentOperator())
        .to_sink(audio_sink))
    
    return env
```

### Join Multiple Streams

```python
from sage.kernel.api.datastream import DataStream

def create_join_pipeline(env):
    # Stream 1: User data
    users = env.from_source(user_source).key_by(lambda r: r.user_id)
    
    # Stream 2: Event data
    events = env.from_source(event_source).key_by(lambda r: r.user_id)
    
    # Join streams
    joined = users.join(events).map(lambda pair: {
        "user": pair[0],
        "event": pair[1],
        "enriched": enrich(pair[0], pair[1])
    })
    
    joined.to_sink(output_sink)
    return env
```

### Iterative Refinement

```python
class IterativeRefinementOperator(MapFunction):
    """
    Iteratively refine results until quality threshold.
    """
    
    def __init__(self, max_iterations=5, quality_threshold=0.9):
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold
    
    def map(self, record):
        result = record
        
        for iteration in range(self.max_iterations):
            # Process/refine result
            result = self.process(result)
            
            # Check quality
            quality = self.evaluate_quality(result)
            
            if quality >= self.quality_threshold:
                result["iterations"] = iteration + 1
                return result
        
        # Return best effort
        result["iterations"] = self.max_iterations
        result["warning"] = "Max iterations reached"
        return result
    
    def process(self, record):
        # Implement refinement logic
        return record
    
    def evaluate_quality(self, record):
        # Implement quality metric
        return 0.0
```

## Advanced RAG

Build sophisticated RAG systems.

### Multi-Source RAG

```python
from sage.middleware.rag.operators import (
    ChromaRetrieverOperator,
    OpenAIGeneratorOperator,
    ContextFusionOperator
)

def create_multi_source_rag(env):
    # Query stream
    queries = env.from_source(query_source)
    
    # Retrieve from multiple sources
    docs_retriever = ChromaRetrieverOperator(collection="documents")
    code_retriever = ChromaRetrieverOperator(collection="code")
    web_retriever = ChromaRetrieverOperator(collection="web")
    
    # Parallel retrieval
    doc_results = queries.map(docs_retriever, parallelism=2)
    code_results = queries.map(code_retriever, parallelism=2)
    web_results = queries.map(web_retriever, parallelism=2)
    
    # Fuse contexts
    fused = (doc_results
        .union(code_results)
        .union(web_results)
        .map(ContextFusionOperator()))
    
    # Generate response
    responses = fused.map(OpenAIGeneratorOperator(
        model="gpt-4",
        temperature=0.7
    ))
    
    responses.to_sink(output_sink)
    return env
```

### Hierarchical RAG

```python
class HierarchicalRAGOperator(MapFunction):
    """
    Two-stage retrieval: coarse then fine.
    """
    
    def __init__(self):
        self.coarse_retriever = ChromaRetrieverOperator(
            collection="summaries",
            top_k=20
        )
        self.fine_retriever = ChromaRetrieverOperator(
            collection="chunks",
            top_k=5
        )
    
    def open(self, context):
        self.coarse_retriever.open(context)
        self.fine_retriever.open(context)
    
    def map(self, query):
        # Stage 1: Coarse retrieval
        coarse_results = self.coarse_retriever.map(query)
        
        # Extract document IDs
        doc_ids = [r["doc_id"] for r in coarse_results]
        
        # Stage 2: Fine retrieval within selected docs
        query_with_filter = {
            **query,
            "filter": {"doc_id": {"$in": doc_ids}}
        }
        fine_results = self.fine_retriever.map(query_with_filter)
        
        return {
            "query": query,
            "coarse_results": coarse_results,
            "fine_results": fine_results
        }
```

### RAG with Re-ranking

```python
from sage.middleware.rag.operators import RerankOperator

def create_reranking_rag(env):
    stream = (env.from_source(query_source)
        # Initial retrieval (high recall)
        .map(ChromaRetrieverOperator(
            collection="docs",
            top_k=50
        ))
        # Re-rank (high precision)
        .map(RerankOperator(
            model="cross-encoder/ms-marco-MiniLM-L-12-v2",
            top_k=5
        ))
        # Generate with best contexts
        .map(OpenAIGeneratorOperator(
            model="gpt-4"
        ))
        .to_sink(output_sink))
    
    return env
```

## Performance Tuning

Optimize SAGE applications for production.

### Profiling

```python
import cProfile
import pstats
from sage.kernel.api.local_environment import LocalStreamEnvironment

def profile_pipeline():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run pipeline
    env = LocalStreamEnvironment("profiling_app")
    create_pipeline(env)
    env.execute()
    
    profiler.disable()
    
    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    
    print("\n=== Top 20 Functions by Cumulative Time ===")
    stats.print_stats(20)
    
    print("\n=== Top 20 Functions by Total Time ===")
    stats.sort_stats('tottime')
    stats.print_stats(20)
```

### Memory Optimization

```python
import gc
from memory_profiler import profile

class MemoryEfficientOperator(MapFunction):
    """
    Process large data with controlled memory usage.
    """
    
    @profile
    def map(self, record):
        # Process in chunks
        results = []
        for chunk in self.chunk_data(record):
            result = self.process_chunk(chunk)
            results.append(result)
            
            # Explicit cleanup
            del chunk
            gc.collect()
        
        return self.merge_results(results)
    
    def chunk_data(self, record, chunk_size=1000):
        data = record.get("data", [])
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]
    
    def process_chunk(self, chunk):
        return [self.process_item(item) for item in chunk]
    
    def merge_results(self, results):
        return [item for chunk in results for item in chunk]
```

### Batch Optimization

```python
class BatchedLLMOperator(MapFunction):
    """
    Batch LLM requests for efficiency.
    """
    
    def __init__(self, batch_size=10, batch_timeout=1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.buffer = []
        self.last_batch_time = time.time()
    
    def map(self, record):
        self.buffer.append(record)
        
        # Check if batch is ready
        batch_ready = (
            len(self.buffer) >= self.batch_size or
            time.time() - self.last_batch_time > self.batch_timeout
        )
        
        if batch_ready:
            results = self.process_batch(self.buffer)
            self.buffer = []
            self.last_batch_time = time.time()
            return results
        
        return None
    
    def process_batch(self, batch):
        # Batch API call
        prompts = [r["prompt"] for r in batch]
        responses = self.llm.batch_generate(prompts)
        return [
            {"prompt": p, "response": r}
            for p, r in zip(prompts, responses)
        ]
```

## Fault Tolerance

Build resilient pipelines.

### Checkpointing

```python
env = LocalStreamEnvironment(
    "fault_tolerant_app",
    config={
        "fault_tolerance": {
            "strategy": "checkpoint",
            "checkpoint_interval": 60.0,
            "checkpoint_dir": "/data/checkpoints",
            "checkpoint_mode": "exactly_once"
        }
    }
)

# Pipeline will automatically checkpoint
stream = (env.from_source(source)
    .map(operator1)
    .map(operator2)
    .to_sink(sink))

env.execute()
```

### Retry Logic

```python
class RetryOperator(MapFunction):
    """
    Retry failed operations with exponential backoff.
    """
    
    def __init__(self, max_retries=3, base_delay=1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def map(self, record):
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return self.process(record)
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed, "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"All retries failed: {e}")
        
        # All retries failed
        raise last_error
    
    def process(self, record):
        # Implement processing logic
        return record
```

## See Also

- [Best Practices](../../guides/best-practices/index.md)
- [API Reference](../../api-reference/index.md)
- [Architecture](../../concepts/architecture/overview.md)
