"""
Generate training data from DyFlow benchmark results.

This script extracts design histories from benchmark evaluation results and converts them
to either KTO (Kahneman-Tversky Optimization) or SFT (Supervised Fine-Tuning) format.

KTO format: Includes both correct (label=True) and incorrect (label=False) samples
SFT format: Only includes correct samples (label=True)

Usage:
    # Generate KTO data from training set
    python train/generate_training_data.py --baseline DyFlow --model phi-4 --output train/kto_data.json --format kto --mode train

    # Generate SFT data from training set
    python train/generate_training_data.py --baseline DyFlow --model phi-4 --output train/sft_data.json --format sft --mode train

Input: Benchmark result files from benchmarks/results/{benchmark}/{mode}/{baseline}_{model}.json
Output: Training data in JSON format compatible with LLaMA-Factory (https://github.com/hiyouga/LLaMA-Factory)

Data Format:
    KTO: [{"messages": [...], "label": true/false, "source": "MATH"}, ...]
    SFT: [{"messages": [...], "source": "MATH"}, ...]
"""

import argparse
import json
import os
import sys

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Task configurations mapping task names to result folders and source labels
def get_task_configs(mode: str) -> dict:
    """Get task configurations with the specified mode (train/test)"""
    return {
        "math_reasoning": {"result_folder": f"benchmarks/results/MATH/{mode}", "source": "MATH"},
        "social_reasoning": {
            "result_folder": f"benchmarks/results/socialmaze/{mode}",
            "source": "SocialMaze",
        },
        "medical_reasoning": {
            "result_folder": f"benchmarks/results/PubMedQA/{mode}",
            "source": "PubMedQA",
        },
        "causal_reasoning": {
            "result_folder": f"benchmarks/results/livebench/{mode}",
            "source": "LiveBench",
        },
        "code_reasoning": {
            "result_folder": f"benchmarks/results/humaneval/{mode}",
            "source": "HumanEval",
        },
    }


def load_benchmark_results(baseline: str, execution_model: str, mode: str) -> dict[str, dict]:
    """Load benchmark results from all 5 tasks"""
    all_results = {}
    task_configs = get_task_configs(mode)

    for task_name, config in task_configs.items():
        result_file = f"{config['result_folder']}/{baseline}_{execution_model}.json"

        if not os.path.exists(result_file):
            print(f"Warning: {result_file} not found, skipping {task_name}")
            continue

        with open(result_file, encoding="utf-8") as f:
            results = json.load(f)

        all_results[task_name] = {"results": results, "source": config["source"]}
        print(f"Loaded {len(results)} results from {task_name}")

    return all_results


def convert_to_kto_format(all_results: dict[str, dict]) -> list[dict]:
    """Convert benchmark results to KTO format (with labels)"""
    kto_samples = []

    for task_name, task_data in all_results.items():
        results = task_data["results"]
        source = task_data["source"]

        for problem_idx, problem in enumerate(results):
            # Check if design_histories exist
            if "design_histories" not in problem or not problem["design_histories"]:
                continue

            # Get judge_results - handle both list format and single result format
            if "judge_results" in problem:
                judge_results = problem["judge_results"]
                if not isinstance(judge_results, list):
                    judge_results = [judge_results]
            elif "results" in problem:
                # For HumanEval format
                judge_results = [r["result"] == "passed" for r in problem["results"]]
            else:
                continue

            design_histories = problem.get("design_histories", [])

            # Process each sample (may have multiple samples_per_task)
            for idx, (design_history, judge_result) in enumerate(
                zip(design_histories, judge_results)
            ):
                if design_history is None:
                    continue

                # design_history is a list, each element is a stage design
                # Format: [{"input": "...", "output": "..."}, ...]
                for stage_design in design_history:
                    kto_sample = {
                        "messages": [
                            {"role": "user", "content": stage_design["input"]},
                            {"role": "assistant", "content": stage_design["output"]},
                        ],
                        "label": bool(judge_result),
                        "source": source,
                    }
                    kto_samples.append(kto_sample)

        print(
            f"Extracted {len([s for s in kto_samples if s['source'] == source])} KTO samples from {task_name}"
        )

    return kto_samples


def convert_to_sft_format(kto_samples: list[dict]) -> list[dict]:
    """Convert KTO data to SFT format (only label=True samples, no labels)"""
    sft_samples = []

    for sample in kto_samples:
        # Only include correct samples
        if sample["label"]:
            sft_sample = {"messages": sample["messages"], "source": sample["source"]}
            sft_samples.append(sft_sample)

    return sft_samples


def validate_data(samples: list[dict], format_type: str):
    """Validate data format and print statistics"""
    print(f"\n{'=' * 60}")
    print(f"{format_type.upper()} Data Validation")
    print(f"{'=' * 60}")
    print(f"Total samples: {len(samples)}")

    # Statistics by label (KTO only)
    if format_type == "kto":
        true_count = sum(1 for s in samples if s["label"])
        false_count = sum(1 for s in samples if not s["label"])
        print("\nLabel distribution:")
        print(f"  True (correct): {true_count} ({true_count / len(samples) * 100:.1f}%)")
        print(f"  False (wrong):  {false_count} ({false_count / len(samples) * 100:.1f}%)")

    # Statistics by source
    sources = {}
    for sample in samples:
        source = sample["source"]
        if format_type == "kto":
            label = sample["label"]
            if source not in sources:
                sources[source] = {"true": 0, "false": 0}
            sources[source]["true" if label else "false"] += 1
        else:
            sources[source] = sources.get(source, 0) + 1

    print("\nBreakdown by source:")
    if format_type == "kto":
        for source, counts in sorted(sources.items()):
            total = counts["true"] + counts["false"]
            print(
                f"  {source:20s}: {total:5d} samples (True={counts['true']}, False={counts['false']})"
            )
    else:
        for source, count in sorted(sources.items()):
            print(f"  {source:20s}: {count:5d} samples")

    # Print sample examples
    print(f"\n{'=' * 60}")
    print(f"Sample {format_type.upper()} data (first 2)")
    print(f"{'=' * 60}")
    for i, sample in enumerate(samples[:2]):
        print(f"\n--- Sample {i + 1} ---")
        print(f"Source: {sample['source']}")
        if format_type == "kto":
            print(f"Label: {sample['label']}")
        print("User prompt (first 200 chars):")
        print(f"  {sample['messages'][0]['content'][:200]}...")
        print("Assistant response (first 200 chars):")
        print(f"  {sample['messages'][1]['content'][:200]}...")


def main(baseline: str, execution_model: str, output_file: str, format_type: str, mode: str):
    """Main function to generate training data"""
    print(f"\n{'=' * 60}")
    print(f"Generating {format_type.upper()} Training Data")
    print(f"{'=' * 60}")
    print(f"Baseline: {baseline}")
    print(f"Execution Model: {execution_model}")
    print(f"Mode: {mode}")
    print(f"Format: {format_type}")
    print(f"Output: {output_file}\n")

    # Load benchmark results
    all_results = load_benchmark_results(baseline, execution_model, mode)

    if not all_results:
        print("Error: No results loaded!")
        return

    # Convert to KTO format first
    kto_samples = convert_to_kto_format(all_results)

    if not kto_samples:
        print("Error: No KTO samples generated!")
        return

    # Convert to desired format
    if format_type == "sft":
        samples = convert_to_sft_format(kto_samples)
        print(f"\nConverted {len(kto_samples)} KTO samples to {len(samples)} SFT samples")
    else:
        samples = kto_samples

    # Validate data
    validate_data(samples, format_type)

    # Save to file
    os.makedirs(
        os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True
    )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"{format_type.upper()} data saved to {output_file}")
    print(f"Total samples: {len(samples)}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate training data from DyFlow benchmark results"
    )
    parser.add_argument(
        "--baseline", type=str, default="DyFlow", help="Baseline name (default: DyFlow)"
    )
    parser.add_argument(
        "--model", type=str, default="phi-4", help="Execution model name (default: phi-4)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="train/training_data.json",
        help="Output file path (default: train/training_data.json)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["kto", "sft"],
        default="kto",
        help="Output format: kto (with labels) or sft (only correct samples) (default: kto)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["train", "test"],
        default="train",
        help="Data mode: train (for training) or test (for evaluation) (default: train)",
    )

    args = parser.parse_args()

    main(args.baseline, args.model, args.output, args.format, args.mode)
