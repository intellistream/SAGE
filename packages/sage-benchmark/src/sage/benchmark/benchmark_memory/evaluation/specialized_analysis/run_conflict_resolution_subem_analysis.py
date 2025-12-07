#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Substring Exact Match (SubEM) Analysis for Conflict Resolution Dataset
Analyzes SubEM scores from JSON test results and generates visualizations.

Based on MemoryAgentBench evaluation metrics for Conflict_Resolution dataset.
Primary metric: SubEM (Substring Exact Match)
"""

# Configuration
INPUT_DIR = ".sage/benchmarks/benchmark_memory/conflict_resolution/251205/stm"
OUTPUT_DIR = ".sage/benchmarks/benchmark_memory/conflict_resolution/251205/stm/output"

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
    from rouge_score import rouge_scorer
except ImportError as e:
    print(f"Error: {e}")
    print("Install: pip install regex nltk rouge-score && python -m nltk.downloader porter_test")
    sys.exit(1)

ps = PorterStemmer()
rouge_scorer_instance = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)


def normalize_answer(s):
    """Normalize answer text (from MemoryAgentBench)."""
    s = str(s)
    s = s.replace(",", "")
    exclude = set(string.punctuation)
    s = "".join(ch for ch in s if ch not in exclude)
    s = regex.sub(r"\b(a|an|the|and)\b", " ", s.lower())
    return " ".join(s.split())


def substring_exact_match_score(prediction, ground_truth):
    """SubEM: Check if GT is substring of prediction after normalization."""
    return int(normalize_answer(ground_truth) in normalize_answer(prediction))


def exact_match_score(prediction, ground_truth):
    """EM: Check exact match after normalization."""
    return int(normalize_answer(prediction) == normalize_answer(ground_truth))


def f1_score(prediction, ground_truth):
    """Calculate token-level F1 score."""
    pred_tokens = [ps.stem(w) for w in normalize_answer(prediction).split()]
    gt_tokens = [ps.stem(w) for w in normalize_answer(ground_truth).split()]

    if len(pred_tokens) == 0 or len(gt_tokens) == 0:
        return 0.0

    common = Counter(pred_tokens) & Counter(gt_tokens)
    num_same = sum(common.values())

    if num_same == 0:
        return 0.0

    precision = 1.0 * num_same / len(pred_tokens)
    recall = 1.0 * num_same / len(gt_tokens)
    return (2 * precision * recall) / (precision + recall)


def calculate_metrics(prediction, ground_truth):
    """Calculate comprehensive metrics."""
    if isinstance(ground_truth, list):
        ground_truths = ground_truth
    else:
        ground_truths = [ground_truth]

    metrics = {
        "substring_exact_match": max(
            substring_exact_match_score(prediction, gt) for gt in ground_truths
        ),
        "exact_match": max(exact_match_score(prediction, gt) for gt in ground_truths),
        "f1": max(f1_score(prediction, gt) for gt in ground_truths),
    }

    rouge_scores = [
        rouge_scorer_instance.score(target=str(gt), prediction=str(prediction))
        for gt in ground_truths
    ]
    for rouge_type in ["rouge1", "rouge2", "rougeL"]:
        metrics[f"{rouge_type}_f1"] = max(score[rouge_type].fmeasure for score in rouge_scores)

    return metrics


def evaluate_questions(questions):
    """Evaluate all questions."""
    all_metrics = {
        "substring_exact_match": [],
        "exact_match": [],
        "f1": [],
        "rouge1_f1": [],
        "rouge2_f1": [],
        "rougeL_f1": [],
    }

    for q in questions:
        prediction = str(q.get("prediction", ""))
        answer = q.get("answer")

        if answer is None:
            continue

        metrics = calculate_metrics(prediction, answer)
        for key in all_metrics:
            all_metrics[key].append(metrics[key])

    print(f"    {len(questions)} questions evaluated")
    return all_metrics


def load_json_files(input_dir):
    """Load all JSON files."""
    json_files = {}
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Error: '{input_dir}' not found!")
        sys.exit(1)
    for f in sorted(input_path.glob("*.json")):
        with open(f, encoding="utf-8") as fp:
            json_files[f.stem] = json.load(fp)
    print(f"Loaded {len(json_files)} JSON files")
    return json_files


def analyze_task(task_name, data):
    """Analyze metrics for one task."""
    results = data.get("test_results", [])
    round_scores = []

    for test in results:
        questions = [
            {
                "answer": q.get("reference_answer", ""),
                "prediction": q.get("predicted_answer", ""),
            }
            for q in test.get("questions", [])
        ]

        if questions:
            metrics = evaluate_questions(questions)
            round_data = {
                "round": test.get("test_index", 0),
                "subem": np.mean(metrics["substring_exact_match"]),
                "em": np.mean(metrics["exact_match"]),
                "f1": np.mean(metrics["f1"]),
                "rouge1": np.mean(metrics["rouge1_f1"]),
                "rouge2": np.mean(metrics["rouge2_f1"]),
                "rougeL": np.mean(metrics["rougeL_f1"]),
            }
            round_scores.append(round_data)

    return {
        "task_name": task_name,
        "round_scores": round_scores,
        "average_subem": np.mean([r["subem"] for r in round_scores]) if round_scores else 0,
        "average_em": np.mean([r["em"] for r in round_scores]) if round_scores else 0,
        "average_f1": np.mean([r["f1"] for r in round_scores]) if round_scores else 0,
        "average_rouge1": np.mean([r["rouge1"] for r in round_scores]) if round_scores else 0,
        "average_rouge2": np.mean([r["rouge2"] for r in round_scores]) if round_scores else 0,
        "average_rougeL": np.mean([r["rougeL"] for r in round_scores]) if round_scores else 0,
    }


def plot_task_subem(analysis, output_dir):
    """Plot SubEM score (main metric)."""
    name = analysis["task_name"]
    rounds = [r["round"] for r in analysis["round_scores"]]
    subem = [r["subem"] for r in analysis["round_scores"]]
    avg = analysis["average_subem"]

    plt.figure(figsize=(10, 6))
    plt.plot(
        rounds,
        subem,
        marker="o",
        linewidth=2,
        markersize=8,
        label="SubEM per Round",
        color="#2E86AB",
    )
    plt.axhline(y=avg, color="r", linestyle="--", linewidth=2, label=f"Avg: {avg:.4f}")
    plt.xlabel("Round", fontsize=12)
    plt.ylabel("SubEM Score", fontsize=12)
    plt.title(f"{name} - Substring Exact Match (SubEM)", fontsize=14, fontweight="bold")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / f"{name}_subem.png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {name}_subem.png (Avg SubEM: {avg:.4f})")


def plot_task_metrics(analysis, output_dir):
    """Plot all metrics for one task."""
    name = analysis["task_name"]
    rounds = [r["round"] for r in analysis["round_scores"]]

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(f"{name} - Metrics Over Rounds", fontsize=16, fontweight="bold")

    metrics_to_plot = [
        ("subem", "SubEM (Substring Exact Match)", "average_subem"),
        ("em", "Exact Match", "average_em"),
        ("f1", "F1 Score", "average_f1"),
        ("rouge1", "ROUGE-1 F1", "average_rouge1"),
        ("rouge2", "ROUGE-2 F1", "average_rouge2"),
        ("rougeL", "ROUGE-L F1", "average_rougeL"),
    ]

    for idx, (metric_key, metric_label, avg_key) in enumerate(metrics_to_plot):
        ax = axes[idx // 3, idx % 3]
        scores = [r[metric_key] for r in analysis["round_scores"]]
        avg = analysis[avg_key]

        ax.plot(rounds, scores, marker="o", linewidth=2, markersize=8, label=f"{metric_label}")
        ax.axhline(y=avg, color="r", linestyle="--", linewidth=2, label=f"Avg: {avg:.4f}")
        ax.set_xlabel("Round", fontsize=10)
        ax.set_ylabel("Score", fontsize=10)
        ax.set_title(metric_label, fontsize=12, fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / f"{name}_metrics.png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {name}_metrics.png")


def plot_summary(analyses, output_dir):
    """Plot summary across all tasks."""
    max_rounds = max(len(a["round_scores"]) for a in analyses)

    metrics_keys = ["subem", "em", "f1", "rouge1", "rouge2", "rougeL"]
    round_avgs = {key: [] for key in metrics_keys}

    for r in range(1, max_rounds + 1):
        for key in metrics_keys:
            scores = []
            for a in analyses:
                for rs in a["round_scores"]:
                    if rs["round"] == r:
                        scores.append(rs[key])
                        break
            if scores:
                round_avgs[key].append({"round": r, "score": np.mean(scores)})

    rounds = [r["round"] for r in round_avgs["subem"]]
    subem_scores = [r["score"] for r in round_avgs["subem"]]
    overall_subem = np.mean(subem_scores) if subem_scores else 0

    plt.figure(figsize=(12, 7))
    plt.plot(
        rounds,
        subem_scores,
        marker="s",
        linewidth=2.5,
        markersize=10,
        color="#2E86AB",
        label="Avg SubEM (All Tasks)",
    )
    plt.axhline(
        y=overall_subem,
        color="r",
        linestyle="--",
        linewidth=2,
        label=f"Overall: {overall_subem:.4f}",
    )
    plt.xlabel("Round", fontsize=13)
    plt.ylabel("SubEM Score", fontsize=13)
    plt.title("Summary: All Tasks Average SubEM", fontsize=15, fontweight="bold")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "summary_subem.png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  ✓ summary_subem.png (Overall SubEM: {overall_subem:.4f})")

    return round_avgs, overall_subem


def save_report(analyses, round_avgs, overall_subem, output_dir):
    """Save JSON report."""
    overall_metrics = {
        "subem": overall_subem,
        "em": np.mean([r["score"] for r in round_avgs["em"]]) if round_avgs["em"] else 0,
        "f1": np.mean([r["score"] for r in round_avgs["f1"]]) if round_avgs["f1"] else 0,
        "rouge1": (
            np.mean([r["score"] for r in round_avgs["rouge1"]]) if round_avgs["rouge1"] else 0
        ),
        "rouge2": (
            np.mean([r["score"] for r in round_avgs["rouge2"]]) if round_avgs["rouge2"] else 0
        ),
        "rougeL": (
            np.mean([r["score"] for r in round_avgs["rougeL"]]) if round_avgs["rougeL"] else 0
        ),
    }

    report = {
        "summary": {
            "dataset": "Conflict_Resolution",
            "primary_metric": "SubEM (Substring Exact Match)",
            "total_tasks": len(analyses),
            "overall_metrics": {k: round(v, 4) for k, v in overall_metrics.items()},
        },
        "tasks": [
            {
                "task_name": a["task_name"],
                "task_averages": {
                    "subem": round(a["average_subem"], 4),
                    "exact_match": round(a["average_em"], 4),
                    "f1": round(a["average_f1"], 4),
                },
            }
            for a in analyses
        ],
    }

    with open(output_dir / "subem_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("  ✓ subem_report.json")


def main():
    """Main pipeline."""
    print("=" * 80)
    print("Conflict Resolution - SubEM Analysis")
    print("=" * 80)
    print(f"Input:  {INPUT_DIR}\nOutput: {OUTPUT_DIR}\n")

    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    files = load_json_files(INPUT_DIR)
    if not files:
        print("No JSON files found.")
        return

    print(f"\n{'=' * 80}\nAnalyzing Tasks\n{'=' * 80}\n")
    analyses = []
    for name, data in files.items():
        print(f"{name}:")
        analysis = analyze_task(name, data)
        analyses.append(analysis)
        plot_task_subem(analysis, output_path)
        plot_task_metrics(analysis, output_path)

    print(f"\n{'=' * 80}\nSummary\n{'=' * 80}\n")
    round_avgs, overall_subem = plot_summary(analyses, output_path)
    save_report(analyses, round_avgs, overall_subem, output_path)

    print(f"\n{'=' * 80}\n✓ Complete!\n{'=' * 80}")


if __name__ == "__main__":
    main()
