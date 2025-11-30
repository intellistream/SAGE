# Keyed State Support in SAGE

SAGE now provides native support for keyed state management through the `get_key()` interface. This
feature enables functions to maintain state partitioned by keys, with automatic persistence and
recovery.

## Overview

Keyed state is essential for many stream processing scenarios:

- **User session management**: Track state per user ID
- **Window aggregations**: Maintain state per time window
- **Feature engineering**: Compute and store features per entity ID
- **Real-time analytics**: Aggregate metrics per dimension

## Key Features

- ✅ **Simple API**: Access current key via `ctx.get_key()`
- ✅ **Automatic Persistence**: Keyed state is automatically saved and restored
- ✅ **Zero Boilerplate**: No need for explicit state management APIs
- ✅ **Backward Compatible**: Works seamlessly with existing code
- ✅ **Type Safe**: Use any Python data structure for keyed state

## Quick Start

### 1. Basic Keyed State

```python
from sage.common.core.stateful_function import StatefulFunction

class UserSessionFunction(StatefulFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Define keyed state - will be automatically persisted
        self.user_sessions = {}

    def execute(self, event_data):
        # Get current packet's key
        user_id = self.ctx.get_key()

        # Initialize state for new users
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'session_count': 0,
                'total_value': 0
            }

        # Update user's state
        self.user_sessions[user_id]['session_count'] += 1
        self.user_sessions[user_id]['total_value'] += event_data['value']

        return self.user_sessions[user_id]
```

### 2. Use with KeyBy Operator

```python
from sage.kernel.api.local_environment import LocalEnvironment
from sage.common.core.functions import MapFunction

class UserIdExtractor(MapFunction):
    def execute(self, event):
        return event['user_id']

# Build pipeline
env = LocalEnvironment("keyed_state_app")

(env.from_source(EventSource, delay=0.5)
   .keyby(UserIdExtractor, strategy="hash")  # Partition by user_id
   .map(UserSessionFunction)  # Maintains per-user state
   .sink(ResultSink))

env.submit()
```

## API Reference

### RuntimeContext Methods

#### `get_key() -> Any`

Returns the key of the currently processing packet. Returns `None` if the packet is not keyed.

```python
key = self.ctx.get_key()
if key is not None:
    # Handle keyed event
    ...
else:
    # Handle unkeyed event (backward compatibility)
    ...
```

#### Internal Methods (for framework developers)

- `set_current_key(key: Any)`: Called by operators to set the current key
- `clear_key()`: Called by operators to clear the key after processing

## Usage Patterns

### Pattern 1: Per-Key Counters

```python
class CounterFunction(StatefulFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counters = {}  # {key: count}

    def execute(self, data):
        key = self.ctx.get_key()
        self.counters[key] = self.counters.get(key, 0) + 1
        return {key: self.counters[key]}
```

### Pattern 2: Time Windows

```python
class WindowAggregator(StatefulFunction):
    def __init__(self, window_size=3600, **kwargs):
        super().__init__(**kwargs)
        self.window_data = {}  # {key: {window_id: [events]}}
        self.window_size = window_size

    def execute(self, event):
        key = self.ctx.get_key()
        window_id = int(time.time() // self.window_size)

        if key not in self.window_data:
            self.window_data[key] = {}
        if window_id not in self.window_data[key]:
            self.window_data[key][window_id] = []

        self.window_data[key][window_id].append(event)

        # Clean up old windows
        old_windows = [w for w in self.window_data[key] if w < window_id - 2]
        for w in old_windows:
            del self.window_data[key][w]

        return {"key": key, "window": window_id,
                "count": len(self.window_data[key][window_id])}
```

### Pattern 3: Feature Computation

```python
class FeatureComputer(StatefulFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.features = {}  # {entity_id: feature_dict}

    def execute(self, event):
        entity_id = self.ctx.get_key()

        if entity_id not in self.features:
            self.features[entity_id] = {
                'mean': 0.0,
                'count': 0,
                'min': float('inf'),
                'max': float('-inf')
            }

        # Update features
        value = event['value']
        features = self.features[entity_id]

        features['count'] += 1
        features['mean'] = (features['mean'] * (features['count'] - 1) + value) / features['count']
        features['min'] = min(features['min'], value)
        features['max'] = max(features['max'], value)

        return {entity_id: features}
```

### Pattern 4: Handling Both Keyed and Unkeyed Streams

```python
class FlexibleFunction(StatefulFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.keyed_state = {}
        self.global_state = {'total_count': 0}

    def execute(self, data):
        key = self.ctx.get_key()

        # Always update global state
        self.global_state['total_count'] += 1

        if key is not None:
            # Keyed stream - update per-key state
            if key not in self.keyed_state:
                self.keyed_state[key] = {'count': 0}
            self.keyed_state[key]['count'] += 1

            return {
                'key': key,
                'key_count': self.keyed_state[key]['count'],
                'global_count': self.global_state['total_count']
            }
        else:
            # Unkeyed stream - only global state
            return {
                'global_count': self.global_state['total_count']
            }
```

## State Persistence

All keyed state defined as instance attributes is automatically persisted by SAGE's checkpoint
mechanism:

```python
class MyFunction(StatefulFunction):
    # Control which attributes are persisted
    __state_include__ = []  # If set, only these attributes are saved
    __state_exclude__ = ['temp_cache']  # Exclude specific attributes

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_data = {}  # Will be persisted
        self.temp_cache = {}  # Will NOT be persisted (excluded)
```

By default:

- All instance attributes are persisted
- Except: `logger`, `_logger`, and `runtime_context` (excluded by default)
- Private attributes (starting with `_`) are excluded unless explicitly included

## Examples

See the complete example in:

- `examples/tutorials/l3-kernel/keyed_state_example.py`

Run it with:

```bash
python examples/tutorials/l3-kernel/keyed_state_example.py
```

## Implementation Details

### How It Works

1. **Key Extraction**: `KeyByOperator` extracts keys from events and attaches them to packets
1. **Key Tracking**: `BaseOperator` sets the current key before processing each packet
1. **Key Access**: Functions access the key via `ctx.get_key()`
1. **Key Cleanup**: After processing, the key is cleared to prevent leakage

### Packet Flow

```
Source -> KeyBy -> Map (Stateful) -> Sink
          ↓         ↓
        Sets key  Gets key via
        in packet  ctx.get_key()
```

### Thread Safety

- Each operator instance has its own `RuntimeContext`
- Keys are set per-packet, cleared after processing
- No cross-thread key contamination

## Best Practices

1. **Initialize State in `__init__`**: Always initialize keyed state dictionaries in the constructor

1. **Check for None Keys**: Handle both keyed and unkeyed streams gracefully

1. **Clean Up Old State**: Implement cleanup logic for time-based state (e.g., old windows)

1. **Use Appropriate Data Structures**: Choose efficient data structures for your use case

   - `dict` for sparse keys
   - `defaultdict` for automatic initialization
   - Custom classes for complex state

1. **Monitor State Size**: Large state can impact memory and checkpoint time

   - Implement state cleanup/expiration
   - Use state TTL where appropriate

## Testing

Test your keyed state functions:

```python
import pytest
from sage.kernel.api.local_environment import LocalEnvironment

def test_keyed_state():
    env = LocalEnvironment("test_keyed_state")

    (env.from_source(TestSource)
       .keyby(KeyExtractor)
       .map(MyKeyedFunction)
       .sink(TestSink))

    env.submit()
    # Add assertions
```

See `packages/sage-kernel/tests/unit/core/function/test_keyed_state.py` for comprehensive test
examples.

## Troubleshooting

### Issue: `get_key()` returns None unexpectedly

**Solution**: Ensure you have a `keyby()` operation before your stateful function:

```python
# ❌ Wrong - no keyby
env.from_source(Source).map(KeyedFunction).sink(Sink)

# ✅ Correct - with keyby
env.from_source(Source).keyby(KeyExtractor).map(KeyedFunction).sink(Sink)
```

### Issue: State not persisting across restarts

**Solution**: Check that:

1. Your attributes are not in `__state_exclude__`
1. Your state is serializable (basic Python types, not file handles or sockets)
1. Checkpointing is enabled in your environment

### Issue: Memory grows unbounded

**Solution**: Implement state cleanup:

```python
def execute(self, data):
    key = self.ctx.get_key()

    # Add to state
    self.state[key] = data

    # Cleanup old keys (example: LRU)
    if len(self.state) > MAX_KEYS:
        oldest_key = next(iter(self.state))
        del self.state[oldest_key]
```

## Migration from Custom State Management

If you were managing keyed state manually, migration is straightforward:

**Before (manual management):**

```python
class MyFunction(BaseFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = {}

    def execute(self, data):
        key = data['key']  # Manual key extraction
        if key not in self.state:
            self.state[key] = {}
        self.state[key]['count'] = self.state[key].get('count', 0) + 1
        return self.state[key]
```

**After (with get_key()):**

```python
class MyFunction(StatefulFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = {}

    def execute(self, data):
        key = self.ctx.get_key()  # Automatic key access
        if key not in self.state:
            self.state[key] = {}
        self.state[key]['count'] = self.state[key].get('count', 0) + 1
        return self.state[key]
```

Changes needed:

1. Change pipeline to use `keyby(KeyExtractor)`
1. Change `StatefulFunction` base class (if not already)
1. Replace manual key extraction with `self.ctx.get_key()`

## Related Documentation

- [SAGE State Management](../../../docs/dev-notes/l3-kernel/state-management.md)
- [KeyBy Operator](../../../docs/dev-notes/l3-kernel/operators.md#keyby)
- [Stateful Functions](../../../docs/dev-notes/l1-common/functions.md#stateful-functions)
