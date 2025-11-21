"""Unit tests for Smart Home Application

Tests for sage.apps.smart_home module
"""

import pytest

from sage.apps.smart_home.operators import (
    DeviceEvent,
    DeviceExecutor,
    DeviceType,
    EnvironmentMonitor,
    EventLogSink,
    LaundryWorkflowSource,
    TaskStatus,
    WorkflowProgressSink,
)


class TestDeviceEvent:
    """Test DeviceEvent dataclass"""

    def test_event_creation(self):
        """Test creating a device event"""
        event = DeviceEvent(
            event_id=1,
            device_id="robot_01",
            device_type=DeviceType.ROBOT,
            event_type="task_started",
            timestamp="2024-01-15T10:00:00",
            data={"task": "pickup_laundry", "status": "running"},
        )

        assert event.event_id == 1
        assert event.device_id == "robot_01"
        assert event.device_type == DeviceType.ROBOT
        assert event.event_type == "task_started"
        assert "task" in event.data

    def test_event_with_sensor_data(self):
        """Test event with sensor data"""
        event = DeviceEvent(
            event_id=2,
            device_id="humidity_01",
            device_type=DeviceType.HUMIDITY_SENSOR,
            event_type="reading",
            timestamp="2024-01-15T10:00:01",
            data={"humidity": 65.0, "temperature": 22.5},
        )

        assert event.device_type == DeviceType.HUMIDITY_SENSOR
        assert event.data["humidity"] == 65.0


class TestDeviceType:
    """Test DeviceType enum"""

    def test_device_types(self):
        """Test all device types are defined"""
        assert DeviceType.ROBOT.value == "robot"
        assert DeviceType.WASHER.value == "washer"
        assert DeviceType.DRYER.value == "dryer"
        assert DeviceType.HUMIDITY_SENSOR.value == "humidity_sensor"
        assert DeviceType.MOTION_SENSOR.value == "motion_sensor"


class TestTaskStatus:
    """Test TaskStatus enum"""

    def test_task_statuses(self):
        """Test all task statuses are defined"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"


class TestLaundryWorkflowSource:
    """Test LaundryWorkflowSource operator"""

    def test_source_creation(self):
        """Test creating laundry workflow source"""
        source = LaundryWorkflowSource(num_cycles=2)

        assert source.num_cycles == 2
        assert source.current_cycle == 0
        assert source.step == 0

    def test_source_generates_workflow_tasks(self):
        """Test source generates workflow tasks"""
        source = LaundryWorkflowSource(num_cycles=1)

        # Execute to get first task
        task = source.execute()

        # Should generate workflow task
        assert task is not None
        assert "task" in task
        assert "device" in task
        assert "cycle" in task
        assert task["cycle"] == 1

    def test_source_workflow_steps(self):
        """Test source generates all workflow steps"""
        source = LaundryWorkflowSource(num_cycles=1)

        tasks = []
        while True:
            task = source.execute()
            if task is None:
                break
            tasks.append(task)

        # Should have 6 steps in workflow
        assert len(tasks) == 6
        assert tasks[0]["task"] == "check_environment"
        assert tasks[1]["task"] == "collect_laundry"
        assert tasks[2]["task"] == "wash"

    def test_source_with_multiple_cycles(self):
        """Test source with multiple laundry cycles"""
        source = LaundryWorkflowSource(num_cycles=2)

        tasks = []
        while True:
            task = source.execute()
            if task is None:
                break
            tasks.append(task)

        # Should have 6 steps * 2 cycles = 12 tasks
        assert len(tasks) == 12
        assert tasks[0]["cycle"] == 1
        assert tasks[6]["cycle"] == 2


class TestDeviceExecutor:
    """Test DeviceExecutor operator"""

    def test_executor_creation(self):
        """Test creating device executor"""
        executor = DeviceExecutor()

        assert executor.event_counter == 0

    def test_execute_robot_task(self):
        """Test executing robot task"""
        executor = DeviceExecutor()

        task_data = {
            "task": "collect_laundry",
            "device": "robot_001",
            "description": "Robot collects laundry",
            "params": {"from": "basket", "to": "washer"},
            "duration": 0.01,
        }

        result = executor.execute(task_data)
        assert result is not None
        assert result["status"] == TaskStatus.COMPLETED.value
        assert "completed_at" in result
        assert "event_id" in result

    def test_execute_washer_task(self):
        """Test executing washer task"""
        executor = DeviceExecutor()

        task_data = {
            "task": "wash",
            "device": "washer_001",
            "description": "Wash laundry",
            "duration": 0.01,
        }

        result = executor.execute(task_data)
        assert result is not None
        assert result["status"] == TaskStatus.COMPLETED.value
        assert result["success"] is True

    def test_execute_dryer_task(self):
        """Test executing dryer task"""
        executor = DeviceExecutor()

        task_data = {
            "task": "dry",
            "device": "dryer_001",
            "description": "Dry laundry",
            "duration": 0.01,
        }

        result = executor.execute(task_data)
        assert result is not None
        assert result["status"] == TaskStatus.COMPLETED.value
        assert result["success"] is True

    def test_execute_humidity_sensor(self):
        """Test executing humidity sensor task"""
        executor = DeviceExecutor()

        task_data = {
            "task": "check_environment",
            "device": "humid_sensor_001",
            "description": "Check humidity",
            "duration": 0.01,
        }

        result = executor.execute(task_data)
        assert result is not None
        assert "humidity" in result
        assert DeviceExecutor.MIN_HUMIDITY <= result["humidity"] <= DeviceExecutor.MAX_HUMIDITY


class TestEnvironmentMonitor:
    """Test EnvironmentMonitor operator"""

    def test_monitor_creation(self):
        """Test creating environment monitor"""
        monitor = EnvironmentMonitor()

        assert monitor is not None

    def test_monitor_check_environment_optimal(self):
        """Test monitor with optimal humidity"""
        monitor = EnvironmentMonitor()

        task_data = {"task": "check_environment", "humidity": 55.0}

        result = monitor.execute(task_data)
        assert result is not None
        assert result["environment_status"] == "optimal"

    def test_monitor_check_environment_too_dry(self):
        """Test monitor with low humidity"""
        monitor = EnvironmentMonitor()

        task_data = {"task": "check_environment", "humidity": 35.0}

        result = monitor.execute(task_data)
        assert result is not None
        assert result["environment_status"] == "too_dry"

    def test_monitor_check_environment_too_humid(self):
        """Test monitor with high humidity"""
        monitor = EnvironmentMonitor()

        task_data = {"task": "check_environment", "humidity": 75.0}

        result = monitor.execute(task_data)
        assert result is not None
        assert result["environment_status"] == "too_humid"

    def test_monitor_non_environment_task(self):
        """Test monitor passes through non-environment tasks"""
        monitor = EnvironmentMonitor()

        task_data = {"task": "wash", "device": "washer_001"}

        result = monitor.execute(task_data)
        assert result is not None
        assert result["task"] == "wash"


class TestWorkflowProgressSink:
    """Test WorkflowProgressSink operator"""

    def test_sink_creation(self):
        """Test creating workflow progress sink"""
        sink = WorkflowProgressSink()

        assert sink.tasks_completed == 0
        assert sink.total_steps == 0

    def test_sink_collects_task(self):
        """Test sink collects workflow task"""
        sink = WorkflowProgressSink()

        task_data = {
            "task": "collect_laundry",
            "device": "robot_001",
            "cycle": 1,
            "step": 2,
            "total_steps": 6,
        }

        sink.execute(task_data)
        assert sink.tasks_completed == 1
        assert sink.total_steps == 6

    def test_sink_tracks_multiple_tasks(self):
        """Test sink tracks multiple workflow tasks"""
        sink = WorkflowProgressSink()

        tasks = [
            {"task": "check_environment", "cycle": 1, "step": i + 1, "total_steps": 6}
            for i in range(6)
        ]

        for task in tasks:
            sink.execute(task)

        assert sink.tasks_completed == 6


class TestEventLogSink:
    """Test EventLogSink operator"""

    def test_sink_creation(self):
        """Test creating event log sink"""
        sink = EventLogSink()

        assert len(sink.events) == 0

    def test_sink_logs_event(self):
        """Test sink logs device event"""
        sink = EventLogSink()

        event_data = {
            "task": "wash",
            "device": "washer_001",
            "status": TaskStatus.COMPLETED.value,
        }

        sink.execute(event_data)
        assert len(sink.events) == 1
        assert sink.events[0]["device"] == "washer_001"

    def test_sink_logs_multiple_events(self):
        """Test sink logs multiple events"""
        sink = EventLogSink()

        events = [{"task": f"task_{i}", "device": "robot_001", "step": i} for i in range(10)]

        for event in events:
            sink.execute(event)

        assert len(sink.events) == 10


@pytest.mark.integration
class TestSmartHomePipeline:
    """Integration tests for smart home laundry workflow"""

    def test_workflow_execution(self):
        """Test complete laundry workflow execution"""
        # Create operators
        source = LaundryWorkflowSource(num_cycles=1)
        executor = DeviceExecutor()
        monitor = EnvironmentMonitor()
        progress_sink = WorkflowProgressSink()
        log_sink = EventLogSink()

        # Execute workflow
        while True:
            task = source.execute()
            if task is None:
                break

            # Execute task
            result = executor.execute(task)

            # Monitor environment
            monitored = monitor.execute(result)

            # Collect results
            progress_sink.execute(monitored)
            log_sink.execute(monitored)

        # Verify completion
        assert progress_sink.tasks_completed == 6
        assert len(log_sink.events) == 6

    @pytest.mark.skip(reason="Pipeline infrastructure test")
    def test_pipeline_creation(self):
        """Test creating the smart home pipeline"""
        # Placeholder for pipeline creation test
        # Would require actual pipeline module
        pass
