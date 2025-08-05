"""
Test Configuration and Summary for SAGE Utils Module Tests

This file provides a comprehensive overview of the test coverage for all
sage.utils modules and serves as a test runner configuration.

Created: 2024
Test Framework: pytest
Coverage Target: ≥80% unit, ≥60% integration, 100% critical path
"""

import pytest
import sys
from pathlib import Path

# Add the source directory to Python path for testing
sage_kernel_src = Path(__file__).parent.parent / "src"
if str(sage_kernel_src) not in sys.path:
    sys.path.insert(0, str(sage_kernel_src))

# Test Coverage Summary
TEST_MODULES = {
    "config": {
        "source_files": [
            "sage.utils.config.loader",
            "sage.utils.config.manager"
        ],
        "test_files": [
            "tests.utils.config.test_loader",
            "tests.utils.config.test_manager"
        ],
        "coverage_areas": [
            "YAML/JSON/TOML configuration loading",
            "Environment variable override",
            "Project root detection",
            "Configuration validation",
            "Configuration caching",
            "Nested key operations"
        ]
    },
    "logging": {
        "source_files": [
            "sage.utils.logging.custom_formatter", 
            "sage.utils.logging.custom_logger"
        ],
        "test_files": [
            "tests.utils.logging.test_custom_formatter",
            "tests.utils.logging.test_custom_logger"
        ],
        "coverage_areas": [
            "Color-coded log formatting",
            "Multi-line message handling",
            "IDE-compatible output",
            "Multiple output targets",
            "Console debug control",
            "Dynamic logger configuration"
        ]
    },
    "network": {
        "source_files": [
            "sage.utils.network.base_tcp_client",
            "sage.utils.network.local_tcp_server"
        ],
        "test_files": [
            "tests.utils.network.test_base_tcp_client",
            "tests.utils.network.test_local_tcp_server"
        ],
        "coverage_areas": [
            "TCP client connection management",
            "Abstract client protocol",
            "TCP server lifecycle",
            "Message handler registration",
            "Connection handling",
            "Concurrent client support",
            "Error response generation"
        ]
    },
    "serialization": {
        "source_files": [
            "sage.utils.serialization.config",
            "sage.utils.serialization.exceptions"
        ],
        "test_files": [
            "tests.utils.serialization.test_config",
            "tests.utils.serialization.test_exceptions"
        ],
        "coverage_areas": [
            "Serialization blacklists",
            "Ray-specific exclusions",
            "Non-serializable type filtering",
            "Custom exception handling",
            "Error message formatting"
        ]
    },
    "system": {
        "source_files": [
            "sage.utils.system.environment",
            "sage.utils.system.network", 
            "sage.utils.system.process"
        ],
        "test_files": [
            "tests.utils.system.test_environment",
            "tests.utils.system.test_network",
            "tests.utils.system.test_process"
        ],
        "coverage_areas": [
            "Execution environment detection",
            "Ray/Kubernetes/Docker detection",
            "System resource monitoring",
            "Port management utilities",
            "Process discovery and termination",
            "Network connectivity testing",
            "Cross-platform process operations",
            "Sudo privilege management"
        ]
    }
}

# Test categories and markers
PYTEST_MARKERS = {
    "unit": "Unit tests - test individual functions/methods in isolation",
    "integration": "Integration tests - test component interaction",
    "slow": "Slow tests - tests that take significant time to run",
    "network": "Network tests - tests requiring network access",
    "system": "System tests - tests requiring system-level operations"
}

# Test execution configuration
PYTEST_CONFIG = {
    "testpaths": ["tests/utils"],
    "python_files": ["test_*.py"],
    "python_classes": ["Test*"],
    "python_functions": ["test_*"],
    "addopts": [
        "-v",                    # Verbose output
        "--tb=short",           # Short traceback format
        "--strict-markers",     # Require marker registration
        "--disable-warnings",   # Disable pytest warnings
        "-ra",                  # Show all test result info
    ],
    "markers": PYTEST_MARKERS,
    "filterwarnings": [
        "ignore::DeprecationWarning",
        "ignore::PendingDeprecationWarning"
    ]
}

def run_all_tests():
    """Run all utils module tests"""
    pytest.main([
        "tests/utils",
        "-v",
        "--tb=short",
        "-m", "not slow"  # Skip slow tests by default
    ])

def run_unit_tests():
    """Run only unit tests"""
    pytest.main([
        "tests/utils", 
        "-v", 
        "-m", "unit"
    ])

def run_integration_tests():
    """Run only integration tests"""
    pytest.main([
        "tests/utils",
        "-v", 
        "-m", "integration"
    ])

def run_performance_tests():
    """Run performance and slow tests"""
    pytest.main([
        "tests/utils",
        "-v",
        "-m", "slow"
    ])

def run_specific_module_tests(module_name: str):
    """Run tests for a specific module"""
    if module_name not in TEST_MODULES:
        print(f"Unknown module: {module_name}")
        print(f"Available modules: {list(TEST_MODULES.keys())}")
        return
    
    pytest.main([
        f"tests/utils/{module_name}",
        "-v",
        "--tb=short"
    ])

def generate_coverage_report():
    """Generate test coverage report"""
    pytest.main([
        "tests/utils",
        "--cov=sage.utils",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=80"
    ])

def run_with_profiling():
    """Run tests with performance profiling"""
    pytest.main([
        "tests/utils",
        "--profile",
        "--profile-svg"
    ])

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SAGE Utils Test Runner")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--slow", action="store_true", help="Run slow/performance tests")
    parser.add_argument("--module", type=str, help="Run tests for specific module")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--profile", action="store_true", help="Run with profiling")
    
    args = parser.parse_args()
    
    if args.coverage:
        generate_coverage_report()
    elif args.profile:
        run_with_profiling()
    elif args.unit:
        run_unit_tests()
    elif args.integration:
        run_integration_tests()
    elif args.slow:
        run_performance_tests()
    elif args.module:
        run_specific_module_tests(args.module)
    elif args.all:
        run_all_tests()
    else:
        print("SAGE Utils Module Test Suite")
        print("===========================")
        print()
        print("Test Coverage Summary:")
        for module, info in TEST_MODULES.items():
            print(f"\n{module.upper()}:")
            print(f"  Source Files: {len(info['source_files'])}")
            print(f"  Test Files: {len(info['test_files'])}")
            print(f"  Coverage Areas: {len(info['coverage_areas'])}")
        
        print(f"\nTotal Modules: {len(TEST_MODULES)}")
        print(f"Total Test Files: {sum(len(info['test_files']) for info in TEST_MODULES.values())}")
        print(f"Total Source Files: {sum(len(info['source_files']) for info in TEST_MODULES.values())}")
        
        print("\nUsage:")
        print("  python test_runner.py --all        # Run all tests")
        print("  python test_runner.py --unit       # Run unit tests only")
        print("  python test_runner.py --integration # Run integration tests")
        print("  python test_runner.py --slow       # Run performance tests")
        print("  python test_runner.py --module config # Run specific module tests")
        print("  python test_runner.py --coverage   # Generate coverage report")
        print("  python test_runner.py --profile    # Run with profiling")
