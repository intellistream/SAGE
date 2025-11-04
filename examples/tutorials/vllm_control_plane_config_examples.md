# SAGE vLLM Control Plane Configuration Examples

## Example 1: Basic Single Instance Configuration

```toml
[services.llm_basic]
type = "ControlPlaneVLLMService"
scheduling_policy = "fifo"
enable_pd_separation = false
routing_strategy = "load_balanced"
default_priority = "NORMAL"
default_max_tokens = 512

[[services.llm_basic.instances]]
instance_id = "llm-1"
host = "localhost"
port = 8000
model_name = "meta-llama/Llama-2-7b-hf"
tensor_parallel_size = 1
gpu_count = 1
```

## Example 2: Multi-Instance Load Balancing

```toml
[services.llm_multi]
type = "ControlPlaneVLLMService"
scheduling_policy = "adaptive"
enable_pd_separation = false
routing_strategy = "load_balanced"

[[services.llm_multi.instances]]
instance_id = "llm-1"
host = "localhost"
port = 8000
model_name = "meta-llama/Llama-2-7b-hf"
tensor_parallel_size = 1
gpu_count = 1

[[services.llm_multi.instances]]
instance_id = "llm-2"
host = "localhost"
port = 8001
model_name = "meta-llama/Llama-2-7b-hf"
tensor_parallel_size = 1
gpu_count = 1

[[services.llm_multi.instances]]
instance_id = "llm-3"
host = "localhost"
port = 8002
model_name = "meta-llama/Llama-2-7b-hf"
tensor_parallel_size = 2
gpu_count = 2
```

## Example 3: Prefilling/Decoding Separation (Recommended for Production)

```toml
[services.llm_pd_separated]
type = "ControlPlaneVLLMService"
scheduling_policy = "slo_aware"
enable_pd_separation = true  # Enable PD separation for +50-80% throughput
routing_strategy = "topology_aware"
default_slo_deadline_ms = 1000

# Prefilling instance - optimized for initial token generation
[[services.llm_pd_separated.instances]]
instance_id = "llm-prefill-1"
host = "localhost"
port = 8000
model_name = "meta-llama/Llama-2-7b-hf"
instance_type = "PREFILLING"
tensor_parallel_size = 4  # Higher TP for prefilling
gpu_count = 4
gpu_memory_gb = 80.0
max_concurrent_requests = 128

# Decoding instances - optimized for token-by-token generation
[[services.llm_pd_separated.instances]]
instance_id = "llm-decode-1"
host = "localhost"
port = 8001
model_name = "meta-llama/Llama-2-7b-hf"
instance_type = "DECODING"
tensor_parallel_size = 1  # Lower TP for decoding
gpu_count = 1
gpu_memory_gb = 80.0
max_concurrent_requests = 256

[[services.llm_pd_separated.instances]]
instance_id = "llm-decode-2"
host = "localhost"
port = 8002
model_name = "meta-llama/Llama-2-7b-hf"
instance_type = "DECODING"
tensor_parallel_size = 1
gpu_count = 1
gpu_memory_gb = 80.0
max_concurrent_requests = 256
```

## Example 4: Priority-Based Scheduling

```toml
[services.llm_priority]
type = "ControlPlaneVLLMService"
scheduling_policy = "priority"
enable_pd_separation = false
routing_strategy = "affinity"
default_priority = "NORMAL"

[[services.llm_priority.instances]]
instance_id = "llm-1"
host = "localhost"
port = 8000
model_name = "meta-llama/Llama-2-7b-hf"
tensor_parallel_size = 2
gpu_count = 2
```

## Example 5: SLO-Aware Scheduling

```toml
[services.llm_slo]
type = "ControlPlaneVLLMService"
scheduling_policy = "slo_aware"
enable_pd_separation = true
routing_strategy = "load_balanced"
default_slo_deadline_ms = 1000  # 1 second default deadline
default_max_tokens = 512
default_temperature = 0.7
default_top_p = 0.95

[[services.llm_slo.instances]]
instance_id = "llm-fast-1"
host = "localhost"
port = 8000
model_name = "meta-llama/Llama-2-7b-hf"
instance_type = "PREFILLING"
tensor_parallel_size = 4

[[services.llm_slo.instances]]
instance_id = "llm-batch-1"
host = "localhost"
port = 8001
model_name = "meta-llama/Llama-2-7b-hf"
instance_type = "DECODING"
tensor_parallel_size = 1
```

## Example 6: Cost-Optimized Scheduling

```toml
[services.llm_cost]
type = "ControlPlaneVLLMService"
scheduling_policy = "cost_optimized"
enable_pd_separation = true
routing_strategy = "locality"

[[services.llm_cost.instances]]
instance_id = "llm-cheap-1"
host = "localhost"
port = 8000
model_name = "meta-llama/Llama-2-7b-hf"
tensor_parallel_size = 1
gpu_count = 1

[[services.llm_cost.instances]]
instance_id = "llm-cheap-2"
host = "localhost"
port = 8001
model_name = "meta-llama/Llama-2-7b-hf"
tensor_parallel_size = 1
gpu_count = 1
```

## Configuration Reference

### Scheduling Policies

- `fifo`: First-In-First-Out (simple, fair)
- `priority`: Priority-based (CRITICAL > HIGH > NORMAL > LOW > BACKGROUND)
- `slo_aware`: SLO deadline-aware (optimizes for meeting deadlines)
- `cost_optimized`: Cost-optimized (minimizes resource usage)
- `adaptive`: Adaptive (automatically switches based on load)

### Routing Strategies

- `load_balanced`: Load-balanced (distributes evenly)
- `affinity`: User affinity (sticky sessions)
- `locality`: Data locality (same model/user)
- `topology_aware`: Topology-aware (NVLINK/NUMA optimization)

### Instance Types

- `GENERAL`: General purpose (default)
- `PREFILLING`: Optimized for prefilling phase
- `DECODING`: Optimized for decoding phase

### Priority Levels

- `CRITICAL`: Highest priority (emergency)
- `HIGH`: High priority (important)
- `NORMAL`: Normal priority (default)
- `LOW`: Low priority
- `BACKGROUND`: Lowest priority (batch jobs)

## Usage Examples

### Python Code

```python
from sage.common.components.sage_vllm import ControlPlaneVLLMService

# Create service from config
config = {
    "scheduling_policy": "adaptive",
    "enable_pd_separation": True,
    "instances": [...],
}

service = ControlPlaneVLLMService(config)
service.setup()

# Generate with priority
results = service.process({
    "task": "generate",
    "inputs": "Your prompt here",
    "options": {
        "priority": "HIGH",
        "slo_deadline_ms": 1000,
        "max_tokens": 256,
    }
})

# Get metrics
metrics = service.process({"task": "get_metrics"})
print(f"Throughput: {metrics['throughput_requests_per_sec']} req/s")
```

### Environment Variables

```bash
# Optional: Override config file location
export SAGE_VLLM_CONFIG=/path/to/config.toml

# Optional: Set default scheduling policy
export SAGE_VLLM_SCHEDULING_POLICY=adaptive

# Optional: Enable debug logging
export SAGE_LOG_LEVEL=DEBUG
```
