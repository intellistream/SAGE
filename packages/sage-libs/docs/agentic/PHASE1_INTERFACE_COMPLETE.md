# Agentic Interface Layer - Phase 1 Complete ✅

**Date**: 2026-01-10\
**Status**: Interface layer structure created and tested

## What Was Done

### 1. Directory Structure Created

```
agentic/interface/
├── __init__.py           # Main exports
├── protocols/
│   └── __init__.py       # PlannerProtocol, ToolSelectorProtocol, AgentProtocol
├── registries/
│   └── __init__.py       # PlannerRegistry, SelectorRegistry, PluginRegistry
└── schemas/
    └── __init__.py       # Re-exports from existing schemas
```

### 2. Module Reorganization

**Moved into agentic/**:

- `sage.libs.reasoning` → `sage.libs.agentic.reasoning`
- `sage.libs.sias` → `sage.libs.agentic.sias`
- `sage.libs.eval` → `sage.libs.agentic.evaluation` (renamed to avoid built-in shadow)

**Final structure**:

```
agentic/
├── agents/         # Agent framework, planning, tool selection
├── eval/           # Evaluation metrics (imported as 'evaluation')
├── intent/         # Intent classification
├── interface/      # ✅ NEW: Stable API layer
├── interfaces/     # Legacy (to be deprecated)
├── reasoning/      # Search algorithms
├── registry/       # Legacy registry (to be deprecated)
├── sias/           # Tool selection reasoning
├── workflow/       # Workflow optimization
└── workflows/      # Workflow presets
```

### 3. Interface Layer Exports

**Protocols** (`sage.libs.agentic.interface.protocols`):

- `PlannerProtocol` - Interface for planner implementations
- `ToolSelectorProtocol` - Interface for tool selector implementations
- `AgentProtocol` - Interface for agent implementations
- `BasePlanner`, `BaseToolSelector`, `BaseAgent` - ABC versions for inheritance

**Registries** (`sage.libs.agentic.interface.registries`):

- `PlannerRegistry` - Plugin registry for planners
  - Methods: `register(name, factory)`, `create(name, *args, **kwargs)`, `list_planners()`
- `SelectorRegistry` - Plugin registry for tool selectors
  - Methods: `register(name, factory)`, `create(name, *args, **kwargs)`, `list_selectors()`
- `PluginRegistry` - Generic plugin system for extensibility

**Schemas** (`sage.libs.agentic.interface.schemas`):

- Planning: `PlanRequest`, `PlanResult`, `PlanStep`, `PlannerConfig`, `TimingMessage`,
  `TimingDecision`
- Tool Selection: `ToolSelectionQuery`, `ToolPrediction`, `SelectorConfig`, `ToolMetadata`

### 4. Import Patterns

```python
# Recommended usage (interface layer)
from sage.libs.agentic.interface import (
    PlannerProtocol,
    PlannerRegistry,
    PlanRequest,
    PlanResult,
    ToolSelectorProtocol,
    SelectorRegistry,
    ToolSelectionQuery,
    ToolPrediction,
)

# Or import from main agentic module
from sage.libs.agentic import (
    PlannerProtocol,
    PlannerRegistry,
    PlanRequest,
    PlanResult,
)

# Access implementations
from sage.libs.agentic import agents, reasoning, sias, evaluation
```

### 5. Key Design Decisions

**Absolute imports**: Used `sage.libs.agentic.agents.planning.schemas` instead of relative imports
to avoid path confusion with nested `interface/` structure.

**eval → evaluation**: Renamed `eval` module import to `evaluation` to avoid shadowing Python's
built-in `eval()` function.

**Registry pattern**: Centralized plugin registry for dynamic component loading, enabling external
packages to register implementations.

**Protocol-first**: Defined protocols before implementations, enabling external packages to
implement interfaces without depending on sage-libs implementations.

## Testing

```bash
# Verify imports work
cd /home/shuhao/SAGE
python3 -c "
from sage.libs.agentic.interface import (
    PlannerProtocol, ToolSelectorProtocol,
    PlannerRegistry, SelectorRegistry,
    PlanRequest, PlanResult
)
print('✅ Interface layer working!')
print(f'  Registries: {PlannerRegistry.__name__}, {SelectorRegistry.__name__}')
print(f'  PlanRequest fields: {list(PlanRequest.model_fields.keys())}')
"
```

## Next Steps (Phase 2)

1. **Implement registrations**: Connect existing planners/selectors to new registries
1. **Deprecation warnings**: Add warnings to legacy `interfaces/` and `registry/` modules
1. **Documentation**: Update README and examples to use new interface layer
1. **External package prep**: Create `isage-agentic` repository structure
1. **Migration guide**: Write guide for transitioning to external package

## Files Modified

- Created:

  - `agentic/interface/__init__.py`
  - `agentic/interface/protocols/__init__.py`
  - `agentic/interface/registries/__init__.py`
  - `agentic/interface/schemas/__init__.py`

- Modified:

  - `agentic/__init__.py` - Added interface exports, renamed eval → evaluation

- Moved:

  - `sage.libs.reasoning/` → `agentic/reasoning/`
  - `sage.libs.sias/` → `agentic/sias/`
  - `sage.libs.eval/` → `agentic/eval/`

## Size Impact

Before: 1.3M, 77 files\
After interface layer: 1.3M + 4 interface files (~8K overhead)\
Estimated final: ~100K interface, ~1.2M implementations (to be externalized)

## Notes

- Interface layer uses **absolute imports** for clarity
- **Protocol pattern** enables multiple implementations
- **Registry system** supports plugin architecture
- **eval** imported as `evaluation` to avoid built-in shadowing
- Current implementations remain in place (Phase 2 will externalize them)
