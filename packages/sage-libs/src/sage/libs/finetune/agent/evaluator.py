"""
Agent Training Evaluator

Evaluates trained agent models against benchmarks.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """评估指标结果"""

    tool_selection_accuracy: float
    plan_success_rate: float
    step_efficiency: float
    timing_precision: float
    end_to_end_success: float

    # 统计信息
    total_samples: int
    successful_samples: int
    failed_samples: int

    # 详细分解
    per_category_accuracy: Optional[dict] = None
    error_analysis: Optional[dict] = None


class AgentTrainingEvaluator:
    """
    Agent 训练效果评估器

    在 agent_benchmark 上评估训练后的模型效果。

    Metrics:
        - tool_selection_accuracy: 工具选择准确率
        - plan_success_rate: 规划成功率
        - step_efficiency: 步骤效率 (实际步数 / 最优步数)
        - timing_precision: 时机准确率
        - end_to_end_success: 端到端成功率

    Example:
        >>> evaluator = AgentTrainingEvaluator(benchmark_loader)
        >>> results = evaluator.evaluate(model, split="test")
        >>> print(f"Tool accuracy: {results.tool_selection_accuracy:.2%}")
    """

    SUPPORTED_METRICS = [
        "tool_selection_accuracy",
        "plan_success_rate",
        "step_efficiency",
        "timing_precision",
        "end_to_end_success",
    ]

    def __init__(
        self,
        benchmark_loader: Any,
        tool_registry: Optional[Any] = None,
        executor: Optional[Any] = None,
    ):
        """
        初始化评估器

        Args:
            benchmark_loader: Benchmark 数据加载器
            tool_registry: 工具注册表 (用于验证工具调用)
            executor: 工具执行器 (用于端到端评估)
        """
        self.benchmark = benchmark_loader
        self.tool_registry = tool_registry
        self.executor = executor

    def evaluate(
        self,
        model: Any,
        split: str = "test",
        metrics: Optional[list[str]] = None,
        max_samples: Optional[int] = None,
        generate_fn: Optional[Callable] = None,
    ) -> EvaluationMetrics:
        """
        评估模型性能

        Args:
            model: 待评估的模型
            split: 数据分割 ("train", "dev", "test")
            metrics: 要计算的指标列表
            max_samples: 最大样本数 (用于快速评估)
            generate_fn: 自定义生成函数，签名 (model, instruction) -> response

        Returns:
            EvaluationMetrics 评估结果
        """
        metrics = metrics or self.SUPPORTED_METRICS
        generate_fn = generate_fn or self._default_generate

        # 收集评估结果
        results = {m: [] for m in metrics}
        errors = []

        # 迭代评估
        sample_count = 0
        for sample in self._iter_samples(split, max_samples):
            sample_count += 1

            try:
                # 生成响应
                response = generate_fn(model, sample.instruction)

                # 计算各项指标
                sample_results = self._evaluate_sample(
                    sample=sample,
                    response=response,
                    metrics=metrics,
                )

                for m in metrics:
                    if m in sample_results:
                        results[m].append(sample_results[m])

            except Exception as e:
                logger.warning(f"Error evaluating sample {sample.sample_id}: {e}")
                errors.append(
                    {
                        "sample_id": sample.sample_id,
                        "error": str(e),
                    }
                )

        # 聚合结果
        return self._aggregate_results(results, sample_count, errors)

    def evaluate_single(
        self,
        model: Any,
        instruction: str,
        ground_truth: dict,
        generate_fn: Optional[Callable] = None,
    ) -> dict:
        """
        评估单个样本

        Args:
            model: 模型
            instruction: 输入指令
            ground_truth: 标准答案
            generate_fn: 生成函数

        Returns:
            各项指标的分数
        """
        generate_fn = generate_fn or self._default_generate
        response = generate_fn(model, instruction)

        # 创建模拟样本对象
        class MockSample:
            def __init__(self, instruction, ground_truth):
                self.instruction = instruction
                self.sample_id = "single"
                self.target_tools = ground_truth.get("target_tools", [])
                self.expected_steps = ground_truth.get("expected_steps", [])
                self.difficulty = ground_truth.get("difficulty", "medium")

        sample = MockSample(instruction, ground_truth)

        return self._evaluate_sample(
            sample=sample,
            response=response,
            metrics=self.SUPPORTED_METRICS,
        )

    def _iter_samples(
        self,
        split: str,
        max_samples: Optional[int],
    ) -> Iterator:
        """迭代评估样本"""
        count = 0
        for sample in self.benchmark.iter_samples(split):
            if max_samples and count >= max_samples:
                break
            yield sample
            count += 1

    def _evaluate_sample(
        self,
        sample: Any,
        response: str,
        metrics: list[str],
    ) -> dict:
        """评估单个样本的所有指标"""
        results = {}

        if "tool_selection_accuracy" in metrics:
            results["tool_selection_accuracy"] = self._eval_tool_selection(response, sample)

        if "plan_success_rate" in metrics:
            results["plan_success_rate"] = self._eval_plan_success(response, sample)

        if "step_efficiency" in metrics:
            results["step_efficiency"] = self._eval_step_efficiency(response, sample)

        if "timing_precision" in metrics:
            results["timing_precision"] = self._eval_timing_precision(response, sample)

        if "end_to_end_success" in metrics:
            results["end_to_end_success"] = self._eval_end_to_end(response, sample)

        return results

    def _eval_tool_selection(self, response: str, sample: Any) -> float:
        """评估工具选择准确率"""

        # 提取预测的工具
        predicted_tools = self._extract_tools(response)
        target_tools = getattr(sample, "target_tools", [])

        if not target_tools:
            return 1.0 if not predicted_tools else 0.5

        if not predicted_tools:
            return 0.0

        # 计算 F1
        predicted_set = set(predicted_tools)
        target_set = set(target_tools)

        correct = len(predicted_set & target_set)
        precision = correct / len(predicted_set) if predicted_set else 0
        recall = correct / len(target_set) if target_set else 0

        if precision + recall == 0:
            return 0.0

        return 2 * precision * recall / (precision + recall)

    def _eval_plan_success(self, response: str, sample: Any) -> float:
        """评估规划成功率"""
        # 检查是否包含有效的规划结构
        plan_indicators = [
            r"step\s*\d+",
            r"first.*then",
            r"1\.\s*\w+.*2\.\s*\w+",
            r"plan:",
            r"步骤",
        ]

        response_lower = response.lower()
        has_plan = any(
            re.search(pattern, response_lower, re.IGNORECASE) for pattern in plan_indicators
        )

        if not has_plan:
            return 0.0

        # 检查规划是否覆盖目标工具
        predicted_tools = self._extract_tools(response)
        target_tools = getattr(sample, "target_tools", [])

        if target_tools:
            coverage = len(set(predicted_tools) & set(target_tools)) / len(target_tools)
            return 0.5 + 0.5 * coverage

        return 0.8  # 有规划但无目标工具时

    def _eval_step_efficiency(self, response: str, sample: Any) -> float:
        """评估步骤效率"""
        # 统计实际步数
        actual_steps = len(self._extract_tools(response))

        # 获取最优步数
        expected_steps = getattr(sample, "expected_steps", [])
        optimal_steps = len(expected_steps) if expected_steps else 3

        if actual_steps == 0:
            return 0.0

        if actual_steps <= optimal_steps:
            return 1.0

        # 效率随超出步数递减
        return max(0.0, 1.0 - 0.1 * (actual_steps - optimal_steps))

    def _eval_timing_precision(self, response: str, sample: Any) -> float:
        """评估时机精确度"""
        predicted_tools = self._extract_tools(response)

        # 检查重复调用
        unique_tools = set(predicted_tools)
        if len(predicted_tools) > len(unique_tools):
            # 有重复调用，扣分
            redundancy = (len(predicted_tools) - len(unique_tools)) / len(predicted_tools)
            return max(0.0, 1.0 - redundancy)

        return 1.0

    def _eval_end_to_end(self, response: str, sample: Any) -> float:
        """评估端到端成功率"""
        if self.executor is None:
            # 无执行器时，基于响应内容评估
            return self._eval_plan_success(response, sample) * 0.8

        # 执行响应中的工具调用
        try:
            tools = self._extract_tools_with_args(response)

            success_count = 0
            for tool_id, args in tools:
                result = self.executor.execute(tool_id, args)
                if result.get("status") == "success":
                    success_count += 1

            return success_count / len(tools) if tools else 0.5

        except Exception as e:
            logger.warning(f"Execution failed: {e}")
            return 0.0

    def _extract_tools(self, response: str) -> list[str]:
        """提取工具 ID 列表"""
        import re

        tools = []

        # 标准格式
        pattern1 = re.compile(r'<tool_call>\s*\{?\s*"?name"?\s*:\s*"?([^"}\s]+)"?')
        tools.extend(pattern1.findall(response))

        # 简单格式
        pattern2 = re.compile(r"(?:call|use|invoke)\s+([a-z_]+_\d{3})", re.IGNORECASE)
        tools.extend(pattern2.findall(response))

        # 去重
        seen = set()
        unique = []
        for t in tools:
            if t not in seen:
                seen.add(t)
                unique.append(t)

        return unique

    def _extract_tools_with_args(self, response: str) -> list[tuple[str, dict]]:
        """提取工具调用及其参数"""
        import json
        import re

        results = []

        pattern = re.compile(r"<tool_call>\s*(\{[^}]+\})\s*</tool_call>", re.DOTALL)

        for match in pattern.finditer(response):
            try:
                call_data = json.loads(match.group(1))
                tool_id = call_data.get("name", "")
                args = call_data.get("arguments", {})
                results.append((tool_id, args))
            except json.JSONDecodeError:
                continue

        return results

    def _default_generate(self, model: Any, instruction: str) -> str:
        """默认生成函数"""
        if hasattr(model, "generate"):
            return model.generate(instruction)
        if callable(model):
            return model(instruction)
        else:
            raise ValueError("Model must have 'generate' method or be callable")

    def _aggregate_results(
        self,
        results: dict[str, list],
        total_samples: int,
        errors: list,
    ) -> EvaluationMetrics:
        """聚合评估结果"""

        def safe_mean(values):
            return float(np.mean(values)) if values else 0.0

        return EvaluationMetrics(
            tool_selection_accuracy=safe_mean(results.get("tool_selection_accuracy", [])),
            plan_success_rate=safe_mean(results.get("plan_success_rate", [])),
            step_efficiency=safe_mean(results.get("step_efficiency", [])),
            timing_precision=safe_mean(results.get("timing_precision", [])),
            end_to_end_success=safe_mean(results.get("end_to_end_success", [])),
            total_samples=total_samples,
            successful_samples=total_samples - len(errors),
            failed_samples=len(errors),
            error_analysis={"errors": errors} if errors else None,
        )

    def generate_report(
        self,
        metrics: EvaluationMetrics,
        model_name: str = "Unknown",
        output_format: str = "markdown",
    ) -> str:
        """
        生成评估报告

        Args:
            metrics: 评估结果
            model_name: 模型名称
            output_format: 输出格式 ("markdown", "json", "text")

        Returns:
            格式化的报告字符串
        """
        if output_format == "markdown":
            return self._generate_markdown_report(metrics, model_name)
        elif output_format == "json":
            import json

            return json.dumps(metrics.__dict__, indent=2, default=str)
        else:
            return self._generate_text_report(metrics, model_name)

    def _generate_markdown_report(
        self,
        metrics: EvaluationMetrics,
        model_name: str,
    ) -> str:
        """生成 Markdown 格式报告"""
        lines = [
            "# Agent Evaluation Report",
            "",
            f"**Model**: {model_name}",
            f"**Samples**: {metrics.total_samples} (Success: {metrics.successful_samples}, Failed: {metrics.failed_samples})",
            "",
            "## Metrics",
            "",
            "| Metric | Score |",
            "|--------|-------|",
            f"| Tool Selection Accuracy | {metrics.tool_selection_accuracy:.2%} |",
            f"| Plan Success Rate | {metrics.plan_success_rate:.2%} |",
            f"| Step Efficiency | {metrics.step_efficiency:.2%} |",
            f"| Timing Precision | {metrics.timing_precision:.2%} |",
            f"| End-to-End Success | {metrics.end_to_end_success:.2%} |",
            "",
            "## Summary",
            "",
            f"Overall Agent Score: **{self._compute_overall_score(metrics):.2%}**",
        ]

        return "\n".join(lines)

    def _generate_text_report(
        self,
        metrics: EvaluationMetrics,
        model_name: str,
    ) -> str:
        """生成纯文本报告"""
        lines = [
            "=== Agent Evaluation Report ===",
            f"Model: {model_name}",
            f"Samples: {metrics.total_samples}",
            "",
            "Metrics:",
            f"  - Tool Selection Accuracy: {metrics.tool_selection_accuracy:.2%}",
            f"  - Plan Success Rate: {metrics.plan_success_rate:.2%}",
            f"  - Step Efficiency: {metrics.step_efficiency:.2%}",
            f"  - Timing Precision: {metrics.timing_precision:.2%}",
            f"  - End-to-End Success: {metrics.end_to_end_success:.2%}",
            "",
            f"Overall Score: {self._compute_overall_score(metrics):.2%}",
        ]

        return "\n".join(lines)

    def _compute_overall_score(self, metrics: EvaluationMetrics) -> float:
        """计算综合分数"""
        weights = {
            "tool_selection_accuracy": 0.30,
            "plan_success_rate": 0.25,
            "step_efficiency": 0.15,
            "timing_precision": 0.10,
            "end_to_end_success": 0.20,
        }

        score = (
            weights["tool_selection_accuracy"] * metrics.tool_selection_accuracy
            + weights["plan_success_rate"] * metrics.plan_success_rate
            + weights["step_efficiency"] * metrics.step_efficiency
            + weights["timing_precision"] * metrics.timing_precision
            + weights["end_to_end_success"] * metrics.end_to_end_success
        )

        return score
