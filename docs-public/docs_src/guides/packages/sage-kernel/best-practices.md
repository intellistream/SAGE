# SAGE Kernel Best Practices

This guide covers best practices for developing with SAGE Kernel, based on real-world usage patterns
and performance considerations.

## Architecture Best Practices

### Environment Selection

**Use LocalEnvironment for:**

- Development and testing
- Single-machine deployments
- Prototyping and experimentation
- CPU-intensive tasks on local hardware

**Use RemoteEnvironment for:**

- Production deployments
- Distributed processing
- GPU-accelerated workloads
- High-availability requirements

```python
# Development
dev_env = LocalEnvironment(config={"debug": True, "log_level": "DEBUG"})

# Production
prod_env = RemoteEnvironment(
    endpoint="https://api.sage-cluster.com",
    config={"timeout": 30, "retry_attempts": 3, "failover_enabled": True},
)
```

### Stream Design Patterns

#### 1. Single Responsibility Streams

Keep each stream focused on a single type of data or operation:

```python
# Good: Focused streams
user_events = env.create_stream("user_events")
system_metrics = env.create_stream("system_metrics")
error_logs = env.create_stream("error_logs")

# Avoid: Mixed-purpose streams
everything_stream = env.create_stream("everything")  # Too broad
```

#### 2. Hierarchical Stream Organization

Organize streams in a hierarchy for complex systems:

```python
# Main data streams
raw_data = env.create_stream("raw_data")

# Processing stages
cleaned_data = raw_data.map(clean_data_func)
enriched_data = cleaned_data.map(enrich_func)
final_output = enriched_data.filter(quality_filter)
```

#### 3. Error Stream Separation

Separate error handling into dedicated streams:

```python
def process_with_errors(data):
    try:
        return process_data(data), None
    except Exception as e:
        return None, str(e)


results, errors = main_stream.map(process_with_errors).split()
errors.filter(lambda x: x is not None).sink(error_handler)
```

## Performance Optimization

### Memory Management

#### 1. Stream Buffer Configuration

Configure appropriate buffer sizes based on your data volume:

```python
# High-throughput streams
high_volume_stream = env.create_stream(
    "high_volume", config={"buffer_size": 10000, "buffer_policy": "drop_oldest"}
)

# Low-latency streams
low_latency_stream = env.create_stream(
    "low_latency", config={"buffer_size": 100, "buffer_policy": "block"}
)
```

#### 2. Resource Cleanup

Always clean up resources properly:

```python
try:
    # Stream processing
    stream = env.create_stream("data")
    result = stream.process(processor_func)
finally:
    # Cleanup
    if stream:
        stream.close()
    env.cleanup()
```

#### 3. Lazy Evaluation

Use lazy evaluation for large datasets:

```python
# Good: Lazy evaluation
large_dataset = env.create_stream("large_data")
filtered = large_dataset.filter(filter_func)
result = filtered.take(1000)  # Only process what's needed

# Avoid: Eager evaluation of large datasets
all_data = large_dataset.collect()  # Loads everything into memory
```

### Processing Optimization

#### 1. Batch Processing

Process data in batches for better throughput:

```python
def batch_processor(batch):
    # Process multiple items together
    return [process_item(item) for item in batch]


# Process in batches of 100
stream.batch(100).map(batch_processor)
```

#### 2. Parallel Processing

Leverage parallelism for CPU-intensive tasks:

```python
from concurrent.futures import ThreadPoolExecutor


def parallel_map(stream, func, max_workers=4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return stream.map_parallel(func, executor)


# Use for I/O bound operations
result = parallel_map(stream, io_intensive_func)
```

#### 3. Pipeline Optimization

Optimize processing pipelines:

```python
# Good: Combine operations
optimized = (
    stream.filter(expensive_filter)  # Filter early
    .map(transform_func)  # Transform remaining items
    .batch(100)  # Batch for efficiency
    .map(batch_process)  # Process batches
)

# Avoid: Inefficient ordering
inefficient = stream.map(expensive_transform).filter(  # Transform everything first
    simple_filter
)  # Then filter (wasteful)
```

## Error Handling and Resilience

### Exception Management

#### 1. Graceful Degradation

Implement graceful degradation for non-critical failures:

```python
def resilient_processor(data):
    try:
        return expensive_operation(data)
    except NonCriticalError as e:
        logger.warning(f"Non-critical error: {e}")
        return fallback_operation(data)
    except CriticalError:
        raise  # Let critical errors bubble up
```

#### 2. Circuit Breaker Pattern

Implement circuit breakers for external dependencies:

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise e


# Usage
circuit_breaker = CircuitBreaker()
result = stream.map(lambda x: circuit_breaker.call(external_api, x))
```

#### 3. Retry Mechanisms

Implement intelligent retry mechanisms:

```python
import time
import random


def retry_with_backoff(func, max_retries=3, base_delay=1):
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e

                # Exponential backoff with jitter
                delay = base_delay * (2**attempt) + random.uniform(0, 1)
                time.sleep(delay)

    return wrapper


# Apply to stream operations
reliable_processor = retry_with_backoff(unreliable_operation)
stream.map(reliable_processor)
```

## Security Best Practices

### Data Protection

#### 1. Sensitive Data Handling

```python
def secure_processor(data):
    # Remove or mask sensitive fields
    if "ssn" in data:
        data["ssn"] = "***-**-" + data["ssn"][-4:]

    if "credit_card" in data:
        data["credit_card"] = mask_credit_card(data["credit_card"])

    return data


# Apply security processing early in pipeline
secure_stream = raw_stream.map(secure_processor)
```

#### 2. Input Validation

```python
def validate_input(data):
    required_fields = ["id", "timestamp", "value"]

    # Check required fields
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Validate data types
    if not isinstance(data["id"], str):
        raise ValueError("ID must be string")

    if not isinstance(data["value"], (int, float)):
        raise ValueError("Value must be numeric")

    return data


validated_stream = input_stream.map(validate_input)
```

### Authentication and Authorization

```python
def authenticate_request(request):
    token = request.get("auth_token")
    if not token or not verify_token(token):
        raise AuthenticationError("Invalid token")
    return request


def authorize_operation(request, required_permission):
    user = get_user_from_token(request["auth_token"])
    if not user.has_permission(required_permission):
        raise AuthorizationError("Insufficient permissions")
    return request


# Apply security checks
secure_stream = (
    input_stream.map(authenticate_request)
    .map(lambda req: authorize_operation(req, "data.read"))
    .map(process_authorized_request)
)
```

## Testing Strategies

### Unit Testing

```python
import unittest
from sage.core.api import LocalEnvironment


class TestStreamProcessing(unittest.TestCase):
    def setUp(self):
        self.env = LocalEnvironment()
        self.test_data = [1, 2, 3, 4, 5]

    def tearDown(self):
        self.env.cleanup()

    def test_basic_mapping(self):
        stream = self.env.create_stream("test")

        # Add test data
        for item in self.test_data:
            stream.write(item)
        stream.close()

        # Test mapping
        result = stream.map(lambda x: x * 2).collect()
        expected = [x * 2 for x in self.test_data]

        self.assertEqual(result, expected)

    def test_error_handling(self):
        stream = self.env.create_stream("error_test")

        def failing_func(x):
            if x == 3:
                raise ValueError("Test error")
            return x

        # Test that errors are handled properly
        with self.assertRaises(ValueError):
            stream.map(failing_func).collect()
```

### Integration Testing

```python
class TestIntegration(unittest.TestCase):
    def test_end_to_end_pipeline(self):
        env = LocalEnvironment()

        # Create test pipeline
        input_stream = env.create_stream("input")
        processed = (
            input_stream.filter(lambda x: x > 0)
            .map(lambda x: x * 2)
            .reduce(lambda a, b: a + b)
        )

        # Test with known data
        test_data = [1, -1, 2, -2, 3]
        for item in test_data:
            input_stream.write(item)

        result = processed.collect()
        expected = sum(x * 2 for x in test_data if x > 0)

        self.assertEqual(result, expected)
```

### Performance Testing

```python
import time
import psutil


def measure_performance(stream_operation, data_size=10000):
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss

    # Run operation
    result = stream_operation(data_size)

    end_time = time.time()
    end_memory = psutil.Process().memory_info().rss

    return {
        "execution_time": end_time - start_time,
        "memory_usage": end_memory - start_memory,
        "result_size": len(result),
    }


# Test different configurations
def test_buffer_sizes():
    configs = [100, 1000, 10000]
    results = {}

    for buffer_size in configs:
        env = LocalEnvironment(config={"buffer_size": buffer_size})

        def operation(size):
            stream = env.create_stream("test")
            return stream.map(lambda x: x * 2).take(size)

        results[buffer_size] = measure_performance(operation)

    return results
```

## Monitoring and Observability

### Logging Best Practices

```python
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def logged_processor(data):
    try:
        logger.info(f"Processing item: {data.get('id', 'unknown')}")
        result = process_data(data)
        logger.info(f"Successfully processed item: {data.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Failed to process item {data.get('id')}: {str(e)}")
        raise


stream.map(logged_processor)
```

### Metrics Collection

```python
from collections import defaultdict
import time


class StreamMetrics:
    def __init__(self):
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)
        self.gauges = defaultdict(float)

    def increment(self, name, value=1):
        self.counters[name] += value

    def time_operation(self, name, func, *args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            self.increment(f"{name}.success")
            return result
        except Exception as e:
            self.increment(f"{name}.error")
            raise
        finally:
            duration = time.time() - start_time
            self.timers[name].append(duration)

    def set_gauge(self, name, value):
        self.gauges[name] = value


# Usage
metrics = StreamMetrics()


def monitored_processor(data):
    return metrics.time_operation("process_data", process_data, data)


stream.map(monitored_processor)
```

### Health Checks

```python
class HealthChecker:
    def __init__(self, environment):
        self.environment = environment
        self.checks = []

    def add_check(self, name, check_func):
        self.checks.append((name, check_func))

    def run_checks(self):
        results = {}
        for name, check_func in self.checks:
            try:
                results[name] = {
                    "status": "healthy" if check_func() else "unhealthy",
                    "timestamp": time.time(),
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": time.time(),
                }
        return results


# Setup health checks
health = HealthChecker(env)
health.add_check("stream_connectivity", lambda: env.test_connection())
health.add_check("memory_usage", lambda: psutil.virtual_memory().percent < 80)

# Run periodically
health_status = health.run_checks()
```

## Deployment Best Practices

### Configuration Management

```python
import os
from typing import Dict, Any


class Config:
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        return {
            "environment": os.getenv("SAGE_ENV", "development"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "buffer_size": int(os.getenv("BUFFER_SIZE", "1000")),
            "max_workers": int(os.getenv("MAX_WORKERS", "4")),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "database_url": os.getenv("DATABASE_URL", "sqlite:///local.db"),
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)


# Usage
config = Config()
env = LocalEnvironment(
    config={
        "buffer_size": config.get("buffer_size"),
        "log_level": config.get("log_level"),
    }
)
```

### Container Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV SAGE_ENV=production
ENV LOG_LEVEL=INFO

# Run application
CMD ["python", "-m", "sage.cli", "serve"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  sage-kernel:
    build: .
    environment:
      - SAGE_ENV=production
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    ports:
      - "8000:8000"

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Production Monitoring

```python
# monitoring.py
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
REQUEST_COUNT = Counter("sage_requests_total", "Total requests", ["method", "endpoint"])
REQUEST_DURATION = Histogram("sage_request_duration_seconds", "Request duration")
ACTIVE_STREAMS = Gauge("sage_active_streams", "Number of active streams")


def monitor_stream_operation(operation_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            REQUEST_COUNT.labels(method="stream", endpoint=operation_name).inc()

            with REQUEST_DURATION.time():
                result = func(*args, **kwargs)

            return result

        return wrapper

    return decorator


# Usage in stream operations
@monitor_stream_operation("data_processing")
def process_data(data):
    return transform(data)
```

This comprehensive guide should help you build robust, performant, and maintainable applications
with SAGE Kernel.
