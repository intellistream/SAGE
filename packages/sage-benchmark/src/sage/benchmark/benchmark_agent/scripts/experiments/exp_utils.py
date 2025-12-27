"""
Experiment Utilities - 实验共享工具函数

为所有 Paper 1 实验提供统一的:
- 环境设置
- 数据加载
- 结果保存
- 客户端获取
- 进度显示
"""

from __future__ import annotations

import json
import os
import random
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np

# =============================================================================
# 控制变量配置 (从 adapter_registry 同步)
# =============================================================================
RANDOM_SEED = 42
BENCHMARK_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
BENCHMARK_LLM_TEMPERATURE = 0.1

# =============================================================================
# 路径配置
# =============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_AGENT_DIR = SCRIPT_DIR.parent.parent
BENCHMARK_ROOT = BENCHMARK_AGENT_DIR.parent.parent.parent.parent

# 尝试导入数据路径模块
try:
    from sage.benchmark.benchmark_agent.data_paths import get_runtime_paths

    _runtime_paths = get_runtime_paths()
    DEFAULT_OUTPUT_DIR = _runtime_paths.results_root.parent / "paper1"
    DEFAULT_DATA_DIR = _runtime_paths.data_root
except ImportError:
    SAGE_ROOT = BENCHMARK_ROOT.parent.parent
    DEFAULT_OUTPUT_DIR = SAGE_ROOT / ".sage" / "benchmark" / "paper1"
    DEFAULT_DATA_DIR = SAGE_ROOT / ".sage" / "benchmark" / "data"


# =============================================================================
# 环境设置
# =============================================================================
def ensure_hf_endpoint_configured(verbose: bool = False) -> tuple[bool, bool]:
    """确保 HuggingFace 端点可用（必要时自动切换镜像）。"""

    configured_endpoint = False
    synced_hub = False

    endpoint = os.environ.get("HF_ENDPOINT", "").strip()
    if not endpoint:
        try:
            urllib.request.urlopen("https://huggingface.co", timeout=3)
        except Exception:
            endpoint = "https://hf-mirror.com"
            os.environ["HF_ENDPOINT"] = endpoint
            configured_endpoint = True
            if verbose:
                print(f"  Auto-configured HF mirror: {endpoint}")
    else:
        endpoint = endpoint.rstrip("/")
        os.environ["HF_ENDPOINT"] = endpoint

    if os.environ.get("HF_ENDPOINT") and not os.environ.get("HF_HUB_ENDPOINT"):
        os.environ["HF_HUB_ENDPOINT"] = os.environ["HF_ENDPOINT"]
        synced_hub = True
        if verbose:
            print(f"  HF_HUB_ENDPOINT synchronized to {os.environ['HF_HUB_ENDPOINT']}")

    return configured_endpoint, synced_hub


# 在模块导入时尽早配置镜像，避免后续导入 transformers 时命中默认域名
ensure_hf_endpoint_configured(verbose=False)


def setup_experiment_env(seed: int = RANDOM_SEED, verbose: bool = True) -> None:
    """
    设置实验环境，确保可复现性。

    Args:
        seed: 随机种子
        verbose: 是否打印设置信息
    """
    # 设置 Python 随机数
    random.seed(seed)

    # 设置 NumPy 随机数
    np.random.seed(seed)

    # 设置 PyTorch 随机数 (如果可用)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            # 确定性算法 (可能降低性能)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        pass

    # 设置环境变量
    os.environ.setdefault("SAGE_TEST_MODE", "true")
    os.environ.setdefault("PYTHONHASHSEED", str(seed))

    # vLLM 配置
    os.environ.setdefault("VLLM_ATTENTION_BACKEND", "FLASH_ATTN")

    # PyTorch 分布式警告抑制
    os.environ.setdefault("GLOO_SOCKET_IFNAME", "lo")
    os.environ.setdefault("NCCL_SOCKET_IFNAME", "lo")
    os.environ.setdefault("TORCH_DISTRIBUTED_DEBUG", "OFF")

    ensure_hf_endpoint_configured(verbose=verbose)

    if verbose:
        print(f"  Random seed: {seed}")
        print(f"  Embedding model: {BENCHMARK_EMBEDDING_MODEL}")
        print(f"  LLM temperature: {BENCHMARK_LLM_TEMPERATURE}")


# =============================================================================
# 数据加载
# =============================================================================
def load_benchmark_data(
    challenge: str,
    split: str = "test",
    max_samples: Optional[int] = None,
    data_dir: Optional[Path] = None,
) -> list[dict]:
    """
    加载 benchmark 数据。

    Args:
        challenge: 挑战类型 ("timing", "planning", "selection")
        split: 数据集划分 ("train", "dev", "test")
        max_samples: 最大样本数 (None 表示全部)
        data_dir: 数据目录 (None 使用默认)

    Returns:
        样本列表
    """
    data_dir = data_dir or DEFAULT_DATA_DIR

    # 映射 challenge 到数据目录
    challenge_dirs = {
        "timing": "timing_judgment",
        "planning": "task_planning",
        "selection": "tool_selection",
    }

    if challenge not in challenge_dirs:
        raise ValueError(f"Unknown challenge: {challenge}. Use: {list(challenge_dirs.keys())}")

    data_file = data_dir / challenge_dirs[challenge] / f"{split}.jsonl"

    if not data_file.exists():
        print(f"  Warning: Data file not found: {data_file}")
        return []

    samples = []
    with open(data_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    if max_samples is not None and max_samples > 0:
        samples = samples[:max_samples]

    return samples


def load_jsonl(file_path: Path) -> list[dict]:
    """加载 JSONL 文件。"""
    if not file_path.exists():
        return []

    samples = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    return samples


# =============================================================================
# 结果保存
# =============================================================================
def save_results(
    results: dict[str, Any],
    section: str,
    name: str,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    保存实验结果。

    Args:
        results: 结果字典
        section: 论文章节 ("5_2_main", "5_3_analysis", "5_4_generalization")
        name: 结果名称 (如 "timing", "error_analysis")
        output_dir: 输出目录 (None 使用默认)

    Returns:
        保存的文件路径
    """
    output_dir = output_dir or DEFAULT_OUTPUT_DIR

    # 创建章节目录
    section_dir = output_dir / f"section_{section}"
    section_dir.mkdir(parents=True, exist_ok=True)

    # 添加元数据
    results["_metadata"] = {
        "timestamp": datetime.now().isoformat(),
        "seed": RANDOM_SEED,
        "embedding_model": BENCHMARK_EMBEDDING_MODEL,
        "llm_temperature": BENCHMARK_LLM_TEMPERATURE,
    }

    # 保存 JSON
    output_file = section_dir / f"{name}_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return output_file


def get_output_dir(section: str, output_dir: Optional[Path] = None) -> Path:
    """获取指定章节的输出目录。"""
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    section_dir = output_dir / f"section_{section}"
    section_dir.mkdir(parents=True, exist_ok=True)
    return section_dir


def get_figures_dir(output_dir: Optional[Path] = None) -> Path:
    """获取 figures 目录。"""
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    return figures_dir


def get_tables_dir(output_dir: Optional[Path] = None) -> Path:
    """获取 tables 目录。"""
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    return tables_dir


# =============================================================================
# 客户端获取
# =============================================================================
def get_llm_client():
    """
    获取统一 LLM 客户端。

    Returns:
        UnifiedInferenceClient 实例
    """
    try:
        from sage.llm import UnifiedInferenceClient

        return UnifiedInferenceClient.create()
    except ImportError as e:
        print(f"  Warning: Could not create LLM client: {e}")
        return None


def get_embedding_client():
    """
    获取 Embedding 客户端。

    Returns:
        EmbeddingClientAdapter 实例
    """
    try:
        from sage.common.components.sage_embedding import (
            EmbeddingClientAdapter,
            EmbeddingFactory,
        )

        raw_embedder = EmbeddingFactory.create("hf", model=BENCHMARK_EMBEDDING_MODEL)
        return EmbeddingClientAdapter(raw_embedder)
    except ImportError as e:
        print(f"  Warning: Could not create embedding client: {e}")
        return None


# =============================================================================
# 进度显示
# =============================================================================
def create_progress_bar(total: int, desc: str = "Processing"):
    """
    创建进度条。

    Args:
        total: 总数
        desc: 描述

    Returns:
        tqdm 进度条或简单迭代器
    """
    try:
        from tqdm import tqdm

        return tqdm(total=total, desc=desc, ncols=80)
    except ImportError:
        # 简单的进度显示
        class SimpleProgress:
            def __init__(self, total, desc):
                self.total = total
                self.current = 0
                self.desc = desc

            def update(self, n=1):
                self.current += n
                if self.current % max(1, self.total // 10) == 0:
                    print(f"  {self.desc}: {self.current}/{self.total}")

            def close(self):
                print(f"  {self.desc}: Complete ({self.total})")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        return SimpleProgress(total, desc)


# =============================================================================
# 实验结果数据类
# =============================================================================
from dataclasses import dataclass, field


@dataclass
class ExperimentResult:
    """单个策略的实验结果。"""

    challenge: str
    strategy: str
    metrics: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)
    passed: bool = False
    target: float = 0.0


@dataclass
class ExperimentSummary:
    """实验汇总。"""

    section: str
    challenge: str
    results: list[ExperimentResult] = field(default_factory=list)
    best_strategy: Optional[str] = None
    best_metric: Optional[float] = None
    target_met: bool = False

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            "section": self.section,
            "challenge": self.challenge,
            "results": [
                {
                    "strategy": r.strategy,
                    "metrics": r.metrics,
                    "passed": r.passed,
                    "target": r.target,
                }
                for r in self.results
            ],
            "best_strategy": self.best_strategy,
            "best_metric": self.best_metric,
            "target_met": self.target_met,
        }


# =============================================================================
# 打印工具
# =============================================================================
def print_section_header(title: str, width: int = 70) -> None:
    """打印章节标题。"""
    print("\n" + "=" * width)
    print(f"📊 {title}")
    print("=" * width)


def print_subsection_header(title: str) -> None:
    """打印子章节标题。"""
    print(f"\n  ▸ {title}")
    print("  " + "-" * 50)


def print_result_row(strategy: str, metrics: dict, passed: bool, target: float) -> None:
    """打印结果行。"""
    primary_metric = list(metrics.values())[0] if metrics else 0.0
    status = "✅ PASS" if passed else "❌ FAIL"
    print(
        f"    {strategy:20s} | {primary_metric * 100:6.1f}% (target: {target * 100:.0f}%) {status}"
    )


def print_metrics_detail(metrics: dict) -> None:
    """打印详细指标。"""
    for name, value in metrics.items():
        if isinstance(value, float):
            print(f"      - {name}: {value * 100:.1f}%")
        else:
            print(f"      - {name}: {value}")
