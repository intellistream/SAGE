#!/bin/bash
# GPU Smoke Test Runner for Task J Phase 5
#
# This script runs the GPU smoke test for finetune engine integration.
# It checks GPU availability and runs the test if GPU is present.
#
# Usage:
#   ./run_gpu_smoke_test.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "========================================="
echo "Task J Phase 5: GPU Smoke Test Runner"
echo "========================================="
echo ""

# Check if running in conda environment
if [[ -z "$CONDA_DEFAULT_ENV" ]]; then
    echo "⚠️  Warning: Not in a conda environment"
    echo "   Recommended: conda activate sage"
    echo ""
fi

# Check GPU availability
echo "🔍 Checking GPU availability..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ nvidia-smi found"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | nl
    echo ""
else
    echo "✗ nvidia-smi not found - GPU may not be available"
    echo ""
fi

# Check PyTorch CUDA
echo "🔍 Checking PyTorch CUDA support..."
python3 -c "import torch; print(f'  PyTorch: {torch.__version__}'); print(f'  CUDA available: {torch.cuda.is_available()}'); print(f'  CUDA version: {torch.version.cuda if hasattr(torch.version, \"cuda\") else \"N/A\"}'); print(f'  GPU count: {torch.cuda.device_count()}')" 2>/dev/null || echo "  ✗ PyTorch not available or no CUDA"
echo ""

# Run the GPU smoke test
echo "🚀 Running GPU smoke test..."
echo "   Test: packages/sage-llm-core/tests/control_plane/test_finetune_gpu_smoke.py"
echo ""

cd "$PROJECT_ROOT"

# Run with pytest
pytest packages/sage-llm-core/tests/control_plane/test_finetune_gpu_smoke.py \
    -v \
    -s \
    --tb=short \
    --timeout=300 \
    -m "gpu" \
    || {
        echo ""
        echo "========================================="
        echo "❌ GPU Smoke Test Failed"
        echo "========================================="
        exit 1
    }

echo ""
echo "========================================="
echo "✅ GPU Smoke Test Completed Successfully"
echo "========================================="
echo ""
echo "Task J Phase 5 Status: PASSED ✓"
echo ""
echo "Next steps:"
echo "  1. Review test output above"
echo "  2. Check checkpoint files in /tmp directory"
echo "  3. Update TASK_J_PHASE2_COMPLETE.md with results"
echo ""
