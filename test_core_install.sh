#!/bin/bash
# Quick test to verify installation order works correctly

echo "=== Testing Core Installation Order ==="

# Create a minimal test environment
TEMP_ENV="/tmp/test_sage_minimal"
echo "Creating minimal test environment at: $TEMP_ENV"

# Remove if exists
rm -rf "$TEMP_ENV"

# Create new virtual environment
python -m venv "$TEMP_ENV"

# Activate the environment
source "$TEMP_ENV/bin/activate"

echo "Virtual environment activated:"
echo "Python: $(python --version)"
echo "Python path: $(which python)"
echo ""

# Simulate CI environment
export CI=true
export PIP_NO_INPUT=1
export PIP_DISABLE_PIP_VERSION_CHECK=1

echo "Step 1: Testing individual package installation..."

# Test installing individual packages first (this should work)
echo "Installing sage-common..."
if pip install -e packages/sage-common --disable-pip-version-check --no-input; then
    echo "✅ sage-common installed successfully"
else
    echo "❌ sage-common installation failed"
    deactivate
    rm -rf "$TEMP_ENV"
    exit 1
fi

echo "Installing sage-kernel..."
if pip install -e packages/sage-kernel --disable-pip-version-check --no-input; then
    echo "✅ sage-kernel installed successfully"
else
    echo "❌ sage-kernel installation failed"
    deactivate
    rm -rf "$TEMP_ENV"
    exit 1
fi

echo "Installing sage-tools..."
if pip install -e packages/sage-tools --disable-pip-version-check --no-input; then
    echo "✅ sage-tools installed successfully"
else
    echo "❌ sage-tools installation failed"
    deactivate
    rm -rf "$TEMP_ENV"
    exit 1
fi

echo ""
echo "Step 2: Testing main package installation..."

# Now test installing the main package (this should work now that dependencies are local)
echo "Installing sage[minimal]..."
if pip install -e packages/sage[minimal] --disable-pip-version-check --no-input; then
    echo "✅ sage[minimal] installed successfully"
else
    echo "❌ sage[minimal] installation failed"
    deactivate
    rm -rf "$TEMP_ENV"
    exit 1
fi

echo ""
echo "Step 3: Testing functionality..."

echo "Testing SAGE import:"
python -c "import sage; print('✅ SAGE import works, version:', sage.__version__)" || echo "❌ SAGE import failed"

echo ""
echo "Testing SAGE CLI:"
hash -r

if command -v sage >/dev/null 2>&1; then
    echo "✅ sage command found at: $(which sage)"
    echo "Testing sage --help (timeout 10s):"
    timeout 10s sage --help >/dev/null && echo "✅ sage --help works" || echo "❌ sage --help failed/timeout"
else
    echo "❌ sage command not found in PATH"
    echo "Testing direct module execution:"
    python -m sage.tools.cli.main --help >/dev/null && echo "✅ CLI module execution works" || echo "❌ CLI module execution failed"
fi

echo ""
echo "Checking installed packages:"
pip list | grep -i sage || echo "No sage packages found"

# Deactivate and cleanup
deactivate
rm -rf "$TEMP_ENV"

echo ""
echo "✅ Core installation order test completed successfully!"
echo "=== End of Test ==="