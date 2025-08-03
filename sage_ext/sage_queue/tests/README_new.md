# SAGE Queue Test Suite 2.0

Modern, comprehensive test suite for SAGE high-performance memory-mapped queue.

## Overview

This redesigned test suite provides comprehensive testing with modern Python testing practices, including:

- **pytest-based architecture** for better test discovery and reporting
- **Modular test organization** (unit, integration, performance)
- **Parallel test execution** support
- **Coverage reporting** and HTML reports
- **Performance benchmarking** with automated assertions
- **Comprehensive fixtures** for queue management

## Architecture

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── run_tests.py             # Modern test runner
├── pytest.ini              # pytest configuration
├── utils/                   # Test utilities and helpers
│   └── __init__.py          # DataGenerator, PerformanceCollector, etc.
├── unit/                    # Unit tests
│   ├── test_basic_operations.py
│   └── test_queue_manager.py
├── integration/             # Integration tests
│   ├── test_multiprocess.py
│   └── test_threading.py
└── performance/             # Performance benchmarks
    └── test_benchmarks.py
```

## Quick Start

### Prerequisites

1. **Compile the C library** (required):
   ```bash
   cd .. && ./build.sh
   ```

2. **Install pytest** (required):
   ```bash
   pip install pytest
   ```

3. **Install optional dependencies** (recommended):
   ```bash
   pip install pytest-cov pytest-html pytest-xdist psutil
   ```

### Running Tests

#### Quick Validation
```bash
python run_tests.py --quick
```

#### Unit Tests Only
```bash
python run_tests.py --unit
```

#### Integration Tests Only
```bash
python run_tests.py --integration
```

#### Performance Tests Only
```bash
python run_tests.py --performance
```

#### All Tests (Default)
```bash
python run_tests.py --all
```

#### With Coverage Report
```bash
python run_tests.py --coverage
```

#### Parallel Execution
```bash
python run_tests.py --all --parallel
```

#### Generate HTML Report
```bash
python run_tests.py --html
```

### Using pytest Directly

You can also use pytest directly for more control:

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m performance

# Run with coverage
pytest --cov=sage_queue --cov-report=html

# Run in parallel
pytest -n auto

# Run specific test file
pytest unit/test_basic_operations.py

# Run specific test
pytest unit/test_basic_operations.py::TestSageQueueBasics::test_queue_creation
```

## Test Categories

### Unit Tests (`-m unit`)
- Basic queue operations (put, get, size, etc.)
- Data type serialization/deserialization
- Error handling and edge cases
- Queue manager functionality

### Integration Tests (`-m integration`)
- Multiprocess communication scenarios
- Multithreading scenarios
- Producer-consumer patterns
- Concurrent access patterns

### Performance Tests (`-m performance`)
- Throughput benchmarks
- Latency measurements
- Memory efficiency tests
- Stress testing under load

## Fixtures

The test suite provides comprehensive fixtures:

- `small_queue`, `medium_queue`, `large_queue`: Pre-configured queues
- `queue_manager`: Queue manager instance
- `process_helper`: Multiprocess testing utilities
- `thread_helper`: Multithreading utilities
- `performance_monitor`: System performance monitoring

## Configuration

Test behavior can be configured through:

- `tests/__init__.py`: Test configuration constants
- `pytest.ini`: pytest settings
- Environment variables (e.g., `SAGE_TEST_MODE=1`)

## Performance Benchmarks

The test suite includes automated performance assertions:

- **Minimum throughput**: 50,000 messages/second
- **Maximum latency**: 1.0ms average
- **Memory efficiency**: >80%
- **Maximum memory usage**: 100MB

These can be adjusted in `tests/__init__.py`.

## Continuous Integration

For CI environments, use:

```bash
# Quick validation
python run_tests.py --quick

# Full test suite (excluding slow tests)
python run_tests.py --all

# With coverage for reporting
python run_tests.py --coverage
```

## Troubleshooting

### Common Issues

1. **"SageQueue not available"**
   - Compile C library: `cd .. && ./build.sh`
   - Check PYTHONPATH includes sage_queue directory

2. **Import errors for optional dependencies**
   - Install missing packages: `pip install pytest-cov pytest-html pytest-xdist psutil`

3. **Performance test failures**
   - Check system load during testing
   - Adjust benchmarks in `tests/__init__.py` if needed

4. **Multiprocess test failures**
   - Increase timeouts for slower systems
   - Check available memory and process limits

### Debug Mode

For debugging failed tests:

```bash
# Verbose output with full tracebacks
pytest -v --tb=long

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s
```

## Migration from Old Test Suite

The new test suite replaces the old modules:

- `test_basic_functionality.py` → `unit/test_basic_operations.py`
- `test_multiprocess_concurrent.py` → `integration/test_multiprocess.py`
- `test_performance_benchmark.py` → `performance/test_benchmarks.py`
- `run_all_tests.py` → `run_tests.py`

Key improvements:
- Better test isolation with fixtures
- More granular test organization
- Improved error reporting
- Parallel execution support
- Modern Python testing practices

## Contributing

When adding new tests:

1. Use appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`, etc.)
2. Use fixtures for queue setup/teardown
3. Include performance assertions for performance tests
4. Add docstrings describing test purpose
5. Follow naming conventions (`test_*` functions in `Test*` classes)

## Legacy Support

The old test files are preserved for reference but should be migrated to the new structure. The old `run_all_tests.py` will continue to work but is deprecated in favor of `run_tests.py`.
