#!/usr/bin/env python3
"""
分类柱状图生成器 - 为所有记忆体方法绘制5个类别的F1得分对比

用途：生成横向对比所有记忆体方法在5个问题类别上的表现

使用方法: python plot_category_bar_chart.py
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
OUTPUT_DIR = ".sage/benchmarks/benchmark_memory/locomo/output/pangu/category_charts"
OUTPUT_FILENAME = "category_f1_comparison.png"

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
    # 处理非字符串类型
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


def analyze_method_categories(method_name: str, data: dict) -> dict:
    """分析一个方法在各个类别上的F1得分"""
    results = data.get("test_results", [])
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
            _, cat_scores = eval_question_answering(qas)
            for cat, scores in cat_scores.items():
                all_category_scores[cat].extend(scores)

    # 计算每个类别的平均分
    category_averages = {}
    for cat in [1, 2, 3, 4, 5]:
        scores = all_category_scores[cat]
        category_averages[cat] = np.mean(scores) if scores else 0.0

    return {
        "method_name": method_name,
        "category_scores": category_averages,
    }


# ============================================================================
# 绘图函数
# ============================================================================


def plot_single_category_chart(category_id: int, analyses: list[dict], output_path: Path):
    """
    为单个类别绘制柱状图，展示所有记忆体方法的F1得分对比

    参数:
        category_id: 类别ID (1-5)
        analyses: 包含每个方法的类别得分的列表
        output_path: 输出文件路径
    """
    methods = [a["method_name"] for a in analyses]
    scores = [a["category_scores"].get(category_id, 0) for a in analyses]
    colors = [METHOD_COLORS.get(a["method_name"], "#95A5A6") for a in analyses]

    # 设置图表尺寸
    fig, ax = plt.subplots(figsize=(14, 8))

    # 绘制柱状图
    x = np.arange(len(methods))
    bars = ax.bar(x, scores, color=colors, edgecolor="black", linewidth=1.0, alpha=0.85, width=0.7)

    # 在柱顶添加数值标签
    for i, (bar, score) in enumerate(zip(bars, scores)):
        if score > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                score,
                f"{score:.3f}",
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
            )

    # 设置图表标签和标题
    ax.set_xlabel("Memory Method", fontsize=14, fontweight="bold")
    ax.set_ylabel("F1 Score", fontsize=14, fontweight="bold")
    ax.set_title(
        f"Category {category_id}: {CATEGORY_NAMES[category_id]} - F1 Score Comparison",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )

    # 设置X轴刻度（旋转45度便于阅读）
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=45, ha="right", fontsize=11)

    # 设置Y轴范围和网格
    ax.set_ylim(0, max(scores) * 1.15 if scores else 1.0)
    ax.grid(axis="y", alpha=0.3, linestyle="--", linewidth=0.7)

    # 添加平均分参考线
    avg_score = np.mean(scores) if scores else 0
    ax.axhline(
        y=avg_score,
        color="red",
        linestyle="--",
        linewidth=1.5,
        alpha=0.6,
        label=f"Average: {avg_score:.3f}",
    )
    ax.legend(fontsize=11, loc="upper right")

    # 调整布局
    plt.tight_layout()

    # 保存图表
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"  ✓ {output_path.name}")


def generate_summary_table(analyses: list[dict], output_dir: Path):
    """生成汇总表格（可选）"""
    summary_path = output_dir / "category_summary.txt"

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("Category F1 Score Summary\n")
        f.write("=" * 80 + "\n\n")

        # 表头
        header = f"{'Method':<15}"
        for cat in [1, 2, 3, 4, 5]:
            header += f"{CATEGORY_NAMES[cat]:<18}"
        header += f"{'Average':<10}"
        f.write(header + "\n")
        f.write("-" * 80 + "\n")

        # 每个方法的数据
        for analysis in analyses:
            method = analysis["method_name"]
            scores = [analysis["category_scores"].get(cat, 0) for cat in [1, 2, 3, 4, 5]]
            avg = np.mean(scores)

            row = f"{method:<15}"
            for score in scores:
                row += f"{score:<18.4f}"
            row += f"{avg:<10.4f}"
            f.write(row + "\n")

        f.write("=" * 80 + "\n")

    print(f"✓ Summary table saved: {summary_path}")


# ============================================================================
# 主函数
# ============================================================================


def main():
    print("=" * 80)
    print("Category Bar Chart Generator for LoCoMo Benchmark")
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

    # 分析每个方法的类别得分
    print("Analyzing category scores...")
    analyses = []
    for method_name, method_info in methods_data.items():
        analysis = analyze_method_categories(method_name, method_info["data"])
        analyses.append(analysis)
        print(f"  ✓ {method_name}")

    # 按方法名称排序（可选）
    analyses.sort(key=lambda x: x["method_name"])

    # 生成5张类别图表
    print("\nGenerating bar charts for each category...")
    for category_id in [1, 2, 3, 4, 5]:
        output_filename = f"category_{category_id}_{CATEGORY_NAMES[category_id].replace('/', '_').replace(' ', '_')}.png"
        output_path = output_dir / output_filename
        plot_single_category_chart(category_id, analyses, output_path)

    # 生成汇总表格
    print("\nGenerating summary table...")
    generate_summary_table(analyses, output_dir)

    print("\n" + "=" * 80)
    print("✓ All tasks completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
