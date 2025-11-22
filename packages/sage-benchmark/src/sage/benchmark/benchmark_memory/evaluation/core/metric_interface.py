"""
指标接口基类 - 所有指标类必须继承此接口
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseMetric(ABC):
    """指标基类

    所有指标（F1、Precision、Recall 等）都必须继承此类并实现抽象方法。

    设计原则：
    1. 统一接口：所有指标使用相同的计算和聚合方式
    2. 可扩展：新增指标只需继承并实现抽象方法
    3. 可配置：支持通过配置文件动态加载指标
    """

    def __init__(self, name: str, description: str = ""):
        """初始化指标

        Args:
            name: 指标名称（如 "F1"）
            description: 指标描述
        """
        self.name = name
        self.description = description

    @abstractmethod
    def compute_single_question(
        self, predicted_answer: str, reference_answer: str, metadata: dict[str, Any] | None = None
    ) -> float:
        """计算单个问题的指标值

        Args:
            predicted_answer: 模型预测的答案
            reference_answer: 参考答案（ground truth）
            metadata: 额外的元数据（如问题类别、evidence 等）

        Returns:
            float: 指标值（通常在 0-1 之间）
        """
        pass

    def compute_test_round(self, questions: list[dict[str, Any]]) -> float:
        """计算单轮测试的指标值（平均）

        Args:
            questions: 单轮测试的问题列表
                每个问题包含: predicted_answer, reference_answer, metadata

        Returns:
            float: 该轮测试的平均指标值
        """
        if not questions:
            return 0.0

        scores = []
        for q in questions:
            predicted = q.get("predicted_answer", "")
            reference = q.get("reference_answer", "")
            metadata = q.get("metadata", {})

            score = self.compute_single_question(predicted, reference, metadata)
            scores.append(score)

        return sum(scores) / len(scores) if scores else 0.0

    def compute_all_rounds(self, test_results: list[dict[str, Any]]) -> list[float]:
        """计算所有测试轮次的指标值

        Args:
            test_results: 所有测试轮次的结果
                格式: [{"test_index": 1, "questions": [...]}, ...]

        Returns:
            List[float]: 每轮的指标值列表
        """
        round_scores = []

        for test_round in test_results:
            questions = test_round.get("questions", [])
            score = self.compute_test_round(questions)
            round_scores.append(score)

        return round_scores

    def compute_overall(self, test_results: list[dict[str, Any]]) -> dict[str, float]:
        """计算整体统计信息

        Args:
            test_results: 所有测试轮次的结果

        Returns:
            Dict: 包含平均值、最大值、最小值等统计信息
        """
        round_scores = self.compute_all_rounds(test_results)

        if not round_scores:
            return {
                "mean": 0.0,
                "max": 0.0,
                "min": 0.0,
                "std": 0.0,
            }

        import statistics

        return {
            "mean": statistics.mean(round_scores),
            "max": max(round_scores),
            "min": min(round_scores),
            "std": statistics.stdev(round_scores) if len(round_scores) > 1 else 0.0,
        }

    def __str__(self) -> str:
        return f"Metric({self.name})"

    def __repr__(self) -> str:
        return f"Metric(name='{self.name}', description='{self.description}')"
