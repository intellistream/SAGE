"""
Test suite for sage.kernels.runtime module

This module contains comprehensive unit and integration tests
for the SAGE runtime components including:

- Dispatcher: Task and service execution management
- TaskContext & ServiceContext: Runtime context management  
- Distributed components: Ray integration and actor wrapping
- Factory components: Task and service creation
- Serialization: Universal serialization utilities
- Communication: Queue and routing components
- Task execution: Local and remote task implementations
- Service execution: Service task implementations

Test Organization:
- Unit tests: Fast, isolated tests for individual components
- Integration tests: Tests for component interactions
- Performance tests: Benchmarks and stress tests
- Edge case tests: Error conditions and boundary cases

Markers:
- @pytest.mark.unit: Unit tests (fast, no external dependencies)
- @pytest.mark.integration: Integration tests (moderate speed)
- @pytest.mark.slow: Performance/stress tests (slow execution)
- @pytest.mark.external: Tests requiring external services (Ray, etc.)

Usage:
    # Run all runtime tests
    pytest tests/runtime/
    
    # Run only unit tests
    pytest tests/runtime/ -m unit
    
    # Run tests excluding slow ones
    pytest tests/runtime/ -m "not slow"
    
    # Run specific component tests
    pytest tests/runtime/test_dispatcher.py
    pytest tests/runtime/distributed/
    pytest tests/runtime/factory/
"""

__version__ = "0.1.4"
