#!/bin/bash
# Build and publish isage-amms to PyPI
# This script should be run on a high-memory machine (64GB+ recommended)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AMMS_DIR="$SCRIPT_DIR"

echo "======================================"
echo "isage-amms PyPI Build and Publish"
echo "======================================"
echo ""
echo "Current directory: $AMMS_DIR"
echo ""

# Parse arguments
DRY_RUN=true
TEST_PYPI=false
BUILD_ONLY=false
ENABLE_CUDA=false
LOW_MEMORY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-dry-run)
            DRY_RUN=false
            shift
            ;;
        --test-pypi)
            TEST_PYPI=true
            shift
            ;;
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --cuda)
            ENABLE_CUDA=true
            shift
            ;;
        --low-memory)
            LOW_MEMORY=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-dry-run     Actually upload to PyPI (default: dry-run)"
            echo "  --test-pypi      Upload to TestPyPI instead of PyPI"
            echo "  --build-only     Only build, don't upload"
            echo "  --cuda           Enable CUDA support"
            echo "  --low-memory     Use low-memory build mode (slower but uses less RAM)"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Dry-run build"
            echo "  $0 --build-only                       # Build without upload"
            echo "  $0 --test-pypi --no-dry-run          # Upload to TestPyPI"
            echo "  $0 --no-dry-run                       # Upload to PyPI"
            echo "  $0 --cuda --low-memory --no-dry-run  # CUDA build with memory optimization"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Configuration summary
echo "Configuration:"
echo "  Dry run: $DRY_RUN"
echo "  Test PyPI: $TEST_PYPI"
echo "  Build only: $BUILD_ONLY"
echo "  CUDA support: $ENABLE_CUDA"
echo "  Low memory mode: $LOW_MEMORY"
echo ""

# Check requirements
echo "Checking requirements..."

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

if ! command -v cmake &> /dev/null; then
    echo "Error: cmake not found"
    exit 1
fi

echo "Python version: $(python3 --version)"
echo "CMake version: $(cmake --version | head -n1)"
echo ""

# Check available memory
TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
echo "Available memory: ${TOTAL_MEM}GB"
if [ "$TOTAL_MEM" -lt 32 ]; then
    echo "Warning: LibAMM compilation requires 64GB+ RAM"
    echo "         Consider using --low-memory flag"
    if [ "$LOW_MEMORY" = false ]; then
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi
echo ""

# Install/upgrade build tools
echo "Installing build dependencies..."
python3 -m pip install --upgrade pip setuptools wheel build twine
echo ""

# Set environment variables
export PYTHONPATH="$AMMS_DIR:$PYTHONPATH"
if [ "$ENABLE_CUDA" = true ]; then
    export AMMS_ENABLE_CUDA=1
fi
if [ "$LOW_MEMORY" = true ]; then
    export AMMS_LOW_MEMORY_BUILD=1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf "$AMMS_DIR/dist" "$AMMS_DIR/build" "$AMMS_DIR/*.egg-info"
rm -rf "$AMMS_DIR/implementations/build"
echo "Cleaned."
echo ""

# Build the package
echo "======================================"
echo "Building isage-amms package..."
echo "======================================"
echo ""

cd "$AMMS_DIR"
python3 -m build --sdist --wheel .

if [ $? -ne 0 ]; then
    echo "Error: Build failed"
    exit 1
fi

echo ""
echo "Build completed successfully!"
echo "Built packages in: $AMMS_DIR/dist/"
ls -lh "$AMMS_DIR/dist/"
echo ""

# Exit if build-only
if [ "$BUILD_ONLY" = true ]; then
    echo "Build-only mode. Exiting without upload."
    exit 0
fi

# Upload to PyPI
if [ "$DRY_RUN" = false ]; then
    echo "======================================"
    if [ "$TEST_PYPI" = true ]; then
        echo "Uploading to TestPyPI..."
        REPO_FLAG="--repository testpypi"
    else
        echo "Uploading to PyPI..."
        REPO_FLAG=""
    fi
    echo "======================================"
    echo ""

    python3 -m twine upload $REPO_FLAG "$AMMS_DIR/dist/*"

    if [ $? -eq 0 ]; then
        echo ""
        echo "======================================"
        echo "Upload successful!"
        echo "======================================"
        if [ "$TEST_PYPI" = true ]; then
            echo "Test installation:"
            echo "  pip install -i https://test.pypi.org/simple/ isage-amms"
        else
            echo "Installation:"
            echo "  pip install isage-amms"
        fi
    else
        echo "Error: Upload failed"
        exit 1
    fi
else
    echo "======================================"
    echo "Dry-run mode (no upload)"
    echo "======================================"
    echo ""
    echo "To upload for real, run with --no-dry-run:"
    echo "  $0 --no-dry-run"
    echo ""
    echo "Or to test on TestPyPI first:"
    echo "  $0 --test-pypi --no-dry-run"
fi

echo ""
echo "Done!"
