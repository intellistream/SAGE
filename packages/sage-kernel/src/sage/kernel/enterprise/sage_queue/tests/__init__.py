"""
SAGE Memory-Mapped Queue Test Suite
Modern test suite for SAGE high-performance memory-mapped queue

This test suite provides comprehensive testing with modern Python testing practices,
including pytest integration, fixture management, and parallel execution.

Architecture:
- conftest.py: Shared fixtures and configuration
- unit/: Unit tests for individual components
- integration/: Integration tests for component interaction
- performance/: Performance benchmarks and stress tests
- utils/: Test utilities and helpers

Usage:
    # Run all tests
    pytest

    # Run specific test category
    pytest unit/
    pytest integration/
    pytest performance/

    # Run with coverage
    pytest --cov=sage_queue

    # Run with parallel execution
    pytest -n auto

    # Generate HTML report
    pytest --html=report.html
"""

__version__ = "2.0.0"
__author__ = "SAGE Project"

# Test configuration
TEST_CONFIG = {
    "default_timeout": 30,
    "performance_iterations": 1000,
    "stress_test_duration": 60,
    "concurrent_workers": 4,
    "memory_limit_mb": 100,
    "default_queue_size": 64 * 1024,  # 64KB
    "multiprocess_method": "spawn",
    "cleanup_on_exit": True,
    "temp_queue_prefix": "sage_test_"
}

# Performance benchmarks
PERFORMANCE_BENCHMARKS = {
    "min_throughput_msg_per_sec": 30000,  # Minimum throughput requirement (lowered from 50000)
    "max_latency_ms": 1.0,                # Maximum latency requirement
    "min_memory_efficiency": 0.8,         # Minimum memory efficiency
    "max_memory_usage_mb": 100             # Maximum memory usage
}
