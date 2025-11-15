"""
Test suite for sage.kernels.runtime.distributed.ray module

Tests Ray integration and initialization functions.
"""

from unittest.mock import patch

import pytest

from sage.kernel.utils.ray.ray_utils import (
    ensure_ray_initialized,
    is_distributed_environment,
)

# Mark tests that need mock updates as expected to fail temporarily
needs_mock_update = pytest.mark.xfail(
    reason="Mock assertions need update to match actual implementation"
)


class TestRayIntegration:
    """Test class for Ray integration functionality"""

    @pytest.mark.unit
    @pytest.mark.ray
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ensure_ray_initialized_not_initialized(self, mock_ray):
        """Test ensure_ray_initialized when Ray is not initialized"""
        # Configure mocks
        mock_ray.is_initialized.return_value = False
        mock_ray.init.return_value = None

        # Call function
        ensure_ray_initialized()

        # Verify Ray initialization attempts
        mock_ray.is_initialized.assert_called_once()
        mock_ray.init.assert_called_once()

        # Check that init was called with ignore_reinit_error and expected parameters
        call_args = mock_ray.init.call_args
        assert call_args is not None
        assert "ignore_reinit_error" in call_args.kwargs
        assert call_args.kwargs["ignore_reinit_error"] is True
        assert "num_cpus" in call_args.kwargs
        assert call_args.kwargs["num_cpus"] == 16
        assert "log_to_driver" in call_args.kwargs
        assert call_args.kwargs["log_to_driver"] is False
        # runtime_env should be included with default sage config

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ensure_ray_initialized_already_initialized(self, mock_ray):
        """Test ensure_ray_initialized when Ray is already initialized"""
        # Configure mocks
        mock_ray.is_initialized.return_value = True

        # Call function
        ensure_ray_initialized()

        # Verify Ray was checked but not initialized
        mock_ray.is_initialized.assert_called_once()
        mock_ray.init.assert_not_called()

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ensure_ray_initialized_auto_connection_success(self, mock_ray):
        """Test successful Ray initialization"""
        mock_ray.is_initialized.return_value = False
        mock_ray.init.return_value = None

        ensure_ray_initialized()

        # Should call init with expected parameters
        mock_ray.init.assert_called_once()
        call_args = mock_ray.init.call_args
        assert "ignore_reinit_error" in call_args.kwargs
        assert "num_cpus" in call_args.kwargs
        assert "log_to_driver" in call_args.kwargs
        # runtime_env should be included with default sage config

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ensure_ray_initialized_initialization_fails(self, mock_ray):
        """Test behavior when Ray initialization fails"""
        mock_ray.is_initialized.return_value = False

        # Ray init fails
        mock_ray.init.side_effect = RuntimeError("Initialization failed")

        with pytest.raises(RuntimeError, match="Initialization failed"):
            ensure_ray_initialized()

        # Should call init once and fail
        assert mock_ray.init.call_count == 1
        # The actual implementation calls ray.init with expected parameters
        calls = mock_ray.init.call_args_list
        call_kwargs = calls[0][1]
        assert "ignore_reinit_error" in call_kwargs
        assert call_kwargs["ignore_reinit_error"] is True
        assert "num_cpus" in call_kwargs
        assert "log_to_driver" in call_kwargs
        # runtime_env should be included with default sage config

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ensure_ray_initialized_all_attempts_fail(self, mock_ray):
        """Test behavior when Ray initialization fails"""
        mock_ray.is_initialized.return_value = False
        mock_ray.init.side_effect = RuntimeError("Local init failed")

        # Should raise the exception
        with pytest.raises(RuntimeError, match="Local init failed"):
            ensure_ray_initialized()

        # Should only attempt once
        assert mock_ray.init.call_count == 1

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_is_distributed_environment_ray_available_and_initialized(self, mock_ray):
        """Test is_distributed_environment when Ray is available and initialized"""
        mock_ray.is_initialized.return_value = True

        result = is_distributed_environment()

        assert result is True
        mock_ray.is_initialized.assert_called_once()

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_is_distributed_environment_ray_available_not_initialized(self, mock_ray):
        """Test is_distributed_environment when Ray is available but not initialized"""
        mock_ray.is_initialized.return_value = False

        result = is_distributed_environment()

        assert result is False
        mock_ray.is_initialized.assert_called_once()

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", False)
    def test_is_distributed_environment_ray_not_available(self):
        """Test is_distributed_environment when Ray is not available"""
        result = is_distributed_environment()

        assert result is False

    @pytest.mark.integration
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ensure_ray_initialized_integration(self, mock_ray):
        """Integration test for Ray initialization process"""
        # Simulate real Ray behavior
        mock_ray.is_initialized.return_value = False
        mock_ray.init.return_value = None

        # Call multiple times to ensure idempotency
        ensure_ray_initialized()
        mock_ray.is_initialized.return_value = True
        ensure_ray_initialized()
        ensure_ray_initialized()

        # Should only initialize once
        assert mock_ray.init.call_count == 1

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ensure_ray_initialized_with_print_statements(self, mock_ray):
        """Test that appropriate messages are printed during initialization"""
        mock_ray.is_initialized.return_value = False
        mock_ray.init.return_value = None

        with patch("builtins.print") as mock_print:
            ensure_ray_initialized()

            # Should print success message
            mock_print.assert_called()
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("Ray initialized" in msg for msg in print_calls)

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ensure_ray_initialized_error_handling(self, mock_ray):
        """Test error handling and reporting in ensure_ray_initialized"""
        mock_ray.is_initialized.return_value = False
        error_message = "Critical Ray failure"
        mock_ray.init.side_effect = RuntimeError(error_message)

        with patch("builtins.print") as mock_print:
            with pytest.raises(RuntimeError, match=error_message):
                ensure_ray_initialized()

            # Should print error message
            mock_print.assert_called()
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("Failed to initialize Ray" in msg for msg in print_calls)


class TestRayIntegrationEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ensure_ray_initialized_ignore_reinit_error_parameter(self, mock_ray):
        """Test that ignore_reinit_error parameter is properly passed"""
        mock_ray.is_initialized.return_value = False
        mock_ray.init.return_value = None

        ensure_ray_initialized()

        # Both initialization attempts should have ignore_reinit_error=True
        calls = mock_ray.init.call_args_list
        for call in calls:
            assert call[1]["ignore_reinit_error"] is True

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_multiple_concurrent_initializations(self, mock_ray):
        """Test concurrent calls to ensure_ray_initialized"""
        import threading

        mock_ray.is_initialized.return_value = False
        mock_ray.init.return_value = None

        results = []

        def init_worker():
            try:
                ensure_ray_initialized()
                results.append("success")
            except Exception as e:
                results.append(f"error: {e}")

        # Start multiple threads
        threads = [threading.Thread(target=init_worker) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All should succeed (or at least not crash)
        assert len(results) == 5

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", False)
    def test_ray_module_import_variations(self):
        """Test different scenarios of Ray module availability"""
        # Test when ray module is completely unavailable
        result = is_distributed_environment()
        assert result is False

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ray_is_initialized_exception(self, mock_ray):
        """Test when ray.is_initialized() raises an exception"""
        mock_ray.is_initialized.side_effect = Exception("Ray internal error")

        result = is_distributed_environment()

        # Should return False when ray check fails
        assert result is False

    @pytest.mark.unit
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ensure_ray_with_specific_exceptions(self, mock_ray):
        """Test ensure_ray_initialized with specific exception types"""
        mock_ray.is_initialized.return_value = False

        # Test different exception types
        exception_types = [
            ConnectionError("Connection refused"),
            TimeoutError("Connection timeout"),
            OSError("Network error"),
            ValueError("Invalid configuration"),
        ]

        for exception in exception_types:
            mock_ray.init.side_effect = exception

            with pytest.raises(type(exception)):
                ensure_ray_initialized()

            # Reset for next iteration
            mock_ray.init.reset_mock()

            # Reset for next test
            mock_ray.init.side_effect = None


# Performance and stress tests
class TestRayPerformance:
    """Performance and stress tests for Ray integration"""

    @pytest.mark.slow
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_ensure_ray_performance(self, mock_ray):
        """Test that ensure_ray_initialized has minimal overhead when Ray is already initialized

        This test verifies the function doesn't have unexpected performance regressions,
        not absolute timing constraints. The test measures throughput rather than
        absolute time to avoid false positives from system load, coverage overhead, etc.
        """
        import time

        mock_ray.is_initialized.return_value = True

        iterations = 1000
        start_time = time.time()

        # Call many times
        for _ in range(iterations):
            ensure_ray_initialized()

        elapsed = time.time() - start_time

        # Verify reasonable throughput: should handle at least 500 calls/second
        # This is extremely conservative - actual performance is much higher
        # but allows for coverage overhead, slow CI machines, etc.
        calls_per_second = iterations / elapsed
        min_throughput = 500  # calls/second

        assert calls_per_second >= min_throughput, (
            f"Performance regression detected: {calls_per_second:.1f} calls/sec "
            f"(minimum: {min_throughput} calls/sec, elapsed: {elapsed:.3f}s)"
        )

    @pytest.mark.slow
    @patch("sage.kernel.utils.ray.ray_utils.RAY_AVAILABLE", True)
    @patch("sage.kernel.utils.ray.ray_utils.ray")
    def test_is_distributed_environment_performance(self, mock_ray):
        """Test that is_distributed_environment has minimal overhead

        This test verifies the function doesn't have unexpected performance regressions,
        not absolute timing constraints. The test measures throughput rather than
        absolute time to avoid false positives from system load, coverage overhead, etc.
        """
        import time

        mock_ray.is_initialized.return_value = True

        iterations = 1000
        start_time = time.time()

        # Call many times
        results = [is_distributed_environment() for _ in range(iterations)]

        elapsed = time.time() - start_time

        # Verify reasonable throughput: should handle at least 500 calls/second
        # This is extremely conservative - actual performance is much higher
        # but allows for coverage overhead, slow CI machines, etc.
        calls_per_second = iterations / elapsed
        min_throughput = 500  # calls/second

        assert calls_per_second >= min_throughput, (
            f"Performance regression detected: {calls_per_second:.1f} calls/sec "
            f"(minimum: {min_throughput} calls/sec, elapsed: {elapsed:.3f}s)"
        )
        assert all(result is True for result in results)


# Fixtures and utilities
@pytest.fixture
def mock_ray_module():
    """Provide a fully mocked Ray module"""
    with patch("sage.kernel.utils.ray.ray_utils.ray") as mock_ray:
        mock_ray.is_initialized.return_value = False
        mock_ray.init.return_value = None
        yield mock_ray
