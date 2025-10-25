"""
Tests for sage.common.core.constants

Tests the constant definitions.
"""

from sage.common.core.constants import (DEFAULT_CHECKPOINT_INTERVAL,
                                        DEFAULT_CLEANUP_TIMEOUT,
                                        DEFAULT_HEALTH_CHECK_INTERVAL,
                                        DEFAULT_MAX_RESTART_ATTEMPTS,
                                        PLACEMENT_STRATEGY_LOAD_BALANCE,
                                        PLACEMENT_STRATEGY_RESOURCE_AWARE,
                                        PLACEMENT_STRATEGY_SIMPLE,
                                        RESTART_STRATEGY_EXPONENTIAL,
                                        RESTART_STRATEGY_FAILURE_RATE,
                                        RESTART_STRATEGY_FIXED,
                                        SCHEDULING_STRATEGY_FIFO,
                                        SCHEDULING_STRATEGY_PRIORITY,
                                        SCHEDULING_STRATEGY_RESOURCE_AWARE)


class TestDefaultConstants:
    """Tests for default configuration constants"""

    def test_checkpoint_interval_type_and_value(self):
        """Test DEFAULT_CHECKPOINT_INTERVAL is a positive integer"""
        assert isinstance(DEFAULT_CHECKPOINT_INTERVAL, int)
        assert DEFAULT_CHECKPOINT_INTERVAL > 0
        assert DEFAULT_CHECKPOINT_INTERVAL == 60

    def test_health_check_interval_type_and_value(self):
        """Test DEFAULT_HEALTH_CHECK_INTERVAL is a positive integer"""
        assert isinstance(DEFAULT_HEALTH_CHECK_INTERVAL, int)
        assert DEFAULT_HEALTH_CHECK_INTERVAL > 0
        assert DEFAULT_HEALTH_CHECK_INTERVAL == 30

    def test_max_restart_attempts_type_and_value(self):
        """Test DEFAULT_MAX_RESTART_ATTEMPTS is a positive integer"""
        assert isinstance(DEFAULT_MAX_RESTART_ATTEMPTS, int)
        assert DEFAULT_MAX_RESTART_ATTEMPTS > 0
        assert DEFAULT_MAX_RESTART_ATTEMPTS == 3

    def test_cleanup_timeout_type_and_value(self):
        """Test DEFAULT_CLEANUP_TIMEOUT is a positive float"""
        assert isinstance(DEFAULT_CLEANUP_TIMEOUT, float)
        assert DEFAULT_CLEANUP_TIMEOUT > 0
        assert DEFAULT_CLEANUP_TIMEOUT == 5.0


class TestRestartStrategyConstants:
    """Tests for restart strategy constants"""

    def test_restart_strategy_types(self):
        """Test that restart strategies are strings"""
        assert isinstance(RESTART_STRATEGY_FIXED, str)
        assert isinstance(RESTART_STRATEGY_EXPONENTIAL, str)
        assert isinstance(RESTART_STRATEGY_FAILURE_RATE, str)

    def test_restart_strategy_values(self):
        """Test restart strategy constant values"""
        assert RESTART_STRATEGY_FIXED == "fixed_delay"
        assert RESTART_STRATEGY_EXPONENTIAL == "exponential_backoff"
        assert RESTART_STRATEGY_FAILURE_RATE == "failure_rate"

    def test_restart_strategies_are_unique(self):
        """Test that restart strategies have unique values"""
        strategies = {
            RESTART_STRATEGY_FIXED,
            RESTART_STRATEGY_EXPONENTIAL,
            RESTART_STRATEGY_FAILURE_RATE,
        }
        assert len(strategies) == 3


class TestPlacementStrategyConstants:
    """Tests for placement strategy constants"""

    def test_placement_strategy_types(self):
        """Test that placement strategies are strings"""
        assert isinstance(PLACEMENT_STRATEGY_SIMPLE, str)
        assert isinstance(PLACEMENT_STRATEGY_RESOURCE_AWARE, str)
        assert isinstance(PLACEMENT_STRATEGY_LOAD_BALANCE, str)

    def test_placement_strategy_values(self):
        """Test placement strategy constant values"""
        assert PLACEMENT_STRATEGY_SIMPLE == "simple"
        assert PLACEMENT_STRATEGY_RESOURCE_AWARE == "resource_aware"
        assert PLACEMENT_STRATEGY_LOAD_BALANCE == "load_balance"

    def test_placement_strategies_are_unique(self):
        """Test that placement strategies have unique values"""
        strategies = {
            PLACEMENT_STRATEGY_SIMPLE,
            PLACEMENT_STRATEGY_RESOURCE_AWARE,
            PLACEMENT_STRATEGY_LOAD_BALANCE,
        }
        assert len(strategies) == 3


class TestSchedulingStrategyConstants:
    """Tests for scheduling strategy constants"""

    def test_scheduling_strategy_types(self):
        """Test that scheduling strategies are strings"""
        assert isinstance(SCHEDULING_STRATEGY_FIFO, str)
        assert isinstance(SCHEDULING_STRATEGY_PRIORITY, str)
        assert isinstance(SCHEDULING_STRATEGY_RESOURCE_AWARE, str)

    def test_scheduling_strategy_values(self):
        """Test scheduling strategy constant values"""
        assert SCHEDULING_STRATEGY_FIFO == "fifo"
        assert SCHEDULING_STRATEGY_PRIORITY == "priority"
        assert SCHEDULING_STRATEGY_RESOURCE_AWARE == "resource_aware"

    def test_scheduling_strategies_are_unique(self):
        """Test that scheduling strategies have unique values"""
        strategies = {
            SCHEDULING_STRATEGY_FIFO,
            SCHEDULING_STRATEGY_PRIORITY,
            SCHEDULING_STRATEGY_RESOURCE_AWARE,
        }
        assert len(strategies) == 3


class TestConstantImmutability:
    """Tests to ensure constants remain constant"""

    def test_constants_are_not_none(self):
        """Test that no constants are None"""
        constants = [
            DEFAULT_CHECKPOINT_INTERVAL,
            DEFAULT_HEALTH_CHECK_INTERVAL,
            DEFAULT_MAX_RESTART_ATTEMPTS,
            DEFAULT_CLEANUP_TIMEOUT,
            RESTART_STRATEGY_FIXED,
            RESTART_STRATEGY_EXPONENTIAL,
            RESTART_STRATEGY_FAILURE_RATE,
            PLACEMENT_STRATEGY_SIMPLE,
            PLACEMENT_STRATEGY_RESOURCE_AWARE,
            PLACEMENT_STRATEGY_LOAD_BALANCE,
            SCHEDULING_STRATEGY_FIFO,
            SCHEDULING_STRATEGY_PRIORITY,
            SCHEDULING_STRATEGY_RESOURCE_AWARE,
        ]
        assert all(c is not None for c in constants)

    def test_strategy_constants_non_empty(self):
        """Test that strategy constants are non-empty strings"""
        strategies = [
            RESTART_STRATEGY_FIXED,
            RESTART_STRATEGY_EXPONENTIAL,
            RESTART_STRATEGY_FAILURE_RATE,
            PLACEMENT_STRATEGY_SIMPLE,
            PLACEMENT_STRATEGY_RESOURCE_AWARE,
            PLACEMENT_STRATEGY_LOAD_BALANCE,
            SCHEDULING_STRATEGY_FIFO,
            SCHEDULING_STRATEGY_PRIORITY,
            SCHEDULING_STRATEGY_RESOURCE_AWARE,
        ]
        assert all(len(s) > 0 for s in strategies)
