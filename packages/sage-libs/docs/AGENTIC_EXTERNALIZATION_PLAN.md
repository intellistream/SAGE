# Agentic Module - Externalization Preparation

**Target Package**: `isage-agentic`\
**Current Size**: 1.3M, 77 Python files\
**Status**: 🚧 Preparing for externalization

## Current Structure

```
agentic/
├── agents/           # Agent framework (planning, bots, runtime)
│   ├── planning/     # ToT, ReAct, hierarchical planners
│   ├── action/       # Tool selection strategies
│   ├── bots/         # Answer/Critic/Question/Searcher bots
│   ├── profile/      # Agent profiles
│   └── runtime/      # Orchestrator, adapters, config
├── intent/           # Intent classification
├── workflow/         # Workflow optimization
│   ├── generators/   # LLM/rule-based generators
│   └── optimizers/   # Workflow optimizers
├── workflows/        # Concrete workflow presets
├── sias/             # Tool selection reasoning
├── reasoning/        # Search algorithms
└── eval/             # Evaluation metrics
```

## What to Keep in sage-libs (Interface Layer)

### Protocols & Base Classes

- `agents/agent.py` - Agent protocol
- `agents/planning/base.py` - Planner interface
- `agents/action/tool_selection/base.py` - Tool selector interface
- `workflow/base.py` - Workflow interface
- `intent/base.py` - Intent recognizer interface

### Registries

- `agents/planning/registry.py` - Planner registry
- `agents/action/tool_selection/registry.py` - Tool selector registry
- `workflow/generators/base.py` - Generator registry
- `intent/factory.py` - Intent recognizer factory

### Type Definitions

- `agents/planning/schemas.py` - Plan schemas
- `workflow/constraints.py` - Constraint types
- Common types and enums

## What to Move to isage-agentic (Implementations)

### Heavy Components

- All planner implementations (ToT, ReAct, Hierarchical, DependencyGraph)
- All tool selection implementations (DFSDT, Embedding, Gorilla, Hybrid, Keyword)
- All bot implementations (Answer, Critic, Question, Searcher)
- Runtime orchestrator and adapters
- Workflow generators and optimizers
- SIAS implementations
- Reasoning search algorithms
- Evaluation metrics implementations

### Templates & Configs

- Prompt templates
- Default configurations
- Preset workflows

## Migration Steps

### Phase 1: Prepare Interface Layer (this repo)

1. Create `agentic/interface/` directory structure
1. Move protocols/bases/registries to interface/
1. Update __init__.py to export only interfaces
1. Add deprecation warnings

### Phase 2: External Package (isage-agentic repo)

1. Create new repo: `intellistream/sage-agentic`
1. Move implementations to external repo
1. Set up pyproject.toml with proper dependencies
1. Publish to PyPI as `isage-agentic`

### Phase 3: Integration

1. Update dependencies-spec.yaml: `isage-agentic: ">=0.1.0"`
1. Update pyproject.toml: Add `agentic = ["isage-agentic>=0.1.0"]`
1. Update tests to use external package
1. Update documentation

### Phase 4: Cleanup

1. Remove implementation files from this repo
1. Keep only interface layer
1. Verify all imports work
1. Run full test suite

## API Stability Plan

### Stable Imports (Keep Working)

```python
# Factory pattern (no change)
from sage.libs.agentic import create_planner, create_tool_selector

# Protocol imports (no change)
from sage.libs.agentic.agents import Agent
from sage.libs.agentic.agents.planning import Planner
from sage.libs.agentic.workflow import Workflow
```

### Implementation Imports (Will Need isage-agentic)

```python
# These will require: pip install isage-agentic
from sage.libs.agentic.agents.planning import ReActPlanner  # ❌ Won't work without external pkg
from sage.libs.agentic.agents.action.tool_selection import DFSDTSelector  # ❌ Won't work
```

## Dependencies to Declare in isage-agentic

```toml
dependencies = [
    "sage-libs>=0.1.4",  # For interfaces
    "transformers>=4.52.0",
    "torch>=2.7.0",
    "sentence-transformers>=3.1.0",
]
```

## Estimated Timeline

- Phase 1 (Interface prep): 2-3 days
- Phase 2 (External repo): 3-5 days
- Phase 3 (Integration): 1-2 days
- Phase 4 (Cleanup): 1 day

**Total**: ~2 weeks for complete externalization

## Benefits

1. **Independent versioning**: agentic can evolve without SAGE core changes
1. **Reduced sage-libs size**: 1.3M → ~100K (interface only)
1. **Faster CI**: Smaller test matrix for core
1. **Clear boundaries**: Explicit interface contracts
1. **Reusability**: Others can use agentic without full SAGE

## Risks & Mitigations

**Risk**: Circular dependencies\
**Mitigation**: Keep interfaces in sage-libs, implementations in external

**Risk**: Breaking existing code\
**Mitigation**: Factory pattern keeps working, add migration guide

**Risk**: Complex dependency graph\
**Mitigation**: Document dependencies clearly in dependencies-spec.yaml

______________________________________________________________________

**Next Actions**:

1. Review this plan with team
1. Create interface/ structure
1. Start Phase 1 implementation
