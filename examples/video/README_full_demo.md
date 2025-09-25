# SAGE Full Video Demo

This script demonstrates a complete SAGE pipeline for video analysis and retrieval-augmented QA.

## Features
- Reads a local video and samples frames
- Generates per-frame captions (CLIP zero-shot or fallback)
- Indexes captions into ChromaDB (or in-memory fallback)
- Runs a RAG QA query over indexed captions
- Optionally uses an LLM generator for answers
- Robust to missing dependencies (CLIP, chromadb, generator)

## How to Run

### 1. Prepare a video file
Place a video file in the workspace, e.g. `examples/video/your_video.mp4`.

### 2. (Optional) Edit the config
Edit `examples/config/config_video_full.yaml` to set the video path and parameters.

### 3. Run with config
```bash
python examples/video/video_full_demo.py --config examples/config/config_video_full.yaml
```

### 4. Run with CLI flags
```bash
python examples/video/video_full_demo.py --video examples/video/your_video.mp4 --query "What is happening?" --sample-every 5 --analysis-interval 1 --max-frames 120
```

### 5. (Optional) Enable LLM generator
Set environment variables for OpenAI-compatible generator:
```
export SAGE_OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_API_KEY="sk-..."
```
Or add a `generator:` block in the YAML config.

## Output
- Prints pipeline progress and QA result to terminal.
- If generator is enabled, answers are generated; otherwise, context and heuristic answer are shown.

## Troubleshooting
- If CLIP or chromadb are missing, the script will use fallback logic and print warnings.
- For test mode, set `SAGE_EXAMPLES_MODE=test` to force all components into lightweight mock fallbacks.

## Advanced
- You can tune sampling, analysis interval, and max frames in the config or CLI.
- The pipeline can be extended to expose agent tools or additional sinks.
