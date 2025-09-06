# SageFlow Development Guide

This guide is for developers contributing to SageFlow. It covers building from source, running tests, and contribution guidelines.

## Building the Project

SageFlow is a C++/Python hybrid project. Use CMake for C++ and pyproject.toml for Python packaging.

### Prerequisites

- CMake 3.16+
- C++17 compiler (e.g., GCC 9+, Clang 10+)
- Python 3.8+
- pybind11 (`pip install pybind11[global]`)
- NumPy (`pip install numpy`)
- Google Test for C++ tests (included via CMake)
- pytest for Python tests (`pip install pytest`)

### Clone and Build

```bash
git clone <repo-url>
cd sage_flow  # Project root
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)  # Or use 'ninja' if configured
```

This builds the C++ library and executables. For debug builds, use `-DCMAKE_BUILD_TYPE=Debug`.

### Python Bindings

The pybind11 bindings are built automatically during C++ build. To install as a package:

```bash
cd ..  # Back to project root
pip install . --force-reinstall --no-build-isolation
```

This compiles extensions and installs `sageflow`. Verify:

```python
from sageflow import Stream
stream = Stream.from_list([1, 2, 3])
print(stream.execute())  # Should print [1, 2, 3]
```

### Code Style

- C++: Use `.clang-format` and `.clang-tidy`. Run `clang-format -i src/**/*.cpp include/**/*.hpp` and `clang-tidy src/**/*.cpp`.
- Python: Follow PEP 8. Use `black` and `flake8` if installed.

See [scripts/check_code_style.sh](../scripts/check_code_style.sh) for automation.

## Running Tests

Tests are divided into unit (C++), Python, integration, and performance.

### C++ Unit Tests

Use Google Test framework. Run from build directory:

```bash
cd build
ctest -V  # Verbose output
# Or specific test: ctest -R test_operators -V
```

Expected: All tests pass without errors. Coverage can be checked with `gcov` if enabled in CMake.

### Python Tests

Run pytest on Python API and bindings:

```bash
pip install .  # Ensure installed
pytest tests/python/ -v  # Verbose, expect 100% pass
# Run all: pytest tests/ -v
```

Includes tests for Stream API chaining, NumPy integration, etc.

### Integration Tests

End-to-end pipeline validation:

```bash
pytest tests/integration/ -v
```

Verifies full stream execution from source to sink.

### Performance Benchmarks

Run timeit-based benchmarks:

```bash
python tests/performance/benchmark_stream.py
```

Measures parallelism impact; compare timings for different configs.

### All Tests

To run everything:

```bash
# C++ first
cd build && ctest -V && cd ..
# Then Python
pytest tests/ -v
# Examples as smoke tests
python examples/sage_flow_examples/run_all_examples.py
```

If tests fail, check sanitizers with [run_with_sanitizers.sh](../scripts/run_with_sanitizers.sh).

## Contribution Guidelines

We welcome contributions! Follow these steps:

1. **Fork and Clone:** Fork the repo on GitHub, clone your fork.
2. **Branch:** Create a feature branch: `git checkout -b feature/my-change`.
3. **Develop:** Implement changes, add tests. Ensure code style compliance.
4. **Test Locally:** Run all tests as above. Aim for 80%+ coverage.
5. **Commit:** Use descriptive messages: `git commit -m "Add NumPy from_array support"`.
6. **Push and PR:** `git push origin feature/my-change`, open Pull Request.
7. **CI Checks:** PR will run tests and linting; address any failures.

### Best Practices

- **No Core Changes:** Unless approved, avoid modifying core C++/bindings; focus on API/examples/docs.
- **Documentation:** Update docs/ for new features. Use [api_reference.md](../api_reference.md) for API docs.
- **Performance:** Benchmark changes; use [performance_monitoring.py](../examples/sage_flow_examples/performance_monitoring.py).
- **Issues:** Report bugs/feature requests on GitHub.

For advanced topics like adding new operators, see [include/operator/](../include/operator/) and bindings.

Join our community via GitHub Discussions for questions.