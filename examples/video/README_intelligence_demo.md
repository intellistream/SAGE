# SAGE Video Intelligence Demo

This advanced example upgrades the original notebook-only prototype into a fully scripted
application that highlights several core strengths of SAGE:

- Declarative pipeline assembly with `BatchFunction`, `MapFunction`, `FlatMapFunction`,
  `KeyBy`, and custom sinks.
- Multi-model perception using CLIP zero-shot scene understanding and MobileNetV3
  object classification.
- Lightweight temporal analytics such as lighting-change detection and sliding-window
  summarisation with optional HuggingFace summariser support.
- Optional middleware integrations that publish embeddings to SageDB/SageFlow and
  enrich summaries with NeuroMem retrievals.
- Structured JSONL/JSON artefacts that make it easy to build dashboards or replay
  insights after the run.

## Prerequisites

Install the required dependencies for video processing:

```bash
# Method 1: Install via sage-libs (recommended)
pip install -e packages/sage-libs[video]

# Method 2: Install via quickstart (includes all dev dependencies)
./quickstart.sh --dev --yes

# Method 3: Manual installation
pip install torch torchvision transformers opencv-python pillow pyyaml
```

Download a short MP4 file (720p is sufficient) and place it anywhere on disk.

To exercise the SageDB and SageFlow integrations, compile the optional middleware
components (skip if they are already built on your machine):

```bash
pushd packages/sage-middleware/src/sage/middleware/components/sage_db && ./build.sh && popd
pushd packages/sage-middleware/src/sage/middleware/components/sage_flow && ./build.sh && popd
```

NeuroMem ships with a demo collection under `data/neuromem_vdb/`, so retrieval-only
workflows run out of the box without extra build steps.

## Quick start

```bash
# From the repository root
python examples/video/video_intelligence_pipeline.py \
    --video /path/to/your_video.mp4 \
    --output-dir artifacts/video-demo \
    --max-frames 360
```

The command produces three artefacts under `artifacts/video-demo/`:

- `timeline.jsonl` – per-frame structured insights (timestamp, scene tags, objects).
- `summary.json` – sliding-window natural language summaries.
- `event_stats.json` – aggregated counts for concepts, objects, and anomalies.

Set `--max-frames` to limit runtime for quick experimentation. Remove it for full runs.

## Using the YAML config

Fine tune the pipeline via `examples/config/config_video_intelligence.yaml`:

```bash
python examples/video/video_intelligence_pipeline.py \
    --config examples/config/config_video_intelligence.yaml \
    --video /path/to/your_video.mp4
```

Key options include frame sampling cadence, CLIP templates, summariser model, and
output paths. The `integrations` section toggles SageDB/SageFlow/NeuroMem usage and
lets you align service names or dimensions with your deployment.

## Working with Sage services

With integrations enabled (the default configuration):

- **SageDB** stores every frame's CLIP embedding and attaches the nearest historical
  frames based on vector similarity to each timeline entry.
- **SageFlow** receives the same embeddings via `push`/`run`, allowing downstream
  vector processors or Python sinks to react in near real-time.
- **NeuroMem** queries the `demo_collection` VDB using each sliding-window summary and
  adds the top matches under `memory_recall`.

Disable any integration by setting the corresponding `enable_*` flag to `false` in the
YAML if a component is unavailable; the rest of the pipeline continues uninterrupted.

## Extending the demo

- Replace MobileNetV3 with a custom detector or plug in your enterprise model.
- Extend the SageFlow sink to forward vectors into your monitoring or alerting stack.
- Enrich the SageDB metadata (e.g. attach scene hashes, embeddings from other models)
  to power downstream retrieval tools.
- Feed the timeline JSONL into the observability stack (`docs-public/`) to visualise
  concept drift and anomaly density over time.
- Swap the summariser for project-specific prompt templates or integrate with
  SAGE's RAG library for knowledge-grounded reports.

Have fun exploring richer multi-modal applications on top of SAGE! 🎥