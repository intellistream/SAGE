# Agentic Module Externalization Plan

**Status**: 🚧 Preparing for extraction to `isage-agentic` package\
**Current Size**: ~1.1M, 65 Python files\
**Target**: Keep interface/registry layer in sage-libs, move implementations to external package

## Current Structure

```
agentic/
├── agents/              # Agent implementations (65% of code)
│   ├── action/
│   │   └── tool_selection/  # Tool selectors (DFS-DT, embedding, hybrid, Gorilla)
│   ├── bots/                # Role-specific bots (answer, critic, question, searcher)
│   ├── planning/            # Planners (ToT, ReAct, hierarchical, timing)
│   ├── profile/             # Agent profiles and presets
│   └── runtime/             # Orchestrator, adapters, telemetry
├── intent/              # Intent classification and routing
├── workflow/            # Workflow generation and optimization
└── workflows/           # Concrete workflow presets/routers
```

## Migration Strategy

### Phase 1: Interface Definition (Keep in sage-libs)

**Goal**: Establish stable public API surface

```python
# sage.libs.agentic (interface layer in sage-libs)
from .interfaces import (
    # Base protocols
    Agent, Planner, ToolSelector, WorkflowOptimizer,
    # Factories
    create_planner, create_tool_selector, create_workflow,
    # Registries
    register_planner, registered_planners,
    register_tool_selector, registered_tool_selectors,
)
```

**Files to Keep**:

- `__init__.py` - Public exports only
- `interfaces/` (new) - Protocol definitions
  - `agent.py` - Agent, Bot protocols
  - `planner.py` - Planner, PlanningContext protocols
  - `tool_selector.py` - ToolSelector protocol
  - `workflow.py` - WorkflowGraph, WorkflowOptimizer protocols
- `registry/` (new) - Factory and registration
  - `planner_registry.py`
  - `tool_selector_registry.py`
  - `workflow_registry.py`

**Estimated Size**: ~100KB, 10-15 files

### Phase 2: Implementation Extraction (Move to isage-agentic)

**Goal**: Move heavy implementations to external package

**Extract to `isage-agentic`**:

- `agents/planning/*` → `isage_agentic.planning`
  - ToT, ReAct, hierarchical, timing_decider implementations
- `agents/action/tool_selection/*` → `isage_agentic.tool_selection`
  - DFS-DT, embedding, hybrid, Gorilla selectors
- `agents/bots/*` → `isage_agentic.bots`
  - Answer, critic, question, searcher bots
- `agents/runtime/*` → `isage_agentic.runtime`
  - Orchestrator, adapters, telemetry implementation
- `workflow/*` → `isage_agentic.workflow`
  - Generators, optimizers, evaluators
- `workflows/*` → `isage_agentic.workflows`
  - Concrete presets and routers
- `intent/*` → `isage_agentic.intent`
  - Classifiers, recognizers, catalog

**Estimated External Package Size**: ~1.0M, 50+ files

### Phase 3: Backward Compatibility Shims

**Goal**: Maintain import compatibility during transition

```python
# sage.libs.agentic.agents.planning (compatibility shim)
import warnings
from isage_agentic.planning import *  # noqa

warnings.warn(
    "Import from isage_agentic.planning instead of sage.libs.agentic.agents.planning",
    DeprecationWarning,
    stacklevel=2,
)
```

## External Package Structure (isage-agentic)

```
isage-agentic/
├── pyproject.toml           # Dependencies: sage-libs (interface only)
├── src/isage_agentic/
│   ├── __init__.py          # Re-export main APIs
│   ├── planning/            # Planner implementations
│   │   ├── tot.py
│   │   ├── react.py
│   │   ├── hierarchical.py
│   │   └── timing_decider.py
│   ├── tool_selection/      # Tool selector implementations
│   │   ├── dfsdt.py
│   │   ├── embedding.py
│   │   ├── hybrid.py
│   │   └── gorilla.py
│   ├── bots/                # Bot implementations
│   ├── runtime/             # Runtime components
│   ├── workflow/            # Workflow implementations
│   ├── workflows/           # Presets
│   └── intent/              # Intent classification
└── tests/
```

## Dependencies

### sage-libs (interface layer)

```toml
dependencies = [
    "sage-common>=0.2.0",
    # No heavy dependencies
]
```

### isage-agentic (implementation)

```toml
dependencies = [
    "sage-libs>=0.2.0",        # Interface layer
    "transformers>=4.52.0",    # For embedding selectors
    "torch>=2.7.0",            # Optional, for model-based components
]
```

## Migration Checklist

### Preparation

- [ ] Create `interfaces/` directory with protocol definitions
- [ ] Create `registry/` directory with factory functions
- [ ] Update `agentic/__init__.py` to export only interfaces
- [ ] Document all public APIs with docstrings
- [ ] Add migration warnings to all implementation modules

### External Package Setup

- [ ] Create `isage-agentic` repository
- [ ] Set up pyproject.toml with correct dependencies
- [ ] Copy implementation files from sage-libs
- [ ] Update imports to use new namespace
- [ ] Set up CI/CD for external package
- [ ] Publish to PyPI

### sage-libs Updates

- [ ] Remove implementation files (keep shims temporarily)
- [ ] Update `sage-libs[agentic]` extra in pyproject.toml
- [ ] Update documentation to reference external package
- [ ] Add deprecation warnings
- [ ] Update examples to use new imports

### Testing & Validation

- [ ] Run full test suite with external package
- [ ] Verify all examples work
- [ ] Check backward compatibility
- [ ] Performance benchmarks (ensure no regression)
- [ ] Update CI to install external package

### Cleanup (after 2-3 releases)

- [ ] Remove compatibility shims
- [ ] Remove old implementation code
- [ ] Update all internal code to use new imports
- [ ] Remove agentic-specific dependencies from sage-libs

## Timeline

- **Week 1-2**: Interface definition and registry setup
- **Week 3-4**: External package creation and initial migration
- **Week 5-6**: Testing, documentation, PyPI publication
- **Week 7-8**: Deprecation warnings and migration guides
- **3 months later**: Remove compatibility shims

## Benefits

1. **Cleaner Dependencies**: sage-libs stays lightweight
1. **Independent Versioning**: isage-agentic can evolve faster
1. **Easier Testing**: Isolated test suites
1. **Better Modularity**: Clear separation of interface vs implementation
1. **Optional Installation**: Users can skip heavy agentic deps if not needed

## Related Documents

- `packages/sage-libs/docs/MIGRATION_EXTERNAL_LIBS.md` - Overall migration strategy
- `docs-public/docs_src/dev-notes/package-architecture.md` - Package architecture
- `.github/copilot-instructions.md` - L3 purity principles
