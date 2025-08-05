# SAGE Queue Communication System

## Overview

The SAGE Queue Communication System provides a unified interface for various queue types through the `QueueDescriptor` class. This system supports local queues, shared memory queues, SAGE high-performance queues, Ray distributed queues, and RPC queues.

## Core Architecture

### QueueDescriptor

The `QueueDescriptor` is the central class that provides:
- **Unified Interface**: All queue types use the same methods (`put`, `get`, `empty`, `qsize`, etc.)
- **Lazy Loading**: Queue instances are created only when first accessed
- **Serialization Support**: Full serialization/deserialization for cross-process communication
- **Multiple Queue Types**: Support for local, shared memory, SAGE, Ray, and RPC queues

## Supported Queue Types

### 1. Local Queue
Standard Python `queue.Queue` for single-process communication.

```python
from sage.kernels.runtime.communication.queue_descriptor import QueueDescriptor

queue = QueueDescriptor.create_local_queue(
    queue_id="my_local_queue",
    maxsize=100
)
```

### 2. Shared Memory Queue
`multiprocessing.Queue` for inter-process communication.

```python
queue = QueueDescriptor.create_shm_queue(
    shm_name="shared_queue",
    queue_id="my_shm_queue",
    maxsize=1000
)
```

### 3. SAGE Queue
High-performance queue with advanced features.

```python
queue = QueueDescriptor.create_sage_queue(
    queue_id="my_sage_queue",
    maxsize=1024 * 1024,
    auto_cleanup=True,
    namespace="my_namespace",
    enable_multi_tenant=True
)
```

### 4. Ray Queue
Distributed queue using Ray's infrastructure.

```python
queue = QueueDescriptor.create_ray_queue(
    queue_id="my_ray_queue",
    maxsize=0  # unlimited
)
```

### 5. Ray Actor Queue
Queue backed by a Ray Actor.

```python
queue = QueueDescriptor.create_ray_actor_queue(
    actor_name="my_actor",
    queue_id="my_ray_actor_queue"
)
```

### 6. RPC Queue
Queue accessed via RPC calls.

```python
queue = QueueDescriptor.create_rpc_queue(
    server_address="localhost",
    port=8080,
    queue_id="my_rpc_queue"
)
```

## Basic Usage

All queue types share the same interface:

```python
# Create any type of queue
queue = QueueDescriptor.create_local_queue(queue_id="example")

# Basic operations
queue.put("hello")
queue.put("world", timeout=5.0)

item = queue.get()
item = queue.get(timeout=1.0)

# Non-blocking operations
try:
    queue.put_nowait("item")
    item = queue.get_nowait()
except:
    pass

# Status checks
is_empty = queue.empty()
size = queue.qsize()
is_full = queue.full()
```

## Serialization

QueueDescriptor supports full serialization for cross-process communication:

```python
# Serialize to dict/JSON
data = queue.to_dict()
json_str = queue.to_json()

# Deserialize
queue2 = QueueDescriptor.from_dict(data)
queue3 = QueueDescriptor.from_json(json_str)

# Batch operations
queue_pool = {
    "q1": QueueDescriptor.create_local_queue(),
    "q2": QueueDescriptor.create_sage_queue()
}

# Serialize entire pool
from sage.kernels.runtime.communication.queue_descriptor import serialize_queue_pool, deserialize_queue_pool
json_data = serialize_queue_pool(queue_pool)
restored_pool = deserialize_queue_pool(json_data)
```

## Advanced Features

### Lazy Loading
Queue instances are created only when first accessed:

```python
queue = QueueDescriptor.create_sage_queue(queue_id="lazy")
# No actual queue created yet

queue.put("item")  # Now the underlying queue is created
```

### Cloning
Create independent copies of queue descriptors:

```python
original = QueueDescriptor.create_local_queue(queue_id="original")
clone = original.clone("cloned_queue")
```

### From Existing Queue
Create descriptors from existing queue objects:

```python
import queue
existing = queue.Queue()
descriptor = QueueDescriptor.from_existing_queue(
    queue_instance=existing,
    queue_type="local",
    queue_id="from_existing"
)
```

## Error Handling

All queue operations follow standard Python queue patterns:

```python
import queue

try:
    queue.put("item", timeout=1.0)
except queue.Full:
    print("Queue is full")

try:
    item = queue.get(timeout=1.0)
except queue.Empty:
    print("Queue is empty")
```

## Performance Notes

- **Lazy Loading**: Reduces memory usage for unused queues
- **Direct Interface**: No intermediate wrapper objects
- **Minimal Overhead**: Direct method calls to underlying queues
- **Efficient Serialization**: Optimized for cross-process communication

## Thread Safety

Thread safety depends on the underlying queue implementation:
- **Local Queue**: Thread-safe (uses `queue.Queue`)
- **Shared Memory Queue**: Process-safe (uses `multiprocessing.Queue`) 
- **SAGE Queue**: Thread and process-safe
- **Ray Queue**: Distributed-safe
- **RPC Queue**: Depends on RPC implementation

## Dependencies

- **Local/Shared Memory**: Built-in Python modules
- **SAGE Queue**: Requires `sage_ext.sage_queue`
- **Ray Queue**: Requires `ray` package
- **RPC Queue**: Implementation-dependent

## Examples

See `tests/` directory for comprehensive usage examples.
