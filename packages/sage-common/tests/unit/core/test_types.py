"""
Tests for sage.common.core.types

Tests the core type definitions, enums, and type aliases.
"""

import pytest
from sage.common.core.types import (
    ExecutionMode,
    JobStatus,
    TaskStatus,
    TaskID,
    ServiceID,
    NodeID,
    QueueID,
    JobID,
    T,
    TaskType,
    ServiceType,
)


class TestExecutionMode:
    """Tests for ExecutionMode enum"""

    def test_execution_mode_values(self):
        """Test that ExecutionMode has the expected values"""
        assert ExecutionMode.LOCAL.value == "local"
        assert ExecutionMode.REMOTE.value == "remote"
        assert ExecutionMode.HYBRID.value == "hybrid"

    def test_execution_mode_members(self):
        """Test that all ExecutionMode members exist"""
        assert hasattr(ExecutionMode, "LOCAL")
        assert hasattr(ExecutionMode, "REMOTE")
        assert hasattr(ExecutionMode, "HYBRID")

    def test_execution_mode_count(self):
        """Test that ExecutionMode has exactly 3 members"""
        assert len(ExecutionMode) == 3


class TestTaskStatus:
    """Tests for TaskStatus enum"""

    def test_task_status_values(self):
        """Test that TaskStatus has the expected values"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.STOPPED.value == "stopped"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.COMPLETED.value == "completed"

    def test_task_status_members(self):
        """Test that all TaskStatus members exist"""
        assert hasattr(TaskStatus, "PENDING")
        assert hasattr(TaskStatus, "RUNNING")
        assert hasattr(TaskStatus, "STOPPED")
        assert hasattr(TaskStatus, "FAILED")
        assert hasattr(TaskStatus, "COMPLETED")

    def test_task_status_count(self):
        """Test that TaskStatus has exactly 5 members"""
        assert len(TaskStatus) == 5

    def test_task_status_comparison(self):
        """Test that TaskStatus members can be compared"""
        assert TaskStatus.PENDING == TaskStatus.PENDING
        assert TaskStatus.PENDING != TaskStatus.RUNNING


class TestJobStatus:
    """Tests for JobStatus enum"""

    def test_job_status_values(self):
        """Test that JobStatus has the expected values"""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.STOPPED.value == "stopped"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.DELETED.value == "deleted"

    def test_job_status_members(self):
        """Test that all JobStatus members exist"""
        assert hasattr(JobStatus, "PENDING")
        assert hasattr(JobStatus, "RUNNING")
        assert hasattr(JobStatus, "STOPPED")
        assert hasattr(JobStatus, "FAILED")
        assert hasattr(JobStatus, "COMPLETED")
        assert hasattr(JobStatus, "DELETED")

    def test_job_status_count(self):
        """Test that JobStatus has exactly 6 members"""
        assert len(JobStatus) == 6


class TestTypeAliases:
    """Tests for type aliases"""

    def test_id_type_aliases_are_str(self):
        """Test that ID type aliases are strings"""
        # These are type aliases, so we just verify the annotation exists
        assert TaskID == str
        assert ServiceID == str
        assert NodeID == str
        assert QueueID == str
        assert JobID == str

    def test_id_usage(self):
        """Test that ID aliases can be used in type annotations"""
        # Runtime test that these types work as expected
        task_id: TaskID = "task_123"
        service_id: ServiceID = "service_456"
        node_id: NodeID = "node_789"
        queue_id: QueueID = "queue_abc"
        job_id: JobID = "job_xyz"

        assert isinstance(task_id, str)
        assert isinstance(service_id, str)
        assert isinstance(node_id, str)
        assert isinstance(queue_id, str)
        assert isinstance(job_id, str)


class TestTypeVars:
    """Tests for generic type variables"""

    def test_type_vars_exist(self):
        """Test that type variables are defined"""
        from typing import TypeVar

        assert isinstance(T, TypeVar)
        assert isinstance(TaskType, TypeVar)
        assert isinstance(ServiceType, TypeVar)

    def test_type_var_names(self):
        """Test that type variables have the expected names"""
        assert T.__name__ == "T"
        assert TaskType.__name__ == "TaskType"
        assert ServiceType.__name__ == "ServiceType"
