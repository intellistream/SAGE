"""
FireAct Trajectory Collection and Processing

Implementation based on FireAct paper (Chen et al., 2023):
"FireAct: Toward Language Agent Fine-tuning"

This module provides:
- AgentTrajectory: Data structure for agent execution traces
- TrajectoryCollector: Collect trajectories from agent execution
- TrajectoryFilter: Filter high-quality trajectories
- TrajectoryToSFTConverter: Convert trajectories to SFT training data

The core idea is to:
1. Let agents execute tasks in an environment
2. Collect execution traces (thoughts, actions, observations)
3. Filter successful high-reward trajectories
4. Convert to supervised fine-tuning data
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator, Literal, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class TrajectoryStep:
    """
    A single step in an agent's execution trajectory.

    Follows the ReAct pattern: Thought → Action → Observation

    Attributes:
        step_id: Unique identifier for this step
        thought: Agent's reasoning/thinking at this step
        action: Action taken (tool name or special action)
        action_input: Arguments/parameters for the action
        observation: Result/feedback from executing the action
        reward: Step-level reward (optional, for filtering)
        timestamp: When this step was executed
        metadata: Additional step metadata
    """

    step_id: int
    thought: str
    action: str
    action_input: dict = field(default_factory=dict)
    observation: str = ""
    reward: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "step_id": self.step_id,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "reward": self.reward,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TrajectoryStep:
        """Create from dictionary."""
        return cls(
            step_id=data.get("step_id", 0),
            thought=data.get("thought", ""),
            action=data.get("action", ""),
            action_input=data.get("action_input", {}),
            observation=data.get("observation", ""),
            reward=data.get("reward", 0.0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AgentTrajectory:
    """
    Complete execution trajectory of an agent on a task.

    Attributes:
        trajectory_id: Unique identifier
        task_id: ID of the task being executed
        instruction: The task instruction/query
        steps: List of execution steps
        success: Whether the task was completed successfully
        total_reward: Cumulative reward for the trajectory
        start_time: When execution started
        end_time: When execution ended
        available_tools: Tools available during execution
        ground_truth: Expected correct answer/actions (if known)
        metadata: Additional trajectory metadata
    """

    trajectory_id: str
    task_id: str
    instruction: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    success: bool = False
    total_reward: float = 0.0
    start_time: str = ""
    end_time: str = ""
    available_tools: list[str] = field(default_factory=list)
    ground_truth: Optional[dict] = None
    metadata: dict = field(default_factory=dict)

    @property
    def num_steps(self) -> int:
        """Number of steps in trajectory."""
        return len(self.steps)

    @property
    def duration_seconds(self) -> float:
        """Duration of execution in seconds."""
        if not self.start_time or not self.end_time:
            return 0.0
        try:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            return (end - start).total_seconds()
        except (ValueError, TypeError):
            return 0.0

    @property
    def actions_taken(self) -> list[str]:
        """List of actions taken."""
        return [step.action for step in self.steps]

    @property
    def tools_used(self) -> set[str]:
        """Set of tools used in this trajectory."""
        return {step.action for step in self.steps if step.action not in ["finish", "error"]}

    def add_step(self, step: TrajectoryStep) -> None:
        """Add a step to the trajectory."""
        self.steps.append(step)
        self.total_reward += step.reward

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "trajectory_id": self.trajectory_id,
            "task_id": self.task_id,
            "instruction": self.instruction,
            "steps": [s.to_dict() for s in self.steps],
            "success": self.success,
            "total_reward": self.total_reward,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "available_tools": self.available_tools,
            "ground_truth": self.ground_truth,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentTrajectory:
        """Create from dictionary."""
        return cls(
            trajectory_id=data.get("trajectory_id", ""),
            task_id=data.get("task_id", ""),
            instruction=data.get("instruction", ""),
            steps=[TrajectoryStep.from_dict(s) for s in data.get("steps", [])],
            success=data.get("success", False),
            total_reward=data.get("total_reward", 0.0),
            start_time=data.get("start_time", ""),
            end_time=data.get("end_time", ""),
            available_tools=data.get("available_tools", []),
            ground_truth=data.get("ground_truth"),
            metadata=data.get("metadata", {}),
        )

    def to_json(self, path: str | Path) -> None:
        """Save trajectory to JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, path: str | Path) -> AgentTrajectory:
        """Load trajectory from JSON file."""
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


# =============================================================================
# Trajectory Collector
# =============================================================================


@dataclass
class CollectorConfig:
    """Configuration for trajectory collection."""

    max_steps: int = 10
    timeout_seconds: float = 60.0
    stop_on_success: bool = True
    reward_correct_tool: float = 1.0
    reward_correct_args: float = 0.5
    reward_success: float = 5.0
    penalty_wrong_tool: float = -0.5
    penalty_error: float = -1.0


class TrajectoryCollector:
    """
    Collect agent execution trajectories.

    This collector runs an agent on tasks and records the execution trace,
    including thoughts, actions, and observations at each step.

    Example:
        >>> from sage.libs.finetune.agent.trajectory import TrajectoryCollector
        >>> collector = TrajectoryCollector(agent=my_agent, environment=my_env)
        >>> trajectories = collector.collect(tasks, max_steps=10)
    """

    def __init__(
        self,
        agent: Any,
        environment: Optional[Any] = None,
        config: Optional[CollectorConfig] = None,
        reward_fn: Optional[Callable] = None,
    ):
        """
        Initialize trajectory collector.

        Args:
            agent: Agent instance with a `run_step()` or similar method
            environment: Environment for executing actions (optional)
            config: Collection configuration
            reward_fn: Custom reward function (observation, ground_truth) -> float
        """
        self.agent = agent
        self.environment = environment
        self.config = config or CollectorConfig()
        self.reward_fn = reward_fn or self._default_reward_fn

        self._trajectory_counter = 0

    def collect(
        self,
        tasks: list[dict],
        max_steps: Optional[int] = None,
    ) -> list[AgentTrajectory]:
        """
        Collect trajectories for multiple tasks.

        Args:
            tasks: List of task dictionaries with 'instruction', 'available_tools', etc.
            max_steps: Maximum steps per task (overrides config)

        Returns:
            List of AgentTrajectory objects
        """
        max_steps = max_steps or self.config.max_steps
        trajectories = []

        for task in tasks:
            try:
                traj = self._run_episode(task, max_steps)
                trajectories.append(traj)
            except Exception as e:
                logger.warning(f"Failed to collect trajectory for task {task.get('task_id')}: {e}")
                # Create failed trajectory
                traj = self._create_failed_trajectory(task, str(e))
                trajectories.append(traj)

        logger.info(f"Collected {len(trajectories)} trajectories")
        return trajectories

    def _run_episode(self, task: dict, max_steps: int) -> AgentTrajectory:
        """
        Run a single episode and collect trajectory.

        Args:
            task: Task dictionary
            max_steps: Maximum steps for this episode

        Returns:
            AgentTrajectory object
        """
        self._trajectory_counter += 1
        trajectory = AgentTrajectory(
            trajectory_id=f"traj_{self._trajectory_counter:06d}",
            task_id=task.get("task_id", f"task_{self._trajectory_counter}"),
            instruction=task.get("instruction", ""),
            available_tools=task.get("available_tools", []),
            ground_truth=task.get("ground_truth"),
            start_time=datetime.now().isoformat(),
        )

        # Reset agent state if needed
        if hasattr(self.agent, "reset"):
            self.agent.reset()

        # Initialize environment if present
        if self.environment and hasattr(self.environment, "reset"):
            self.environment.reset(task)

        # Run steps
        done = False
        step_count = 0

        while not done and step_count < max_steps:
            step = self._execute_step(trajectory, step_count, task)
            trajectory.add_step(step)

            # Check termination
            if step.action in ["finish", "done", "error"]:
                done = True
            elif self.config.stop_on_success and step.reward >= self.config.reward_success:
                done = True

            step_count += 1

        # Finalize trajectory
        trajectory.end_time = datetime.now().isoformat()
        trajectory.success = self._evaluate_success(trajectory, task)

        return trajectory

    def _execute_step(
        self,
        trajectory: AgentTrajectory,
        step_idx: int,
        task: dict,
    ) -> TrajectoryStep:
        """
        Execute a single step and record it.

        Args:
            trajectory: Current trajectory being built
            step_idx: Current step index
            task: Original task

        Returns:
            TrajectoryStep object
        """
        # Get agent's thought and action
        thought, action, action_input = self._get_agent_action(trajectory, task)

        # Execute action in environment
        observation = self._execute_action(action, action_input)

        # Calculate reward
        reward = self.reward_fn(
            action=action,
            action_input=action_input,
            observation=observation,
            ground_truth=task.get("ground_truth"),
            step_idx=step_idx,
        )

        step = TrajectoryStep(
            step_id=step_idx,
            thought=thought,
            action=action,
            action_input=action_input,
            observation=observation,
            reward=reward,
        )

        return step

    def _get_agent_action(
        self,
        trajectory: AgentTrajectory,
        task: dict,
    ) -> tuple[str, str, dict]:
        """
        Get agent's thought and action for current state.

        Returns:
            (thought, action, action_input) tuple
        """
        # Build context from trajectory history
        context = {
            "instruction": trajectory.instruction,
            "available_tools": trajectory.available_tools,
            "history": [s.to_dict() for s in trajectory.steps],
        }

        # Call agent
        if hasattr(self.agent, "run_step"):
            result = self.agent.run_step(context)
        elif hasattr(self.agent, "act"):
            result = self.agent.act(context)
        elif callable(self.agent):
            result = self.agent(context)
        else:
            # Mock agent for testing
            result = {
                "thought": "I should use a tool to complete this task.",
                "action": trajectory.available_tools[0] if trajectory.available_tools else "finish",
                "action_input": {},
            }

        thought = result.get("thought", "")
        action = result.get("action", "finish")
        action_input = result.get("action_input", {})

        return thought, action, action_input

    def _execute_action(self, action: str, action_input: dict) -> str:
        """
        Execute action in environment.

        Args:
            action: Action/tool name
            action_input: Action arguments

        Returns:
            Observation string
        """
        if self.environment is None:
            # Mock observation for testing
            return f"Action '{action}' executed with input {action_input}. Result: success."

        try:
            if hasattr(self.environment, "step"):
                observation, _, _, _ = self.environment.step(action, action_input)
            elif hasattr(self.environment, "execute"):
                observation = self.environment.execute(action, action_input)
            else:
                observation = str(self.environment(action, action_input))
            return str(observation)
        except Exception as e:
            return f"Error executing {action}: {e}"

    def _default_reward_fn(
        self,
        action: str,
        action_input: dict,
        observation: str,
        ground_truth: Optional[dict],
        step_idx: int,
    ) -> float:
        """
        Default reward function.

        Args:
            action: Action taken
            action_input: Action arguments
            observation: Result of action
            ground_truth: Expected correct answer
            step_idx: Current step index

        Returns:
            Reward value
        """
        reward = 0.0

        # Check for errors
        if "error" in observation.lower():
            return self.config.penalty_error

        # Check against ground truth if available
        if ground_truth:
            expected_tools = ground_truth.get("expected_tools", [])
            if action in expected_tools:
                reward += self.config.reward_correct_tool

            # Check arguments
            expected_args = ground_truth.get("expected_args", {}).get(action, {})
            if expected_args:
                if all(action_input.get(k) == v for k, v in expected_args.items()):
                    reward += self.config.reward_correct_args

        return reward

    def _evaluate_success(self, trajectory: AgentTrajectory, task: dict) -> bool:
        """
        Evaluate if the trajectory successfully completed the task.

        Args:
            trajectory: Completed trajectory
            task: Original task

        Returns:
            True if successful
        """
        ground_truth = task.get("ground_truth", {})
        if not ground_truth:
            # No ground truth, consider success if no errors
            return all("error" not in s.observation.lower() for s in trajectory.steps)

        # Check if all expected tools were used
        expected_tools = set(ground_truth.get("expected_tools", []))
        used_tools = trajectory.tools_used

        if expected_tools and expected_tools.issubset(used_tools):
            return True

        # Check based on reward threshold
        return trajectory.total_reward >= (len(trajectory.steps) * 0.5)

    def _create_failed_trajectory(self, task: dict, error_msg: str) -> AgentTrajectory:
        """Create a failed trajectory record."""
        self._trajectory_counter += 1
        return AgentTrajectory(
            trajectory_id=f"traj_{self._trajectory_counter:06d}",
            task_id=task.get("task_id", "unknown"),
            instruction=task.get("instruction", ""),
            steps=[
                TrajectoryStep(
                    step_id=0,
                    thought="Collection failed",
                    action="error",
                    observation=error_msg,
                    reward=self.config.penalty_error,
                )
            ],
            success=False,
            total_reward=self.config.penalty_error,
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            metadata={"error": error_msg},
        )


# =============================================================================
# Trajectory Filter
# =============================================================================


class TrajectoryFilter:
    """
    Filter trajectories based on quality criteria.

    FireAct's key insight: only use high-quality trajectories for fine-tuning.

    Example:
        >>> filter = TrajectoryFilter(min_reward=0.5, require_success=True)
        >>> good_trajectories = filter.filter(all_trajectories)
    """

    def __init__(
        self,
        min_reward: float = 0.0,
        require_success: bool = True,
        min_steps: int = 1,
        max_steps: Optional[int] = None,
        min_tool_usage: int = 1,
        exclude_actions: Optional[list[str]] = None,
    ):
        """
        Initialize filter.

        Args:
            min_reward: Minimum total reward threshold
            require_success: Only keep successful trajectories
            min_steps: Minimum number of steps
            max_steps: Maximum number of steps (None = no limit)
            min_tool_usage: Minimum number of unique tools used
            exclude_actions: Actions that disqualify a trajectory
        """
        self.min_reward = min_reward
        self.require_success = require_success
        self.min_steps = min_steps
        self.max_steps = max_steps
        self.min_tool_usage = min_tool_usage
        self.exclude_actions = set(exclude_actions or [])

    def filter(self, trajectories: list[AgentTrajectory]) -> list[AgentTrajectory]:
        """
        Filter trajectories based on criteria.

        Args:
            trajectories: List of trajectories to filter

        Returns:
            Filtered list of high-quality trajectories
        """
        filtered = []

        for traj in trajectories:
            if self._passes_filter(traj):
                filtered.append(traj)

        logger.info(
            f"Filtered trajectories: {len(filtered)}/{len(trajectories)} "
            f"({len(filtered) / len(trajectories) * 100:.1f}% kept)"
        )
        return filtered

    def _passes_filter(self, trajectory: AgentTrajectory) -> bool:
        """Check if trajectory passes all filters."""
        # Success check
        if self.require_success and not trajectory.success:
            return False

        # Reward check
        if trajectory.total_reward < self.min_reward:
            return False

        # Step count checks
        if len(trajectory.steps) < self.min_steps:
            return False
        if self.max_steps and len(trajectory.steps) > self.max_steps:
            return False

        # Tool usage check
        if len(trajectory.tools_used) < self.min_tool_usage:
            return False

        # Excluded actions check
        if self.exclude_actions:
            if any(s.action in self.exclude_actions for s in trajectory.steps):
                return False

        return True

    def get_stats(self, trajectories: list[AgentTrajectory]) -> dict:
        """
        Get filtering statistics.

        Args:
            trajectories: Trajectories to analyze

        Returns:
            Statistics dictionary
        """
        total = len(trajectories)
        successful = sum(1 for t in trajectories if t.success)
        above_reward = sum(1 for t in trajectories if t.total_reward >= self.min_reward)

        passed = len(self.filter(trajectories))

        return {
            "total": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0,
            "above_reward_threshold": above_reward,
            "passed_filter": passed,
            "filter_pass_rate": passed / total if total > 0 else 0,
        }


# =============================================================================
# Trajectory to SFT Converter
# =============================================================================


@dataclass
class SFTConversionConfig:
    """Configuration for trajectory to SFT conversion."""

    output_format: Literal["alpaca", "sharegpt", "chatml"] = "chatml"
    include_thought: bool = True
    include_observation: bool = True
    max_turns_per_sample: Optional[int] = None
    system_prompt: Optional[str] = None
    tool_call_format: Literal["generic", "qwen", "function_call"] = "generic"


class TrajectoryToSFTConverter:
    """
    Convert agent trajectories to SFT training data.

    Supports multiple output formats:
    - alpaca: {"instruction": str, "input": str, "output": str}
    - sharegpt: {"conversations": [{"from": str, "value": str}, ...]}
    - chatml: ChatML format with system/user/assistant roles

    Example:
        >>> converter = TrajectoryToSFTConverter()
        >>> sft_data = converter.convert(trajectories)
    """

    DEFAULT_SYSTEM_PROMPT = """You are an intelligent assistant that helps users complete tasks using available tools.

Available tools: {available_tools}

When you need to use a tool, respond with:
<tool_call>
{{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}
</tool_call>

Think step by step and use the most appropriate tools to complete the user's request."""

    TOOL_CALL_TEMPLATE = """<tool_call>
{{"name": "{name}", "arguments": {arguments}}}
</tool_call>"""

    def __init__(self, config: Optional[SFTConversionConfig] = None):
        """
        Initialize converter.

        Args:
            config: Conversion configuration
        """
        self.config = config or SFTConversionConfig()

    def convert(self, trajectories: list[AgentTrajectory]) -> list[dict]:
        """
        Convert trajectories to SFT training data.

        Args:
            trajectories: List of trajectories to convert

        Returns:
            List of formatted training samples
        """
        sft_data = []

        for traj in trajectories:
            try:
                sample = self._convert_trajectory(traj)
                sft_data.append(sample)
            except Exception as e:
                logger.warning(f"Failed to convert trajectory {traj.trajectory_id}: {e}")

        logger.info(f"Converted {len(sft_data)} trajectories to SFT format")
        return sft_data

    def _convert_trajectory(self, trajectory: AgentTrajectory) -> dict:
        """
        Convert a single trajectory to SFT format.

        Args:
            trajectory: Trajectory to convert

        Returns:
            Formatted training sample
        """
        if self.config.output_format == "alpaca":
            return self._to_alpaca(trajectory)
        elif self.config.output_format == "sharegpt":
            return self._to_sharegpt(trajectory)
        else:  # chatml
            return self._to_chatml(trajectory)

    def _to_alpaca(self, trajectory: AgentTrajectory) -> dict:
        """Convert to Alpaca format."""
        # Build output as the sequence of thoughts and actions
        output_parts = []
        for step in trajectory.steps:
            if self.config.include_thought and step.thought:
                output_parts.append(f"Thought: {step.thought}")

            # Format tool call
            tool_call = self._format_tool_call(step.action, step.action_input)
            output_parts.append(tool_call)

            if self.config.include_observation and step.observation:
                output_parts.append(f"Observation: {step.observation}")

        return {
            "instruction": trajectory.instruction,
            "input": f"Available tools: {', '.join(trajectory.available_tools)}",
            "output": "\n\n".join(output_parts),
            "metadata": {
                "trajectory_id": trajectory.trajectory_id,
                "task_id": trajectory.task_id,
                "success": trajectory.success,
                "total_reward": trajectory.total_reward,
            },
        }

    def _to_sharegpt(self, trajectory: AgentTrajectory) -> dict:
        """Convert to ShareGPT format."""
        conversations = []

        # System message
        system_prompt = self.config.system_prompt or self.DEFAULT_SYSTEM_PROMPT.format(
            available_tools=", ".join(trajectory.available_tools)
        )
        conversations.append({"from": "system", "value": system_prompt})

        # User message
        conversations.append({"from": "human", "value": trajectory.instruction})

        # Agent responses (interleaved with observations)
        for step in trajectory.steps:
            # Build assistant response
            response_parts = []
            if self.config.include_thought and step.thought:
                response_parts.append(f"Thought: {step.thought}")

            tool_call = self._format_tool_call(step.action, step.action_input)
            response_parts.append(tool_call)

            conversations.append(
                {
                    "from": "gpt",
                    "value": "\n\n".join(response_parts),
                }
            )

            # Add observation as system/tool response
            if self.config.include_observation and step.observation:
                conversations.append(
                    {
                        "from": "tool",
                        "value": step.observation,
                    }
                )

        return {
            "conversations": conversations,
            "metadata": {
                "trajectory_id": trajectory.trajectory_id,
                "task_id": trajectory.task_id,
                "success": trajectory.success,
            },
        }

    def _to_chatml(self, trajectory: AgentTrajectory) -> dict:
        """Convert to ChatML format."""
        messages = []

        # System message
        system_prompt = self.config.system_prompt or self.DEFAULT_SYSTEM_PROMPT.format(
            available_tools=", ".join(trajectory.available_tools)
        )
        messages.append({"role": "system", "content": system_prompt})

        # User message
        messages.append({"role": "user", "content": trajectory.instruction})

        # Build full assistant response
        response_parts = []
        for step in trajectory.steps:
            if self.config.include_thought and step.thought:
                response_parts.append(f"Thought: {step.thought}")

            tool_call = self._format_tool_call(step.action, step.action_input)
            response_parts.append(tool_call)

            if self.config.include_observation and step.observation:
                response_parts.append(f"Observation: {step.observation}")

        messages.append(
            {
                "role": "assistant",
                "content": "\n\n".join(response_parts),
            }
        )

        return {
            "messages": messages,
            "metadata": {
                "trajectory_id": trajectory.trajectory_id,
                "task_id": trajectory.task_id,
                "success": trajectory.success,
                "total_reward": trajectory.total_reward,
            },
        }

    def _format_tool_call(self, action: str, action_input: dict) -> str:
        """Format tool call based on configured style."""
        if self.config.tool_call_format == "qwen":
            # Qwen style
            return f'<tool_call>\n{{"name": "{action}", "arguments": {json.dumps(action_input, ensure_ascii=False)}}}\n</tool_call>'
        elif self.config.tool_call_format == "function_call":
            # OpenAI function call style
            return json.dumps(
                {
                    "function_call": {
                        "name": action,
                        "arguments": json.dumps(action_input, ensure_ascii=False),
                    }
                },
                ensure_ascii=False,
            )
        else:
            # Generic style
            return self.TOOL_CALL_TEMPLATE.format(
                name=action,
                arguments=json.dumps(action_input, ensure_ascii=False),
            )

    def save_jsonl(self, sft_data: list[dict], path: str | Path) -> None:
        """
        Save SFT data to JSONL file.

        Args:
            sft_data: List of training samples
            path: Output file path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            for sample in sft_data:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        logger.info(f"Saved {len(sft_data)} samples to {path}")


# =============================================================================
# Convenience Functions
# =============================================================================


def collect_and_convert(
    agent: Any,
    tasks: list[dict],
    environment: Optional[Any] = None,
    min_reward: float = 0.5,
    require_success: bool = True,
    output_format: str = "chatml",
    save_path: Optional[str | Path] = None,
) -> list[dict]:
    """
    Convenience function for full FireAct pipeline.

    Collects trajectories, filters high-quality ones, and converts to SFT format.

    Args:
        agent: Agent to collect trajectories from
        tasks: List of tasks
        environment: Optional execution environment
        min_reward: Minimum reward threshold for filtering
        require_success: Only keep successful trajectories
        output_format: SFT output format
        save_path: Optional path to save results

    Returns:
        List of SFT training samples
    """
    # Collect
    collector = TrajectoryCollector(agent=agent, environment=environment)
    trajectories = collector.collect(tasks)

    # Filter
    filter = TrajectoryFilter(min_reward=min_reward, require_success=require_success)
    filtered = filter.filter(trajectories)

    # Convert
    converter = TrajectoryToSFTConverter(config=SFTConversionConfig(output_format=output_format))
    sft_data = converter.convert(filtered)

    # Save if requested
    if save_path:
        converter.save_jsonl(sft_data, save_path)

    return sft_data


def load_trajectories(path: str | Path) -> Iterator[AgentTrajectory]:
    """
    Load trajectories from JSONL file.

    Args:
        path: Path to JSONL file

    Yields:
        AgentTrajectory objects
    """
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                yield AgentTrajectory.from_dict(data)
