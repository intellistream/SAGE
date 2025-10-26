# sage-apps

Application examples showcasing SAGE's capabilities.

**Layer**: L5 (Applications)

## Overview

`sage-apps` contains real-world application examples built with SAGE:

- **Medical Diagnosis**: AI-powered medical image analysis system
- **Video Intelligence**: Video content analysis pipeline
- More applications coming soon...

## Applications

### Medical Diagnosis

AI-powered medical diagnosis system using MRI image analysis.

**Features**:

- Diagnostic agent with image analysis
- Report generation
- Knowledge base integration
- Batch processing support

**Location**: `packages/sage-apps/src/sage/apps/medical_diagnosis/`

**Quick Start**:

```bash
# Setup
cd packages/sage-apps/src/sage/apps/medical_diagnosis

# Download dataset (optional)
python scripts/download_lumbar_dataset.py

# Prepare data
python scripts/prepare_data.py

# Run diagnosis
python run_diagnosis.py
```

**Components**:

- `agents/`: Diagnostic agents (DiagnosticAgent, ImageAnalyzer, ReportGenerator)
- `tools/`: Medical knowledge base and utilities
- `config/`: Agent and model configurations
- `scripts/`: Data preparation scripts

**Documentation**:

- See `packages/sage-apps/src/sage/apps/medical_diagnosis/README.md`
- Example workflows in `examples/apps/medical_diagnosis/`

### Video Intelligence

Video content analysis and understanding pipeline.

**Features**:

- Video frame extraction
- Object detection and tracking
- Scene understanding
- Event detection
- Content summarization

**Location**: `packages/sage-apps/src/sage/apps/video/`

**Quick Start**:

```bash
# Run video pipeline
cd packages/sage-apps/src/sage/apps/video
python video_intelligence_pipeline.py --video input.mp4
```

**Operators**:

- `perception.py`: Visual perception (object detection, face recognition)
- `analytics.py`: Scene analysis and event detection
- `preprocessing.py`: Video preprocessing (frame extraction, resizing)
- `formatters.py`: Output formatting
- `sources.py`: Video input sources
- `sinks.py`: Result output

**Documentation**:

- See `packages/sage-apps/src/sage/apps/video/README.md`

## Installation

Install sage-apps:

```bash
pip install -e packages/sage-apps
```

Or with all dependencies:

```bash
pip install -e packages/sage-apps[all]
```

## Running Examples

### Medical Diagnosis

```python
from sage.apps.medical_diagnosis import DiagnosticAgent

# Create diagnostic agent
agent = DiagnosticAgent(config_path="config/agent_config.yaml")

# Diagnose single case
result = agent.diagnose(
    image_path="data/case_001.npy", patient_info={"age": 45, "gender": "男"}
)

print(result.report)
```

### Video Intelligence

```python
from sage.kernel.api.local_environment import LocalStreamEnvironment
from sage.apps.video import VideoIntelligencePipeline

# Create pipeline
env = LocalStreamEnvironment("video_analysis")
pipeline = VideoIntelligencePipeline(env)

# Process video
results = pipeline.process("input.mp4")
```

## Development

### Adding New Applications

1. Create application directory:

   ```
   packages/sage-apps/src/sage/apps/my_app/
   ├── __init__.py
   ├── README.md
   ├── operators/      # Custom operators
   ├── agents/         # If using agents
   ├── config/         # Configuration files
   └── scripts/        # Utility scripts
   ```

1. Implement your application logic

1. Add documentation and examples

1. Add tests in `packages/sage-apps/tests/my_app/`

### Testing

```bash
# Run all tests
cd packages/sage-apps
pytest tests/ -v

# Test specific app
pytest tests/medical_diagnosis/ -v
pytest tests/video/ -v
```

## Architecture

Applications in `sage-apps` demonstrate:

- **Integration patterns**: How to combine kernel, libs, and middleware
- **Best practices**: Recommended ways to structure SAGE applications
- **Real-world usage**: Practical examples with complete workflows

## See Also

- [Package Architecture](../../concepts/architecture/package-structure.md)
- [Getting Started](../../getting-started/quickstart.md)
- [Examples](https://github.com/intellistream/SAGE/tree/main/examples)

## Contributing

We welcome new application examples! Please:

1. Ensure code quality and documentation
1. Add comprehensive tests
1. Follow SAGE architecture guidelines
1. Include setup instructions and dependencies

See [Contributing Guide](../../community/community.md) for details.
