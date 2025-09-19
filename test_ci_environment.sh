#!/bin/bash
# Test script to reproduce CI installation environment

echo "=== Testing CI Environment Simulation ==="

# Simulate CI environment variables
export CI=true
export PIP_NO_INPUT=1
export PIP_DISABLE_PIP_VERSION_CHECK=1

echo "Environment variables set:"
echo "CI: $CI"
echo "PIP_NO_INPUT: $PIP_NO_INPUT"
echo "PIP_DISABLE_PIP_VERSION_CHECK: $PIP_DISABLE_PIP_VERSION_CHECK"
echo ""

echo "Current Python environment:"
echo "Python: $(python --version)"
echo "Python path: $(which python)"
echo "Pip: $(pip --version)"
echo "Pip path: $(which pip)"
echo ""

echo "Testing SAGE import:"
python -c "import sage; print('✅ SAGE import works, version:', sage.__version__)" || echo "❌ SAGE import failed"

echo ""
echo "Testing SAGE CLI:"
echo "Checking if sage command is in PATH:"
if command -v sage >/dev/null 2>&1; then
    echo "✅ sage command found at: $(which sage)"
    echo "Testing sage --help:"
    sage --help >/dev/null && echo "✅ sage --help works" || echo "❌ sage --help failed"
    echo "Testing sage version:"
    sage version && echo "✅ sage version works" || echo "❌ sage version failed"
else
    echo "❌ sage command not found in PATH"
    echo "PATH: $PATH"
    echo ""
    echo "Testing direct module import:"
    python -c "import sage.tools.cli.main; print('✅ CLI module import works')" || echo "❌ CLI module import failed"
    echo ""
    echo "Testing direct module execution:"
    python -m sage.tools.cli.main --help >/dev/null && echo "✅ CLI module execution works" || echo "❌ CLI module execution failed"
    echo ""
    echo "Checking installed packages for sage entry points:"
    python -c "
import pkg_resources
for ep in pkg_resources.iter_entry_points('console_scripts'):
    if ep.name == 'sage':
        print(f'Found sage entry point: {ep}')
        break
else:
    print('❌ No sage entry point found')
"
fi

echo ""
echo "Checking pip list for sage packages:"
pip list | grep -i sage || echo "No sage packages found in pip list"

echo ""
echo "=== End of CI Environment Test ==="