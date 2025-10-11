# Video Intelligence Configuration Guide

## Configuration File

This directory contains the default configuration for the SAGE Video Intelligence application.

**File**: `default_config.yaml`

## Configuration Options

### Video Processing
- `video_path`: Path to input video file (required)
- `sample_every_n_frames`: Frame sampling rate (default: 3)
- `max_frames`: Maximum frames to process (optional, for testing)
- `frame_resize`: Frame resize dimension (default: 336)

### Analysis Settings
- `analysis.clip_templates`: Scene understanding templates
- `analysis.clip_top_k`: Top K CLIP results (default: 4)
- `analysis.classifier_top_k`: Top K classifier results (default: 5)
- `analysis.min_event_confidence`: Minimum confidence threshold (default: 0.25)
- `analysis.brightness_delta_threshold`: Brightness change threshold (default: 35.0)

### Window Summary
- `window_summary.window_seconds`: Summary window size (default: 8.0)
- `window_summary.stride_seconds`: Window stride (default: 4.0)
- `window_summary.max_frames_per_window`: Max frames per window (default: 120)

### Output Settings
- `output.timeline_path`: Timeline output path
- `output.summary_path`: Summary output path
- `output.event_stats_path`: Event statistics path

### Integrations
- `integrations.enable_sage_db`: Enable SAGE DB integration
- `integrations.enable_sage_flow`: Enable SAGE Flow integration
- `integrations.enable_neuromem`: Enable NeuroMem integration

## Usage

### Use Default Configuration
```bash
python examples/apps/run_video_intelligence.py --video path/to/video.mp4
```

### Use Custom Configuration
```bash
# Copy default config
cp packages/sage-apps/src/sage/apps/video/config/default_config.yaml my_config.yaml

# Edit as needed
vim my_config.yaml

# Use it
python examples/apps/run_video_intelligence.py --config my_config.yaml --video path/to/video.mp4
```

## Example Configurations

### Quick Test (Limited Frames)
```yaml
video_path: "./test_video.mp4"
max_frames: 30
sample_every_n_frames: 5
```

### High Quality Analysis
```yaml
video_path: "./important_video.mp4"
sample_every_n_frames: 1  # Process every frame
frame_resize: 512
analysis:
  clip_top_k: 10
  min_event_confidence: 0.15
```

## Configuration Priority

The application searches for configuration in this order:
1. User-specified config (`--config` argument)
2. This default config file
3. Examples config directory (backward compatibility)
4. Built-in defaults

## Troubleshooting

### Config File Not Found
- Check file path (absolute or relative to working directory)
- Verify file extension (`.yaml`)
- Check file permissions

### Invalid Configuration
- Check YAML syntax (indentation, colons)
- Verify all required fields
- Check data types (strings, numbers, lists)
