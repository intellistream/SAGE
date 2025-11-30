#!/usr/bin/env python3
"""
Agent Tool ID Validation Script

Validates tool_id consistency across agent_tools, agent_benchmark, and agent_sft data sources.
Ensures all referenced tools exist in the tool catalog.

Usage:
    python tools/scripts/validate_agent_tool_ids.py
    python tools/scripts/validate_agent_tool_ids.py --verbose
    python tools/scripts/validate_agent_tool_ids.py --fix-missing
"""

import argparse
import json
import sys
from pathlib import Path


class AgentToolIDValidator:
    """Validator for cross-source tool ID consistency."""

    def __init__(self, sage_root: Path, verbose: bool = False):
        """
        Initialize validator.

        Args:
            sage_root: Root directory of SAGE repository
            verbose: Enable verbose output
        """
        self.sage_root = sage_root
        self.verbose = verbose
        self.data_root = sage_root / "packages/sage-benchmark/src/sage/data/sources"

        # Statistics
        self.stats = {
            "tools_total": 0,
            "benchmark_references": 0,
            "sft_references": 0,
            "missing_in_benchmark": [],
            "missing_in_sft": [],
            "orphaned_tools": [],
        }

    def log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"  {message}")

    def load_tool_catalog(self) -> set[str]:
        """
        Load all tool IDs from agent_tools catalog.

        Returns:
            Set of tool_id strings
        """
        catalog_path = self.data_root / "agent_tools/data/tool_catalog.jsonl"

        if not catalog_path.exists():
            print(f"❌ Tool catalog not found: {catalog_path}")
            return set()

        tool_ids = set()
        with open(catalog_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    tool = json.loads(line)
                    tool_ids.add(tool["tool_id"])

        self.stats["tools_total"] = len(tool_ids)
        self.log(f"Loaded {len(tool_ids)} tools from catalog")
        return tool_ids

    def extract_benchmark_tool_ids(self) -> set[str]:
        """
        Extract all tool IDs referenced in agent_benchmark.

        Returns:
            Set of tool_id strings
        """
        benchmark_path = self.data_root / "agent_benchmark/splits"

        if not benchmark_path.exists():
            print(f"⚠️  Benchmark data not found: {benchmark_path}")
            return set()

        tool_ids = set()

        # Process all split files
        for split_file in benchmark_path.glob("*.jsonl"):
            self.log(f"Processing {split_file.name}")
            with open(split_file, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        sample = json.loads(line)

                        # Extract from candidate_tools
                        if "candidate_tools" in sample:
                            tool_ids.update(sample["candidate_tools"])

                        # Extract from tool_sequence (for task_planning)
                        if "tool_sequence" in sample:
                            tool_ids.update(sample.get("tool_sequence", []))

                        # Extract from ground_truth
                        if "ground_truth" in sample:
                            gt = sample["ground_truth"]
                            if "top_k" in gt:
                                tool_ids.update(gt["top_k"])
                            if "tools" in gt:
                                tool_ids.update(gt["tools"])

        self.stats["benchmark_references"] = len(tool_ids)
        self.log(f"Found {len(tool_ids)} unique tools in benchmark")
        return tool_ids

    def extract_sft_tool_ids(self) -> set[str]:
        """
        Extract all tool IDs referenced in agent_sft.

        Returns:
            Set of tool_id strings
        """
        sft_path = self.data_root / "agent_sft/data/sft_conversations.jsonl"

        if not sft_path.exists():
            print(f"⚠️  SFT data not found: {sft_path}")
            return set()

        tool_ids = set()

        self.log("Processing SFT conversations")
        with open(sft_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    dialog = json.loads(line)

                    # Extract from target_tools
                    if "target_tools" in dialog:
                        tool_ids.update(dialog["target_tools"])

                    # Extract from turns
                    for turn in dialog.get("turns", []):
                        if turn.get("role") == "tool" and "tool_id" in turn:
                            tool_ids.add(turn["tool_id"])

        self.stats["sft_references"] = len(tool_ids)
        self.log(f"Found {len(tool_ids)} unique tools in SFT data")
        return tool_ids

    def validate(self) -> bool:
        """
        Run validation across all data sources.

        Returns:
            True if validation passes, False otherwise
        """
        print("🔍 Validating agent tool IDs across data sources...")
        print("=" * 70)

        # Load tool catalog
        catalog_tools = self.load_tool_catalog()
        if not catalog_tools:
            print("❌ Failed to load tool catalog")
            return False

        print(f"✓ Loaded {len(catalog_tools)} tools from catalog")

        # Extract referenced tools
        benchmark_tools = self.extract_benchmark_tool_ids()
        sft_tools = self.extract_sft_tool_ids()

        print(f"✓ Found {len(benchmark_tools)} tools in benchmark")
        print(f"✓ Found {len(sft_tools)} tools in SFT data")
        print()

        # Check for missing tools
        missing_in_benchmark = benchmark_tools - catalog_tools
        missing_in_sft = sft_tools - catalog_tools

        self.stats["missing_in_benchmark"] = list(missing_in_benchmark)
        self.stats["missing_in_sft"] = list(missing_in_sft)

        # Check for orphaned tools (in catalog but never referenced)
        all_referenced = benchmark_tools | sft_tools
        orphaned = catalog_tools - all_referenced
        self.stats["orphaned_tools"] = list(orphaned)

        # Report results
        print("📊 Validation Results")
        print("=" * 70)

        success = True

        if missing_in_benchmark:
            print(f"❌ Benchmark references {len(missing_in_benchmark)} missing tools:")
            for tool_id in sorted(missing_in_benchmark)[:10]:
                print(f"   - {tool_id}")
            if len(missing_in_benchmark) > 10:
                print(f"   ... and {len(missing_in_benchmark) - 10} more")
            success = False
        else:
            print("✅ All benchmark tool references are valid")

        if missing_in_sft:
            print(f"❌ SFT data references {len(missing_in_sft)} missing tools:")
            for tool_id in sorted(missing_in_sft)[:10]:
                print(f"   - {tool_id}")
            if len(missing_in_sft) > 10:
                print(f"   ... and {len(missing_in_sft) - 10} more")
            success = False
        else:
            print("✅ All SFT tool references are valid")

        if orphaned:
            print(f"⚠️  {len(orphaned)} tools in catalog are never referenced:")
            for tool_id in sorted(orphaned)[:5]:
                print(f"   - {tool_id}")
            if len(orphaned) > 5:
                print(f"   ... and {len(orphaned) - 5} more")

        # Coverage stats
        coverage_pct = (len(all_referenced) / len(catalog_tools) * 100) if catalog_tools else 0
        print()
        print(f"📈 Tool Coverage: {len(all_referenced)}/{len(catalog_tools)} ({coverage_pct:.1f}%)")

        print("=" * 70)

        if success:
            print("✅ Validation PASSED: All tool IDs are consistent")
        else:
            print("❌ Validation FAILED: Found missing tool references")

        return success

    def generate_report(self, output_path: Path):
        """
        Generate a detailed validation report.

        Args:
            output_path: Path to save the report (JSON)
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)

        print(f"📄 Detailed report saved to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate tool_id consistency across agent data sources"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--report", "-r", type=str, help="Path to save validation report (JSON)")
    parser.add_argument(
        "--sage-root",
        type=Path,
        default=Path.cwd(),
        help="Root directory of SAGE repository (default: current directory)",
    )

    args = parser.parse_args()

    # Find SAGE root if not specified
    sage_root = args.sage_root
    if not (sage_root / "packages").exists():
        # Try parent directories
        for parent in [sage_root.parent, sage_root.parent.parent]:
            if (parent / "packages").exists():
                sage_root = parent
                break

    # Validate
    validator = AgentToolIDValidator(sage_root, verbose=args.verbose)
    success = validator.validate()

    # Generate report if requested
    if args.report:
        validator.generate_report(Path(args.report))

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
