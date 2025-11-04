"""
SAGE Operators for Auto-Scaling Chat System

Implements operators for simulated chat system with auto-scaling capabilities.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sage.common.core import BatchFunction, MapFunction, SinkFunction


@dataclass
class UserRequest:
    """Represents a user chat request."""

    request_id: int
    user_id: int
    timestamp: str
    message: str
    processing_time: float = 0.0
    server_id: int | None = None


class UserTrafficSource(BatchFunction):
    """
    BatchFunction source that generates simulated user traffic.

    Simulates variable user load with peaks and valleys.
    """

    # Probability scaling constant for request generation
    PROBABILITY_SCALE = 100.0

    def __init__(
        self,
        duration: int = 30,
        base_rate: int = 5,
        peak_rate: int = 50,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.duration = duration
        self.base_rate = base_rate
        self.peak_rate = peak_rate
        self.start_time = time.time()
        self.request_count = 0

    def execute(self) -> dict[str, Any] | None:
        """Generate user requests based on current load pattern."""
        elapsed = time.time() - self.start_time

        if elapsed >= self.duration:
            return None

        # Simulate traffic pattern: gradual increase, peak, then decrease
        progress = elapsed / self.duration
        if progress < 0.3:
            # Ramp up phase
            rate = self.base_rate + (self.peak_rate - self.base_rate) * (progress / 0.3)
        elif progress < 0.7:
            # Peak phase
            rate = self.peak_rate
        else:
            # Ramp down phase
            rate = self.peak_rate - (self.peak_rate - self.base_rate) * ((progress - 0.7) / 0.3)

        # Determine if we should emit a request based on rate
        # Higher rate = more requests per second
        probability = rate / self.PROBABILITY_SCALE
        if random.random() < probability:
            self.request_count += 1
            return {
                "request_id": self.request_count,
                "user_id": random.randint(1, 1000),
                "timestamp": datetime.now().isoformat(),
                "message": f"User message #{self.request_count}",
                "current_load": int(rate),
            }

        # Small delay to control emission rate
        time.sleep(0.05)
        return None


class LoadBalancer(MapFunction):
    """
    MapFunction that distributes requests across available servers.

    Implements simple round-robin load balancing.
    """

    def __init__(self, initial_servers: int = 2, **kwargs) -> None:
        super().__init__(**kwargs)
        self.num_servers = initial_servers
        self.current_server = 0
        self.server_loads: dict[int, int] = dict.fromkeys(range(initial_servers), 0)

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """Assign request to a server."""
        # Round-robin assignment
        server_id = self.current_server
        self.current_server = (self.current_server + 1) % self.num_servers

        # Update server load
        self.server_loads[server_id] = self.server_loads.get(server_id, 0) + 1

        # Assign to request
        data["server_id"] = server_id
        data["num_servers"] = self.num_servers

        return data

    def scale_servers(self, new_count: int) -> None:
        """Scale number of servers."""
        old_count = self.num_servers
        self.num_servers = new_count

        # Initialize new servers
        for i in range(old_count, new_count):
            self.server_loads[i] = 0

        self.logger.info(f"Scaled servers: {old_count} → {new_count}")


class AutoScaler(MapFunction):
    """
    MapFunction that makes auto-scaling decisions based on load.
    """

    def __init__(
        self,
        scale_up_threshold: int = 30,
        scale_down_threshold: int = 10,
        min_servers: int = 2,
        max_servers: int = 10,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.min_servers = min_servers
        self.max_servers = max_servers
        self.current_servers = min_servers
        self.last_scale_time = time.time()
        self.cooldown = 5.0  # seconds

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """Make scaling decision based on current load."""
        current_load = data.get("current_load", 0)
        now = time.time()

        # Check if we're in cooldown period
        if now - self.last_scale_time < self.cooldown:
            data["scaling_action"] = "cooldown"
            return data

        # Calculate average load per server
        avg_load_per_server = current_load / self.current_servers if self.current_servers > 0 else 0

        scaling_action = "none"

        # Scale up if load is high
        if (
            avg_load_per_server > self.scale_up_threshold
            and self.current_servers < self.max_servers
        ):
            new_servers = min(self.current_servers + 1, self.max_servers)
            scaling_action = "scale_up"
            self.current_servers = new_servers
            self.last_scale_time = now
            self.logger.warning(
                f"⚠️ Scaling Threshold Reached! "
                f"Load: {current_load}, Scaling up to {new_servers} servers"
            )

        # Scale down if load is low
        elif (
            avg_load_per_server < self.scale_down_threshold
            and self.current_servers > self.min_servers
        ):
            new_servers = max(self.current_servers - 1, self.min_servers)
            scaling_action = "scale_down"
            self.current_servers = new_servers
            self.last_scale_time = now
            self.logger.info(f"Scaling down to {new_servers} servers (low load)")

        data["scaling_action"] = scaling_action
        data["total_servers"] = self.current_servers
        data["avg_load_per_server"] = avg_load_per_server

        return data


class RequestProcessor(MapFunction):
    """
    MapFunction that simulates request processing on servers.
    """

    def __init__(self, processing_time: float = 0.1, **kwargs) -> None:
        super().__init__(**kwargs)
        self.processing_time = processing_time

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process request."""
        # Simulate processing time
        time.sleep(random.uniform(0, self.processing_time))

        data["processing_time"] = self.processing_time
        data["processed_at"] = datetime.now().isoformat()

        return data


class MetricsCollector(SinkFunction):
    """
    SinkFunction that collects and displays system metrics.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.total_requests = 0
        self.scaling_events = 0
        self.peak_servers = 0
        self.peak_load = 0
        self.start_time = time.time()
        self.load_history: list[int] = []
        self.server_history: list[int] = []

    def execute(self, data: dict[str, Any]) -> None:
        """Collect metrics from requests."""
        self.total_requests += 1

        current_load = data.get("current_load", 0)
        num_servers = data.get("total_servers", 0)
        scaling_action = data.get("scaling_action", "none")

        # Update peak metrics
        self.peak_load = max(self.peak_load, current_load)
        self.peak_servers = max(self.peak_servers, num_servers)

        # Track scaling events
        if scaling_action in ["scale_up", "scale_down"]:
            self.scaling_events += 1

        # Record history
        self.load_history.append(current_load)
        self.server_history.append(num_servers)

        # Log every 10 requests
        if self.total_requests % 10 == 0:
            self.logger.info(
                f"📊 Load: {current_load:3d} users | "
                f"Servers: {num_servers:2d} | "
                f"Requests: {self.total_requests:4d}"
            )

    def close(self) -> None:
        """Display final metrics summary."""
        elapsed = time.time() - self.start_time

        print("\n" + "=" * 70)
        print("📊 Auto-Scaling System Metrics")
        print("=" * 70)
        print(f"   Total requests processed: {self.total_requests}")
        print(f"   Total duration: {elapsed:.2f}s")
        print(f"   Average throughput: {self.total_requests / elapsed:.2f} req/s")
        print(f"   Peak load: {self.peak_load} concurrent users")
        print(f"   Peak servers: {self.peak_servers}")
        print(f"   Scaling events: {self.scaling_events}")

        if self.load_history:
            avg_load = sum(self.load_history) / len(self.load_history)
            print(f"   Average load: {avg_load:.1f} users")

        if self.server_history:
            avg_servers = sum(self.server_history) / len(self.server_history)
            print(f"   Average servers: {avg_servers:.1f}")

        print("=" * 70 + "\n")


class ScalingEventsSink(SinkFunction):
    """
    SinkFunction that logs all scaling events.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.events: list[dict[str, Any]] = []

    def execute(self, data: dict[str, Any]) -> None:
        """Log scaling events."""
        scaling_action = data.get("scaling_action", "none")
        if scaling_action in ["scale_up", "scale_down"]:
            event = {
                "action": scaling_action,
                "servers": data.get("total_servers", 0),
                "load": data.get("current_load", 0),
                "timestamp": data.get("timestamp", ""),
            }
            self.events.append(event)

    def close(self) -> None:
        """Display scaling events log."""
        if self.events:
            print("\n🔄 Scaling Events:")
            for i, event in enumerate(self.events, 1):
                action_icon = "📈" if event["action"] == "scale_up" else "📉"
                print(
                    f"   {i}. {action_icon} {event['action'].upper()}: "
                    f"{event['servers']} servers (load: {event['load']})"
                )
