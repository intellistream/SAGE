"""
Agent Reward Model

Computes rewards for agent responses based on:
- Task completion
- Tool selection accuracy
- Execution efficiency
- Timing quality
- Format compliance
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from .config import AgentRewardConfig

logger = logging.getLogger(__name__)


@dataclass
class RewardResult:
    """奖励计算结果"""

    total: float
    breakdown: dict[str, float]
    feedback: str
    penalties_applied: list[str]


class AgentRewardModel:
    """
    Agent 奖励模型

    用于计算 Agent 响应的奖励分数，支持:
    - 任务完成度评估
    - 工具选择准确性评估
    - 执行效率评估
    - 时机质量评估
    - 格式合规性评估

    Example:
        >>> reward_model = AgentRewardModel(AgentRewardConfig())
        >>> result = reward_model.compute_reward(
        ...     query="查询天气",
        ...     response="<tool_call>weather_001</tool_call>",
        ...     ground_truth={"target_tools": ["weather_001"]},
        ...     execution_trace=[]
        ... )
        >>> print(f"Total reward: {result.total:.2f}")
    """

    # 工具调用模式
    TOOL_CALL_PATTERN = re.compile(
        r'<tool_call>\s*\{?\s*"?name"?\s*:\s*"?([^"}\s]+)"?', re.IGNORECASE
    )

    # 简单工具 ID 模式
    SIMPLE_TOOL_PATTERN = re.compile(
        r"(?:call|use|invoke|execute)\s+([a-z_]+_\d{3})", re.IGNORECASE
    )

    def __init__(self, config: AgentRewardConfig | None = None):
        """
        初始化奖励模型

        Args:
            config: 奖励配置，None 则使用默认配置
        """
        self.config = config or AgentRewardConfig()

        # 验证权重总和
        weight_sum = sum(self.config.weights.values())
        if abs(weight_sum - 1.0) > 0.01:
            logger.warning(f"Reward weights sum to {weight_sum}, expected 1.0")

    def compute_reward(
        self,
        query: str,
        response: str,
        ground_truth: dict,
        execution_trace: list | None = None,
    ) -> RewardResult:
        """
        计算综合奖励分数

        Args:
            query: 用户请求
            response: 模型响应
            ground_truth: 标准答案，包含 target_tools, expected_steps 等
            execution_trace: 执行轨迹 (可选)

        Returns:
            RewardResult 包含总分、分项分数、反馈和惩罚
        """
        execution_trace = execution_trace or []
        rewards = {}
        penalties_applied = []

        # 1. 任务完成度
        rewards["task_completion"] = self._eval_task_completion(
            response, ground_truth, execution_trace
        )

        # 2. 工具选择准确性
        target_tools = ground_truth.get("target_tools", [])
        rewards["tool_accuracy"], tool_penalties = self._eval_tool_accuracy(response, target_tools)
        penalties_applied.extend(tool_penalties)

        # 3. 执行效率
        optimal_steps = ground_truth.get("optimal_steps", 5)
        rewards["efficiency"] = self._eval_efficiency(execution_trace, optimal_steps)

        # 4. 时机质量
        rewards["timing_quality"] = self._eval_timing(response, execution_trace, ground_truth)

        # 5. 格式合规性
        rewards["format_compliance"], format_penalties = self._eval_format(response)
        penalties_applied.extend(format_penalties)

        # 加权求和
        total = sum(rewards[k] * self.config.weights.get(k, 0) for k in rewards)

        # 应用惩罚
        for penalty_type in penalties_applied:
            penalty_value = self.config.penalties.get(penalty_type, 0)
            total += penalty_value

        # 归一化到 [0, 1]
        total = max(0.0, min(1.0, total))

        # 生成反馈
        feedback = self._generate_feedback(rewards, penalties_applied)

        return RewardResult(
            total=total,
            breakdown=rewards,
            feedback=feedback,
            penalties_applied=penalties_applied,
        )

    def _eval_task_completion(
        self,
        response: str,
        ground_truth: dict,
        execution_trace: list,
    ) -> float:
        """评估任务完成度"""
        # 检查执行轨迹中是否有成功标记
        if execution_trace:
            success_count = sum(1 for step in execution_trace if step.get("status") == "success")
            total_steps = len(execution_trace)
            if total_steps > 0:
                return success_count / total_steps

        # 基于响应内容判断
        # 检查是否包含最终答案/结论
        completion_indicators = [
            "完成",
            "done",
            "finished",
            "结果是",
            "答案是",
            "总结",
            "conclusion",
            "最终",
            "final",
        ]

        response_lower = response.lower()
        has_conclusion = any(ind in response_lower for ind in completion_indicators)

        # 检查是否调用了目标工具
        target_tools = ground_truth.get("target_tools", [])
        predicted_tools = self._extract_tool_calls(response)

        if target_tools:
            tool_coverage = len(set(predicted_tools) & set(target_tools)) / len(target_tools)
        else:
            tool_coverage = 1.0 if not predicted_tools else 0.5

        # 综合评分
        score = 0.5 * tool_coverage + 0.5 * (1.0 if has_conclusion else 0.5)
        return score

    def _eval_tool_accuracy(
        self,
        response: str,
        target_tools: list[str],
    ) -> tuple[float, list[str]]:
        """
        评估工具选择准确率

        Returns:
            (accuracy_score, penalties_list)
        """
        penalties = []
        predicted_tools = self._extract_tool_calls(response)

        if not target_tools:
            # 无目标工具时，调用任何工具都可以
            return (1.0 if not predicted_tools else 0.7, penalties)

        if not predicted_tools:
            # 应该调用工具但没有调用
            return (0.0, penalties)

        # 计算 Precision 和 Recall
        predicted_set = set(predicted_tools)
        target_set = set(target_tools)

        correct = len(predicted_set & target_set)

        # Precision: 预测的工具中有多少是正确的
        precision = correct / len(predicted_set) if predicted_set else 0

        # Recall: 目标工具中有多少被预测到
        recall = correct / len(target_set) if target_set else 0

        # 检查错误工具
        wrong_tools = predicted_set - target_set
        if wrong_tools:
            penalties.append("wrong_tool")

        # 检查幻觉工具 (格式不符合 tool_id 规范的)
        for tool in predicted_tools:
            if not re.match(r"^[a-z]+(_[a-z]+)*_\d{3}$", tool):
                penalties.append("hallucination")
                break

        # F1 Score
        if precision + recall == 0:
            return (0.0, penalties)

        f1 = 2 * precision * recall / (precision + recall)
        return (f1, penalties)

    def _eval_efficiency(
        self,
        execution_trace: list,
        optimal_steps: int,
    ) -> float:
        """评估执行效率"""
        actual_steps = len(execution_trace)

        if actual_steps == 0:
            return 0.5  # 没有执行轨迹时给中等分

        if actual_steps <= optimal_steps:
            return 1.0

        # 超过最优步数时，效率递减
        excess_ratio = (actual_steps - optimal_steps) / optimal_steps
        score = max(0.0, 1.0 - 0.2 * excess_ratio)

        return score

    def _eval_timing(
        self,
        response: str,
        execution_trace: list,
        ground_truth: dict,
    ) -> float:
        """评估调用时机质量"""
        # 检查是否有冗余调用
        predicted_tools = self._extract_tool_calls(response)
        unique_tools = set(predicted_tools)

        if len(predicted_tools) > len(unique_tools):
            # 有重复调用
            redundancy_penalty = 0.2 * (len(predicted_tools) - len(unique_tools))
            return max(0.0, 1.0 - redundancy_penalty)

        # 检查调用顺序是否合理 (基于执行轨迹)
        if execution_trace:
            # 检查是否有失败后重试
            retry_count = sum(
                1
                for i, step in enumerate(execution_trace[1:], 1)
                if step.get("tool_id") == execution_trace[i - 1].get("tool_id")
            )
            if retry_count > 0:
                return max(0.5, 1.0 - 0.1 * retry_count)

        return 1.0  # 默认良好

    def _eval_format(self, response: str) -> tuple[float, list[str]]:
        """
        评估格式合规性

        Returns:
            (format_score, penalties_list)
        """
        penalties = []
        score = 1.0

        # 检查工具调用格式
        tool_calls = self.TOOL_CALL_PATTERN.findall(response)
        simple_calls = self.SIMPLE_TOOL_PATTERN.findall(response)

        # 如果使用了非标准格式
        if simple_calls and not tool_calls:
            score -= 0.2
            penalties.append("format_error")

        # 检查是否有未闭合的标签
        open_tags = response.count("<tool_call>")
        close_tags = response.count("</tool_call>")
        if open_tags != close_tags:
            score -= 0.3
            penalties.append("format_error")

        # 检查 JSON 格式
        if "<tool_call>" in response:
            try:
                import json

                # 提取 JSON 部分
                json_match = re.search(r"<tool_call>\s*(\{[^}]+\})\s*</tool_call>", response)
                if json_match:
                    json.loads(json_match.group(1))
            except json.JSONDecodeError:
                score -= 0.2

        return (max(0.0, score), penalties)

    def _extract_tool_calls(self, response: str) -> list[str]:
        """从响应中提取工具调用"""
        tools = []

        # 标准格式
        tools.extend(self.TOOL_CALL_PATTERN.findall(response))

        # 简单格式
        tools.extend(self.SIMPLE_TOOL_PATTERN.findall(response))

        # 去重但保持顺序
        seen = set()
        unique_tools = []
        for tool in tools:
            if tool not in seen:
                seen.add(tool)
                unique_tools.append(tool)

        return unique_tools

    def _generate_feedback(
        self,
        rewards: dict[str, float],
        penalties: list[str],
    ) -> str:
        """生成人类可读的反馈"""
        feedback_parts = []

        # 分数反馈
        for metric, score in rewards.items():
            if score < 0.5:
                feedback_parts.append(f"❌ {metric}: {score:.2f} (需改进)")
            elif score < 0.8:
                feedback_parts.append(f"⚠️ {metric}: {score:.2f} (一般)")
            else:
                feedback_parts.append(f"✅ {metric}: {score:.2f} (良好)")

        # 惩罚反馈
        if penalties:
            penalty_msgs = {
                "wrong_tool": "选择了错误的工具",
                "redundant_call": "存在冗余的工具调用",
                "format_error": "响应格式不规范",
                "timeout": "执行超时",
                "hallucination": "调用了不存在的工具",
            }
            for p in set(penalties):
                msg = penalty_msgs.get(p, f"惩罚: {p}")
                feedback_parts.append(f"🚫 {msg}")

        return "\n".join(feedback_parts)


class ToolVerifier:
    """工具调用验证器"""

    def __init__(self, tool_registry: Any | None = None):
        self.tool_registry = tool_registry

    def verify_tool_exists(self, tool_id: str) -> bool:
        """验证工具是否存在"""
        if self.tool_registry is None:
            # 只验证格式
            return bool(re.match(r"^[a-z]+(_[a-z]+)*_\d{3}$", tool_id))

        return self.tool_registry.has_tool(tool_id)

    def verify_arguments(self, tool_id: str, arguments: dict) -> tuple[bool, str]:
        """验证工具参数是否合法"""
        if self.tool_registry is None:
            return (True, "")

        tool = self.tool_registry.get_tool(tool_id)
        if not tool:
            return (False, f"Tool {tool_id} not found")

        # 检查必需参数
        required_params = getattr(tool, "required_params", [])
        missing = [p for p in required_params if p not in arguments]

        if missing:
            return (False, f"Missing required parameters: {missing}")

        return (True, "")


class PlanEvaluator:
    """规划质量评估器"""

    def evaluate_plan(
        self,
        plan_steps: list[dict],
        ground_truth_steps: list[dict] | None = None,
    ) -> dict:
        """
        评估规划质量

        Args:
            plan_steps: 模型生成的规划步骤
            ground_truth_steps: 标准规划步骤 (可选)

        Returns:
            评估结果
        """
        result = {
            "step_count": len(plan_steps),
            "has_clear_goal": False,
            "has_tool_assignments": False,
            "is_executable": False,
            "score": 0.0,
        }

        if not plan_steps:
            return result

        # 检查是否有明确目标
        first_step = plan_steps[0]
        if "goal" in first_step or "objective" in first_step:
            result["has_clear_goal"] = True

        # 检查是否有工具分配
        for step in plan_steps:
            if "tool" in step or "tool_id" in step:
                result["has_tool_assignments"] = True
                break

        # 检查是否可执行 (每个步骤都有 action)
        result["is_executable"] = all("action" in step or "tool" in step for step in plan_steps)

        # 计算总分
        score = 0.0
        if result["has_clear_goal"]:
            score += 0.3
        if result["has_tool_assignments"]:
            score += 0.4
        if result["is_executable"]:
            score += 0.3

        result["score"] = score

        return result
