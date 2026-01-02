# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Base scheduling policy interface."""

from abc import ABC, abstractmethod

from ..types import ExecutionInstance, RequestMetadata, SchedulingDecision


class SchedulingPolicy(ABC):
    """Base class for scheduling policies."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def schedule(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """
        Schedule requests to instances.

        Args:
            requests: List of pending requests to schedule
            instances: List of available execution instances

        Returns:
            List of scheduling decisions
        """
        pass

    @abstractmethod
    def prioritize(self, requests: list[RequestMetadata]) -> list[RequestMetadata]:
        """
        Prioritize requests for scheduling.

        Args:
            requests: List of requests to prioritize

        Returns:
            Sorted list of requests by priority
        """
        pass
