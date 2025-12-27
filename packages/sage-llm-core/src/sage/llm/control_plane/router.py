# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Request router for the Control Plane."""

import hashlib
import random

from .types import ExecutionInstance, RequestMetadata, SchedulingDecision


class RequestRouter:
    """Routes requests to execution instances."""

    def __init__(self, routing_strategy: str = "load_balanced"):
        """
        Initialize request router.

        Args:
            routing_strategy: Strategy to use for routing
                - "load_balanced": Route to least loaded instance
                - "round_robin": Round-robin across instances
                - "random": Random selection
                - "affinity": User/session affinity based routing
                - "locality": Prefer instances with cached prefixes
                - "topology_aware": Topology-aware routing (prefers same machine/NVLINK)
        """
        self.routing_strategy = routing_strategy
        self.round_robin_index = 0
        self.affinity_map: dict[str, str] = {}  # user_id -> instance_id
        self.last_instance_map: dict[str, str] = {}  # request -> last instance (for topology)

    def route(
        self,
        request: RequestMetadata,
        instances: list[ExecutionInstance],
        decision: SchedulingDecision | None = None,
    ) -> ExecutionInstance | None:
        """
        Route a request to an execution instance.

        Args:
            request: Request to route
            instances: Available execution instances
            decision: Optional scheduling decision with target instance

        Returns:
            Selected execution instance or None if no instance available
        """

        # Filter available instances
        available = [i for i in instances if i.can_accept_request]
        if not available:
            return None

        # If decision specifies target instance, use it
        if decision and decision.target_instance_id:
            for instance in available:
                if instance.instance_id == decision.target_instance_id:
                    return instance

        # Apply routing strategy
        if self.routing_strategy == "load_balanced":
            return self._load_balanced_route(available)
        elif self.routing_strategy == "round_robin":
            return self._round_robin_route(available)
        elif self.routing_strategy == "random":
            return self._random_route(available)
        elif self.routing_strategy == "affinity":
            return self._affinity_route(request, available)
        elif self.routing_strategy == "locality":
            return self._locality_route(request, available)
        elif self.routing_strategy == "topology_aware":
            return self._topology_aware_route(request, available)
        else:
            return self._load_balanced_route(available)

    def _load_balanced_route(
        self,
        instances: list[ExecutionInstance],
    ) -> ExecutionInstance:
        """Route to least loaded instance."""
        return min(instances, key=lambda i: i.current_load)

    def _round_robin_route(
        self,
        instances: list[ExecutionInstance],
    ) -> ExecutionInstance:
        """Route in round-robin fashion."""
        instance = instances[self.round_robin_index % len(instances)]
        self.round_robin_index += 1
        return instance

    def _random_route(
        self,
        instances: list[ExecutionInstance],
    ) -> ExecutionInstance:
        """Route randomly."""
        return random.choice(instances)

    def _affinity_route(
        self,
        request: RequestMetadata,
        instances: list[ExecutionInstance],
    ) -> ExecutionInstance:
        """Route with user affinity."""

        if not request.user_id:
            return self._load_balanced_route(instances)

        # Check if user has affinity to an instance
        if request.user_id in self.affinity_map:
            target_id = self.affinity_map[request.user_id]
            for instance in instances:
                if instance.instance_id == target_id:
                    return instance

        # Create new affinity
        instance = self._load_balanced_route(instances)
        self.affinity_map[request.user_id] = instance.instance_id
        return instance

    def _locality_route(
        self,
        request: RequestMetadata,
        instances: list[ExecutionInstance],
    ) -> ExecutionInstance:
        """Route based on locality (e.g., cached prefixes)."""

        # Hash request to determine preferred instance
        # This helps with prefix caching - similar requests go to same instance
        request_hash = hashlib.md5(f"{request.model_name}:{request.user_id}".encode()).hexdigest()

        index = int(request_hash[:8], 16) % len(instances)
        return instances[index]

    def _topology_aware_route(
        self,
        request: RequestMetadata,
        instances: list[ExecutionInstance],
    ) -> ExecutionInstance:
        """
        Route based on GPU topology awareness.

        Prefers instances with high affinity (same machine, NVLINK connected).
        If request has preferred_instance_id or prior instance, tries to route
        to instances with good topology affinity to minimize communication cost.

        Args:
            request: Request metadata
            instances: Available instances

        Returns:
            Best instance based on topology
        """
        # Check if request has a preferred instance or last instance
        preferred_instance = None

        if request.preferred_instance_id:
            # Look for the preferred instance
            for inst in instances:
                if inst.instance_id == request.preferred_instance_id:
                    preferred_instance = inst
                    break

        # If no preferred instance, check if this user/request had a previous instance
        if not preferred_instance and request.user_id:
            last_instance_id = self.last_instance_map.get(request.user_id)
            if last_instance_id:
                for inst in instances:
                    if inst.instance_id == last_instance_id:
                        preferred_instance = inst
                        break

        # If we have a preferred instance, try to find instances with good affinity
        if preferred_instance:
            # Filter instances on the same machine
            same_machine = [
                inst
                for inst in instances
                if inst.machine_id and inst.machine_id == preferred_instance.machine_id
            ]

            if same_machine:
                # Among same-machine instances, prefer NVLINK connected or least loaded
                nvlink_connected = [
                    inst
                    for inst in same_machine
                    if inst.instance_id in preferred_instance.nvlink_peers
                ]

                if nvlink_connected:
                    # Choose least loaded NVLINK-connected instance
                    selected = min(nvlink_connected, key=lambda i: i.current_load)
                else:
                    # Choose least loaded same-machine instance
                    selected = min(same_machine, key=lambda i: i.current_load)
            else:
                # No same-machine instances, fall back to load balancing
                selected = self._load_balanced_route(instances)
        else:
            # No preferred instance, use load balancing
            selected = self._load_balanced_route(instances)

        # Update last instance for this user
        if request.user_id:
            self.last_instance_map[request.user_id] = selected.instance_id

        return selected

    def update_affinity(self, user_id: str, instance_id: str):
        """Update user affinity mapping."""
        self.affinity_map[user_id] = instance_id

    def clear_affinity(self, user_id: str | None = None):
        """Clear affinity mapping for a user or all users."""
        if user_id:
            self.affinity_map.pop(user_id, None)
        else:
            self.affinity_map.clear()


class LoadBalancer:
    """Advanced load balancer with multiple algorithms."""

    def __init__(self):
        self.request_counts: dict[str, int] = {}
        self.latency_history: dict[str, list[float]] = {}

    def select_instance(
        self,
        instances: list[ExecutionInstance],
        algorithm: str = "weighted_round_robin",
    ) -> ExecutionInstance | None:
        """
        Select instance using specified algorithm.

        Args:
            instances: Available instances
            algorithm: Load balancing algorithm
                - "weighted_round_robin": Weight by available capacity
                - "least_connections": Prefer instance with fewest active requests
                - "least_response_time": Prefer instance with lowest latency
                - "power_of_two": Random choice between two random instances
        """

        available = [i for i in instances if i.can_accept_request]
        if not available:
            return None

        if algorithm == "weighted_round_robin":
            return self._weighted_round_robin(available)
        elif algorithm == "least_connections":
            return self._least_connections(available)
        elif algorithm == "least_response_time":
            return self._least_response_time(available)
        elif algorithm == "power_of_two":
            return self._power_of_two(available)
        else:
            return min(available, key=lambda i: i.current_load)

    def _weighted_round_robin(
        self,
        instances: list[ExecutionInstance],
    ) -> ExecutionInstance:
        """Weighted round-robin based on available capacity."""

        weights = [i.available_capacity for i in instances]
        total_weight = sum(weights)

        if total_weight == 0:
            return instances[0]

        # Random selection weighted by capacity
        rand = random.uniform(0, total_weight)
        cumulative = 0.0

        for instance, weight in zip(instances, weights, strict=False):
            cumulative += weight
            if rand <= cumulative:
                return instance

        return instances[-1]

    def _least_connections(
        self,
        instances: list[ExecutionInstance],
    ) -> ExecutionInstance:
        """Select instance with fewest active requests."""
        return min(instances, key=lambda i: i.active_requests)

    def _least_response_time(
        self,
        instances: list[ExecutionInstance],
    ) -> ExecutionInstance:
        """Select instance with lowest average latency."""
        return min(instances, key=lambda i: i.avg_latency_ms)

    def _power_of_two(
        self,
        instances: list[ExecutionInstance],
    ) -> ExecutionInstance:
        """Power of two choices algorithm."""

        if len(instances) <= 2:
            return min(instances, key=lambda i: i.current_load)

        # Randomly select two instances
        choices = random.sample(instances, 2)

        # Return the one with lower load
        return min(choices, key=lambda i: i.current_load)

    def record_request(self, instance_id: str):
        """Record request sent to instance."""
        self.request_counts[instance_id] = self.request_counts.get(instance_id, 0) + 1

    def record_latency(self, instance_id: str, latency_ms: float):
        """Record latency for instance."""
        if instance_id not in self.latency_history:
            self.latency_history[instance_id] = []

        self.latency_history[instance_id].append(latency_ms)

        # Keep only last 100 samples
        if len(self.latency_history[instance_id]) > 100:
            self.latency_history[instance_id].pop(0)

    def get_stats(self, instance_id: str) -> dict[str, float]:
        """Get statistics for an instance."""
        latencies = self.latency_history.get(instance_id, [])
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        return {
            "request_count": self.request_counts.get(instance_id, 0),
            "avg_latency_ms": avg_latency,
        }
