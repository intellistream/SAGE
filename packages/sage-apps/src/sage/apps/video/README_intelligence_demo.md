# SAGE Video Intelligence Demo

This advanced example upgrades the original notebook-only prototype into a fully scripted
application that highlights several core strengths of SAGE:

- Declarative pipeline assembly with `BatchFunction`, `MapFunction`, `FlatMapFunction`, `KeyBy`, and
  custom sinks.
- Multi-model perception using CLIP zero-shot scene understanding and MobileNetV3 object
  classification.
- Lightweight temporal analytics such as lighting-change detection and sliding-window summarisation
  with optional HuggingFace summariser support.
- Optional middleware integrations that publish embeddings to SageDB/SageFlow and enrich summaries
  with NeuroMem retrievals.
- Structured JSONL/JSON artefacts that make it easy to build dashboards or replay insights after the
  run.

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

To exercise the SageDB and SageFlow integrations, compile the optional middleware components (skip
if they are already built on your machine):

```bash
pushd packages/sage-middleware/src/sage/middleware/components/sage_db && ./build.sh && popd
pushd packages/sage-middleware/src/sage/middleware/components/sage_flow && ./build.sh && popd
```

NeuroMem ships with a demo collection under `data/neuromem_vdb/`, so retrieval-only workflows run
out of the box without extra build steps.

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

Key options include frame sampling cadence, CLIP templates, summariser model, and output paths. The
`integrations` section toggles SageDB/SageFlow/NeuroMem usage and lets you align service names or
dimensions with your deployment.

## Working with Sage services

With integrations enabled (the default configuration):

- **SageDB** stores every frame's CLIP embedding and attaches the nearest historical frames based on
  vector similarity to each timeline entry.
- **SageFlow** receives the same embeddings via `push`/`run`, allowing downstream vector processors
  or Python sinks to react in near real-time.
- **NeuroMem** queries the `demo_collection` VDB using each sliding-window summary and adds the top
  matches under `memory_recall`.

Disable any integration by setting the corresponding `enable_*` flag to `false` in the YAML if a
component is unavailable; the rest of the pipeline continues uninterrupted.

## Extending the demo

- Replace MobileNetV3 with a custom detector or plug in your enterprise model.
- Extend the SageFlow sink to forward vectors into your monitoring or alerting stack.
- Enrich the SageDB metadata (e.g. attach scene hashes, embeddings from other models) to power
  downstream retrieval tools.
- Feed the timeline JSONL into the observability stack (`docs-public/`) to visualise concept drift
  and anomaly density over time.
- Swap the summariser for project-specific prompt templates or integrate with SAGE's RAG library for
  knowledge-grounded reports.

Have fun exploring richer multi-modal applications on top of SAGE! 🎥

## Output Format Details

### 1. Timeline (video_timeline.jsonl)

Each line is a JSON object representing one processed frame:

```json
{
  "frame_id": 0,
  "timestamp": 0.0,
  "primary_scene": "Outdoor cycling activity",
  "scene_confidences": {"Outdoor cycling activity": 0.85, "Car driving on a road": 0.12},
  "top_object_labels": ["bicycle", "person", "tree"],
  "object_confidences": [0.92, 0.88, 0.75],
  "brightness": 128.5,
  "is_bright_change": false,
  "sagedb_neighbors": [{"frame_id": 12, "distance": 0.15}]
}
```

**Fields:**

- `frame_id`: Frame number in the video
- `timestamp`: Time in seconds
- `primary_scene`: Top CLIP-matched scene from templates
- `scene_confidences`: Confidence scores for all scene templates
- `top_object_labels`: Detected objects from MobileNetV3
- `object_confidences`: Confidence for each detected object
- `brightness`: Average frame brightness (0-255)
- `is_bright_change`: Whether significant lighting change detected
- `sagedb_neighbors`: Similar frames from vector database (if enabled)

### 2. Summary (video_summary.json)

Sliding-window natural language summaries:

```json
{
  "window_count": 5,
  "summaries": [
    {
      "window_id": 0,
      "start_frame": 0,
      "end_frame": 30,
      "start_time": 0.0,
      "end_time": 10.0,
      "text": "The video shows outdoor cycling activity with people riding bicycles...",
      "memory_recall": [
        {"text": "Previous cycling scene from 2024-01-15", "score": 0.89}
      ]
    }
  ]
}
```

**Fields:**

- `window_count`: Total number of windows processed
- `summaries`: Array of window summaries
  - `window_id`: Sequential window number
  - `start_frame`/`end_frame`: Frame range in window
  - `start_time`/`end_time`: Time range in seconds
  - `text`: Natural language summary from HuggingFace model
  - `memory_recall`: Related memories from NeuroMem (if enabled)

### 3. Event Stats (video_event_stats.json)

Aggregated statistics for detected events:

```json
{
  "total_events": 45,
  "event_counts": {
    "scene_outdoor_cycling": 20,
    "object_bicycle": 18,
    "object_person": 22,
    "brightness_change": 5,
    "scene_car_driving": 12
  }
}
```

**Fields:**

- `total_events`: Total number of events detected across all frames
- `event_counts`: Counter for each event type
  - Events are prefixed by type: `scene_`, `object_`, `brightness_change`, etc.

### Using the Output

**Analyze the timeline:**

```python
import json

# Load timeline
with open("artifacts/video_timeline.jsonl") as f:
    frames = [json.loads(line) for line in f]

# Find frames with specific scenes
cycling_frames = [f for f in frames if "cycling" in f["primary_scene"].lower()]
print(f"Found {len(cycling_frames)} cycling frames")

# Track brightness changes
brightness_changes = [f for f in frames if f.get("is_bright_change")]
print(f"Detected {len(brightness_changes)} scene transitions")
```

**Analyze summaries:**

```python
import json

# Load summaries
with open("artifacts/video_summary.json") as f:
    data = json.load(f)

# Print all summaries
for summary in data["summaries"]:
    print(f"Window {summary['window_id']}: {summary['text']}")
```

**Visualize event distribution:**

```python
import json
import matplotlib.pyplot as plt

# Load event stats
with open("artifacts/video_event_stats.json") as f:
    stats = json.load(f)

# Plot top 10 events
events = sorted(stats["event_counts"].items(), key=lambda x: x[1], reverse=True)[:10]
labels, counts = zip(*events)

plt.barh(labels, counts)
plt.xlabel("Count")
plt.title("Top 10 Detected Events")
plt.tight_layout()
plt.show()
```
