"""
Explore Metrics - 指标探索脚本

快速计算基础指标，用于探索哪些指标适合评估记忆增强系统。

使用方法：
    python explore_metrics.py --input .sage/benchmarks/benchmark_memory/locomo/251121
    python explore_metrics.py --input .sage/benchmarks/benchmark_memory/locomo/251121 --task conv-26
"""

import argparse
import json
from pathlib import Path


def compute_token_f1(predicted: str, reference: str) -> dict:
    """计算基于token的F1、精确率、召回率"""
    if not predicted or not reference:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    pred_tokens = set(str(predicted).lower().split())
    ref_tokens = set(str(reference).lower().split())

    if not pred_tokens or not ref_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    common = pred_tokens & ref_tokens
    precision = len(common) / len(pred_tokens) if pred_tokens else 0.0
    recall = len(common) / len(ref_tokens) if ref_tokens else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1}


def compute_exact_match(predicted: str, reference: str) -> float:
    """计算精确匹配率"""
    pred_clean = str(predicted).strip().lower()
    ref_clean = str(reference).strip().lower()
    return 1.0 if pred_clean == ref_clean else 0.0


def analyze_single_file(file_path: Path) -> dict:
    """分析单个结果文件"""
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    task_id = data.get("experiment_info", {}).get("task_id", "unknown")
    test_results = data.get("test_results", [])

    all_metrics = {
        "task_id": task_id,
        "total_rounds": len(test_results),
        "rounds": [],
        "overall": {},
    }

    # 按轮次计算指标
    f1_scores = []
    em_scores = []

    for test_round in test_results:
        test_index = test_round.get("test_index", 0)
        questions = test_round.get("questions", [])

        round_f1 = []
        round_em = []

        for q in questions:
            pred = q.get("predicted_answer", "")
            ref = q.get("reference_answer", "")

            metrics = compute_token_f1(pred, ref)
            em = compute_exact_match(pred, ref)

            round_f1.append(metrics["f1"])
            round_em.append(em)

        avg_f1 = sum(round_f1) / len(round_f1) if round_f1 else 0.0
        avg_em = sum(round_em) / len(round_em) if round_em else 0.0

        all_metrics["rounds"].append(
            {"test_index": test_index, "f1": avg_f1, "exact_match": avg_em}
        )

        f1_scores.append(avg_f1)
        em_scores.append(avg_em)

    # 计算整体统计
    all_metrics["overall"] = {
        "avg_f1": sum(f1_scores) / len(f1_scores) if f1_scores else 0.0,
        "avg_exact_match": sum(em_scores) / len(em_scores) if em_scores else 0.0,
        "max_f1": max(f1_scores) if f1_scores else 0.0,
        "min_f1": min(f1_scores) if f1_scores else 0.0,
    }

    return all_metrics


def main():
    parser = argparse.ArgumentParser(description="指标探索脚本")
    parser.add_argument("--input", type=str, required=True, help="实验结果文件夹或文件路径")
    parser.add_argument("--task", type=str, help="指定任务ID（可选）")
    parser.add_argument("--output", type=str, help="输出目录（可选）")
    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"❌ 路径不存在: {input_path}")
        return

    # 收集所有JSON文件
    if input_path.is_file():
        json_files = [input_path]
    else:
        json_files = list(input_path.rglob("*.json"))

    if args.task:
        # 过滤特定任务
        json_files = [f for f in json_files if args.task in f.name]

    if not json_files:
        print("❌ 未找到JSON文件")
        return

    print(f"\n{'=' * 60}")
    print(f"📊 指标探索分析")
    print(f"{'=' * 60}")
    print(f"文件数: {len(json_files)}\n")

    all_results = []

    for json_file in json_files:
        print(f"分析: {json_file.name}")
        try:
            result = analyze_single_file(json_file)
            all_results.append(result)

            # 打印结果
            print(f"  任务ID: {result['task_id']}")
            print(f"  轮次数: {result['total_rounds']}")
            print(f"  平均F1: {result['overall']['avg_f1']:.4f}")
            print(f"  精确匹配: {result['overall']['avg_exact_match']:.4f}")
            print()

        except Exception as e:
            print(f"  ❌ 分析失败: {e}\n")

    # 保存结果
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "metrics_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        print(f"✅ 结果已保存到: {output_file}")

    print(f"\n{'=' * 60}")
    print("✨ 分析完成")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
