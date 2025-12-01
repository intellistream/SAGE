#!/usr/bin/env python3
"""
找出最重要的检索头 - 简化版

用法:
    python find_heads.py --model /path/to/model --dataset nq --num_samples 100
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml
from datasets import load_dataset

from sage.benchmark.benchmark_refiner.analysis.head_analysis import (
    AttentionHookExtractor,
    HeadwiseEvaluator,
)
from sage.benchmark.benchmark_refiner.analysis.visualization import plot_mnr_curve

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def load_dataset_samples(
    dataset_name: str,
    split: str = "train",
    num_samples: int = 100,
) -> list[dict]:
    """加载数据集样本

    Args:
        dataset_name: 数据集名称 (nq, hotpotqa, triviaqa, squad)
        split: 数据集分割
        num_samples: 样本数量

    Returns:
        [{"question": str, "context": str, "answers": list}, ...]
    """
    logger.info(f"Loading dataset: {dataset_name} ({split})")

    # FlashRAG 数据集映射
    dataset_map = {
        "nq": "namespace-Pt/projects",
        "hotpotqa": "hotpot_qa",
        "triviaqa": "trivia_qa",
        "squad": "squad",
    }

    hf_dataset_name = dataset_map.get(dataset_name, dataset_name)

    try:
        ds = load_dataset(hf_dataset_name, split=split, trust_remote_code=True)
    except Exception as e:
        logger.error(f"Failed to load dataset {hf_dataset_name}: {e}")
        logger.info("Falling back to mock data...")
        # 简单的 fallback
        return [
            {
                "question": f"What is question {i}?",
                "context": f"This is context for question {i}. " * 50,
                "answers": [f"answer{i}"],
            }
            for i in range(num_samples)
        ]

    samples = []
    ds = ds.select(range(min(num_samples, len(ds))))

    for item in ds:
        # 提取 question
        question = item.get("question", item.get("query", ""))

        # 提取 context - 不截断到前3个，保留所有正样本 context
        if "context" in item:
            context = item["context"]
        elif "contexts" in item:
            # 保留所有 contexts（或至少前10个以避免过长）
            contexts = item["contexts"]
            if isinstance(contexts, list):
                context = " ".join(contexts[:10])  # 最多取前10个
            else:
                context = str(contexts)
        elif "positive_ctxs" in item:
            # 保留所有 positive contexts（或至少前10个）
            positive_ctxs = item["positive_ctxs"]
            if isinstance(positive_ctxs, list):
                context = " ".join([ctx.get("text", "") for ctx in positive_ctxs[:10]])
            else:
                context = str(positive_ctxs)
        else:
            # 如果没有 context，使用问题本身（不理想但可以工作）
            context = f"Context for: {question}"

        # 提取 answers
        answers = item.get("answers", item.get("answer", []))
        if isinstance(answers, str):
            answers = [answers]

        if question and context:
            samples.append(
                {
                    "question": question,
                    "context": context,
                    "answers": answers,
                }
            )

        if len(samples) >= num_samples:
            break

    logger.info(f"Loaded {len(samples)} samples")
    return samples


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Find important retrieval heads")

    # 只接受配置文件
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to YAML config file",
    )

    args = parser.parse_args()

    # 从配置文件加载所有配置
    logger.info(f"Loading config from: {args.config}")
    with open(args.config) as f:
        config = yaml.safe_load(f)

    # 创建配置对象
    class Config:
        pass

    cfg = Config()
    for key, value in config.items():
        setattr(cfg, key, value)

    logger.info("=" * 80)
    logger.info("Attention Head Selection for Retrieval")
    logger.info("=" * 80)
    logger.info(f"Model: {cfg.model}")
    logger.info(f"Dataset: {cfg.dataset}")
    logger.info(f"Samples: {cfg.num_samples}")
    logger.info(f"Device: {cfg.device}")
    logger.info("=" * 80)

    # 创建输出目录
    output_dir = Path(cfg.output_dir) / f"{cfg.dataset}_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # 加载数据集
    samples = load_dataset_samples(cfg.dataset, cfg.get("split", "train"), cfg.num_samples)

    if not samples:
        logger.error("No samples loaded!")
        return

    # 创建模型提取器
    logger.info("\n" + "-" * 80)
    logger.info("Loading Model and Registering Hooks")
    logger.info("-" * 80)

    layer_range = None
    if hasattr(cfg, "layer_end") and cfg.layer_end is not None:
        layer_start = getattr(cfg, "layer_start", 0)
        layer_range = (layer_start, cfg.layer_end)

    extractor = AttentionHookExtractor(
        model_name=cfg.model,
        dtype=getattr(cfg, "dtype", "bfloat16"),
        device=cfg.device,
        layer_range=layer_range,
    )

    extractor.register_hooks()

    # 创建评估器
    logger.info("\n" + "-" * 80)
    logger.info("Initializing Evaluator")
    logger.info("-" * 80)

    evaluator = HeadwiseEvaluator(
        model_extractor=extractor,
        query_pooling="max",
        context_pooling="mean",
        output_top_k=getattr(cfg, "top_k", 20),
    )

    # 运行评估
    logger.info("\n" + "-" * 80)
    logger.info("Running Evaluation")
    logger.info("-" * 80)

    results_df = evaluator.evaluate_samples(samples, log_interval=10)

    # 保存结果
    logger.info("\n" + "-" * 80)
    logger.info("Saving Results")
    logger.info("-" * 80)

    evaluator.save_results(results_df, output_dir, cfg.dataset)

    # 显示 top heads
    top_heads = evaluator.get_top_heads(results_df)

    logger.info("\n" + "=" * 80)
    logger.info(f"🔍 Top-{getattr(cfg, 'top_k', 20)} Heads for {cfg.dataset.upper()}")
    logger.info("=" * 80)

    for idx, row in top_heads.iterrows():
        logger.info(
            f"  {idx + 1:2d}. {row['head_type']}-Head "
            f"Layer {int(row['layer']):2d} Head {int(row['head']):2d}: "
            f"MNR = {row['mnr']:.4f} (±{row['mnr_std']:.4f})"
        )

    # 生成可视化
    logger.info("\n" + "-" * 80)
    logger.info("Generating Visualizations")
    logger.info("-" * 80)

    viz_dir = output_dir / "visualizations"
    viz_dir.mkdir(exist_ok=True)

    try:
        plot_mnr_curve(
            results_df,
            viz_dir / "mnr_curve.png",
            dataset_name=cfg.dataset,
        )
        logger.info(f"Saved visualization to {viz_dir}")
    except Exception as e:
        logger.warning(f"Failed to generate visualization: {e}")

    # 保存配置
    config_path = output_dir / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    logger.info(f"Saved config to {config_path}")

    # 清理
    extractor.remove_hooks()

    logger.info("\n" + "=" * 80)
    logger.info("✅ Analysis Complete!")
    logger.info("=" * 80)
    logger.info(f"Results: {output_dir}")
    best = top_heads.iloc[0]
    logger.info(
        f"Best head: {best['head_type']}-Head "
        f"Layer {int(best['layer'])} Head {int(best['head'])} "
        f"(MNR={best['mnr']:.4f})"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nFailed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
