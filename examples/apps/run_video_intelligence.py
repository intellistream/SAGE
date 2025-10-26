#!/usr/bin/env python3
"""
Video Intelligence Pipeline Example

This script demonstrates how to use the Video Intelligence application from sage-apps.
It performs multi-model video analysis using CLIP and MobileNetV3.

Requirements:
    pip install -e packages/sage-apps[video]

Usage:
    python examples/apps/run_video_intelligence.py --video path/to/video.mp4
    python examples/apps/run_video_intelligence.py --video path/to/video.mp4 --config custom_config.yaml

Test Configuration:
    @test_category: apps
    @test_speed: slow
    @test_requires: [video]
    @test_skip_ci: true
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

try:
    from sage.apps.video.video_intelligence_pipeline import main as video_main
except ImportError as e:
    print(f"Error importing sage.apps.video: {e}")
    print("\nPlease install sage-apps with video dependencies:")
    print("  pip install -e packages/sage-apps[video]")
    sys.exit(1)


def main():
    """Run the video intelligence pipeline."""
    parser = argparse.ArgumentParser(
        description="SAGE Video Intelligence Pipeline - Multi-model video analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a video file
  python %(prog)s --video path/to/video.mp4

  # Use custom configuration
  python %(prog)s --video path/to/video.mp4 --config config_video_intelligence.yaml

  # Process multiple frames
  python %(prog)s --video path/to/video.mp4 --max-frames 100

Features:
  - Scene understanding with CLIP model
  - Action recognition with MobileNetV3
  - Frame-by-frame analysis
  - Comprehensive video insights
  - Configurable processing pipeline
        """,
    )

    parser.add_argument("--video", type=str, help="Path to the video file to analyze")

    parser.add_argument("--config", type=str, default=None, help="Path to configuration file")

    parser.add_argument("--max-frames", type=int, help="Maximum number of frames to process")

    parser.add_argument("--output", type=str, help="Output directory for results")

    args = parser.parse_args()

    # If no video is provided, show help and exit successfully (for testing purposes)
    if not args.video:
        print("=" * 60)
        print("SAGE Video Intelligence Pipeline")
        print("=" * 60)
        print("No video file provided. This example requires a video file to process.")
        print("\nUsage:")
        print("  python examples/apps/run_video_intelligence.py --video path/to/video.mp4")
        print("\nFor more information, use --help")
        print("=" * 60)
        sys.exit(0)

    # Validate video file if provided
    if args.video and not Path(args.video).exists():
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)

    # Validate config file if provided
    if args.config and not Path(args.config).exists():
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    print("=" * 60)
    print("SAGE Video Intelligence Pipeline")
    print("=" * 60)
    if args.video:
        print(f"Video: {args.video}")
    if args.config:
        print(f"Config: {args.config}")
    else:
        print("Config: Using default configuration")
    if args.max_frames:
        print(f"Max Frames: {args.max_frames}")
    if args.output:
        print(f"Output: {args.output}")
    print("=" * 60)
    print()

    # Call the video intelligence main function
    # The actual implementation will handle the arguments
    try:
        video_main()
    except Exception as e:
        print(f"Error running video intelligence pipeline: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
