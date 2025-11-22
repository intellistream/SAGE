"""
Memory Benchmark Evaluation Module

提供对记忆基准测试结果的分析和可视化功能。

主要功能：
1. 加载实验结果 JSON 文件
2. 计算各类指标（准确率、效率等）
3. 生成可视化图表

使用示例：
    python data_analyze.py --folder .sage/benchmarks/benchmark_memory/locomo/251121 --mode independent
"""

from .core.analyzer import Analyzer
from .core.metric_interface import BaseMetric
from .core.result_loader import ResultLoader

__all__ = ["Analyzer", "BaseMetric", "ResultLoader"]
