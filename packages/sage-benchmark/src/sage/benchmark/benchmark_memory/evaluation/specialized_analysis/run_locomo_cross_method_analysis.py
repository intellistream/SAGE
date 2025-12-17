#!/usr/bin/env python3
"""
Cross-Method F1 Score Analysis for LoCoMo Benchmark
Compares F1 scores across different memory methods and generates visualizations.

Usage: python run_locomo_cross_method_analysis.py
"""

# ============================================================================
# CONFIGURATION - Modify these paths as needed
# ============================================================================
INPUT_BASE_DIR = ".sage/benchmarks/benchmark_memory/locomo/251217"
OUTPUT_DIR = ".sage/benchmarks/benchmark_memory/locomo/output/251217/cross_method"
# ============================================================================

import json
import string
import sys
from collections import Counter
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")

try:
    import regex
    from nltk.stem import PorterStemmer
except ImportError as e:
    print(f"Error: {e}\nInstall: pip install regex nltk && python -m nltk.downloader porter_test")
    sys.exit(1)

ps = PorterStemmer()

# Color palette for different methods
METHOD_COLORS = {
    "TiM": "#E74C3C",
    "A-Mem": "#3498DB",
    "LD-Agent": "#2ECC71",
    "Mem0": "#9B59B6",
    "MemGPT": "#F39C12",
    "MemoryBank": "#1ABC9C",
    "MemoryOS": "#E91E63",
    "SCM": "#00BCD4",
    "HippoRAG": "#FF5722",
    "stm": "#607D8B",
}


# ============================================================================
# F1 Score Calculation Functions
# ============================================================================


def normalize_answer(s):
    """Normalize answer text for comparison."""
    s = s.replace(",", "")
    exclude = set(string.punctuation)
    s = "".join(ch for ch in s if ch not in exclude)
    s = regex.sub(r"\b(a|an|the|and)\b", " ", s.lower())
    return " ".join(s.split())


def f1_score(prediction, ground_truth):
    """Calculate token-level F1 score."""
    pred_tokens = [ps.stem(w) for w in normalize_answer(prediction).split()]
    gt_tokens = [ps.stem(w) for w in normalize_answer(ground_truth).split()]
    common = Counter(pred_tokens) & Counter(gt_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0
    precision = 1.0 * num_same / len(pred_tokens)
    recall = 1.0 * num_same / len(gt_tokens)
    return (2 * precision * recall) / (precision + recall)


def f1_multi(prediction, ground_truth):
    """F1 for comma-separated multi-answers."""
    preds = [p.strip() for p in prediction.split(",")]
    gts = [g.strip() for g in ground_truth.split(",")]
    return np.mean([max([f1_score(p, gt) for p in preds]) for gt in gts])


def eval_question_answering(qas):
    """Evaluate QA with category-specific F1 calculation."""
    f1_scores = []
    category_scores = {1: [], 2: [], 3: [], 4: [], 5: []}

    for q in qas:
        answer = str(q["answer"])
        output = q["prediction"].strip()
        category = q["category"]

        # Category 5: 优先判断"信息未提及"
        if category == 5:
            is_not_mentioned = any(
                keyword in output.lower()
                for keyword in [
                    "not mentioned",
                    "no information",
                    "not in the conversation",
                    "cannot be determined",
                ]
            )
            score = 1 if is_not_mentioned else 0
            f1_scores.append(score)
            category_scores[5].append(score)
            continue

        # Category 3: 清理分号后的注释部分
        if category == 3:
            answer = answer.split(";")[0].strip()
            output = output.split(";")[0].strip()

        # Category 1: 多答案（逗号分隔）
        if category == 1:
            score = f1_multi(output, answer)
        else:
            score = f1_score(output, answer)

        f1_scores.append(score)
        if category in category_scores:
            category_scores[category].append(score)

    return f1_scores, category_scores


# ============================================================================
# Data Loading Functions
# ============================================================================


def load_all_methods(input_base_dir: str) -> dict[str, dict]:
    """Load results from all method directories."""
    base_path = Path(input_base_dir)
    if not base_path.exists():
        print(f"Error: '{input_base_dir}' not found!")
        sys.exit(1)

    methods_data = {}
    for method_dir in sorted(base_path.iterdir()):
        if method_dir.is_dir():
            json_files = list(method_dir.glob("*.json"))
            if json_files:
                # Use the first (or only) JSON file
                json_file = json_files[0]
                with open(json_file, encoding="utf-8") as fp:
                    methods_data[method_dir.name] = {
                        "file": json_file.name,
                        "data": json.load(fp),
                    }
                print(f"  ✓ {method_dir.name}: {json_file.name}")
            else:
                print(f"  ✗ {method_dir.name}: No JSON files found (skipped)")

    return methods_data


def analyze_method(method_name: str, data: dict) -> dict:
    """Analyze F1 scores for one method."""
    results = data.get("test_results", [])
    round_scores = []
    all_category_scores = {1: [], 2: [], 3: [], 4: [], 5: []}

    for test in results:
        qas = [
            {
                "answer": q.get("reference_answer", ""),
                "prediction": q.get("predicted_answer", ""),
                "category": q.get("category", 1),
            }
            for q in test.get("questions", [])
        ]
        if qas:
            f1s, cat_scores = eval_question_answering(qas)
            round_scores.append(
                {
                    "round": test.get("test_index", 0),
                    "f1_score": np.mean(f1s),
                    "num_questions": len(qas),
                }
            )
            for cat, scores in cat_scores.items():
                all_category_scores[cat].extend(scores)

    # Calculate category averages
    category_averages = {}
    for cat, scores in all_category_scores.items():
        if scores:
            category_averages[cat] = np.mean(scores)

    return {
        "method_name": method_name,
        "round_scores": round_scores,
        "average_f1": np.mean([r["f1_score"] for r in round_scores]) if round_scores else 0,
        "category_scores": category_averages,
        "total_questions": sum(r["num_questions"] for r in round_scores),
    }


# ============================================================================
# Visualization Functions
# ============================================================================


def plot_cross_method_comparison(analyses: list[dict], output_dir: Path):
    """Bar chart comparing average F1 across methods."""
    # Sort by average F1
    sorted_analyses = sorted(analyses, key=lambda x: x["average_f1"], reverse=True)
    methods = [a["method_name"] for a in sorted_analyses]
    f1s = [a["average_f1"] for a in sorted_analyses]
    colors = [METHOD_COLORS.get(m, "#95A5A6") for m in methods]

    plt.figure(figsize=(12, 7))
    bars = plt.bar(methods, f1s, color=colors, edgecolor="black", linewidth=1.2)

    # Add value labels on bars
    for bar, f1 in zip(bars, f1s):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{f1:.3f}",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )

    plt.xlabel("Memory Method", fontsize=13)
    plt.ylabel("Average F1 Score", fontsize=13)
    plt.title("Cross-Method F1 Comparison (LoCoMo conv-26)", fontsize=15, fontweight="bold")
    plt.xticks(rotation=45, ha="right")
    plt.ylim(0, max(f1s) * 1.15)
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "cross_method_f1_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ cross_method_f1_comparison.png")


def plot_round_progression(analyses: list[dict], output_dir: Path):
    """Line chart showing F1 progression across rounds for all methods."""
    plt.figure(figsize=(14, 8))

    for analysis in analyses:
        method = analysis["method_name"]
        rounds = [r["round"] for r in analysis["round_scores"]]
        f1s = [r["f1_score"] for r in analysis["round_scores"]]
        color = METHOD_COLORS.get(method, "#95A5A6")
        plt.plot(rounds, f1s, marker="o", linewidth=2, markersize=6, label=method, color=color)

    plt.xlabel("Round", fontsize=13)
    plt.ylabel("F1 Score", fontsize=13)
    plt.title("F1 Score Progression Across Rounds", fontsize=15, fontweight="bold")
    plt.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "round_progression_all_methods.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ round_progression_all_methods.png")


def plot_category_comparison(analyses: list[dict], output_dir: Path):
    """Grouped bar chart comparing F1 scores by category across methods."""
    categories = [1, 2, 3, 4, 5]
    category_names = {
        1: "Multi-Answer",
        2: "Single-Span",
        3: "Yes/No",
        4: "Unanswerable",
        5: "Not Mentioned",
    }

    # Prepare data
    methods = [a["method_name"] for a in analyses]
    x = np.arange(len(categories))
    width = 0.8 / len(methods)

    plt.figure(figsize=(14, 8))

    for i, analysis in enumerate(analyses):
        method = analysis["method_name"]
        scores = [analysis["category_scores"].get(cat, 0) for cat in categories]
        color = METHOD_COLORS.get(method, "#95A5A6")
        offset = (i - len(methods) / 2 + 0.5) * width
        plt.bar(
            x + offset, scores, width, label=method, color=color, edgecolor="black", linewidth=0.5
        )

    plt.xlabel("Question Category", fontsize=13)
    plt.ylabel("F1 Score", fontsize=13)
    plt.title("F1 Scores by Question Category", fontsize=15, fontweight="bold")
    plt.xticks(x, [category_names[c] for c in categories])
    plt.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "category_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ category_comparison.png")


def plot_radar_chart(analyses: list[dict], output_dir: Path):
    """Radar chart comparing methods across categories."""
    categories = [1, 2, 3, 4, 5]
    category_names = ["Multi-Ans", "Single", "Yes/No", "Unans", "NotMent"]
    num_vars = len(categories)

    # Compute angle for each axis
    angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
    angles += angles[:1]  # Complete the loop

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"projection": "polar"})

    for analysis in analyses:
        method = analysis["method_name"]
        values = [analysis["category_scores"].get(cat, 0) for cat in categories]
        values += values[:1]  # Complete the loop
        color = METHOD_COLORS.get(method, "#95A5A6")
        ax.plot(angles, values, "o-", linewidth=2, label=method, color=color)
        ax.fill(angles, values, alpha=0.1, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(category_names, fontsize=11)
    ax.set_ylim(0, 1)
    plt.title("Method Comparison by Category (Radar)", fontsize=14, fontweight="bold", pad=20)
    plt.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))
    plt.tight_layout()
    plt.savefig(output_dir / "radar_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ radar_comparison.png")


def plot_heatmap(analyses: list[dict], output_dir: Path):
    """Heatmap showing F1 scores per round per method."""
    # Find max rounds
    max_rounds = max(len(a["round_scores"]) for a in analyses)
    methods = [a["method_name"] for a in analyses]

    # Build matrix
    data = np.zeros((len(methods), max_rounds))
    for i, analysis in enumerate(analyses):
        for rs in analysis["round_scores"]:
            round_idx = rs["round"] - 1
            if 0 <= round_idx < max_rounds:
                data[i, round_idx] = rs["f1_score"]

    plt.figure(figsize=(14, 8))
    im = plt.imshow(data, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)
    plt.colorbar(im, label="F1 Score")

    plt.yticks(range(len(methods)), methods, fontsize=11)
    plt.xticks(range(max_rounds), [f"R{i + 1}" for i in range(max_rounds)], fontsize=10)
    plt.xlabel("Round", fontsize=13)
    plt.ylabel("Method", fontsize=13)
    plt.title("F1 Heatmap: Methods × Rounds", fontsize=15, fontweight="bold")

    # Add text annotations
    for i in range(len(methods)):
        for j in range(max_rounds):
            if data[i, j] > 0:
                text_color = "white" if data[i, j] < 0.5 else "black"
                plt.text(
                    j,
                    i,
                    f"{data[i, j]:.2f}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=text_color,
                )

    plt.tight_layout()
    plt.savefig(output_dir / "f1_heatmap.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ f1_heatmap.png")


# ============================================================================
# Report Generation
# ============================================================================


def save_report(analyses: list[dict], output_dir: Path):
    """Save comprehensive JSON report."""
    # Sort by average F1 for ranking
    sorted_analyses = sorted(analyses, key=lambda x: x["average_f1"], reverse=True)

    report = {
        "summary": {
            "total_methods": len(analyses),
            "ranking": [
                {
                    "rank": i + 1,
                    "method": a["method_name"],
                    "average_f1": round(a["average_f1"], 4),
                    "total_questions": a["total_questions"],
                }
                for i, a in enumerate(sorted_analyses)
            ],
            "best_method": sorted_analyses[0]["method_name"] if sorted_analyses else None,
            "best_f1": round(sorted_analyses[0]["average_f1"], 4) if sorted_analyses else 0,
        },
        "category_analysis": {
            "category_names": {
                "1": "Multi-Answer",
                "2": "Single-Span",
                "3": "Yes/No",
                "4": "Unanswerable",
                "5": "Not Mentioned",
            },
            "scores_by_method": {
                a["method_name"]: {
                    str(cat): round(score, 4) for cat, score in a["category_scores"].items()
                }
                for a in analyses
            },
        },
        "round_details": {
            a["method_name"]: [
                {"round": r["round"], "f1_score": round(r["f1_score"], 4)}
                for r in a["round_scores"]
            ]
            for a in analyses
        },
    }

    with open(output_dir / "cross_method_report.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("  ✓ cross_method_report.json")


def print_summary_table(analyses: list[dict]):
    """Print a nice summary table to console."""
    sorted_analyses = sorted(analyses, key=lambda x: x["average_f1"], reverse=True)

    print("\n" + "=" * 70)
    print("RANKING SUMMARY")
    print("=" * 70)
    print(f"{'Rank':<6}{'Method':<15}{'Avg F1':<10}{'Questions':<12}{'Best Cat':<12}")
    print("-" * 70)

    for i, a in enumerate(sorted_analyses):
        # Find best category
        if a["category_scores"]:
            best_cat = max(a["category_scores"].items(), key=lambda x: x[1])
            best_cat_str = f"Cat{best_cat[0]}({best_cat[1]:.2f})"
        else:
            best_cat_str = "N/A"

        print(
            f"{i + 1:<6}{a['method_name']:<15}{a['average_f1']:<10.4f}"
            f"{a['total_questions']:<12}{best_cat_str:<12}"
        )

    print("=" * 70)


# ============================================================================
# Main
# ============================================================================


def main():
    """Main pipeline."""
    print("=" * 80)
    print("Cross-Method F1 Score Analysis for LoCoMo Benchmark")
    print("=" * 80)
    print(f"Input:  {INPUT_BASE_DIR}")
    print(f"Output: {OUTPUT_DIR}\n")

    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load all methods
    print("Loading method results:")
    methods_data = load_all_methods(INPUT_BASE_DIR)

    if not methods_data:
        print("No valid method results found!")
        return

    # Analyze each method
    print(f"\n{'=' * 80}\nAnalyzing Methods\n{'=' * 80}\n")
    analyses = []
    for method_name, info in methods_data.items():
        print(f"Analyzing {method_name}...")
        analysis = analyze_method(method_name, info["data"])
        analyses.append(analysis)
        print(f"  → Avg F1: {analysis['average_f1']:.4f}, Questions: {analysis['total_questions']}")

    # Generate visualizations
    print(f"\n{'=' * 80}\nGenerating Visualizations\n{'=' * 80}\n")
    plot_cross_method_comparison(analyses, output_path)
    plot_round_progression(analyses, output_path)
    plot_category_comparison(analyses, output_path)
    plot_radar_chart(analyses, output_path)
    plot_heatmap(analyses, output_path)

    # Save report
    print(f"\n{'=' * 80}\nSaving Report\n{'=' * 80}\n")
    save_report(analyses, output_path)

    # Print summary
    print_summary_table(analyses)

    print(f"\n{'=' * 80}")
    print("✓ Analysis Complete!")
    print(f"{'=' * 80}")
    print(f"\nResults saved to: {OUTPUT_DIR}")
    print(f"  • {len(analyses)} methods analyzed")
    print("  • 5 visualization charts")
    print("  • 1 comprehensive JSON report\n")


if __name__ == "__main__":
    main()
