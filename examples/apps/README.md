# SAGE Applications Examples

This directory contains example scripts for running applications from the `sage-apps` package.

## Overview

The `sage-apps` package provides production-ready AI applications built on the SAGE framework. These
example scripts demonstrate how to use them.

## Available Applications

### 1. Video Intelligence Pipeline

Multi-model video analysis combining CLIP and MobileNetV3 for comprehensive video understanding.

**Run:**

```bash
python examples/apps/run_video_intelligence.py --video path/to/video.mp4
```

**Features:**

- Scene understanding with CLIP
- Action recognition with MobileNetV3
- Frame-by-frame analysis
- Comprehensive video insights

### 2. Medical Diagnosis System

AI-assisted medical imaging analysis using multi-agent systems.

**Run:**

```bash
python examples/apps/run_medical_diagnosis.py
```

**Features:**

- Multi-agent diagnostic workflow
- Medical image analysis
- Knowledge base integration
- Diagnostic report generation

## Installation

### Install All Applications

```bash
pip install -e packages/sage-apps[all]
```

### Install Specific Applications

```bash
# Video Intelligence only
pip install -e packages/sage-apps[video]

# Medical Diagnosis only
pip install -e packages/sage-apps[medical]
```

## Configuration

Each application can be configured using YAML files located in `examples/config/`:

- Video Intelligence: `config_video_intelligence.yaml`
- Medical Diagnosis: Custom configurations in the medical diagnosis data directory

## Development

For developing new applications or modifying existing ones, see:

- `packages/sage-apps/README.md` - Package overview
- `packages/sage-apps/MIGRATION.md` - Migration guide
- `packages/sage-apps/PACKAGE_CREATION_SUMMARY.md` - Implementation details

## Support

For questions or issues:

1. Check the application-specific documentation in `packages/sage-apps/src/sage/apps/<app_name>/`
1. Review the main SAGE documentation
1. Open an issue on GitHub
