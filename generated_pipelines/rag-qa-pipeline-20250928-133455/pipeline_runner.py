"""Auto-generated SAGE pipeline.

This script was created by `sage pipeline build` and provides a
dense-retrieval RAG reference pipeline. Tune the configuration or extend
the operators to match your deployment requirements before putting it in
production.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Tuple

from sage.common.utils.config.loader import load_config
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.sink import TerminalSink
from sage.libs.io_utils.source import FileSource
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import ChromaRetriever


def build_pipeline(config: dict) -> Tuple[LocalEnvironment, object]:
    """Create the streaming pipeline for the provided configuration."""

    env = LocalEnvironment(config["pipeline"]["name"])

    query_stream = (
        env.from_source(FileSource, config["source"])
        .map(ChromaRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"])
        .sink(TerminalSink, config["sink"])
    )

    return env, query_stream


def run_pipeline(config_path: Path, *, streaming: bool = False) -> None:
    """Load configuration and execute the pipeline once or in streaming mode."""

    config = load_config(str(config_path))
    env, _ = build_pipeline(config)

    try:
        env.submit()
        if streaming:
            env.run_streaming()
        else:
            env.run_once()
    finally:
        env.stop()
        env.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the generated SAGE pipeline")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("pipeline_config.yaml"),
        help="Path to the pipeline configuration file.",
    )
    parser.add_argument(
        "--streaming",
        action="store_true",
        help="Run the pipeline with env.run_streaming() instead of a single pass.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output for debugging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    logging.getLogger(__name__).info("Starting pipeline with config: %s", args.config)
    run_pipeline(args.config, streaming=args.streaming)


if __name__ == "__main__":
    main()
