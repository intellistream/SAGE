#!/bin/bash
set -e

echo "Building SAGE DB - Vector Database Module..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
BUILD_TYPE="Release"
BUILD_DIR="build"
INSTALL_PREFIX="$SCRIPT_DIR/install"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            BUILD_TYPE="Debug"
            shift
            ;;
        --clean)
            echo "Cleaning previous build..."
            rm -rf "$BUILD_DIR" "$INSTALL_PREFIX"
            shift
            ;;
        --install-deps)
            echo "Installing dependencies (prefer pip, fallback to conda)..."
            # Avoid failing the entire build if dependency install has conflicts (e.g., conda solver pins)
            set +e
            INSTALLED=false
            if command -v pip &> /dev/null; then
                echo "📦 Trying: pip install faiss-cpu pybind11[global]"
                pip install --upgrade pip >/dev/null 2>&1
                if pip install "faiss-cpu>=1.7.3" "pybind11[global]"; then
                    INSTALLED=true
                    echo "✅ Dependencies installed via pip"
                else
                    echo "⚠️  pip installation failed, will try conda if available"
                fi
            fi

            if [ "$INSTALLED" != true ] && command -v conda &> /dev/null; then
                echo "📦 Trying: conda install -c conda-forge faiss-cpu pybind11"
                # Use conda-forge explicitly and allow failures (avoid libmamba pin issues on CI)
                if conda install -c conda-forge faiss-cpu pybind11 -y; then
                    INSTALLED=true
                    echo "✅ Dependencies installed via conda"
                else
                    echo "⚠️  conda installation failed; continuing without FAISS (fallback build)"
                fi
            fi

            if [ "$INSTALLED" != true ]; then
                echo "ℹ️ Proceeding without FAISS; the build will use a fallback implementation."
                echo "   For optimal performance, install FAISS manually later:"
                echo "   - pip install faiss-cpu"
                echo "   - or: conda install -c conda-forge faiss-cpu"
            fi
            set -e
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --debug        Build in debug mode"
            echo "  --clean        Clean previous build"
            echo "  --install-deps Install dependencies (FAISS, pybind11)"
            echo "  --help         Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check for required tools
echo "Checking build dependencies..."

if ! command -v cmake &> /dev/null; then
    echo "❌ CMake not found. Please install CMake."
    exit 1
fi

if ! command -v g++ &> /dev/null && ! command -v clang++ &> /dev/null; then
    echo "❌ No C++ compiler found. Please install g++ or clang++."
    exit 1
fi

echo "✅ Build tools found"

# Try to find FAISS
echo "Checking for FAISS..."
FAISS_FOUND=false

# Check in conda environment
if [[ -n "$CONDA_PREFIX" ]] && [[ -f "$CONDA_PREFIX/include/faiss/IndexFlat.h" ]]; then
    echo "✅ Found FAISS in conda environment: $CONDA_PREFIX"
    FAISS_FOUND=true
    export CMAKE_PREFIX_PATH="$CONDA_PREFIX:$CMAKE_PREFIX_PATH"
elif [[ -f "/usr/local/include/faiss/IndexFlat.h" ]]; then
    echo "✅ Found FAISS in system path"
    FAISS_FOUND=true
elif [[ -f "/usr/include/faiss/IndexFlat.h" ]]; then
    echo "✅ Found FAISS in system path"
    FAISS_FOUND=true
else
    echo "⚠️  FAISS not found. Building with fallback implementation."
    echo "   For optimal performance, install FAISS:"
    echo "   conda install -c conda-forge faiss-cpu"
    echo "   or: pip install faiss-cpu"
fi

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure with CMake
echo "Configuring build..."
CMAKE_ARGS=(
    "-DCMAKE_BUILD_TYPE=$BUILD_TYPE"
    "-DCMAKE_INSTALL_PREFIX=$INSTALL_PREFIX"
    "-DBUILD_TESTS=ON"
    "-DBUILD_PYTHON_BINDINGS=ON"
    "-DUSE_OPENMP=ON"
)

# Add conda prefix if available
if [[ -n "$CONDA_PREFIX" ]]; then
    CMAKE_ARGS+=("-DCMAKE_PREFIX_PATH=$CONDA_PREFIX")
    CMAKE_ARGS+=("-DPython3_ROOT_DIR=$CONDA_PREFIX")
fi

cmake "${CMAKE_ARGS[@]}" ..

# Build
echo "Building..."
make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

# Run tests if available
if [[ -f "test_sage_db" ]]; then
    echo "Running tests..."
    ./test_sage_db
fi

# Install
echo "Installing..."
make install

# Copy Python extension next to canonical python/ for import stability
cd "$SCRIPT_DIR"
if ls "$BUILD_DIR"/_sage_db* 1> /dev/null 2>&1; then
    echo "Copying Python extension into python/ ..."
    mkdir -p python
    cp "$BUILD_DIR"/_sage_db* python/
fi

echo "✅ SAGE DB build completed!"
echo ""
echo "📁 Files prepared:"
echo "   - libsage_db.* (C++ library in build)"
echo "   - python/_sage_db.* (Python C++ extension)"
echo "   - python/sage_db.py (Python API wrapper in repo)"
echo ""
