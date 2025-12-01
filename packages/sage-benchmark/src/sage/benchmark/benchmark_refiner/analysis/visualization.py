"""可视化工具 - 绘制注意力头分析结果"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_mnr_curve(
    results_df: pd.DataFrame,
    output_path: str | Path,
    dataset_name: str = "dataset",
    top_k: int = 30,
) -> None:
    """绘制 MNR 曲线（Top-K 头的 MNR 分数）

    Args:
        results_df: 结果 DataFrame (columns: layer, head, head_type, mnr, mnr_std)
        output_path: 保存路径
        dataset_name: 数据集名称
        top_k: 显示前 k 个头
    """
    # 按 MNR 排序并取 top-k
    top_heads = results_df.nsmallest(top_k, "mnr")

    # 创建标签
    labels = [
        f"{row['head_type']}-L{int(row['layer'])}H{int(row['head'])}"
        for _, row in top_heads.iterrows()
    ]
    mnr_scores = top_heads["mnr"].values
    mnr_stds = top_heads["mnr_std"].values

    # 绘图
    plt.figure(figsize=(14, 8))

    # 主曲线
    x = range(len(labels))
    plt.plot(x, mnr_scores, "o-", linewidth=2, markersize=8, label="MNR Score")
    plt.fill_between(x, mnr_scores - mnr_stds, mnr_scores + mnr_stds, alpha=0.2, label="±1 std")

    # 设置
    plt.xticks(x, labels, rotation=45, ha="right")
    plt.xlabel("Attention Head (Type-Layer-Head)", fontsize=12)
    plt.ylabel("Mean Normalized Rank (MNR)", fontsize=12)
    plt.title(
        f"Top-{top_k} Attention Heads by Retrieval Performance ({dataset_name.upper()})",
        fontsize=14,
    )
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # 保存
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✅ Saved MNR curve to {output_path}")
