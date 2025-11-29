"""
Base Protocols and Abstract Classes for Planning

Defines the abstract interfaces that planners and timing deciders must implement.
"""

from abc import ABC, abstractmethod
from typing import Protocol

from .schemas import (
    PlannerConfig,
    PlanRequest,
    PlanResult,
    TimingConfig,
    TimingDecision,
    TimingMessage,
)


class PlannerProtocol(Protocol):
    """Protocol for planner implementations."""

    name: str

    def plan(self, request: PlanRequest) -> PlanResult:
        """
        Generate a task plan from a request.

        Args:
            request: PlanRequest containing goal, tools, and constraints

        Returns:
            PlanResult with generated steps
        """
        ...


class BasePlanner(ABC):
    """
    Abstract base class for planners.

    Provides common functionality and enforces interface.
    """

    name: str = "base_planner"

    def __init__(self, config: PlannerConfig):
        """
        Initialize planner with configuration.

        Args:
            config: PlannerConfig instance
        """
        self.config = config

    @classmethod
    def from_config(cls, config: PlannerConfig, **kwargs) -> "BasePlanner":
        """
        Create planner instance from configuration.

        Args:
            config: PlannerConfig instance
            **kwargs: Additional resources (e.g., llm_client, tool_selector)

        Returns:
            Initialized planner instance
        """
        return cls(config=config, **kwargs)

    @abstractmethod
    def plan(self, request: PlanRequest) -> PlanResult:
        """
        Generate a task plan.

        Must be implemented by subclasses.

        Args:
            request: PlanRequest

        Returns:
            PlanResult
        """
        pass

    def validate_plan(self, result: PlanResult) -> bool:
        """
        Validate a generated plan.

        Args:
            result: PlanResult to validate

        Returns:
            True if valid, False otherwise
        """
        if not result.success:
            return False

        if not result.steps:
            return False

        # Check step count constraints
        num_steps = result.num_steps
        if num_steps < self.config.min_steps or num_steps > self.config.max_steps:
            return False

        return True


class TimingDeciderProtocol(Protocol):
    """Protocol for timing decider implementations."""

    name: str

    def decide(self, message: TimingMessage) -> TimingDecision:
        """
        Decide whether to call a tool.

        Args:
            message: TimingMessage with conversation context

        Returns:
            TimingDecision
        """
        ...


class BaseTimingDecider(ABC):
    """
    Abstract base class for timing deciders.

    Provides common functionality and enforces interface.
    """

    name: str = "base_timing_decider"

    def __init__(self, config: TimingConfig):
        """
        Initialize timing decider with configuration.

        Args:
            config: TimingConfig instance
        """
        self.config = config

    @classmethod
    def from_config(cls, config: TimingConfig, **kwargs) -> "BaseTimingDecider":
        """
        Create timing decider from configuration.

        Args:
            config: TimingConfig instance
            **kwargs: Additional resources

        Returns:
            Initialized timing decider
        """
        return cls(config=config, **kwargs)

    @abstractmethod
    def decide(self, message: TimingMessage) -> TimingDecision:
        """
        Make timing decision.

        Must be implemented by subclasses.

        Args:
            message: TimingMessage

        Returns:
            TimingDecision
        """
        pass
