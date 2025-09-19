#!/bin/bash
# Test script to simulate fresh installation like CI

echo "=== Testing Fresh Installation Simulation ==="

# Create a temporary virtual environment
TEMP_ENV="/tmp/test_sage_install"
echo "Creating temporary test environment at: $TEMP_ENV"

# Remove if exists
rm -rf "$TEMP_ENV"

# Create new virtual environment
python -m venv "$TEMP_ENV"

# Activate the environment
source "$TEMP_ENV/bin/activate"

echo "Virtual environment activated:"
echo "Python: $(python --version)"
echo "Python path: $(which python)"
echo "Pip: $(pip --version)"
echo "Pip path: $(which pip)"
echo ""

# Simulate CI environment
export CI=true
export PIP_NO_INPUT=1
export PIP_DISABLE_PIP_VERSION_CHECK=1

echo "Installing SAGE in dev mode..."
echo "Command: pip install -e packages/sage[dev] --disable-pip-version-check --no-input"

if pip install -e packages/sage[dev] --disable-pip-version-check --no-input; then
    echo "✅ SAGE installation completed"
else
    echo "❌ SAGE installation failed"
    deactivate
    rm -rf "$TEMP_ENV"
    exit 1
fi

echo ""
echo "Testing installation:"

echo "Testing SAGE import:"
python -c "import sage; print('✅ SAGE import works, version:', sage.__version__)" || echo "❌ SAGE import failed"

echo ""
echo "Testing SAGE CLI:"
echo "Refreshing shell environment..."
hash -r

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
    echo "Testing direct module execution:"
    python -m sage.tools.cli.main --help >/dev/null && echo "✅ CLI module execution works" || echo "❌ CLI module execution failed"
    echo ""
    echo "Checking entry points:"
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
echo "Checking installed packages:"
pip list | grep -i sage || echo "No sage packages found"

# Deactivate and cleanup
deactivate
rm -rf "$TEMP_ENV"

echo ""
echo "=== End of Fresh Installation Test ==="