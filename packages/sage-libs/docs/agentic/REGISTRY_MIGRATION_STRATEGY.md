# Registry Migration Strategy

**Date**: 2026-01-10\
**Status**: 🚧 Planning Phase 2

## Current State

### Legacy Registry (sage.libs.agentic.registry/)

- **Style**: Module-level functions
- **Location**: `agentic/registry/`
- **Files**:
  - `planner_registry.py` - Functions: `register()`, `create()`, `registered()`
  - `tool_selector_registry.py` - Functions: `register()`, `create()`, `registered()`
  - `workflow_registry.py` - Functions: `register()`, `create()`, `registered()`
- **Auto-registration**: `_register_*.py` files automatically register implementations
- **Status**: ✅ Working, tested, widely used

### New Interface Registry (sage.libs.agentic.interface/registries/)

- **Style**: Class-based registry pattern
- **Location**: `agentic/interface/registries/`
- **Classes**:
  - `PlannerRegistry` - Methods: `register()`, `create()`, `list_planners()`
  - `SelectorRegistry` - Methods: `register()`, `create()`, `list_selectors()`
  - `PluginRegistry` - Generic plugin system
- **Auto-registration**: Not yet implemented
- **Status**: ✅ Interface defined, not connected to implementations

## Migration Options

### Option 1: Dual System (Recommended for Phase 2)

**Keep both registries, sync automatically**

```python
# In agentic/interface/registries/__init__.py
from ...registry import planner_registry as _legacy_planner
from ...registry import tool_selector_registry as _legacy_selector

class PlannerRegistry:
    @classmethod
    def register(cls, name: str, factory=None):
        def decorator(factory_fn):
            # Register in both systems
            _legacy_planner.register(name, factory_fn)
            cls._registry[name] = factory_fn
            return factory_fn
        ...

    @classmethod
    def create(cls, name: str, *args, **kwargs):
        # Delegate to legacy for now
        return _legacy_planner.create(name, **kwargs)
```

**Pros**: Backward compatible, gradual migration\
**Cons**: Dual maintenance, complexity

### Option 2: Wrapper Around Legacy

**New registry wraps legacy functions**

```python
class PlannerRegistry:
    @classmethod
    def register(cls, name: str, factory=None):
        return _legacy_planner.register(name, factory)

    @classmethod
    def create(cls, name: str, *args, **kwargs):
        return _legacy_planner.create(name, **kwargs)

    @classmethod
    def list_planners(cls):
        return _legacy_planner.registered()
```

**Pros**: Simple, no duplication, works immediately\
**Cons**: New interface depends on legacy code

### Option 3: Replace Completely

**Rewrite legacy to use new registry classes**

```python
# In agentic/registry/planner_registry.py
from ..interface.registries import PlannerRegistry as _NewRegistry

# Expose as module functions for backward compat
def register(name: str, factory):
    return _NewRegistry.register(name, factory)

def create(name: str, **kwargs):
    return _NewRegistry.create(name, **kwargs)

def registered():
    return _NewRegistry.list_planners()
```

**Pros**: Single source of truth, clean\
**Cons**: Requires rewriting auto-registration, risky

## Recommended Approach

### Phase 2A: Wrapper Implementation (This Week)

1. ✅ Keep legacy registry as-is
1. 🔄 Implement Option 2 (wrapper) in new registry
1. 🔄 Add deprecation warnings to legacy functions
1. 🔄 Update documentation to recommend new interface
1. ✅ Maintain 100% backward compatibility

### Phase 2B: Sync System (Next Week)

1. Implement Option 1 (dual sync)
1. Migrate auto-registration to new system
1. Add migration guide
1. Update examples to use new interface

### Phase 3: External Package (Future)

1. Move implementations to `isage-agentic`
1. Keep registries in `sage-libs` as stable interface
1. External package registers via `PlannerRegistry.register()`

## Implementation Plan for Phase 2A

### File: agentic/interface/registries/__init__.py

```python
"""Plugin registries with legacy compatibility."""

from typing import Any, Callable, Optional
from ...registry import (
    planner_registry as _legacy_planner,
    tool_selector_registry as _legacy_selector,
    workflow_registry as _legacy_workflow,
)

class PlannerRegistry:
    """Registry for planner implementations (wraps legacy)."""

    @classmethod
    def register(cls, name: str, factory: Optional[Callable] = None):
        """Register via legacy system."""
        if factory is None:
            return lambda f: _legacy_planner.register(name, f) or f
        _legacy_planner.register(name, factory)
        return factory

    @classmethod
    def create(cls, name: str, *args, **kwargs):
        """Create via legacy system."""
        return _legacy_planner.create(name, **kwargs)

    @classmethod
    def list_planners(cls) -> list[str]:
        """List registered planners."""
        return _legacy_planner.registered()

# Similar for SelectorRegistry, WorkflowRegistry
```

### File: agentic/registry/__init__.py (add deprecation)

```python
"""Agentic registries - Factory and registration system.

⚠️ DEPRECATION WARNING:
This module is deprecated. Use the new interface layer instead:
    from sage.libs.agentic.interface import PlannerRegistry, SelectorRegistry

The legacy API will be maintained for backward compatibility but
may be removed in a future version.
"""

import warnings

warnings.warn(
    "sage.libs.agentic.registry is deprecated. "
    "Use sage.libs.agentic.interface.registries instead.",
    DeprecationWarning,
    stacklevel=2,
)

# ... rest of file
```

## Testing Strategy

1. **Backward compatibility**: All existing code using legacy registry must continue to work
1. **New interface**: New code can use `PlannerRegistry.create()` and get same results
1. **Cross-compatibility**: Registrations via legacy appear in new interface and vice versa

## Success Criteria

- ✅ All existing tests pass (including `test_registry.py`)
- ✅ New interface imports work
- ✅ `PlannerRegistry.list_planners()` returns same as `planner_registry.registered()`
- ✅ `PlannerRegistry.create("react")` works same as `planner_registry.create("react")`
- ✅ No breaking changes to existing code

## Timeline

- **Day 1-2** (Now): Implement wrapper (Option 2)
- **Day 3**: Add deprecation warnings
- **Day 4**: Update documentation
- **Day 5**: Write migration guide

Next: Week 2 - Sync system (Option 1) for external package support
