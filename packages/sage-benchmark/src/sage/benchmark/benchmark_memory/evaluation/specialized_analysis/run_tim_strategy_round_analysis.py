#!/usr/bin/env python3
"""
TiM Query Strategy Round-by-Round Analysis
分析TiM不同查询策略在每个轮次的表现（包括各类别的详细统计）

Usage: python run_tim_strategy_round_analysis.py
"""

import json
import string
from collections import Counter
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import regex
from nltk.stem import PorterStemmer

matplotlib.use("Agg")

ps = PorterStemmer()

# ============================================================================
# CONFIGURATION
# ============================================================================
INPUT_BASE_DIR = ".sage/benchmarks/benchmark_memory/locomo/251219"
OUTPUT_DIR = ".sage/benchmarks/benchmark_memory/locomo/output/251219/tim_strategy_round_analysis"

# 策略名称映射和颜色
STRATEGY_NAMES = {
    "TiM-embedding": "Baseline",
    "TiM-validate": "Validate",
    "TiM-keyword_extract": "Keyword",
    "TiM-expand": "Expand",
    "TiM-rewrite": "Rewrite",
    "TiM-decompose": "Decompose",
}

STRATEGY_COLORS = {
    "Baseline": "#E74C3C",
    "Validate": "#3498DB",
    "Keyword": "#2ECC71",
    "Expand": "#F39C12",
    "Rewrite": "#9B59B6",
    "Decompose": "#1ABC9C",
}

CATEGORY_NAMES = {
    1: "Multi-Answer",
    2: "Single-Span",
    3: "Yes/No",
    4: "Unanswerable",
    5: "Not Mentioned",
}

CATEGORY_COLORS = {
    1: "#E74C3C",
    2: "#3498DB",
    3: "#F39C12",
    4: "#2ECC71",
    5: "#9B59B6",
}


# ============================================================================
# F1 Score Calculation Functions
# ============================================================================


def normalize_answer(s):
    """Normalize answer text for comparison."""
    s = str(s)  # 确保是字符串
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
        return 0.0
    precision = 1.0 * num_same / len(pred_tokens)
    recall = 1.0 * num_same / len(gt_tokens)
    return (2 * precision * recall) / (precision + recall)


def f1_multi(prediction, ground_truth):
    """F1 for comma-separated multi-answers."""
    prediction = str(prediction)
    ground_truth = str(ground_truth)
    preds = [p.strip() for p in prediction.split(",")]
    gts = [g.strip() for g in ground_truth.split(",")]
    return np.mean([max([f1_score(p, gt) for p in preds]) for gt in gts])


def calculate_f1(prediction, ground_truth, category):
    """Calculate F1 based on category."""
    if category == 1:  # Multi-answer
        return f1_multi(prediction, ground_truth)
    else:
        return f1_score(prediction, ground_truth)


# ============================================================================
# Data Loading and Analysis
# ============================================================================


def load_strategy_data(base_dir: str) -> dict:
    """Load all strategy results."""
    base_path = Path(base_dir)
    strategy_data = {}

    for strategy_dir, display_name in STRATEGY_NAMES.items():
        dir_path = base_path / strategy_dir
        if not dir_path.exists():
            print(f"  ✗ {display_name}: Directory not found")
            continue

        json_files = list(dir_path.glob("*.json"))
        if not json_files:
            print(f"  ✗ {display_name}: No JSON files found")
            continue

        json_file = json_files[0]
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        strategy_data[display_name] = {
            "raw_data": data,
            "file": json_file.name,
        }
        print(f"  ✓ {display_name}: {json_file.name}")

    return strategy_data


def analyze_strategy_by_round(strategy_name: str, data: dict) -> dict:
    """分析单个策略的逐轮表现（包括类别细分）"""
    test_results = data.get("test_results", [])

    round_analyses = []

    for test in test_results:
        round_idx = test.get("test_index", 0)
        questions = test.get("questions", [])

        # 整体F1
        all_f1_scores = []
        # 按类别统计
        category_f1 = {cat: [] for cat in CATEGORY_NAMES.keys()}

        for q in questions:
            pred = q.get("predicted_answer", "")
            ref = q.get("reference_answer", "")
            cat = q.get("category", 1)

            f1 = calculate_f1(pred, ref, cat)
            all_f1_scores.append(f1)
            if cat in category_f1:
                category_f1[cat].append(f1)

        # 计算各类别平均分
        category_avg = {}
        for cat, scores in category_f1.items():
            if scores:
                category_avg[cat] = np.mean(scores)

        round_analyses.append(
            {
                "round": round_idx,
                "f1_overall": np.mean(all_f1_scores) if all_f1_scores else 0,
                "num_questions": len(questions),
                "category_f1": category_avg,
            }
        )

    return {
        "strategy_name": strategy_name,
        "round_analyses": round_analyses,
        "average_f1": np.mean([r["f1_overall"] for r in round_analyses]) if round_analyses else 0,
    }


# ============================================================================
# Visualization Functions
# ============================================================================


def plot_round_comparison(analyses: dict, output_dir: Path):
    """折线图：各策略在各轮次的F1对比"""
    plt.figure(figsize=(14, 8))

    for strategy_name, analysis in analyses.items():
        rounds = [r["round"] for r in analysis["round_analyses"]]
        f1_scores = [r["f1_overall"] for r in analysis["round_analyses"]]
        color = STRATEGY_COLORS.get(strategy_name, "#95A5A6")

        plt.plot(
            rounds,
            f1_scores,
            marker="o",
            linewidth=2.5,
            markersize=8,
            label=strategy_name,
            color=color,
        )

    plt.xlabel("Round", fontsize=14, fontweight="bold")
    plt.ylabel("F1 Score", fontsize=14, fontweight="bold")
    plt.title("TiM Query Strategies: F1 Score by Round", fontsize=16, fontweight="bold")
    plt.legend(loc="best", fontsize=12)
    plt.grid(True, alpha=0.3, linestyle="--")
    plt.ylim(0, 1.0)
    plt.tight_layout()
    plt.savefig(output_dir / "round_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ round_comparison.png")


def plot_round_heatmap(analyses: dict, output_dir: Path):
    """热力图：策略×轮次的F1得分"""
    strategies = list(analyses.keys())
    max_rounds = max(len(a["round_analyses"]) for a in analyses.values())

    data = np.zeros((len(strategies), max_rounds))

    for i, (strategy_name, analysis) in enumerate(analyses.items()):
        for r in analysis["round_analyses"]:
            round_idx = r["round"] - 1
            if 0 <= round_idx < max_rounds:
                data[i, round_idx] = r["f1_overall"]

    plt.figure(figsize=(14, 8))
    im = plt.imshow(data, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)
    plt.colorbar(im, label="F1 Score")

    plt.yticks(range(len(strategies)), strategies, fontsize=12)
    plt.xticks(range(max_rounds), [f"R{i + 1}" for i in range(max_rounds)], fontsize=11)
    plt.xlabel("Round", fontsize=14, fontweight="bold")
    plt.ylabel("Strategy", fontsize=14, fontweight="bold")
    plt.title("TiM Strategies: F1 Heatmap (Strategy × Round)", fontsize=16, fontweight="bold")

    # 添加数值标注
    for i in range(len(strategies)):
        for j in range(max_rounds):
            if data[i, j] > 0:
                text_color = "white" if data[i, j] < 0.5 else "black"
                plt.text(
                    j,
                    i,
                    f"{data[i, j]:.2f}",
                    ha="center",
                    va="center",
                    fontsize=10,
                    color=text_color,
                    fontweight="bold",
                )

    plt.tight_layout()
    plt.savefig(output_dir / "round_heatmap.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ round_heatmap.png")


def plot_category_round_comparison(analyses: dict, output_dir: Path):
    """为每个类别生成轮次对比折线图"""
    for cat_id, cat_name in CATEGORY_NAMES.items():
        plt.figure(figsize=(14, 8))

        for strategy_name, analysis in analyses.items():
            rounds = []
            scores = []

            for r in analysis["round_analyses"]:
                if cat_id in r["category_f1"]:
                    rounds.append(r["round"])
                    scores.append(r["category_f1"][cat_id])

            if rounds:
                color = STRATEGY_COLORS.get(strategy_name, "#95A5A6")
                plt.plot(
                    rounds,
                    scores,
                    marker="o",
                    linewidth=2.5,
                    markersize=8,
                    label=strategy_name,
                    color=color,
                )

        plt.xlabel("Round", fontsize=14, fontweight="bold")
        plt.ylabel("F1 Score", fontsize=14, fontweight="bold")
        plt.title(
            f"Category {cat_id}: {cat_name} - F1 Score by Round", fontsize=16, fontweight="bold"
        )
        plt.legend(loc="best", fontsize=12)
        plt.grid(True, alpha=0.3, linestyle="--")
        plt.ylim(0, 1.0)
        plt.tight_layout()

        filename = (
            f"category_{cat_id}_{cat_name.lower().replace(' ', '_').replace('/', '_')}_rounds.png"
        )
        plt.savefig(output_dir / filename, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"  ✓ {filename}")


def plot_category_heatmaps(analyses: dict, output_dir: Path):
    """为每个类别生成策略×轮次热力图"""
    for cat_id, cat_name in CATEGORY_NAMES.items():
        strategies = list(analyses.keys())
        max_rounds = max(len(a["round_analyses"]) for a in analyses.values())

        data = np.zeros((len(strategies), max_rounds))

        for i, (strategy_name, analysis) in enumerate(analyses.items()):
            for r in analysis["round_analyses"]:
                round_idx = r["round"] - 1
                if 0 <= round_idx < max_rounds and cat_id in r["category_f1"]:
                    data[i, round_idx] = r["category_f1"][cat_id]

        plt.figure(figsize=(14, 8))
        im = plt.imshow(data, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)
        plt.colorbar(im, label="F1 Score")

        plt.yticks(range(len(strategies)), strategies, fontsize=12)
        plt.xticks(range(max_rounds), [f"R{i + 1}" for i in range(max_rounds)], fontsize=11)
        plt.xlabel("Round", fontsize=14, fontweight="bold")
        plt.ylabel("Strategy", fontsize=14, fontweight="bold")
        plt.title(
            f"Category {cat_id}: {cat_name} - Strategy × Round Heatmap",
            fontsize=16,
            fontweight="bold",
        )

        # 添加数值标注
        for i in range(len(strategies)):
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
                        fontweight="bold",
                    )

        plt.tight_layout()
        filename = (
            f"category_{cat_id}_{cat_name.lower().replace(' ', '_').replace('/', '_')}_heatmap.png"
        )
        plt.savefig(output_dir / filename, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"  ✓ {filename}")


def plot_strategy_category_comparison(analyses: dict, output_dir: Path):
    """每个策略的类别对比（折线图，展示各类别在轮次中的表现）"""
    for strategy_name, analysis in analyses.items():
        plt.figure(figsize=(14, 8))

        for cat_id, cat_name in CATEGORY_NAMES.items():
            rounds = []
            scores = []

            for r in analysis["round_analyses"]:
                if cat_id in r["category_f1"]:
                    rounds.append(r["round"])
                    scores.append(r["category_f1"][cat_id])

            if rounds:
                color = CATEGORY_COLORS[cat_id]
                plt.plot(
                    rounds,
                    scores,
                    marker="o",
                    linewidth=2.5,
                    markersize=8,
                    label=f"Cat{cat_id}: {cat_name}",
                    color=color,
                )

        plt.xlabel("Round", fontsize=14, fontweight="bold")
        plt.ylabel("F1 Score", fontsize=14, fontweight="bold")
        plt.title(
            f"{strategy_name}: Category Performance Across Rounds", fontsize=16, fontweight="bold"
        )
        plt.legend(loc="best", fontsize=11)
        plt.grid(True, alpha=0.3, linestyle="--")
        plt.ylim(0, 1.0)
        plt.tight_layout()

        filename = f"{strategy_name.lower()}_categories_by_round.png"
        plt.savefig(output_dir / filename, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"  ✓ {filename}")


def plot_average_comparison(analyses: dict, output_dir: Path):
    """柱状图：各策略的平均F1对比"""
    sorted_analyses = sorted(analyses.items(), key=lambda x: x[1]["average_f1"], reverse=True)
    strategies = [name for name, _ in sorted_analyses]
    avg_f1s = [data["average_f1"] for _, data in sorted_analyses]
    colors = [STRATEGY_COLORS.get(s, "#95A5A6") for s in strategies]

    plt.figure(figsize=(12, 7))
    bars = plt.bar(strategies, avg_f1s, color=colors, edgecolor="black", linewidth=1.5)

    # 添加数值标注
    for bar, f1 in zip(bars, avg_f1s):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{f1:.4f}",
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
        )

    plt.xlabel("Strategy", fontsize=14, fontweight="bold")
    plt.ylabel("Average F1 Score", fontsize=14, fontweight="bold")
    plt.title("TiM Query Strategies: Average F1 Comparison", fontsize=16, fontweight="bold")
    plt.ylim(0, max(avg_f1s) * 1.15)
    plt.grid(axis="y", alpha=0.3, linestyle="--")
    plt.tight_layout()
    plt.savefig(output_dir / "average_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ average_comparison.png")


# ============================================================================
# Report Generation
# ============================================================================


def save_json_report(analyses: dict, output_dir: Path):
    """保存详细的JSON报告"""
    report = {
        "summary": {
            "total_strategies": len(analyses),
            "ranking": [
                {
                    "rank": i + 1,
                    "strategy": name,
                    "average_f1": round(data["average_f1"], 4),
                }
                for i, (name, data) in enumerate(
                    sorted(analyses.items(), key=lambda x: x[1]["average_f1"], reverse=True)
                )
            ],
        },
        "round_details": {
            strategy_name: [
                {
                    "round": r["round"],
                    "f1_overall": round(r["f1_overall"], 4),
                    "num_questions": r["num_questions"],
                    "category_f1": {
                        str(cat): round(score, 4) for cat, score in r["category_f1"].items()
                    },
                }
                for r in data["round_analyses"]
            ]
            for strategy_name, data in analyses.items()
        },
        "category_names": {str(k): v for k, v in CATEGORY_NAMES.items()},
    }

    with open(output_dir / "tim_strategy_round_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("  ✓ tim_strategy_round_report.json")


def print_summary_table(analyses: dict):
    """打印汇总表格"""
    sorted_analyses = sorted(analyses.items(), key=lambda x: x[1]["average_f1"], reverse=True)

    print("\n" + "=" * 80)
    print("TiM QUERY STRATEGIES - PERFORMANCE RANKING")
    print("=" * 80)
    print(f"{'Rank':<6}{'Strategy':<15}{'Avg F1':<12}{'Best Round':<15}{'Worst Round':<15}")
    print("-" * 80)

    for i, (strategy_name, data) in enumerate(sorted_analyses):
        rounds = data["round_analyses"]
        best_round = max(rounds, key=lambda x: x["f1_overall"])
        worst_round = min(rounds, key=lambda x: x["f1_overall"])

        print(
            f"{i + 1:<6}{strategy_name:<15}{data['average_f1']:<12.4f}"
            f"R{best_round['round']}({best_round['f1_overall']:.3f}){'':<4}"
            f"R{worst_round['round']}({worst_round['f1_overall']:.3f})"
        )

    print("=" * 80)


# ============================================================================
# Main
# ============================================================================


def main():
    """主程序"""
    print("=" * 80)
    print("TiM Query Strategy Round-by-Round Analysis")
    print("=" * 80)
    print(f"Input:  {INPUT_BASE_DIR}")
    print(f"Output: {OUTPUT_DIR}\n")

    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    # 加载数据
    print("Loading strategy results:")
    strategy_data = load_strategy_data(INPUT_BASE_DIR)

    if not strategy_data:
        print("\n❌ No valid strategy results found!")
        return

    # 分析各策略
    print(f"\n{'=' * 80}\nAnalyzing Strategies\n{'=' * 80}\n")
    analyses = {}
    for strategy_name, data in strategy_data.items():
        print(f"Analyzing {strategy_name}...")
        analysis = analyze_strategy_by_round(strategy_name, data["raw_data"])
        analyses[strategy_name] = analysis
        print(f"  → Avg F1: {analysis['average_f1']:.4f}")

    # 生成可视化
    print(f"\n{'=' * 80}\nGenerating Visualizations\n{'=' * 80}\n")
    print("Overall comparison:")
    plot_average_comparison(analyses, output_path)
    plot_round_comparison(analyses, output_path)
    plot_round_heatmap(analyses, output_path)

    print("\nCategory-wise round comparison:")
    plot_category_round_comparison(analyses, output_path)

    print("\nCategory-wise heatmaps:")
    plot_category_heatmaps(analyses, output_path)

    print("\nStrategy-specific category analysis:")
    plot_strategy_category_comparison(analyses, output_path)

    # 保存报告
    print(f"\n{'=' * 80}\nSaving Report\n{'=' * 80}\n")
    save_json_report(analyses, output_path)

    # 打印汇总
    print_summary_table(analyses)

    print(f"\n{'=' * 80}")
    print("✅ Analysis Complete!")
    print(f"{'=' * 80}")
    print(f"\nResults saved to: {OUTPUT_DIR}")
    print(f"  • {len(analyses)} strategies analyzed")
    print(f"  • {3 + 5 + 5 + len(analyses)} visualization charts")
    print("    - 3 overall comparison charts")
    print("    - 5 category round comparison charts")
    print("    - 5 category heatmaps")
    print(f"    - {len(analyses)} strategy-specific category charts")
    print("  • 1 comprehensive JSON report\n")


if __name__ == "__main__":
    main()
