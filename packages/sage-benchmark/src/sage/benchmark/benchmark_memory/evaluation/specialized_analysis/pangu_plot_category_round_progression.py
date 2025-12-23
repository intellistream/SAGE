#!/usr/bin/env python3
"""
分类轮次进展图生成器 - 为每个类别绘制轮次-记忆体方法对比

用途：展示每个类别下，各个记忆体方法在不同轮次的F1得分变化

使用方法: python plot_category_round_progression.py
"""

import json
import string
import sys
from collections import Counter
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import regex

matplotlib.use("Agg")

try:
    from nltk.stem import PorterStemmer
except ImportError as e:
    print(f"Error: {e}\nInstall: pip install regex nltk && python -m nltk.downloader porter_test")
    sys.exit(1)

ps = PorterStemmer()

# ============================================================================
# 配置区域
# ============================================================================
INPUT_BASE_DIR = ".sage/benchmarks/benchmark_memory/locomo/pangu"
OUTPUT_DIR = ".sage/benchmarks/benchmark_memory/locomo/output/pangu/category_round_charts"
OUTPUT_PREFIX = "category_round_progression"

# 方法颜色配置（13个方法）
METHOD_COLORS = {
    "TiM": "#E74C3C",  # 红色
    "A-Mem": "#3498DB",  # 蓝色
    "LD-Agent": "#2ECC71",  # 绿色
    "Mem0": "#9B59B6",  # 紫色
    "Mem0g": "#8E44AD",  # 深紫色
    "MemGPT-Agent": "#F39C12",  # 橙色
    "MemoryBank": "#1ABC9C",  # 青绿色
    "MemoryOS": "#E91E63",  # 粉红色
    "SCM": "#00BCD4",  # 青色
    "HippoRAG": "#FF5722",  # 深橙色
    "HippoRAG2": "#FF6F00",  # 琥珀色
    "SeCom": "#795548",  # 棕色
    "stm": "#607D8B",  # 蓝灰色
}

# 类别名称
CATEGORY_NAMES = {
    1: "Multi-Answer",
    2: "Single-Span",
    3: "Yes/No",
    4: "Unanswerable",
    5: "Not Mentioned",
}

# ============================================================================
# F1 分数计算函数
# ============================================================================


def normalize_answer(s):
    """标准化答案文本"""
    if not isinstance(s, str):
        s = str(s)
    s = s.replace(",", "")
    exclude = set(string.punctuation)
    s = "".join(ch for ch in s if ch not in exclude)
    s = regex.sub(r"\b(a|an|the|and)\b", " ", s.lower())
    return " ".join(s.split())


def f1_score(prediction, ground_truth):
    """计算token级别的F1分数"""
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
    """处理逗号分隔的多答案F1计算"""
    preds = [p.strip() for p in prediction.split(",")]
    gts = [g.strip() for g in ground_truth.split(",")]
    return np.mean([max([f1_score(p, gt) for p in preds]) for gt in gts])


def eval_question_answering(qas):
    """评估问答对，按类别分别计算F1（与原始分析逻辑一致）"""
    f1_scores = []
    category_scores = {1: [], 2: [], 3: [], 4: [], 5: []}

    for q in qas:
        answer = str(q.get("answer", ""))
        pred = q.get("prediction", "").strip()
        category = q.get("category", 1)

        # Category 5: 判断是否正确选择 (b) 或识别"信息未提及"
        if category == 5:
            pred_lower = pred.lower()

            # 方式1: 检查是否选择了选项 (b)
            selected_b = any(
                pattern in pred_lower
                for pattern in [
                    "(b)",
                    "option b",
                    "answer is b",
                    "select b",
                    "choice b",
                ]
            )

            # 方式2: 检查是否包含 "not mentioned" 关键字（兜底）
            is_not_mentioned = any(
                keyword in pred_lower
                for keyword in [
                    "not mentioned",
                    "no information",
                    "not in the conversation",
                    "cannot be determined",
                ]
            )

            # 只要选择了 (b) 或者说明了"未提及"，就算正确
            score = 1.0 if (selected_b or is_not_mentioned) else 0.0
            f1_scores.append(score)
            category_scores[5].append(score)
            continue

        # Category 3: 清理分号后的注释部分
        if category == 3:
            answer = answer.split(";")[0].strip()
            pred = pred.split(";")[0].strip()

        # Category 1: 多答案（逗号分隔）
        if category == 1:
            score = f1_multi(pred, answer) if "," in answer else f1_score(pred, answer)
        else:
            score = f1_score(pred, answer)

        f1_scores.append(score)
        category_scores[category].append(score)

    return f1_scores, category_scores


# ============================================================================
# 数据加载和分析
# ============================================================================


def load_all_methods(input_base_dir: str) -> dict[str, dict]:
    """从所有方法目录加载结果"""
    base_path = Path(input_base_dir)
    if not base_path.exists():
        print(f"Error: '{input_base_dir}' not found!")
        sys.exit(1)

    methods_data = {}
    print(f"Loading methods from: {input_base_dir}")

    for method_dir in sorted(base_path.iterdir()):
        if method_dir.is_dir():
            json_files = list(method_dir.glob("*.json"))
            if json_files:
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


def analyze_method_rounds(method_name: str, data: dict) -> dict:
    """分析一个方法在各轮次各类别的F1得分"""
    results = data.get("test_results", [])

    # 存储每轮每个类别的得分
    # round_scores[round_idx][category] = [scores]
    round_category_scores = {}

    for test in results:
        round_idx = test.get("test_index", 0)
        qas = [
            {
                "answer": q.get("reference_answer", ""),
                "prediction": q.get("predicted_answer", ""),
                "category": q.get("category", 1),
            }
            for q in test.get("questions", [])
        ]

        if qas:
            _, cat_scores = eval_question_answering(qas)

            if round_idx not in round_category_scores:
                round_category_scores[round_idx] = {1: [], 2: [], 3: [], 4: [], 5: []}

            for cat in [1, 2, 3, 4, 5]:
                round_category_scores[round_idx][cat] = cat_scores.get(cat, [])

    # 计算每轮每个类别的平均分
    round_averages = {}
    for round_idx, cat_scores in round_category_scores.items():
        round_averages[round_idx] = {}
        for cat in [1, 2, 3, 4, 5]:
            scores = cat_scores[cat]
            round_averages[round_idx][cat] = np.mean(scores) if scores else 0.0

    return {
        "method_name": method_name,
        "round_averages": round_averages,  # {round_idx: {category: avg_f1}}
    }


# ============================================================================
# 绘图函数
# ============================================================================


def plot_category_round_progression(category_id: int, analyses: list[dict], output_path: Path):
    """
    为单个类别绘制轮次进展图：X轴=轮次，Y轴=F1分数，每个方法一条线

    参数:
        category_id: 类别ID (1-5)
        analyses: 包含每个方法的轮次得分的列表
        output_path: 输出文件路径
    """
    fig, ax = plt.subplots(figsize=(16, 10))

    # 收集所有轮次
    all_rounds = set()
    for analysis in analyses:
        all_rounds.update(analysis["round_averages"].keys())
    rounds = sorted(all_rounds)

    if not rounds:
        print(f"  ⚠ No data for category {category_id}")
        return

    # 为每个方法绘制线条
    for analysis in analyses:
        method = analysis["method_name"]
        round_scores = analysis["round_averages"]

        # 提取该类别在各轮次的得分
        scores = [round_scores.get(r, {}).get(category_id, 0) for r in rounds]

        color = METHOD_COLORS.get(method, "#95A5A6")

        # 绘制折线图
        ax.plot(
            rounds,
            scores,
            marker="o",
            label=method,
            color=color,
            linewidth=2.5,
            markersize=8,
            alpha=0.85,
        )

    # 设置图表标签和标题
    ax.set_xlabel("Test Round", fontsize=14, fontweight="bold")
    ax.set_ylabel("F1 Score", fontsize=14, fontweight="bold")
    ax.set_title(
        f"Category {category_id}: {CATEGORY_NAMES[category_id]} - Round Progression",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )

    # 设置X轴刻度（显示所有轮次）
    ax.set_xticks(rounds)
    ax.set_xticklabels([f"R{r}" for r in rounds], fontsize=11)

    # 设置Y轴范围和网格（自动放缩）
    # 收集所有得分数据以确定合适的Y轴范围
    all_scores = []
    for analysis in analyses:
        round_scores = analysis["round_averages"]
        all_scores.extend([round_scores.get(r, {}).get(category_id, 0) for r in rounds])

    if all_scores:
        min_score = min(all_scores)
        max_score = max(all_scores)

        # 添加一些边距使图表更美观
        margin = (max_score - min_score) * 0.1 if max_score > min_score else 0.1
        y_min = max(0, min_score - margin)  # 确保不低于0
        y_max = min(1.0, max_score + margin)  # 确保不高于1.0

        # 如果所有值都很接近，确保有足够的显示范围
        if y_max - y_min < 0.1:
            y_center = (y_max + y_min) / 2
            y_min = max(0, y_center - 0.05)
            y_max = min(1.0, y_center + 0.05)

        ax.set_ylim(y_min, y_max)
    else:
        ax.set_ylim(0, 1.0)

    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.7)

    # 设置图例（放在图表右侧）
    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=11,
        frameon=True,
        shadow=True,
        ncol=1,
    )

    # 调整布局
    plt.tight_layout()

    # 保存图表
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"  ✓ {output_path.name}")


def generate_round_summary_table(analyses: list[dict], output_dir: Path):
    """生成轮次汇总表格（可选）"""
    summary_path = output_dir / "round_progression_summary.txt"

    # 收集所有轮次
    all_rounds = set()
    for analysis in analyses:
        all_rounds.update(analysis["round_averages"].keys())
    rounds = sorted(all_rounds)

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("=" * 100 + "\n")
        f.write("Round Progression Summary by Category\n")
        f.write("=" * 100 + "\n\n")

        for cat in [1, 2, 3, 4, 5]:
            f.write(f"\n{'=' * 100}\n")
            f.write(f"Category {cat}: {CATEGORY_NAMES[cat]}\n")
            f.write(f"{'=' * 100}\n")

            # 表头
            header = f"{'Method':<15}"
            for r in rounds:
                header += f"{'R' + str(r):<10}"
            header += f"{'Average':<10}"
            f.write(header + "\n")
            f.write("-" * 100 + "\n")

            # 每个方法的数据
            for analysis in analyses:
                method = analysis["method_name"]
                round_scores = analysis["round_averages"]

                scores = [round_scores.get(r, {}).get(cat, 0) for r in rounds]
                avg = np.mean(scores) if scores else 0

                row = f"{method:<15}"
                for score in scores:
                    row += f"{score:<10.4f}"
                row += f"{avg:<10.4f}"
                f.write(row + "\n")

            f.write("\n")

        f.write("=" * 100 + "\n")

    print(f"✓ Round summary table saved: {summary_path}")


# ============================================================================
# 主函数
# ============================================================================


def main():
    print("=" * 80)
    print("Category Round Progression Chart Generator for LoCoMo Benchmark")
    print("=" * 80)
    print()

    # 创建输出目录
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    # 加载所有方法的数据
    methods_data = load_all_methods(INPUT_BASE_DIR)

    if not methods_data:
        print("Error: No method data found!")
        sys.exit(1)

    print(f"\nFound {len(methods_data)} methods\n")

    # 分析每个方法的轮次得分
    print("Analyzing round scores by category...")
    analyses = []
    for method_name, method_info in methods_data.items():
        analysis = analyze_method_rounds(method_name, method_info["data"])
        analyses.append(analysis)
        print(f"  ✓ {method_name}")

    # 按方法名称排序（可选）
    analyses.sort(key=lambda x: x["method_name"])

    # 生成5张类别轮次进展图
    print("\nGenerating round progression charts for each category...")
    for category_id in [1, 2, 3, 4, 5]:
        output_filename = f"{OUTPUT_PREFIX}_category_{category_id}_{CATEGORY_NAMES[category_id].replace('/', '_').replace(' ', '_')}.png"
        output_path = output_dir / output_filename
        plot_category_round_progression(category_id, analyses, output_path)

    # 生成汇总表格
    print("\nGenerating round progression summary table...")
    generate_round_summary_table(analyses, output_dir)

    print("\n" + "=" * 80)
    print("✓ All tasks completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
