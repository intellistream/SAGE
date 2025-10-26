# Medical Diagnosis Configuration Guide

## Configuration File

This directory contains the configuration for the SAGE Medical Diagnosis Agent.

**File**: `agent_config.yaml`

## Configuration Options

### Agent Settings

- `agent.name`: Agent name
- `agent.version`: Agent version
- `agent.max_iterations`: Maximum iterations (default: 5)
- `agent.timeout`: Timeout in seconds (default: 300)

### Model Settings

- `models.vision_model`: Vision model for image analysis (default: Qwen/Qwen2-VL-7B-Instruct)
- `models.llm_model`: Language model for report generation (default: Qwen/Qwen2.5-7B-Instruct)
- `models.embedding_model`: Embedding model for retrieval (default: BAAI/bge-large-zh-v1.5)

### Service Configuration

#### VLLM Service

- `services.vllm.enabled`: Enable VLLM (default: true)
- `services.vllm.gpu_memory_utilization`: GPU memory usage (default: 0.9)
- `services.vllm.tensor_parallel_size`: Tensor parallel size (default: 1)

#### Embedding Service

- `services.embedding.method`: Embedding method (default: "hf")
- `services.embedding.cache_enabled`: Enable cache (default: true)
- `services.embedding.batch_size`: Batch size (default: 32)

#### Vector Database

- `services.vector_db.backend`: Backend type (default: "sage_db")
- `services.vector_db.collection_name`: Collection name
- `services.vector_db.top_k`: Top K results (default: 5)

### Image Processing

- `image_processing.input_size`: Input image size (default: \[512, 512\])
- `image_processing.normalization`: Enable normalization (default: true)
- `image_processing.segmentation.enabled`: Enable segmentation (default: false)

### Diagnosis Settings

- `diagnosis.confidence_threshold`: Confidence threshold (default: 0.7)
- `diagnosis.detection.disc_herniation_threshold`: Disc herniation threshold (default: 0.8)
- `diagnosis.detection.degeneration_threshold`: Degeneration threshold (default: 0.6)
- `diagnosis.report.include_similar_cases`: Include similar cases (default: true)
- `diagnosis.report.max_similar_cases`: Max similar cases (default: 5)

### Output Settings

- `output.format`: Output format (default: "structured")
- `output.save_path`: Save path (default: "output/diagnoses/")
- `output.include_image_annotations`: Include annotations (default: true)

## Usage

### Use Default Configuration

```bash
python examples/apps/run_medical_diagnosis.py
```

### Use Custom Configuration

```bash
# Copy default config
cp packages/sage-apps/src/sage/apps/medical_diagnosis/config/agent_config.yaml my_config.yaml

# Edit as needed
vim my_config.yaml

# Use it
python examples/apps/run_medical_diagnosis.py --config my_config.yaml
```

## Example Configurations

### High Confidence Mode

```yaml
diagnosis:
  confidence_threshold: 0.85
  detection:
    disc_herniation_threshold: 0.90
    degeneration_threshold: 0.75
```

### Custom Models

```yaml
models:
  vision_model: "my-org/custom-medical-vit"
  llm_model: "my-org/custom-medical-llm"
```

### PDF Report Output

```yaml
output:
  format: "pdf"
  save_path: "reports/"
  include_image_annotations: true
  include_similar_cases: true
  include_references: true
```

## Configuration Priority

The application searches for configuration in this order:

1. User-specified config (`--config` argument)
1. This agent config file
1. Built-in defaults

## Troubleshooting

### Config File Not Found

- Check file path is correct
- Verify file extension (`.yaml`)
- Check file permissions

### Model Loading Errors

- Verify model names are correct
- Check GPU memory availability
- Ensure models are accessible (HuggingFace or local)

### Invalid Configuration

- Check YAML syntax (indentation, colons)
- Verify all required fields are present
- Check data types match expectations
