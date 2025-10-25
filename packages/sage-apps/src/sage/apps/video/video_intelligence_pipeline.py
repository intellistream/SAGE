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

@test:skip - Requires HuggingFace model downloads (CLIP, MobileNetV3).
CI environments may have network restrictions preventing model downloads.
Run with: python -m sage.apps.video.video_intelligence_pipeline
Or use: python examples/apps/run_video_intelligence.py
"""

from __future__ import annotations

import argparse
import os
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment


# Helper function to get logger
def get_logger(name: str) -> CustomLogger:
    """Get a CustomLogger instance with the given name."""
    return CustomLogger(outputs=[("console", "INFO")], name=name)


try:  # Optional middleware components - sage_mem (migrated from neuromem)
    from sage.middleware.components.sage_mem.services.neuromem_vdb_service import NeuroMemVDBService
except ImportError:  # pragma: no cover - optional dependency
    NeuroMemVDBService = None  # type: ignore[assignment]

try:
    from sage.middleware.components.sage_db.python.micro_service import SageDBService
except ImportError:  # pragma: no cover - optional dependency
    SageDBService = None  # type: ignore[assignment]

try:
    from sage.middleware.components.sage_flow.python.micro_service import SageFlowService
except ImportError:  # pragma: no cover - optional dependency
    SageFlowService = None  # type: ignore[assignment]

from sage.apps.video.operators import (  # noqa: E402
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

# Default config path
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "default_config.yaml"


def load_config(config_path: str | None) -> dict[str, Any]:
    """Load YAML configuration for the demo."""

    # If user provided a config path, use it
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Config file {path} must define a mapping at the top level")
        print(f"[INFO] Loaded config from: {path}")
        return data

    # Use default config
    if DEFAULT_CONFIG_PATH.exists():
        with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(
                f"Config file {DEFAULT_CONFIG_PATH} must define a mapping at the top level"
            )
        print(f"[INFO] Loaded config from: {DEFAULT_CONFIG_PATH}")
        return data

    # If no config file found, return default configuration
    print("[WARNING] No config file found")
    print("[INFO] Using built-in default configuration")
    return {
        "video_path": None,
        "output_dir": "output/video_intelligence",
        "max_frames": None,
        "sample_every_n_frames": 3,
        "frame_resize": 336,
        "analysis": {
            "clip_top_k": 4,
            "classifier_top_k": 5,
            "min_event_confidence": 0.25,
        },
        "models": {
            "clip": "openai/clip-vit-base-patch32",
            "mobilenet": "google/mobilenet_v3_small_100_224",
        },
    }


def download_test_video(output_path: str) -> bool:
    """Download a small test video for automated testing.

    Args:
        output_path: Path where the video should be saved

    Returns:
        True if download succeeded, False otherwise
    """
    # Use a small sample video from a public source
    # This is a ~1MB sample video suitable for testing
    test_video_url = "https://sample-videos.com/video321/mp4/240/big_buck_bunny_240p_1mb.mp4"

    logger = CustomLogger("video_downloader")

    try:
        logger.info(f"Downloading test video from {test_video_url}")
        logger.info(f"Saving to {output_path}")

        # Create parent directory if it doesn't exist
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Download the file
        urllib.request.urlretrieve(test_video_url, output_path)

        # Verify the file exists and has content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(
                f"Successfully downloaded test video ({os.path.getsize(output_path)} bytes)"
            )
            return True
        else:
            logger.error("Downloaded file is empty or doesn't exist")
            return False

    except Exception as e:
        logger.error(f"Failed to download test video: {e}")
        return False


def ensure_video_exists(video_path: str, auto_download: bool = True) -> str:
    """Ensure a video file exists, downloading a test video if needed.

    Args:
        video_path: Configured video path
        auto_download: Whether to automatically download a test video if file doesn't exist

    Returns:
        Path to the video file

    Raises:
        FileNotFoundError: If video doesn't exist and auto_download is False or download failed
    """
    logger = CustomLogger("video_validator")

    # If the configured path exists, use it
    if os.path.exists(video_path):
        logger.info(f"Using existing video file: {video_path}")
        return video_path

    # If auto-download is disabled, raise an error
    if not auto_download:
        raise FileNotFoundError(
            f"Video file '{video_path}' does not exist. Provide --video or update the config."
        )

    # Try to download a test video
    logger.warning(f"Video file '{video_path}' not found. Attempting to download test video...")

    # Determine download path
    if video_path == "./video_demo.mp4":
        # Default case: download to current directory or sage.apps.video location
        download_path = str(Path(__file__).parent / "video_demo.mp4")
    else:
        # Use the configured path
        download_path = video_path

    if download_test_video(download_path):
        logger.info(f"Test video ready at: {download_path}")
        return download_path
    else:
        raise FileNotFoundError(
            f"Video file '{video_path}' does not exist and automatic download failed. "
            f"Please provide a video file using --video or update the config."
        )


# ---------------------------------------------------------------------------
# Pipeline assembly
# ---------------------------------------------------------------------------


def build_pipeline(env: LocalEnvironment, config: dict[str, Any]) -> None:
    video_path = config["video_path"]
    sample_every = config["sample_every_n_frames"]
    max_frames = config.get("max_frames")
    frame_resize = config.get("frame_resize")

    analysis_cfg = config.get("analysis", {})
    window_cfg = config.get("window_summary", {})
    output_cfg = config.get("output", {})
    integrations_cfg = config.get("integrations", {})

    logger = get_logger("video_intelligence_pipeline")

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

    # Disable NeuroMem in test mode (requires pre-created collection)
    if os.environ.get("SAGE_EXAMPLES_MODE") == "test":
        if enable_neuromem:
            logger.info("Test mode: Disabling NeuroMem (requires collection setup)")
            enable_neuromem = False

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
            brightness_delta_threshold=analysis_cfg.get("brightness_delta_threshold", 35.0),
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


def apply_runtime_overrides(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
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


def download_test_video_to_temp() -> str | None:
    """Download a small test video for CI/testing purposes.

    Uses a public domain short video clip suitable for testing.
    Returns the path to the downloaded video file, or None if download fails.
    """
    import urllib.request
    from pathlib import Path

    # Use a small public domain video (approx 1-2MB)
    # Sample videos from Pexels (free to use)
    test_video_url = (
        "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
    )

    # Download to a temp location
    video_dir = Path("/tmp/sage_test_videos")
    video_dir.mkdir(exist_ok=True)
    video_path = video_dir / "test_video.mp4"

    if video_path.exists():
        print(f"[INFO] Test video already exists at {video_path}")
        return str(video_path)

    try:
        print(f"[INFO] Downloading test video from {test_video_url}")
        urllib.request.urlretrieve(test_video_url, str(video_path))
        print(f"[INFO] Test video downloaded to {video_path}")
        return str(video_path)
    except Exception as e:
        print(f"[WARNING] Failed to download test video: {e}")
        return None


def main() -> None:
    args = parse_args()
    config = load_config(args.config_path)
    config = apply_runtime_overrides(config, args)

    video_path = config.get("video_path")

    # If no video file provided, try to download a test video
    if not video_path or not os.path.exists(video_path):
        print("\n" + "=" * 80)
        print("📥 No video file provided - attempting to download test video...")
        print("=" * 80)
        test_video = download_test_video_to_temp()
        if test_video:
            video_path = test_video
            config["video_path"] = video_path
            print(f"✅ Test video downloaded: {test_video}")

            # In test mode, limit frames for faster testing
            if os.environ.get("SAGE_EXAMPLES_MODE") == "test" and "max_frames" not in config:
                config["max_frames"] = 30
                print("[INFO] Test mode: Limiting to 30 frames for faster testing")
        else:
            print("\n" + "=" * 80)
            print("❌ Error: Could not download test video")
            print("=" * 80)
            print("\nPlease provide a video file using one of these methods:")
            print("  1. Command line: --video path/to/video.mp4")
            print("  2. Config file: Set 'video_path' in the config YAML")
            print("\nExample:")
            print("  python examples/apps/run_video_intelligence.py --video my_video.mp4")
            print("=" * 80 + "\n")
            raise FileNotFoundError(
                "Could not download test video and no video file provided. "
                "Please provide --video or update the config."
            )
        print("=" * 80 + "\n")

    # Double check video file exists
    if not video_path or not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file '{video_path}' does not exist.")

    env = LocalEnvironment("video_intelligence_demo")
    build_pipeline(env, config)

    logger = get_logger("video_intelligence_demo")
    logger.info("Starting pipeline on video '%s'", video_path)

    print("\n" + "=" * 80)
    print("🎥 SAGE Video Intelligence Pipeline")
    print("=" * 80)
    print(f"📁 Video: {video_path}")
    print(f"📊 Config: {config.get('video_path', 'default')}")
    print("⚙️  Services: ", end="")
    services = []
    if config.get("integrations", {}).get("enable_sage_db"):
        services.append("SageDB")
    if config.get("integrations", {}).get("enable_sage_flow"):
        services.append("SageFlow")
    if (
        config.get("integrations", {}).get("enable_neuromem")
        and os.environ.get("SAGE_EXAMPLES_MODE") != "test"
    ):
        services.append("NeuroMem")
    print(", ".join(services) if services else "None")
    print("=" * 80 + "\n")

    # Submit and wait for pipeline to complete
    env.submit(autostop=True)

    print("\n" + "=" * 80)
    print("✅ Pipeline execution completed!")

    # Show output file locations
    output_cfg = config.get("output", {})
    if output_cfg:
        print("\n📂 Output files generated:")
        if output_cfg.get("timeline_path"):
            print(f"   • Timeline: {output_cfg['timeline_path']}")
        if output_cfg.get("summary_path"):
            print(f"   • Summary: {output_cfg['summary_path']}")
        if output_cfg.get("event_stats_path"):
            print(f"   • Events: {output_cfg['event_stats_path']}")
    print("=" * 80 + "\n")

    logger.info("Pipeline execution completed")


if __name__ == "__main__":  # pragma: no cover
    main()
