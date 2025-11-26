#!/usr/bin/env python3
"""
Prepare Tool Selection Data Script

This script prepares and validates data for the Tool Selection benchmark (Challenge 3).
It can:
1. Validate existing data (1000+ tools, 500+ samples)
2. Generate additional synthetic data if needed
3. Create splits with different candidate pool sizes (100/500/1000)

Default output: .sage/benchmark/data/tool_selection/

Usage:
    python prepare_tool_selection_data.py --validate
    python prepare_tool_selection_data.py --generate --samples 500
    python prepare_tool_selection_data.py --create-splits --num-candidates 100,500,1000
"""

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_AGENT_DIR = SCRIPT_DIR.parent.parent
# Fix: BENCHMARK_ROOT is sage-benchmark package root (contains src/)
BENCHMARK_ROOT = BENCHMARK_AGENT_DIR.parent.parent.parent.parent  # sage-benchmark
SAGE_ROOT = BENCHMARK_ROOT.parent.parent  # SAGE repo root

# Default output in .sage/
DEFAULT_OUTPUT_DIR = SAGE_ROOT / ".sage" / "benchmark" / "data" / "tool_selection"

# Ensure sage packages are importable
sys.path.insert(0, str(BENCHMARK_ROOT / "src"))


def get_data_paths():
    """Get paths to data directories."""
    source_root = BENCHMARK_ROOT / "src" / "sage" / "data" / "sources"
    return {
        "tools_dir": source_root / "agent_tools" / "data",
        "benchmark_dir": source_root / "agent_benchmark" / "splits",
        "output_dir": DEFAULT_OUTPUT_DIR,
    }


def load_tools_catalog(tools_dir: Path) -> list[dict]:
    """Load all tools from the catalog."""
    catalog_file = tools_dir / "tool_catalog.jsonl"
    tools = []
    with open(catalog_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                tools.append(json.loads(line))
    return tools


def load_benchmark_samples(benchmark_dir: Path, task_type: str = "tool_selection") -> list[dict]:
    """Load existing benchmark samples."""
    file_path = benchmark_dir / f"{task_type}.jsonl"
    samples = []
    if file_path.exists():
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    samples.append(json.loads(line))
    return samples


def validate_data(tools: list[dict], samples: list[dict]) -> dict:
    """Validate data quality and completeness."""
    print("\n" + "=" * 60)
    print("DATA VALIDATION REPORT")
    print("=" * 60)

    results = {"valid": True, "issues": [], "stats": {}}

    # Tool statistics
    print(f"\n📦 Tools Catalog: {len(tools)} tools")
    results["stats"]["total_tools"] = len(tools)

    if len(tools) < 1000:
        results["issues"].append(f"Tool count ({len(tools)}) below target (1000)")
        results["valid"] = False

    # Category distribution
    categories = Counter(t.get("category", "unknown") for t in tools)
    print(f"   Categories: {len(categories)} unique")
    for cat, count in categories.most_common(5):
        print(f"     - {cat}: {count}")

    # Sample statistics
    print(f"\n📊 Benchmark Samples: {len(samples)} samples")
    results["stats"]["total_samples"] = len(samples)

    if len(samples) < 500:
        results["issues"].append(f"Sample count ({len(samples)}) below target (500)")
        results["valid"] = False

    # Split distribution
    splits = Counter(s.get("split", "unknown") for s in samples)
    print(f"   Splits: {dict(splits)}")

    # Difficulty distribution
    difficulties = Counter(s.get("metadata", {}).get("difficulty", "unknown") for s in samples)
    print(f"   Difficulty: {dict(difficulties)}")

    # Candidate tools analysis
    candidate_counts = [len(s.get("candidate_tools", [])) for s in samples]
    if candidate_counts:
        print(
            f"   Candidate tools: min={min(candidate_counts)}, max={max(candidate_counts)}, "
            f"avg={sum(candidate_counts) / len(candidate_counts):.1f}"
        )

    # Validate tool references in samples
    tool_ids = {t["tool_id"] for t in tools}
    missing_tools = set()
    for sample in samples:
        for tool_id in sample.get("candidate_tools", []):
            if tool_id not in tool_ids:
                missing_tools.add(tool_id)
        for tool_id in sample.get("ground_truth", {}).get("top_k", []):
            if tool_id not in tool_ids:
                missing_tools.add(tool_id)

    if missing_tools:
        print(f"\n⚠️  Warning: {len(missing_tools)} tool references not found in catalog")
        results["issues"].append(f"{len(missing_tools)} missing tool references")

    # Summary
    print("\n" + "-" * 60)
    if results["valid"] and not results["issues"]:
        print("✅ Data validation PASSED")
    else:
        print("❌ Data validation FAILED")
        for issue in results["issues"]:
            print(f"   - {issue}")

    return results


def generate_synthetic_sample(
    sample_id: int,
    tools: list[dict],
    num_candidates: int = 8,
    split: str = "train",
) -> dict:
    """Generate a synthetic tool selection sample."""
    # Select a random tool as the ground truth
    ground_truth_tool = random.choice(tools)

    # Generate instruction based on tool capabilities
    capabilities = ground_truth_tool.get("capabilities", ["general task"])
    capability = random.choice(capabilities) if capabilities else "task"

    templates = [
        f"Help me with {capability}",
        f"I need to {capability.lower()}",
        f"Can you {capability.lower()} for me?",
        f"Perform {capability} operation",
        f"Execute a {capability.lower()} task",
    ]
    instruction = random.choice(templates)

    # Select distractor tools
    other_tools = [t for t in tools if t["tool_id"] != ground_truth_tool["tool_id"]]
    distractors = random.sample(other_tools, min(num_candidates - 1, len(other_tools)))

    candidate_tools = [ground_truth_tool["tool_id"]] + [t["tool_id"] for t in distractors]
    random.shuffle(candidate_tools)

    # Determine difficulty based on capability overlap
    similar_caps = sum(
        1
        for t in distractors
        if any(
            c.lower() in [cap.lower() for cap in t.get("capabilities", [])] for c in capabilities
        )
    )
    if similar_caps >= 3:
        difficulty = "hard"
    elif similar_caps >= 1:
        difficulty = "medium"
    else:
        difficulty = "easy"

    return {
        "sample_id": f"ts_{sample_id:06d}",
        "task_type": "tool_selection",
        "instruction": instruction,
        "context": f"User has access to {num_candidates} tools.",
        "candidate_tools": candidate_tools,
        "ground_truth": {
            "top_k": [ground_truth_tool["tool_id"]],
            "explanation": f"Selected tool for {capability}",
        },
        "metadata": {
            "difficulty": difficulty,
            "tags": ["tool_selection", difficulty],
            "created_by": "synthetic_generator_v1",
        },
        "split": split,
    }


def generate_samples(
    tools: list[dict],
    num_samples: int = 500,
    start_id: int = 1,
    num_candidates: int = 8,
) -> list[dict]:
    """Generate synthetic samples."""
    samples = []

    # Split ratios: 70% train, 15% dev, 15% test
    splits = (
        ["train"] * int(num_samples * 0.7)
        + ["dev"] * int(num_samples * 0.15)
        + ["test"] * int(num_samples * 0.15)
    )
    random.shuffle(splits)

    for i, split in enumerate(splits[:num_samples]):
        sample = generate_synthetic_sample(
            sample_id=start_id + i,
            tools=tools,
            num_candidates=num_candidates,
            split=split,
        )
        samples.append(sample)

    return samples


def create_varied_candidate_splits(
    samples: list[dict],
    tools: list[dict],
    candidate_sizes: list[int],
    output_dir: Path,
) -> None:
    """Create sample splits with different candidate pool sizes."""
    tool_ids = [t["tool_id"] for t in tools]

    for num_candidates in candidate_sizes:
        print(f"\n📝 Creating split with {num_candidates} candidates...")

        output_samples = []
        for sample in samples:
            new_sample = sample.copy()
            new_sample["candidate_tools"] = list(new_sample["candidate_tools"])

            ground_truth_tools = new_sample["ground_truth"]["top_k"]

            # Ensure ground truth tools are in candidates
            current_candidates = set(new_sample["candidate_tools"])
            for gt in ground_truth_tools:
                if gt not in current_candidates:
                    current_candidates.add(gt)

            # Add more candidates from tool catalog
            while len(current_candidates) < num_candidates:
                new_tool = random.choice(tool_ids)
                current_candidates.add(new_tool)

            # Trim if too many
            current_candidates = list(current_candidates)
            if len(current_candidates) > num_candidates:
                # Keep ground truth, randomly select others
                others = [c for c in current_candidates if c not in ground_truth_tools]
                random.shuffle(others)
                current_candidates = (
                    ground_truth_tools + others[: num_candidates - len(ground_truth_tools)]
                )

            random.shuffle(current_candidates)
            new_sample["candidate_tools"] = current_candidates
            new_sample["context"] = f"User has access to {len(current_candidates)} tools."

            output_samples.append(new_sample)

        # Save to file
        output_file = output_dir / f"tool_selection_{num_candidates}.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            for sample in output_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        print(f"   Saved {len(output_samples)} samples to {output_file.name}")


def main():
    parser = argparse.ArgumentParser(description="Prepare Tool Selection Data")
    parser.add_argument("--validate", action="store_true", help="Validate existing data")
    parser.add_argument("--generate", action="store_true", help="Generate synthetic samples")
    parser.add_argument("--samples", type=int, default=500, help="Number of samples to generate")
    parser.add_argument(
        "--create-splits", action="store_true", help="Create splits with varied candidates"
    )
    parser.add_argument(
        "--num-candidates", type=str, default="100,500,1000", help="Comma-separated candidate sizes"
    )
    args = parser.parse_args()

    paths = get_data_paths()

    # Load existing data
    print("Loading data...")
    tools = load_tools_catalog(paths["tools_dir"])
    samples = load_benchmark_samples(paths["benchmark_dir"])

    if args.validate or not (args.generate or args.create_splits):
        validate_data(tools, samples)

    if args.generate:
        print(f"\n🔧 Generating {args.samples} synthetic samples...")
        start_id = len(samples) + 1
        new_samples = generate_samples(tools, args.samples, start_id)

        # Ensure output directory exists
        paths["output_dir"].mkdir(parents=True, exist_ok=True)

        # Append to existing file
        output_file = paths["output_dir"] / "tool_selection.jsonl"
        with open(output_file, "a", encoding="utf-8") as f:
            for sample in new_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        print(f"   Added {len(new_samples)} samples")

        # Re-validate
        all_samples = samples + new_samples
        validate_data(tools, all_samples)

    if args.create_splits:
        candidate_sizes = [int(x.strip()) for x in args.num_candidates.split(",")]
        create_varied_candidate_splits(samples, tools, candidate_sizes, paths["output_dir"])

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
