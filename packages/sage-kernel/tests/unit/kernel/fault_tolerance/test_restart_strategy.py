"""
Tests for Restart Strategy Implementations

Comprehensive test coverage for restart strategy classes.
"""

import time

import pytest

from sage.kernel.fault_tolerance.impl.restart_strategy import (
    ExponentialBackoffStrategy,
    FailureRateStrategy,
    FixedDelayStrategy,
    RestartStrategy,
)


class TestFixedDelayStrategy:
    """Test FixedDelayStrategy"""

    def test_init_default_parameters(self):
        """Test initialization with default parameters"""
        strategy = FixedDelayStrategy()
        assert strategy.delay == 5.0
        assert strategy.max_attempts == 3  # DEFAULT_MAX_RESTART_ATTEMPTS

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters"""
        strategy = FixedDelayStrategy(delay=10.0, max_attempts=5)
        assert strategy.delay == 10.0
        assert strategy.max_attempts == 5

    def test_should_restart_below_max(self):
        """Test should_restart returns True when below max attempts"""
        strategy = FixedDelayStrategy(max_attempts=3)

        assert strategy.should_restart(0) is True
        assert strategy.should_restart(1) is True
        assert strategy.should_restart(2) is True

    def test_should_restart_at_max(self):
        """Test should_restart returns False at max attempts"""
        strategy = FixedDelayStrategy(max_attempts=3)

        assert strategy.should_restart(3) is False
        assert strategy.should_restart(4) is False

    def test_get_restart_delay_always_fixed(self):
        """Test get_restart_delay returns fixed delay regardless of failure count"""
        strategy = FixedDelayStrategy(delay=7.5)

        assert strategy.get_restart_delay(0) == 7.5
        assert strategy.get_restart_delay(1) == 7.5
        assert strategy.get_restart_delay(5) == 7.5
        assert strategy.get_restart_delay(100) == 7.5

    def test_on_restart_attempt_no_op(self):
        """Test on_restart_attempt is a no-op"""
        strategy = FixedDelayStrategy()

        # Should not raise exception
        strategy.on_restart_attempt(1)
        strategy.on_restart_attempt(5)


class TestExponentialBackoffStrategy:
    """Test ExponentialBackoffStrategy"""

    def test_init_default_parameters(self):
        """Test initialization with default parameters"""
        strategy = ExponentialBackoffStrategy()
        assert strategy.initial_delay == 1.0
        assert strategy.max_delay == 60.0
        assert strategy.multiplier == 2.0
        assert strategy.max_attempts == 5

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters"""
        strategy = ExponentialBackoffStrategy(
            initial_delay=2.0, max_delay=120.0, multiplier=3.0, max_attempts=10
        )
        assert strategy.initial_delay == 2.0
        assert strategy.max_delay == 120.0
        assert strategy.multiplier == 3.0
        assert strategy.max_attempts == 10

    def test_should_restart_below_max(self):
        """Test should_restart returns True when below max attempts"""
        strategy = ExponentialBackoffStrategy(max_attempts=5)

        assert strategy.should_restart(0) is True
        assert strategy.should_restart(1) is True
        assert strategy.should_restart(4) is True

    def test_should_restart_at_max(self):
        """Test should_restart returns False at max attempts"""
        strategy = ExponentialBackoffStrategy(max_attempts=5)

        assert strategy.should_restart(5) is False
        assert strategy.should_restart(6) is False

    def test_get_restart_delay_exponential_growth(self):
        """Test get_restart_delay grows exponentially"""
        strategy = ExponentialBackoffStrategy(initial_delay=1.0, max_delay=100.0, multiplier=2.0)

        # delay = initial_delay * multiplier^failure_count
        assert strategy.get_restart_delay(0) == 1.0  # 1.0 * 2^0 = 1.0
        assert strategy.get_restart_delay(1) == 2.0  # 1.0 * 2^1 = 2.0
        assert strategy.get_restart_delay(2) == 4.0  # 1.0 * 2^2 = 4.0
        assert strategy.get_restart_delay(3) == 8.0  # 1.0 * 2^3 = 8.0

    def test_get_restart_delay_respects_max(self):
        """Test get_restart_delay respects max_delay cap"""
        strategy = ExponentialBackoffStrategy(initial_delay=1.0, max_delay=10.0, multiplier=2.0)

        # Should cap at max_delay
        assert strategy.get_restart_delay(10) == 10.0  # Would be 1024.0 without cap
        assert strategy.get_restart_delay(20) == 10.0  # Would be very large

    def test_get_restart_delay_custom_multiplier(self):
        """Test get_restart_delay with custom multiplier"""
        strategy = ExponentialBackoffStrategy(initial_delay=1.0, max_delay=100.0, multiplier=3.0)

        assert strategy.get_restart_delay(0) == 1.0  # 1.0 * 3^0 = 1.0
        assert strategy.get_restart_delay(1) == 3.0  # 1.0 * 3^1 = 3.0
        assert strategy.get_restart_delay(2) == 9.0  # 1.0 * 3^2 = 9.0
        assert strategy.get_restart_delay(3) == 27.0  # 1.0 * 3^3 = 27.0

    def test_get_restart_delay_initial_delay_effect(self):
        """Test get_restart_delay with different initial delays"""
        strategy = ExponentialBackoffStrategy(initial_delay=5.0, max_delay=100.0, multiplier=2.0)

        assert strategy.get_restart_delay(0) == 5.0  # 5.0 * 2^0 = 5.0
        assert strategy.get_restart_delay(1) == 10.0  # 5.0 * 2^1 = 10.0
        assert strategy.get_restart_delay(2) == 20.0  # 5.0 * 2^2 = 20.0


class TestFailureRateStrategy:
    """Test FailureRateStrategy"""

    def test_init_default_parameters(self):
        """Test initialization with default parameters"""
        strategy = FailureRateStrategy()
        assert strategy.max_failures_per_interval == 5
        assert strategy.interval_seconds == 60.0
        assert strategy.delay == 5.0
        assert strategy.failure_timestamps == []

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters"""
        strategy = FailureRateStrategy(
            max_failures_per_interval=10, interval_seconds=120.0, delay=15.0
        )
        assert strategy.max_failures_per_interval == 10
        assert strategy.interval_seconds == 120.0
        assert strategy.delay == 15.0

    def test_should_restart_first_failure(self):
        """Test should_restart on first failure"""
        strategy = FailureRateStrategy(max_failures_per_interval=5)

        # First failure should be allowed
        assert strategy.should_restart(1) is True
        assert len(strategy.failure_timestamps) == 1

    def test_should_restart_below_threshold(self):
        """Test should_restart returns True when below threshold"""
        strategy = FailureRateStrategy(max_failures_per_interval=5)

        # Simulate 3 failures
        for i in range(3):
            result = strategy.should_restart(i + 1)
            assert result is True

        assert len(strategy.failure_timestamps) == 3

    def test_should_restart_at_threshold(self):
        """Test should_restart at failure threshold"""
        strategy = FailureRateStrategy(max_failures_per_interval=5)

        # Simulate 5 failures
        for i in range(5):
            result = strategy.should_restart(i + 1)
            assert result is True

        assert len(strategy.failure_timestamps) == 5

    def test_should_restart_exceeds_threshold(self):
        """Test should_restart returns False when threshold exceeded"""
        strategy = FailureRateStrategy(max_failures_per_interval=5)

        # Simulate 5 failures
        for i in range(5):
            strategy.should_restart(i + 1)

        # 6th failure should fail
        assert strategy.should_restart(6) is False
        assert len(strategy.failure_timestamps) == 6

    def test_should_restart_cleans_old_timestamps(self):
        """Test should_restart cleans up old failure timestamps"""
        strategy = FailureRateStrategy(max_failures_per_interval=3, interval_seconds=1.0)

        # Add 3 failures
        for i in range(3):
            strategy.should_restart(i + 1)

        # Wait for interval to expire
        time.sleep(1.1)

        # Old timestamps should be cleaned up, new failure allowed
        assert strategy.should_restart(4) is True
        assert len(strategy.failure_timestamps) == 1  # Only the new one

    def test_should_restart_mixed_old_and_new(self):
        """Test should_restart with mix of old and new timestamps"""
        strategy = FailureRateStrategy(max_failures_per_interval=3, interval_seconds=2.0)

        # Add 2 failures
        strategy.should_restart(1)
        strategy.should_restart(2)

        # Wait half the interval
        time.sleep(1.1)

        # Add 2 more failures (should keep old ones)
        assert strategy.should_restart(3) is True
        assert strategy.should_restart(4) is False  # Exceeds threshold

        # Wait for old ones to expire
        time.sleep(1.0)

        # Should only have recent failures, allow restart
        assert strategy.should_restart(5) is True

    def test_get_restart_delay_always_fixed(self):
        """Test get_restart_delay returns fixed delay"""
        strategy = FailureRateStrategy(delay=12.5)

        assert strategy.get_restart_delay(0) == 12.5
        assert strategy.get_restart_delay(1) == 12.5
        assert strategy.get_restart_delay(10) == 12.5


class TestRestartStrategyInterface:
    """Test RestartStrategy abstract base class"""

    def test_cannot_instantiate_directly(self):
        """Test that RestartStrategy cannot be instantiated directly"""
        with pytest.raises(TypeError):
            RestartStrategy()  # type: ignore

    def test_subclass_must_implement_should_restart(self):
        """Test that subclasses must implement should_restart"""

        class IncompleteStrategy(RestartStrategy):
            def get_restart_delay(self, failure_count: int) -> float:
                return 1.0

        with pytest.raises(TypeError):
            IncompleteStrategy()  # type: ignore

    def test_subclass_must_implement_get_restart_delay(self):
        """Test that subclasses must implement get_restart_delay"""

        class IncompleteStrategy(RestartStrategy):
            def should_restart(self, failure_count: int) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteStrategy()  # type: ignore

    def test_on_restart_attempt_has_default_impl(self):
        """Test that on_restart_attempt has a default no-op implementation"""

        class MinimalStrategy(RestartStrategy):
            def should_restart(self, failure_count: int) -> bool:
                return True

            def get_restart_delay(self, failure_count: int) -> float:
                return 1.0

        strategy = MinimalStrategy()
        # Should not raise exception
        strategy.on_restart_attempt(1)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_fixed_delay_zero_delay(self):
        """Test FixedDelayStrategy with zero delay"""
        strategy = FixedDelayStrategy(delay=0.0)
        assert strategy.get_restart_delay(1) == 0.0

    def test_fixed_delay_zero_max_attempts(self):
        """Test FixedDelayStrategy with zero max attempts"""
        strategy = FixedDelayStrategy(max_attempts=0)
        assert strategy.should_restart(0) is False

    def test_exponential_backoff_zero_initial_delay(self):
        """Test ExponentialBackoffStrategy with zero initial delay"""
        strategy = ExponentialBackoffStrategy(initial_delay=0.0)
        assert strategy.get_restart_delay(0) == 0.0
        assert strategy.get_restart_delay(5) == 0.0

    def test_exponential_backoff_multiplier_one(self):
        """Test ExponentialBackoffStrategy with multiplier=1 (no growth)"""
        strategy = ExponentialBackoffStrategy(initial_delay=5.0, multiplier=1.0)

        assert strategy.get_restart_delay(0) == 5.0
        assert strategy.get_restart_delay(1) == 5.0
        assert strategy.get_restart_delay(10) == 5.0

    def test_exponential_backoff_max_delay_less_than_initial(self):
        """Test ExponentialBackoffStrategy with max_delay < initial_delay"""
        strategy = ExponentialBackoffStrategy(initial_delay=10.0, max_delay=5.0)

        # Should cap at max_delay even on first attempt
        assert strategy.get_restart_delay(0) == 5.0

    def test_failure_rate_zero_max_failures(self):
        """Test FailureRateStrategy with zero max failures"""
        strategy = FailureRateStrategy(max_failures_per_interval=0)

        # First failure should exceed threshold
        assert strategy.should_restart(1) is False

    def test_failure_rate_very_short_interval(self):
        """Test FailureRateStrategy with very short interval"""
        strategy = FailureRateStrategy(max_failures_per_interval=3, interval_seconds=0.1)

        # Add 3 failures quickly
        for i in range(3):
            strategy.should_restart(i + 1)

        # Wait for interval to expire
        time.sleep(0.15)

        # Should allow restart after cleanup
        assert strategy.should_restart(4) is True

    def test_negative_failure_count(self):
        """Test strategies with negative failure count"""
        fixed = FixedDelayStrategy(max_attempts=3)
        exponential = ExponentialBackoffStrategy()

        # Should handle gracefully
        assert fixed.should_restart(-1) is True
        assert exponential.should_restart(-1) is True
        assert exponential.get_restart_delay(-1) == 0.5  # 1.0 * 2^-1 = 0.5

    def test_very_large_failure_count(self):
        """Test strategies with very large failure count"""
        exponential = ExponentialBackoffStrategy(max_delay=100.0)

        # Should cap at max_delay
        assert exponential.get_restart_delay(1000) == 100.0
