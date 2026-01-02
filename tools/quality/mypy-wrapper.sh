#!/bin/bash
# Wrapper script for mypy that always exits with 0
# This allows mypy to show warnings without blocking commits or CI/CD

# Run mypy with all passed arguments
mypy "$@"

# Capture the exit code
EXIT_CODE=$?

# If mypy found errors, print a warning message
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "⚠️  Mypy found type checking issues above (exit code: $EXIT_CODE)"
    echo "⚠️  These are treated as warnings and won't block the commit/CI"
    echo ""
fi

# Always exit with 0 to not block the commit/CI
exit 0
