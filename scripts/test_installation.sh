#!/usr/bin/env bash

# Test the optimized installation with pinned dependencies

set -e

echo "=== Testing SAGE Installation Performance with Pinned Dependencies ==="

# Create a fresh virtual environment for testing
echo "Creating fresh test environment..."
rm -rf test_env
python -m venv test_env
source test_env/bin/activate

# Upgrade core tools
pip install --upgrade pip setuptools wheel

# Record start time
echo "Starting installation at $(date)"
start_time=$(date +%s)

# Install SAGE with wheels (pinned dependencies should resolve much faster)
echo "Installing SAGE with pinned dependencies..."
pip install sage \
  --find-links=./build/wheels \
  --prefer-binary \
  --only-binary=:all: \
  2>&1 | tee install_test.log

# Record end time
end_time=$(date +%s)
duration=$((end_time - start_time))

echo "Installation completed in ${duration} seconds"

# Test basic import
echo "Testing SAGE import..."
python -c "
try:
    import sage
    print('✅ SAGE imported successfully!')
    
    # Test importing sub-modules
    from sage import kernel
    print('✅ sage.kernel imported successfully!')
    
    from sage import middleware  
    print('✅ sage.middleware imported successfully!')
    
    from sage import userspace
    print('✅ sage.userspace imported successfully!')
    
    print('🎉 All SAGE modules are working correctly!')
    
except ImportError as e:
    print(f'❌ Import failed: {e}')
    exit(1)
"

echo "=== Installation Test Complete ==="
echo "Duration: ${duration} seconds"
echo "Check install_test.log for detailed output"

# Clean up
deactivate
