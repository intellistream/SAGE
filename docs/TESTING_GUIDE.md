# SAGE Testing Guide

This document explains how to run tests in the SAGE framework.

## Quick Start

The recommended way to run tests is using the `sage-dev` CLI tool:

```bash
# Run all tests in current package
sage-dev test

# Run tests with verbose output  
sage-dev test --verbose

# Run only previously failed tests
sage-dev test --failed

# Run tests with custom timeout (10 minutes)
sage-dev test --timeout 600

# Run tests with specific number of parallel workers
sage-dev test --jobs 8

# Run tests in a specific directory
sage-dev test /path/to/package
```

## Package-Specific Testing

To test specific SAGE packages:

```bash
# Test kernel package
cd packages/sage-kernel
sage-dev test

# Test middleware package  
cd packages/sage-middleware
sage-dev test

# Test common package
cd packages/sage-common
sage-dev test
```

## Test Output and Logs

Test results are automatically saved to `.sage/logs/` directory:

```
.sage/logs/
├── kernel/          # Kernel package test logs
├── middleware/      # Middleware package test logs  
├── common/          # Common package test logs
└── apps/            # Apps package test logs
```

Each test file gets its own log file:
- `test_example.py.log` - Complete test output
- `failed_tests.txt` - List of failed tests
- `latest_status.txt` - Last test run summary

## Cache Management

```bash
# List previously failed tests
sage-dev test cache list

# Clear failed tests cache
sage-dev test cache clear

# Show cache status
sage-dev test cache status
```

## Test Discovery

```bash
# List all available tests
sage-dev test list

# List tests with details
sage-dev test list --verbose

# List tests matching pattern
sage-dev test list --pattern "*_integration.py"
```

## Advanced Options

```bash
# Custom test file pattern
sage-dev test --pattern "*_integration.py"

# Disable parallel execution
sage-dev test --jobs 1

# Long-running tests with extended timeout
sage-dev test --timeout 1200

# Run failed tests with verbose output
sage-dev test --failed --verbose
```

## Project-Wide Testing

For testing all packages at once, you can use simple shell commands:

```bash
# Test all packages sequentially
for pkg in packages/sage-*; do
    echo "Testing $pkg..."
    cd "$pkg" && sage-dev test
    cd - > /dev/null
done

# Test all packages in parallel (be careful with resource usage)
for pkg in packages/sage-*; do
    (cd "$pkg" && sage-dev test) &
done
wait

# Test specific packages
for pkg in sage-kernel sage-middleware; do
    cd "packages/$pkg" && sage-dev test
    cd - > /dev/null
done
```

## ⚠️ Important Notes

1. **Always use `sage-dev test`** - This is the recommended way to run tests
2. **Avoid direct script usage** - Internal test scripts are implementation details
3. **Check logs** - Detailed test output is saved to `.sage/logs/`
4. **Use failed mode** - Quickly re-run only failed tests with `--failed`
5. **Parallel execution** - Use `--jobs` for faster test runs on multi-core systems

## Troubleshooting

### No tests found
```bash
# Make sure you're in the right directory
cd packages/sage-kernel
sage-dev test

# Check available tests
sage-dev test list
```

### Tests timeout
```bash
# Increase timeout (default: 300s)
sage-dev test --timeout 600

# Disable parallel execution
sage-dev test --jobs 1
```

### Import errors
```bash
# Make sure sage environment is activated
conda activate sage

# Check sage-dev is available
sage-dev --help
```

### Clear state
```bash
# Clear failed tests cache
sage-dev test cache clear

# Clean build artifacts
sage-dev artifacts clean
```
