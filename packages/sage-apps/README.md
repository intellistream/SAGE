# SAGE Applications

Real-world AI applications built on the SAGE framework, showcasing end-to-end solutions for various domains.

## Overview

`isage-apps` provides production-ready applications demonstrating SAGE's capabilities:

- **Video Intelligence**: Multi-model video analysis pipeline with CLIP and MobileNetV3
- **Medical Diagnosis**: AI-assisted medical image analysis for healthcare

## Installation

### Basic Installation
```bash
pip install isage-apps
```

### Install with Specific Applications
```bash
# Video intelligence only
pip install isage-apps[video]

# Medical diagnosis only
pip install isage-apps[medical]

# All applications
pip install isage-apps[all]
```

### Development Installation
```bash
cd packages/sage-apps
pip install -e ".[dev]"
```

## Applications

### 1. Video Intelligence

Advanced video analysis pipeline combining multiple AI models:

- **Frame sampling and preprocessing**
- **Zero-shot scene understanding** (CLIP)
- **Object classification** (MobileNetV3)
- **Temporal anomaly detection**
- **Sliding-window summarization**
- **Keyed event aggregation**

**Quick Start:**
```bash
pip install isage-apps[video]
python -m sage.apps.video.video_intelligence_pipeline --video path/to/video.mp4
```

**Features:**
- Multi-model inference pipeline
- Real-time processing with SAGE operators
- Structured JSON output (timeline, summary, events)
- Console progress monitoring
- Graceful degradation (works offline with cached models)

**Documentation:** See `sage/apps/video/README_intelligence_demo.md`

### 2. Medical Diagnosis

AI-assisted diagnostic system for medical imaging:

- **Multi-agent architecture** (diagnostic, image analysis, report generation)
- **Knowledge-based reasoning**
- **Structured medical reports**
- **Training and evaluation tools**

**Quick Start:**
```bash
pip install isage-apps[medical]
python -m sage.apps.medical_diagnosis.run_diagnosis
```

**Features:**
- Agent-based diagnostic workflow
- Medical knowledge base integration
- Configurable diagnostic criteria
- Report generation

**Documentation:** See `sage/apps/medical_diagnosis/README.md`

## Package Structure

```
sage-apps/
├── src/sage/apps/
│   ├── __init__.py
│   ├── video/                    # Video intelligence application
│   │   ├── video_intelligence_pipeline.py
│   │   ├── operators/            # SAGE operators for video
│   │   ├── config/               # Configuration files
│   │   └── README_intelligence_demo.md
│   └── medical_diagnosis/        # Medical diagnosis application
│       ├── run_diagnosis.py
│       ├── agents/               # Diagnostic agents
│       ├── config/               # Agent configurations
│       ├── data/                 # Medical datasets
│       └── README.md
└── tests/                        # Application tests
```

## Dependencies

### Core Framework
- `isage-common` - Common utilities
- `isage-kernel` - Runtime and operators
- `isage-middleware` - Services (SageDB, SageFlow, NeuroMem)
- `isage-libs` - Operator libraries

### Application-Specific

**Video Intelligence:**
- `opencv-python` - Video processing
- `torch` - Deep learning
- `transformers` - CLIP and language models

**Medical Diagnosis:**
- `pillow` - Image processing
- `scikit-learn` - ML utilities

## Usage Examples

### Video Intelligence

```python
from sage.apps.video.video_intelligence_pipeline import main

# Run with custom video
main(["--video", "my_video.mp4", "--max-frames", "100"])
```

### Medical Diagnosis

```python
from sage.apps.medical_diagnosis.run_diagnosis import run_diagnosis

# Run diagnostic pipeline
run_diagnosis(config_path="config/agent_config.yaml")
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Format code
black src/

# Lint
ruff check src/

# Type checking
mypy src/
```

## CI/CD Notes

**Video Intelligence:**
- Requires HuggingFace model downloads (~170MB)
- Tagged with `@test:skip` in CI due to network restrictions
- Test locally with: `python -m sage.apps.video.video_intelligence_pipeline`

**Medical Diagnosis:**
- Works in CI (uses local data)
- Test with: `pytest tests/test_medical_diagnosis.py`

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](../../LICENSE) for details.

## Related Documentation

- [SAGE Framework](../../README.md)
- [Video Intelligence Demo](src/sage/apps/video/README_intelligence_demo.md)
- [Medical Diagnosis](src/sage/apps/medical_diagnosis/README.md)
- [CI Test Fix](src/sage/apps/video/CI_TEST_FIX.md)
