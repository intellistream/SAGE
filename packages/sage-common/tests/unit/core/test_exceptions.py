"""
Tests for sage.common.core.exceptions

Tests the exception class hierarchy.
"""

import pytest
from sage.common.core.exceptions import (
    KernelError,
    SchedulingError,
    FaultToleranceError,
    ResourceAllocationError,
    RecoveryError,
    CheckpointError,
    PlacementError,
)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy"""

    def test_kernel_error_is_exception(self):
        """Test that KernelError is an Exception"""
        assert issubclass(KernelError, Exception)

    def test_scheduling_error_hierarchy(self):
        """Test SchedulingError is subclass of KernelError"""
        assert issubclass(SchedulingError, KernelError)
        assert issubclass(SchedulingError, Exception)

    def test_fault_tolerance_error_hierarchy(self):
        """Test FaultToleranceError is subclass of KernelError"""
        assert issubclass(FaultToleranceError, KernelError)
        assert issubclass(FaultToleranceError, Exception)

    def test_resource_allocation_error_hierarchy(self):
        """Test ResourceAllocationError is subclass of SchedulingError"""
        assert issubclass(ResourceAllocationError, SchedulingError)
        assert issubclass(ResourceAllocationError, KernelError)
        assert issubclass(ResourceAllocationError, Exception)

    def test_recovery_error_hierarchy(self):
        """Test RecoveryError is subclass of FaultToleranceError"""
        assert issubclass(RecoveryError, FaultToleranceError)
        assert issubclass(RecoveryError, KernelError)
        assert issubclass(RecoveryError, Exception)

    def test_checkpoint_error_hierarchy(self):
        """Test CheckpointError is subclass of FaultToleranceError"""
        assert issubclass(CheckpointError, FaultToleranceError)
        assert issubclass(CheckpointError, KernelError)
        assert issubclass(CheckpointError, Exception)

    def test_placement_error_hierarchy(self):
        """Test PlacementError is subclass of SchedulingError"""
        assert issubclass(PlacementError, SchedulingError)
        assert issubclass(PlacementError, KernelError)
        assert issubclass(PlacementError, Exception)


class TestExceptionRaising:
    """Tests for raising and catching exceptions"""

    def test_raise_kernel_error(self):
        """Test raising KernelError"""
        with pytest.raises(KernelError, match="test error"):
            raise KernelError("test error")

    def test_raise_scheduling_error(self):
        """Test raising SchedulingError"""
        with pytest.raises(SchedulingError, match="scheduling failed"):
            raise SchedulingError("scheduling failed")

    def test_raise_fault_tolerance_error(self):
        """Test raising FaultToleranceError"""
        with pytest.raises(FaultToleranceError, match="fault detected"):
            raise FaultToleranceError("fault detected")

    def test_raise_resource_allocation_error(self):
        """Test raising ResourceAllocationError"""
        with pytest.raises(ResourceAllocationError, match="no resources"):
            raise ResourceAllocationError("no resources")

    def test_raise_recovery_error(self):
        """Test raising RecoveryError"""
        with pytest.raises(RecoveryError, match="recovery failed"):
            raise RecoveryError("recovery failed")

    def test_raise_checkpoint_error(self):
        """Test raising CheckpointError"""
        with pytest.raises(CheckpointError, match="checkpoint failed"):
            raise CheckpointError("checkpoint failed")

    def test_raise_placement_error(self):
        """Test raising PlacementError"""
        with pytest.raises(PlacementError, match="placement failed"):
            raise PlacementError("placement failed")


class TestExceptionCatching:
    """Tests for catching exceptions with hierarchy"""

    def test_catch_scheduling_as_kernel_error(self):
        """Test catching SchedulingError as KernelError"""
        with pytest.raises(KernelError):
            raise SchedulingError("test")

    def test_catch_resource_allocation_as_scheduling(self):
        """Test catching ResourceAllocationError as SchedulingError"""
        with pytest.raises(SchedulingError):
            raise ResourceAllocationError("test")

    def test_catch_recovery_as_fault_tolerance(self):
        """Test catching RecoveryError as FaultToleranceError"""
        with pytest.raises(FaultToleranceError):
            raise RecoveryError("test")

    def test_exception_with_message(self):
        """Test exception messages are preserved"""
        try:
            raise KernelError("custom message")
        except KernelError as e:
            assert str(e) == "custom message"

    def test_exception_with_args(self):
        """Test exception with multiple arguments"""
        try:
            raise SchedulingError("error", "details", 42)
        except SchedulingError as e:
            assert e.args == ("error", "details", 42)
