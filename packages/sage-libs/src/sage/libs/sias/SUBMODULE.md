# Git Submodule: SIAS

⚠️ **This directory will become a Git submodule** - it will be extracted as a separate repository.

## Repository Information

- **Name:** SIAS (Streaming Importance-Aware Agent System)
- **Future Repository:** https://github.com/intellistream/SIAS.git
- **Branch:** main-dev
- **Path:** `packages/sage-libs/src/sage/libs/sias`

## Current Status

**Development Phase**: SIAS is currently developed in-place within the SAGE monorepo. After Paper 2
acceptance, it will be extracted as an independent repository.

## Module Structure

```
sias/
├── __init__.py              # Public API
├── SUBMODULE.md             # This file
├── core/                    # Core algorithms
│   ├── coreset_selector.py  # Sample selection strategies
│   ├── continual_learner.py # Experience replay buffer
│   └── types.py             # Data types
├── training/                # [TODO] Streaming training
├── memory/                  # [TODO] Reflective memory
└── runtime/                 # [TODO] Adaptive execution
```

## Usage

```python
# Within SAGE
from sage.libs.sias import CoresetSelector, OnlineContinualLearner

# After extraction (standalone)
from sias import CoresetSelector, OnlineContinualLearner
```

## Migration Plan

| Phase   | Status         | Description                                         |
| ------- | -------------- | --------------------------------------------------- |
| Phase 1 | ✅ Done        | Create directory structure, migrate core components |
| Phase 2 | 🔄 In Progress | Update imports in sage-libs, sage-tools             |
| Phase 3 | ⏳ Pending     | Implement remaining SIAS components                 |
| Phase 4 | ⏳ Pending     | Extract to independent repo after paper acceptance  |

## Quick Guide for Future Submodule

### After Extraction

```bash
# Navigate to this directory
cd packages/sage-libs/src/sage/libs/sias

# Make changes
git add .
git commit -m "feat: your change"
git push origin main-dev

# Update reference in main SAGE repo
cd ../../../../../
git add packages/sage-libs/src/sage/libs/sias
git commit -m "chore: update SIAS submodule"
git push origin main-dev
```
