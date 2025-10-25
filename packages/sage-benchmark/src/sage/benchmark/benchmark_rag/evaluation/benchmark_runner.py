"""
Universal Benchmark Runner for RAG Pipelines

This module provides a generic framework for benchmarking any RAG pipeline implementation.
It handles:
- Batch processing of large datasets
- Running any pipeline from implementations/pipelines/
- Collecting and saving results
- Performance metrics tracking
"""

import importlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from sage.common.config.output_paths import get_output_file
from sage.common.core.functions.batch_function import BatchFunction
from sage.common.core.functions.map_function import MapFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment


def load_config(path: str) -> dict:
    """Load YAML configuration file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class BatchDataLoader(BatchFunction):
    """
    Batch data loader for benchmark datasets.

    Supports loading large datasets in batches for efficient processing.
    Compatible with Self-RAG dataset format and other QA datasets.
    """

    def __init__(self, config: dict):
        self.config = config
        self.data_path = config.get("data_path")
        self.max_samples = config.get("max_samples", None)

        # Load data
        data = self._load_data()
        if self.max_samples:
            data = data[: self.max_samples]

        self.batch_size = config.get("batch_size", len(data))
        self.current_batch = 0
        self.total_batches = (len(data) + self.batch_size - 1) // self.batch_size
        self._data = data

    def _load_data(self) -> List[Dict[str, Any]]:
        """Load dataset from JSONL file."""
        data = []
        with open(self.data_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))

        # Limit samples if max_samples is set
        if self.max_samples and self.max_samples > 0:
            print(
                f"📊 Limiting dataset to {self.max_samples} samples (total available: {len(data)})"
            )
            data = data[: self.max_samples]

        return data

    def execute(self) -> Optional[Dict[str, Any]]:
        """Return next batch of data."""
        if self.current_batch >= self.total_batches:
            return None

        start_idx = self.current_batch * self.batch_size
        end_idx = min(start_idx + self.batch_size, len(self._data))
        batch = self._data[start_idx:end_idx]

        result = {
            "batch_data": batch,
            "batch_id": self.current_batch,
            "total_batches": self.total_batches,
        }

        self.current_batch += 1
        return result


class PipelineRunner(MapFunction):
    """
    Generic pipeline runner that can execute any RAG pipeline.

    Dynamically loads and runs pipeline implementations from
    implementations/pipelines/ directory.

    Expected pipeline interface:
    - process_item(item: Dict, config: Dict) -> Dict
    """

    def __init__(self, config: dict):
        self.config = config
        self.pipeline_name = config.get("pipeline_name")
        self.pipeline_config = config.get("pipeline_config", {})

        # Dynamically import pipeline module
        self.pipeline_module = self._load_pipeline()

    def _load_pipeline(self):
        """Dynamically load pipeline implementation."""
        module_path = f"sage.benchmark.benchmark_rag.implementations.pipelines.{self.pipeline_name}"

        try:
            module = importlib.import_module(module_path)

            # Verify the module has process_item function
            if not hasattr(module, "process_item"):
                raise ImportError(
                    f"Pipeline module {module_path} must have a 'process_item' function "
                    f"with signature: process_item(item: Dict, config: Dict) -> Dict"
                )

            return module
        except ImportError as e:
            raise ImportError(
                f"Failed to load pipeline '{self.pipeline_name}': {e}\n"
                f"Make sure the pipeline exists in implementations/pipelines/ "
                f"and has a 'process_item' function"
            )

    def execute(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pipeline on a batch of data."""
        batch = batch_data["batch_data"]

        # Process each item in the batch
        results = []
        for i, item in enumerate(batch):
            try:
                # Run the pipeline on this item
                result = self.pipeline_module.process_item(item, self.pipeline_config)
                results.append(result)

                # Progress indicator
                if (i + 1) % 10 == 0:
                    print(f"  Processed {i + 1}/{len(batch)} items in batch...")

            except Exception as e:
                # Log error but continue processing
                print(f"⚠️  Error processing item {item.get('id', 'unknown')}: {e}")
                results.append(
                    {
                        "id": item.get("id", "unknown"),
                        "question": item.get("question", ""),
                        "error": str(e),
                        "ground_truth": item.get("answers", []),
                    }
                )

        return {
            "results": results,
            "batch_id": batch_data["batch_id"],
            "total_batches": batch_data["total_batches"],
        }


class ResultsCollector(MapFunction):
    """
    Collects and saves benchmark results.

    Handles incremental or final saving of results with metadata.
    """

    def __init__(self, config: dict):
        self.config = config
        default_output = get_output_file("benchmark_results.json", "benchmarks")
        self.output_path = config.get("output_path", str(default_output))
        self.save_mode = config.get("save_mode", "incremental")
        self.all_results = []
        self.start_time = time.time()

    def execute(self, batch_result: Dict[str, Any]) -> Dict[str, Any]:
        """Collect results from a batch."""
        results = batch_result["results"]
        batch_id = batch_result["batch_id"]
        total_batches = batch_result["total_batches"]

        self.all_results.extend(results)

        print(
            f"✅ Processed batch {batch_id + 1}/{total_batches}, "
            f"Total results: {len(self.all_results)}"
        )

        # Save based on mode
        if self.save_mode == "incremental":
            self._save_results(batch_id + 1, total_batches)
        elif self.save_mode == "final" and batch_id + 1 == total_batches:
            self._save_results(batch_id + 1, total_batches)

        return batch_result

    def _save_results(self, current_batch: int, total_batches: int):
        """Save results to file with metadata."""
        elapsed_time = time.time() - self.start_time

        output = {
            "metadata": {
                "pipeline_name": self.config.get("pipeline_name", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "total_samples": len(self.all_results),
                "completed_batches": f"{current_batch}/{total_batches}",
                "elapsed_time_seconds": round(elapsed_time, 2),
                "config": self.config,
            },
            "results": self.all_results,
        }

        # Ensure output directory exists
        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"💾 Results saved to: {self.output_path}")


def run_benchmark(config: dict) -> None:
    """
    Run benchmark with the specified configuration.

    Args:
        config: Configuration dictionary with:
            - data: Data loading configuration
            - pipeline: Pipeline configuration
            - output: Output configuration
    """
    print("=" * 60)
    print("🚀 Starting RAG Benchmark")
    print("=" * 60)

    pipeline_name = config.get("pipeline", {}).get("pipeline_name", "unknown")
    data_path = config.get("data", {}).get("data_path", "unknown")

    print(f"📊 Pipeline: {pipeline_name}")
    print(f"📁 Dataset: {data_path}")
    print(f"💾 Output: {config.get('output', {}).get('output_path', 'default')}")
    print("=" * 60)

    env = LocalEnvironment("benchmark_pipeline")

    # Build benchmark pipeline
    (
        env.from_source(BatchDataLoader, config["data"])
        .map(PipelineRunner, config["pipeline"])
        .sink(ResultsCollector, {**config["output"], **config["pipeline"]})
    )

    env.submit()
    env.close()

    print("=" * 60)
    print("✅ Benchmark completed!")
    print("=" * 60)


def main():
    """Main entry point for benchmark runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Run RAG pipeline benchmarks")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to benchmark configuration YAML file",
    )
    parser.add_argument(
        "--pipeline",
        type=str,
        default=None,
        help="Pipeline name (e.g., 'selfrag', 'qa_dense_retrieval_milvus')",
    )
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Path to dataset JSONL file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to output results file",
    )

    args = parser.parse_args()

    # Load configuration
    if args.config:
        config = load_config(args.config)
    else:
        # Use default config path
        current_dir = Path(__file__).parent
        default_config = current_dir / "config" / "benchmark_config.yaml"

        if default_config.exists():
            config = load_config(str(default_config))
        else:
            raise ValueError(
                "No configuration file specified and default config not found. "
                "Use --config to specify a configuration file."
            )

    # Override with command-line arguments
    if args.pipeline:
        config["pipeline"]["pipeline_name"] = args.pipeline
    if args.data:
        config["data"]["data_path"] = args.data
    if args.output:
        config["output"]["output_path"] = args.output

    # Setup
    CustomLogger.disable_global_console_debug()
    load_dotenv(override=False)

    # Run benchmark
    run_benchmark(config)


if __name__ == "__main__":
    main()
