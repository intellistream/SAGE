# Migration to sage-apps Package

## Overview

This document describes the migration of application code to the new `sage-apps` package.

## What Changed

### New Package Structure

Created a new package `isage-apps` (`sage.apps`) to house real-world applications built on SAGE:

```
packages/sage-apps/
├── src/sage/apps/
│   ├── __init__.py
│   ├── video/                    # Moved from examples/video
│   │   ├── video_intelligence_pipeline.py
│   │   ├── operators/
│   │   ├── config/
│   │   └── README_intelligence_demo.md
│   └── medical_diagnosis/        # Moved from sage-libs/applications
│       ├── run_diagnosis.py
│       ├── agents/
│       ├── config/
│       └── README.md
├── tests/
├── pyproject.toml
└── README.md
```

### Moved Applications

#### 1. Video Intelligence (`examples/video` → `sage.apps.video`)

**Old Location:** `/examples/video/`  
**New Location:** `/packages/sage-apps/src/sage/apps/video/`

**Import Changes:**
```python
# Old (when in examples/)
from operators.perception import SceneConceptExtractor
from operators.sources import VideoFrameSource

# New (as installed package)
from sage.apps.video.operators.perception import SceneConceptExtractor
from sage.apps.video.operators.sources import VideoFrameSource
```

**Running the Application:**
```bash
# Old
python examples/video/video_intelligence_pipeline.py

# New (after installation)
pip install isage-apps[video]
python -m sage.apps.video.video_intelligence_pipeline

# Or directly
cd packages/sage-apps
python src/sage/apps/video/video_intelligence_pipeline.py
```

#### 2. Medical Diagnosis (`sage.libs.applications.medical_diagnosis` → `sage.apps.medical_diagnosis`)

**Old Location:** `/packages/sage-libs/src/sage/libs/applications/medical_diagnosis/`  
**New Location:** `/packages/sage-apps/src/sage/apps/medical_diagnosis/`

**Import Changes:**
```python
# Old
from sage.libs.applications.medical_diagnosis import DiagnosticAgent
from sage.libs.applications.medical_diagnosis.agents.image_analyzer import ImageAnalyzer

# New
from sage.apps.medical_diagnosis import DiagnosticAgent
from sage.apps.medical_diagnosis.agents.image_analyzer import ImageAnalyzer
```

**Running the Application:**
```bash
# Old
python -m sage.libs.applications.medical_diagnosis.run_diagnosis

# New
pip install isage-apps[medical]
python -m sage.apps.medical_diagnosis.run_diagnosis
```

## Rationale

### Why a Separate Package?

1. **Clear Separation of Concerns**
   - `sage-kernel`: Core runtime and operators
   - `sage-libs`: Reusable operator libraries
   - `sage-apps`: End-to-end applications

2. **Dependency Management**
   - Applications have heavy dependencies (PyTorch, transformers, etc.)
   - Users can install only what they need
   - Core framework stays lightweight

3. **Development Workflow**
   - Applications can be developed independently
   - Easier to add new applications
   - Better testing isolation

4. **Distribution**
   - Applications can have separate release cycles
   - Optional dependencies clearly defined
   - Users choose: `pip install isage-apps[video]` or `[medical]` or `[all]`

### Why Move from Examples?

The `examples/` folder was meant for simple demonstrations, but the video intelligence pipeline evolved into a production-ready application with:
- Multi-file structure
- Complex operators
- Configuration management
- Comprehensive documentation

Moving it to `sage-apps` better reflects its maturity.

### Why Move from sage-libs?

`sage-libs` is for reusable **operator libraries** that multiple applications can use. The medical diagnosis application is a complete **end-to-end solution**, not a library.

## Installation

### As User
```bash
# Install specific application
pip install isage-apps[video]
pip install isage-apps[medical]

# Install all applications
pip install isage-apps[all]
```

### As Developer
```bash
cd packages/sage-apps
pip install -e ".[dev]"
```

## Testing

### Run All Tests
```bash
cd packages/sage-apps
pytest tests/
```

### Test Specific Application
```bash
# Video intelligence (skipped in CI due to model downloads)
python -m sage.apps.video.video_intelligence_pipeline --video test.mp4

# Medical diagnosis
python -m sage.apps.medical_diagnosis.run_diagnosis
```

## Migration Checklist

- [x] Create `sage-apps` package structure
- [x] Create `pyproject.toml` with dependencies
- [x] Move `examples/video` → `sage.apps.video`
- [x] Move `sage.libs.applications.medical_diagnosis` → `sage.apps.medical_diagnosis`
- [x] Update import paths in medical_diagnosis
- [x] Create README.md
- [x] Create basic tests
- [x] Create migration documentation
- [ ] Update root Makefile to include sage-apps
- [ ] Update CI workflows
- [ ] Update main documentation
- [ ] Remove old locations (after verification)

## Impact on Existing Code

### Minimal Impact
- Core framework (kernel, common, middleware) unchanged
- sage-libs operators unchanged
- Only applications moved

### User Impact
Users currently running examples need to update:

```bash
# Old workflow
git clone SAGE
python examples/video/video_intelligence_pipeline.py

# New workflow
pip install isage-apps[video]
python -m sage.apps.video.video_intelligence_pipeline
```

### Developer Impact
Developers contributing applications should now:
1. Create new applications in `packages/sage-apps/src/sage/apps/`
2. Add dependencies to `pyproject.toml` optional-dependencies
3. Add tests in `packages/sage-apps/tests/`

## Future Applications

New applications should be added to `sage-apps`:

```
sage.apps/
├── video/              # ✅ Migrated
├── medical_diagnosis/  # ✅ Migrated
├── nlp_pipeline/       # 🔜 Future
├── financial_analysis/ # 🔜 Future
└── ...
```

## Questions?

See the main [SAGE Documentation](../../README.md) or open an issue on GitHub.

---

**Migration Date:** October 10, 2025  
**Status:** ✅ Complete - Ready for testing and verification
