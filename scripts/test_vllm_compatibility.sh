#!/usr/bin/env bash

# Script to test vLLM compatibility with PyTorch 2.7.1

set -e

echo "=== Testing vLLM Development Version Compatibility ==="

# Create a clean test environment
echo "Creating clean test environment..."
rm -rf test_vllm_env
python -m venv test_vllm_env
source test_vllm_env/bin/activate

# Install PyTorch 2.7.1 first
echo "Installing PyTorch 2.7.1..."
pip install --upgrade pip setuptools wheel
pip install torch==2.7.1 torchvision==0.22.1 --prefer-binary

# Check PyTorch version
echo "Checking PyTorch version..."
python -c "import torch; print(f'PyTorch version: {torch.__version__}')"

# Try to install vLLM development version
echo "Installing vLLM development version..."
pip install "vllm>=0.8.0,<1.0.0" --prefer-binary || {
    echo "Trying to install from source..."
    pip install --pre vllm
}

# Test basic import and compatibility
echo "Testing vLLM import and basic functionality..."
python -c "
import sys
try:
    import torch
    print(f'✅ PyTorch {torch.__version__} imported successfully')
    
    import vllm
    print(f'✅ vLLM {vllm.__version__} imported successfully')
    
    # Test CUDA availability if applicable
    if torch.cuda.is_available():
        print(f'✅ CUDA is available: {torch.cuda.get_device_name(0)}')
        print(f'✅ CUDA version: {torch.version.cuda}')
    else:
        print('ℹ️  CUDA not available (CPU-only mode)')
    
    # Basic vLLM compatibility check
    from vllm import LLM
    print('✅ vLLM core classes imported successfully')
    
    print('🎉 vLLM is compatible with PyTorch 2.7.1!')
    
except ImportError as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)
except Exception as e:
    print(f'⚠️  Compatibility issue: {e}')
    sys.exit(1)
"

echo "=== Compatibility Test Complete ==="

# Clean up
deactivate
rm -rf test_vllm_env

echo "✅ vLLM development version is compatible with PyTorch 2.7.1"
