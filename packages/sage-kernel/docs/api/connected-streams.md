# Connected Streams API

The Connected Streams API provides advanced stream processing capabilities for building complex data pipelines with inter-stream dependencies.

## Overview

Connected streams allow you to:
- Link multiple data streams together
- Share state between stream operations
- Build complex event processing pipelines
- Handle stream dependencies and ordering

## Core Classes

### ConnectedStreams

Main class for managing connected stream operations.

```python
from sage.core.api.connected_streams import ConnectedStreams

# Create connected streams from multiple sources
stream1 = environment.create_stream("source1")
stream2 = environment.create_stream("source2")

connected = ConnectedStreams([stream1, stream2])
```

#### Methods

##### `process(processor_func, **kwargs)`

Process connected streams with a custom function.

```python
def merge_processor(streams, state):
    """Merge data from multiple streams"""
    merged_data = []
    for stream in streams:
        for item in stream.read():
            merged_data.append(item)
    return merged_data

result = connected.process(merge_processor)
```

##### `join(join_type="inner", key_func=None)`

Join streams based on keys or conditions.

```python
# Join by key
def get_user_id(item):
    return item.get("user_id")

joined = connected.join(
    join_type="inner",
    key_func=get_user_id
)

# Custom join condition
def join_condition(item1, item2):
    return item1["timestamp"] == item2["timestamp"]

joined = connected.join(
    join_type="outer",
    condition=join_condition
)
```

##### `window(window_type, size, slide=None)`

Apply windowing operations across connected streams.

```python
# Tumbling window
windowed = connected.window(
    window_type="tumbling",
    size=60  # 60 seconds
)

# Sliding window
windowed = connected.window(
    window_type="sliding",
    size=300,  # 5 minutes
    slide=60   # 1 minute slide
)

# Session window
windowed = connected.window(
    window_type="session",
    timeout=30  # 30 seconds timeout
)
```

### StreamState

Shared state management for connected streams.

```python
from sage.core.api.connected_streams import StreamState

# Create shared state
state = StreamState()

# Store values
state.set("counter", 0)
state.set("last_timestamp", time.time())

# Retrieve values
counter = state.get("counter", default=0)

# Atomic operations
state.increment("counter")
state.append("events", new_event)
```

#### Methods

##### `get(key, default=None)`

Get value from shared state.

```python
value = state.get("my_key", default=0)
```

##### `set(key, value)`

Set value in shared state.

```python
state.set("status", "processing")
```

##### `increment(key, amount=1)`

Atomically increment a numeric value.

```python
state.increment("processed_count")
state.increment("total_bytes", data_size)
```

##### `append(key, value)`

Append to a list in shared state.

```python
state.append("errors", error_message)
```

##### `update(key, update_func)`

Atomically update a value using a function.

```python
def update_stats(current_stats):
    current_stats["last_update"] = time.time()
    current_stats["count"] += 1
    return current_stats

state.update("statistics", update_stats)
```

## Advanced Features

### Stream Synchronization

Synchronize streams based on timestamps or events.

```python
# Timestamp-based synchronization
synchronized = connected.synchronize(
    sync_type="timestamp",
    tolerance=1.0  # 1 second tolerance
)

# Event-based synchronization
synchronized = connected.synchronize(
    sync_type="event",
    sync_event="marker"
)
```

### Error Handling

Handle errors across connected streams.

```python
def error_handler(stream_id, error, context):
    print(f"Error in stream {stream_id}: {error}")
    # Log error and continue processing
    return "continue"

connected.on_error(error_handler)
```

### Backpressure Management

Control data flow when streams process at different rates.

```python
# Configure backpressure
connected.configure_backpressure(
    strategy="block",  # or "drop", "buffer"
    buffer_size=1000,
    timeout=30
)
```

## Examples

### Simple Stream Merge

```python
from sage.core.api import LocalEnvironment
from sage.core.api.connected_streams import ConnectedStreams

# Setup
env = LocalEnvironment()
stream1 = env.create_stream("data1")
stream2 = env.create_stream("data2")

# Connect and merge
connected = ConnectedStreams([stream1, stream2])

def merge_data(streams, state):
    merged = []
    for stream in streams:
        while stream.has_data():
            item = stream.read()
            item["source"] = stream.name
            merged.append(item)
    return merged

result_stream = connected.process(merge_data)
```

### Time-Window Aggregation

```python
def window_aggregator(window_data, state):
    """Aggregate data within time windows"""
    total = 0
    count = 0
    
    for stream_data in window_data:
        for item in stream_data:
            total += item.get("value", 0)
            count += 1
    
    return {
        "window_start": window_data.start_time,
        "window_end": window_data.end_time,
        "total": total,
        "average": total / count if count > 0 else 0,
        "count": count
    }

# Apply windowing
windowed = connected.window("tumbling", size=60)
aggregated = windowed.process(window_aggregator)
```

### Complex Event Processing

```python
from sage.core.api.connected_streams import StreamState

def event_processor(streams, state):
    """Process complex event patterns"""
    events = []
    
    # Collect events from all streams
    for stream in streams:
        while stream.has_data():
            event = stream.read()
            events.append(event)
    
    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"])
    
    # Detect patterns
    patterns = []
    for i in range(len(events) - 1):
        current = events[i]
        next_event = events[i + 1]
        
        # Example: detect login followed by purchase
        if (current["type"] == "login" and 
            next_event["type"] == "purchase" and
            current["user_id"] == next_event["user_id"]):
            
            patterns.append({
                "pattern": "login_purchase",
                "user_id": current["user_id"],
                "login_time": current["timestamp"],
                "purchase_time": next_event["timestamp"],
                "purchase_amount": next_event["amount"]
            })
    
    return patterns

result = connected.process(event_processor)
```

### Stream Join Example

```python
# User activity and user profile streams
activity_stream = env.create_stream("user_activity")
profile_stream = env.create_stream("user_profiles")

connected = ConnectedStreams([activity_stream, profile_stream])

# Join on user_id
def get_user_id(item):
    return item.get("user_id")

joined = connected.join(
    join_type="inner",
    key_func=get_user_id
)

def enrich_activity(joined_data, state):
    """Enrich activity with profile data"""
    enriched = []
    
    for activity, profile in joined_data:
        enriched_activity = activity.copy()
        enriched_activity.update({
            "user_name": profile.get("name"),
            "user_tier": profile.get("tier"),
            "user_location": profile.get("location")
        })
        enriched.append(enriched_activity)
    
    return enriched

enriched_stream = joined.process(enrich_activity)
```

## Best Practices

### Performance Optimization

1. **Minimize State Size**: Keep shared state minimal and clean up unused data
2. **Efficient Joins**: Use appropriate join types and optimize key functions
3. **Window Management**: Choose appropriate window sizes for your use case
4. **Backpressure**: Configure backpressure to handle varying processing speeds

### Error Handling

1. **Graceful Degradation**: Handle stream failures without stopping the entire pipeline
2. **Error Isolation**: Isolate errors to prevent cascade failures
3. **Recovery Strategies**: Implement retry and recovery mechanisms

### Memory Management

1. **Buffer Limits**: Set appropriate buffer sizes to prevent memory overflow
2. **State Cleanup**: Regularly clean up old state data
3. **Window Expiry**: Ensure windows expire to free memory

### Monitoring

1. **Stream Health**: Monitor individual stream health and performance
2. **Join Efficiency**: Track join hit rates and performance
3. **State Growth**: Monitor shared state size and growth patterns

## Error Handling

Common error scenarios and solutions:

```python
def robust_processor(streams, state):
    try:
        # Processing logic
        return process_streams(streams)
    except Exception as e:
        # Log error
        state.append("errors", str(e))
        # Return empty result or default
        return []

# Configure error handling
connected.on_error(lambda stream_id, error, context: "continue")
connected.set_error_threshold(max_errors=10, time_window=60)
```

## Integration with Other APIs

### With DataStream API

```python
from sage.core.api import DataStream

# Create individual streams
stream1 = DataStream("stream1")
stream2 = DataStream("stream2")

# Connect them
connected = ConnectedStreams([stream1, stream2])
```

### With Functions API

```python
from sage.core.api.functions import register_function

@register_function
def connected_processor(connected_streams):
    return connected_streams.process(my_processor)
```

This Connected Streams API enables sophisticated stream processing patterns while maintaining the simplicity and flexibility of the SAGE kernel architecture.
