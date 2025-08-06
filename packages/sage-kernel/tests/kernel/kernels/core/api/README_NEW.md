# SAGE Core API Tests

This directory contains comprehensive unit tests for the `sage.kernel.api` module, following the testing organization structure outlined in the project issue.

## Test Structure

The test organization follows the source code structure exactly:

```
tests/core/api/
├── conftest.py                    # Shared test configuration and fixtures
├── test_base_environment.py       # Tests for base_environment.py
├── test_local_environment.py      # Tests for local_environment.py
├── test_remote_environment.py     # Tests for remote_environment.py
├── test_datastream.py             # Tests for datastream.py
└── test_connected_streams.py      # Tests for connected_streams.py
```

## Test Categories

All tests are properly marked with pytest markers:

- `@pytest.mark.unit`: Pure unit tests with mocked dependencies
- `@pytest.mark.integration`: Integration tests testing component interactions
- `@pytest.mark.slow`: Tests that take longer to execute

## Test Coverage

### BaseEnvironment (`test_base_environment.py`)
- ✅ Initialization with various configurations
- ✅ Console log level management
- ✅ Service registration functionality
- ✅ Kafka source creation
- ✅ Data source methods (from_source, from_collection, from_batch)
- ✅ Future stream creation
- ✅ Property lazy loading (logger, client)
- ✅ Logging system setup
- ✅ Auxiliary methods
- ✅ Edge cases and error conditions

### LocalEnvironment (`test_local_environment.py`)
- ✅ Initialization and inheritance
- ✅ JobManager integration
- ✅ Job submission
- ✅ Pipeline stopping and closing
- ✅ Queue descriptor creation
- ✅ Integration workflows
- ✅ Edge cases

### RemoteEnvironment (`test_remote_environment.py`)
- ✅ Initialization with connection parameters
- ✅ JobManager client management
- ✅ Job submission with serialization
- ✅ Error handling in submission process
- ✅ Queue descriptor creation
- ✅ Logging functionality
- ✅ Integration workflows

### DataStream (`test_datastream.py`)
- ✅ Initialization and type resolution
- ✅ Transformation methods (map, filter, flatmap, sink, keyby)
- ✅ Lambda function wrapping
- ✅ Stream connection
- ✅ Future stream filling
- ✅ Print utility method
- ✅ Method chaining
- ✅ Integration scenarios

### ConnectedStreams (`test_connected_streams.py`)
- ✅ Initialization with multiple transformations
- ✅ Transformation applications
- ✅ Stream connections
- ✅ CoMap functionality
- ✅ Multi-input handling
- ✅ Method chaining
- ✅ Complex workflows

## Running Tests

### Run all API tests:
```bash
cd /home/flecther/SAGE/packages/sage-kernel
pytest tests/core/api/ -v
```

### Run specific test file:
```bash
pytest tests/core/api/test_base_environment.py -v
```

### Run only unit tests:
```bash
pytest tests/core/api/ -m unit -v
```

### Run only integration tests:
```bash
pytest tests/core/api/ -m integration -v
```

### Run with coverage:
```bash
pytest tests/core/api/ --cov=sage.kernel.api --cov-report=html -v
```

### Run specific test class:
```bash
pytest tests/core/api/test_base_environment.py::TestBaseEnvironmentInit -v
```

### Run specific test method:
```bash
pytest tests/core/api/test_base_environment.py::TestBaseEnvironmentInit::test_init_with_defaults -v
```

## Test Quality Standards

All tests follow these quality standards:

1. **Single Responsibility**: Each test method tests one specific functionality
2. **Clear Naming**: Test names clearly describe what is being tested
3. **Comprehensive Coverage**: Tests cover normal, boundary, and error cases
4. **Proper Mocking**: External dependencies are properly mocked
5. **Performance**: Unit tests complete in < 1 second
6. **Independence**: Tests can run in any order without side effects

## Test Data and Fixtures

- **conftest.py**: Contains shared fixtures and configuration
- **Mock Classes**: Each test file defines appropriate mock classes
- **Sample Data**: Fixtures provide various test data scenarios

## Continuous Integration

These tests are designed to run in CI/CD pipelines with:
- Automated execution on code changes
- Code coverage reporting
- Test result notifications
- Performance regression detection

## Contributing

When adding new functionality to `sage.kernel.api`:

1. Add corresponding tests following the naming convention
2. Use appropriate pytest markers
3. Include unit tests for all public methods
4. Add integration tests for complex workflows
5. Ensure tests are fast and reliable
6. Document any special test requirements

## Dependencies

Test dependencies are managed in the main `pyproject.toml`:
- pytest >= 7.0.0
- pytest-cov >= 4.0.0
- pytest-asyncio >= 0.21.0
- pytest-mock (for enhanced mocking)

## Known Issues

- Some import issues with queue descriptors are handled by testing interfaces rather than concrete types
- Mock objects are used extensively to avoid heavy dependencies during testing
