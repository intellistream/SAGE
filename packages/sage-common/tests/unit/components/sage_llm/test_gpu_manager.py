# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Unit tests for GPUResourceManager.

Tests the GPU resource manager using mock mode (no actual GPU required).
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

pytest.importorskip(
    "sage.llm.control_plane.gpu_manager",
    reason="sage-llm-core package not available; skip GPU manager tests.",
)

import pytest

from sage.llm.control_plane.gpu_manager import (
    GPUResourceManager,
    GPUStatus,
)

pytest.importorskip(
    "sage.llm.control_plane.gpu_manager",
    reason="sage-llm-core control_plane not available; skip GPU manager tests.",
)


class TestGPUResourceManagerMockMode:
    """Tests for GPUResourceManager in mock mode."""

    def test_init_with_nvml_disabled(self):
        """Test initialization with NVML explicitly disabled."""
        with patch.dict(
            os.environ, {"SAGE_DISABLE_NVML": "true", "SAGE_GPU_MOCK_COUNT": "2"}, clear=False
        ):
            manager = GPUResourceManager()
            try:
                assert manager._mock_mode is True
                assert manager._nvml_available is False
                assert manager._mock_gpu_count == 2
            finally:
                manager.close()

    def test_get_system_status_mock(self):
        """Test getting system status in mock mode."""
        with patch.dict(
            os.environ,
            {
                "SAGE_DISABLE_NVML": "true",
                "SAGE_GPU_MOCK_COUNT": "2",
                "SAGE_GPU_MOCK_MEMORY_GB": "16",
            },
            clear=False,
        ):
            manager = GPUResourceManager()
            try:
                statuses = manager.get_system_status()

                assert len(statuses) == 2
                for i, status in enumerate(statuses):
                    assert status.get("index") == i
                    assert status.get("memory_total_gb") == 16.0
                    assert status.get("is_mock") is True
            finally:
                manager.close()

    def test_check_resource_availability_mock(self):
        """Test checking resource availability in mock mode."""
        with patch.dict(
            os.environ,
            {
                "SAGE_DISABLE_NVML": "true",
                "SAGE_GPU_MOCK_COUNT": "4",
                "SAGE_GPU_MOCK_MEMORY_GB": "24",
            },
            clear=False,
        ):
            manager = GPUResourceManager()
            try:
                # Should find 2 GPUs with 10GB free
                available = manager.check_resource_availability(10.0, count=2)
                assert len(available) == 2

                # Should find 4 GPUs with 20GB free
                available = manager.check_resource_availability(20.0, count=4)
                assert len(available) == 4

                # Cannot find 8 GPUs (only have 4)
                available = manager.check_resource_availability(10.0, count=8)
                assert len(available) == 4  # Returns only available ones
            finally:
                manager.close()

    def test_allocate_and_release_resources(self):
        """Test allocating and releasing GPU resources."""
        with patch.dict(
            os.environ,
            {
                "SAGE_DISABLE_NVML": "true",
                "SAGE_GPU_MOCK_COUNT": "2",
                "SAGE_GPU_MOCK_MEMORY_GB": "24",
            },
            clear=False,
        ):
            manager = GPUResourceManager()
            try:
                # Allocate 10GB on one GPU
                gpu_ids = manager.allocate_resources(10.0, count=1)
                assert len(gpu_ids) == 1
                assert gpu_ids[0] in [0, 1]

                # Check allocation was recorded
                assert manager._allocations.get(gpu_ids[0], 0.0) == 10.0

                # Release resources
                manager.release_resources(gpu_ids, 10.0)

                # Check allocation was cleared
                assert manager._allocations.get(gpu_ids[0], 0.0) == 0.0
            finally:
                manager.close()

    def test_allocate_insufficient_resources_mock(self):
        """Test allocation failure when resources are insufficient in mock mode."""
        with patch.dict(
            os.environ,
            {
                "SAGE_DISABLE_NVML": "true",
                "SAGE_GPU_MOCK_COUNT": "1",
                "SAGE_GPU_MOCK_MEMORY_GB": "8",
            },
            clear=False,
        ):
            manager = GPUResourceManager()
            try:
                # Allocate most of the memory
                manager.allocate_resources(6.0, count=1)

                # Try to allocate more than available - should fail
                with pytest.raises(RuntimeError, match="Insufficient GPU memory"):
                    manager.allocate_resources(6.0, count=1)
            finally:
                manager.close()

    def test_estimate_model_memory(self):
        """Test model memory estimation."""
        with patch.dict(os.environ, {"SAGE_DISABLE_NVML": "true"}, clear=False):
            manager = GPUResourceManager()
            try:
                # Test with known model pattern
                memory_7b = manager.estimate_model_memory("Qwen/Qwen2.5-7B-Instruct")
                assert memory_7b > 0

                # Test with tensor parallel
                memory_7b_tp2 = manager.estimate_model_memory(
                    "Qwen/Qwen2.5-7B-Instruct", tensor_parallel_size=2
                )
                # With TP=2, per-GPU memory should be less
                assert memory_7b_tp2 < memory_7b

                # Test with unknown model (should return overhead)
                memory_unknown = manager.estimate_model_memory("unknown-model")
                assert memory_unknown >= 4.0  # At least overhead
            finally:
                manager.close()

    def test_allocate_zero_or_negative(self):
        """Test allocation with zero or negative values."""
        with patch.dict(os.environ, {"SAGE_DISABLE_NVML": "true"}, clear=False):
            manager = GPUResourceManager()
            try:
                # Zero memory
                result = manager.allocate_resources(0.0, count=1)
                assert result == []

                # Negative memory
                result = manager.allocate_resources(-10.0, count=1)
                assert result == []

                # Zero count
                result = manager.allocate_resources(10.0, count=0)
                assert result == []
            finally:
                manager.close()

    def test_release_zero_or_negative(self):
        """Test release with zero or negative values does nothing."""
        with patch.dict(os.environ, {"SAGE_DISABLE_NVML": "true"}, clear=False):
            manager = GPUResourceManager()
            try:
                # Should not raise
                manager.release_resources([0], 0.0)
                manager.release_resources([0], -10.0)
                manager.release_resources([], 10.0)
            finally:
                manager.close()


class TestGPUStatus:
    """Tests for GPUStatus TypedDict."""

    def test_gpu_status_structure(self):
        """Test GPUStatus TypedDict structure."""
        status: GPUStatus = {
            "index": 0,
            "name": "Mock GPU 0",
            "memory_total_gb": 24.0,
            "memory_used_gb": 8.0,
            "memory_free_gb": 16.0,
            "memory_reserved_gb": 0.0,
            "utilization": 0.0,
            "is_mock": True,
        }

        assert status["index"] == 0
        assert status["name"] == "Mock GPU 0"
        assert status["memory_total_gb"] == 24.0
        assert status["memory_free_gb"] == 16.0
        assert status["is_mock"] is True
