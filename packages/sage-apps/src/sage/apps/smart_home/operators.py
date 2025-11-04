"""
SAGE Operators for Smart Home System

Implements IoT device operators for smart home automation.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from sage.common.core import BatchFunction, MapFunction, SinkFunction


class DeviceType(Enum):
    """IoT device types."""

    ROBOT = "robot"
    WASHER = "washer"
    DRYER = "dryer"
    HUMIDITY_SENSOR = "humidity_sensor"
    MOTION_SENSOR = "motion_sensor"


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DeviceEvent:
    """Event emitted by a device."""

    event_id: int
    device_id: str
    device_type: DeviceType
    event_type: str
    timestamp: str
    data: dict[str, Any]


class LaundryWorkflowSource(BatchFunction):
    """
    BatchFunction source that generates laundry workflow tasks.

    Emits a sequence of tasks for the automated laundry workflow.
    """

    def __init__(self, num_cycles: int = 1, **kwargs) -> None:
        super().__init__(**kwargs)
        self.num_cycles = num_cycles
        self.current_cycle = 0
        self.step = 0

        # Define workflow steps
        self.steps = [
            {
                "task": "check_environment",
                "device": "humid_sensor_001",
                "description": "Check humidity and environment",
            },
            {
                "task": "collect_laundry",
                "device": "robot_001",
                "description": "Robot collects laundry from basket",
                "params": {"from": "basket", "to": "washer"},
            },
            {
                "task": "wash",
                "device": "washer_001",
                "description": "Wash laundry",
                "duration": 2.0,
            },
            {
                "task": "move_to_dryer",
                "device": "robot_001",
                "description": "Robot moves laundry to dryer",
                "params": {"from": "washer", "to": "dryer"},
            },
            {
                "task": "dry",
                "device": "dryer_001",
                "description": "Dry laundry",
                "duration": 1.5,
            },
            {
                "task": "move_to_rack",
                "device": "robot_001",
                "description": "Robot moves laundry to drying rack",
                "params": {"from": "dryer", "to": "drying_rack"},
            },
        ]

    def execute(self) -> dict[str, Any] | None:
        """Generate next workflow task."""
        if self.current_cycle >= self.num_cycles:
            return None

        if self.step >= len(self.steps):
            self.current_cycle += 1
            self.step = 0
            if self.current_cycle >= self.num_cycles:
                return None

        task = self.steps[self.step].copy()
        task["cycle"] = self.current_cycle + 1
        task["step"] = self.step + 1
        task["total_steps"] = len(self.steps)

        self.step += 1
        return task


class DeviceExecutor(MapFunction):
    """
    MapFunction that simulates device task execution.
    """

    # Humidity sensor constants
    MIN_HUMIDITY = 30.0
    MAX_HUMIDITY = 80.0

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.event_counter = 0

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """Execute device task."""
        device_id = data.get("device", "unknown")
        task = data.get("task", "unknown")
        description = data.get("description", "")
        duration = data.get("duration", 0.5)

        # Log task start
        icon = {
            "robot_001": "🤖",
            "washer_001": "🧺",
            "dryer_001": "💨",
            "humid_sensor_001": "📊",
        }.get(device_id, "📱")

        self.logger.info(f"{icon} {device_id}: {description}")

        # Simulate task execution
        time.sleep(duration)

        # Generate result
        self.event_counter += 1
        result = data.copy()
        result["status"] = TaskStatus.COMPLETED.value
        result["completed_at"] = datetime.now().isoformat()
        result["event_id"] = self.event_counter

        # Add device-specific results
        if "humid_sensor" in device_id:
            result["humidity"] = random.uniform(self.MIN_HUMIDITY, self.MAX_HUMIDITY)
        elif task in ["wash", "dry"]:
            result["success"] = True

        return result


class EnvironmentMonitor(MapFunction):
    """
    MapFunction that monitors environmental conditions.
    """

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """Monitor and log environmental conditions."""
        if data.get("task") == "check_environment":
            humidity = data.get("humidity", 0)
            self.logger.info(f"   📊 Current humidity: {humidity:.1f}%")

            # Check if conditions are suitable
            if 40 <= humidity <= 70:
                data["environment_status"] = "optimal"
            elif humidity < 40:
                data["environment_status"] = "too_dry"
            else:
                data["environment_status"] = "too_humid"

        return data


class WorkflowProgressSink(SinkFunction):
    """
    SinkFunction that tracks and displays workflow progress.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tasks_completed = 0
        self.start_time = time.time()
        self.total_steps = 0

    def execute(self, data: dict[str, Any]) -> None:
        """Track task completion."""
        self.tasks_completed += 1
        step = data.get("step", 0)
        total = data.get("total_steps", 0)
        cycle = data.get("cycle", 1)

        if total > 0:
            self.total_steps = total

        # Log progress
        if step == total:
            self.logger.info(f"✓ Cycle {cycle} completed ({step}/{total} steps)")

    def close(self) -> None:
        """Display final summary."""
        elapsed = time.time() - self.start_time

        print("\n" + "=" * 70)
        print("✅ Smart Home Workflow Summary")
        print("=" * 70)
        print(f"   Total tasks completed: {self.tasks_completed}")
        print(f"   Total time: {elapsed:.2f}s")
        print(f"   Average time per task: {elapsed / max(self.tasks_completed, 1):.2f}s")
        print("=" * 70 + "\n")


class EventLogSink(SinkFunction):
    """
    SinkFunction that logs all device events.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.events: list[dict[str, Any]] = []

    def execute(self, data: dict[str, Any]) -> None:
        """Log device event."""
        self.events.append(data)

    def close(self) -> None:
        """Display event log summary."""
        print("\n📝 Event Log Summary:")
        print(f"   Total events: {len(self.events)}")

        # Group by device
        by_device: dict[str, int] = {}
        for event in self.events:
            device = event.get("device", "unknown")
            by_device[device] = by_device.get(device, 0) + 1

        print("   Events by device:")
        for device, count in sorted(by_device.items()):
            icon = {
                "robot_001": "🤖",
                "washer_001": "🧺",
                "dryer_001": "💨",
                "humid_sensor_001": "📊",
            }.get(device, "📱")
            print(f"      {icon} {device}: {count} events")
