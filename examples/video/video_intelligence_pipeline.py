"""Advanced video intelligence demo built on SAGE.

This example upgrades the original notebook-only demo with a fully scripted
pipeline that showcases SAGE's declarative operators (Batch, Map, FlatMap,
KeyBy, Sink) and combines multiple AI capabilities:

* Frame sampling and preprocessing
* Zero-shot scene understanding with CLIP
* Image classification with MobileNetV3
* Lightweight temporal anomaly detection
* Sliding-window summarisation backed by an optional HuggingFace summariser
* Structured event stream with keyed aggregation for observability
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.local_environment import LocalEnvironment

try:  # Optional middleware components
    from sage.middleware.components.neuromem.micro_service.neuromem_vdb_service import (
        NeuroMemVDBService,
    )
except ImportError:  # pragma: no cover - optional dependency
    NeuroMemVDBService = None  # type: ignore[assignment]

try:
    from sage.middleware.components.sage_db.python.micro_service import SageDBService
except ImportError:  # pragma: no cover - optional dependency
    SageDBService = None  # type: ignore[assignment]

try:
    from sage.middleware.components.sage_flow.python.micro_service import (
        SageFlowService,
    )
except ImportError:  # pragma: no cover - optional dependency
    SageFlowService = None  # type: ignore[assignment]

from examples.video.operators import (
    EventStatsSink,
    FrameEventEmitter,
    FrameLightweightFormatter,
    FrameObjectClassifier,
    FramePreprocessor,
    SageMiddlewareIntegrator,
    SceneConceptExtractor,
    SlidingWindowSummaryEmitter,
    SummaryMemoryAugmentor,
    SummarySink,
    TemporalAnomalyDetector,
    TimelineSink,
    VideoFrameSource,
)

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "config_video_intelligence.yaml"
)


def load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """Load YAML configuration for the demo."""

    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must define a mapping at the top level")

    return data


# ---------------------------------------------------------------------------
# Pipeline assembly
# ---------------------------------------------------------------------------


def build_pipeline(env: LocalEnvironment, config: Dict[str, Any]) -> None:
    video_path = config["video_path"]
    sample_every = config["sample_every_n_frames"]
    max_frames = config.get("max_frames")
    frame_resize = config.get("frame_resize")

    analysis_cfg = config.get("analysis", {})
    window_cfg = config.get("window_summary", {})
    output_cfg = config.get("output", {})
    integrations_cfg = config.get("integrations", {})

    logger = CustomLogger("video_intelligence_pipeline")

    # ------------------------------------------------------------------
    # Service registrations (SageDB, SageFlow, NeuroMem)
    # ------------------------------------------------------------------
    db_cfg = integrations_cfg.get("sage_db", {})
    db_service_name = db_cfg.get("service_name", "video_scene_db")
    db_dimension = int(db_cfg.get("dimension", 512))
    enable_db = bool(integrations_cfg.get("enable_sage_db", False))
    if enable_db and SageDBService is None:
        logger.warning(
            "SageDBService is unavailable (module missing). Disabling SageDB integration."
        )
        enable_db = False

    flow_cfg = integrations_cfg.get("sage_flow", {})
    flow_service_name = flow_cfg.get("service_name", "video_vector_flow")
    flow_dim = int(flow_cfg.get("dim", 512))
    flow_dtype = flow_cfg.get("dtype", "Float32")
    enable_flow = bool(integrations_cfg.get("enable_sage_flow", False))
    if enable_flow and SageFlowService is None:
        logger.warning(
            "SageFlowService is unavailable (module missing). Disabling SageFlow integration."
        )
        enable_flow = False

    memory_cfg = integrations_cfg.get("neuromem", {})
    memory_service_name = memory_cfg.get("service_name", "video_memory_service")
    memory_collection = memory_cfg.get("collection_name", "demo_collection")
    enable_neuromem = bool(integrations_cfg.get("enable_neuromem", False))
    if enable_neuromem and NeuroMemVDBService is None:
        logger.warning(
            "NeuroMemVDBService is unavailable (module missing). Disabling NeuroMem integration."
        )
        enable_neuromem = False

    if enable_db:
        try:
            env.register_service(
                db_service_name,
                SageDBService,
                dimension=db_dimension,
                index_type=db_cfg.get("index_type", "AUTO"),
            )
            logger.info(
                "Registered SageDB service '%s' (dim=%d)",
                db_service_name,
                db_dimension,
            )
        except Exception as exc:  # pragma: no cover - runtime resilience
            logger.error("Failed to register SageDB service: %s", exc)
            enable_db = False

    if enable_flow:
        try:
            env.register_service(
                flow_service_name,
                SageFlowService,
                dim=flow_dim,
                dtype=flow_dtype,
            )
            logger.info(
                "Registered SageFlow service '%s' (dim=%d, dtype=%s)",
                flow_service_name,
                flow_dim,
                flow_dtype,
            )
        except Exception as exc:  # pragma: no cover - runtime resilience
            logger.error("Failed to register SageFlow service: %s", exc)
            enable_flow = False

    if enable_neuromem:
        try:
            env.register_service(
                memory_service_name,
                NeuroMemVDBService,
                collection_name=memory_collection,
            )
            logger.info(
                "Registered NeuroMem service '%s' (collection=%s)",
                memory_service_name,
                memory_collection,
            )
        except Exception as exc:  # pragma: no cover - runtime resilience
            logger.error("Failed to register NeuroMem service: %s", exc)
            enable_neuromem = False

    source_stream = env.from_source(
        VideoFrameSource,
        video_path=video_path,
        sample_every_n_frames=sample_every,
        max_frames=max_frames,
    )

    annotated_stream = (
        source_stream.map(FramePreprocessor, target_size=frame_resize)
        .map(
            SceneConceptExtractor,
            templates=analysis_cfg.get("clip_templates", []),
            top_k=analysis_cfg.get("clip_top_k", 4),
        )
        .map(
            FrameObjectClassifier,
            top_k=analysis_cfg.get("classifier_top_k", 5),
        )
        .map(
            TemporalAnomalyDetector,
            brightness_delta_threshold=analysis_cfg.get(
                "brightness_delta_threshold", 35.0
            ),
        )
        .map(
            SageMiddlewareIntegrator,
            enable_db=enable_db,
            db_service_name=db_service_name,
            db_neighbor_k=int(db_cfg.get("neighbor_k", 3)),
            enable_flow=enable_flow,
            flow_service_name=flow_service_name,
            flow_auto_flush=int(flow_cfg.get("auto_flush", 1)),
        )
        .map(FrameLightweightFormatter)
    )

    annotated_stream.sink(
        TimelineSink,
        output_path=output_cfg.get("timeline_path"),
        preview_every=output_cfg.get("preview_every", 12),
    )

    events_stream = annotated_stream.flatmap(
        FrameEventEmitter,
        min_confidence=analysis_cfg.get("min_event_confidence", 0.22),
    )

    events_stream.sink(
        EventStatsSink,
        stats_path=output_cfg.get("event_stats_path"),
        log_every=30,
    )

    summary_stream = annotated_stream.flatmap(
        SlidingWindowSummaryEmitter,
        window_seconds=window_cfg.get("window_seconds", 8.0),
        stride_seconds=window_cfg.get("stride_seconds", 4.0),
        max_frames=window_cfg.get("max_frames_per_window", 120),
        summarizer_model=window_cfg.get("summarizer_model"),
        max_summary_tokens=window_cfg.get("max_summary_tokens", 90),
    )

    summary_stream = summary_stream.map(
        SummaryMemoryAugmentor,
        enable=enable_neuromem,
        service_name=memory_service_name,
        top_k=int(memory_cfg.get("topk", 3)),
        collection_name=memory_collection,
        with_metadata=bool(memory_cfg.get("with_metadata", True)),
    )

    summary_stream.sink(
        SummarySink,
        summary_path=output_cfg.get("summary_path"),
    )


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the advanced SAGE video intelligence pipeline"
    )
    parser.add_argument(
        "--video",
        dest="video_path",
        type=str,
        help="Path to a local video file (overrides config)",
    )
    parser.add_argument(
        "--config",
        dest="config_path",
        type=str,
        help="Optional YAML config overriding defaults",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        type=str,
        help="Optional base directory for generated artefacts",
    )
    parser.add_argument(
        "--max-frames",
        dest="max_frames",
        type=int,
        help="Limit the number of frames processed (for quick demos)",
    )
    return parser.parse_args()


def apply_runtime_overrides(config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    if args.video_path:
        config["video_path"] = args.video_path
    if args.max_frames is not None:
        config["max_frames"] = args.max_frames

    output_dir = args.output_dir
    if output_dir:
        out_cfg = config.setdefault("output", {})
        base = Path(output_dir)
        out_cfg["timeline_path"] = str(base / "timeline.jsonl")
        out_cfg["summary_path"] = str(base / "summary.json")
        out_cfg["event_stats_path"] = str(base / "event_stats.json")

    return config


def main() -> None:
    args = parse_args()
    config = load_config(args.config_path)
    config = apply_runtime_overrides(config, args)

    video_path = config.get("video_path")
    if not video_path or not os.path.exists(video_path):
        raise FileNotFoundError(
            f"Video file '{video_path}' does not exist. Provide --video or update the config."
        )

    env = LocalEnvironment("video_intelligence_demo")
    build_pipeline(env, config)

    CustomLogger("video_intelligence_demo").info(
        "Starting pipeline on video '%s'", video_path
    )
    env.submit()
    CustomLogger("video_intelligence_demo").info("Pipeline execution completed")


if __name__ == "__main__":  # pragma: no cover
    main()
