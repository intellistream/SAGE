#!/bin/bash
# 构建 PyCANDYAlgo 模块的脚本

set -e  # 遇到错误立即退出

echo "========================================="
echo "Building PyCANDYAlgo Module"
echo "========================================="
echo ""

# 检查依赖
echo "Checking dependencies..."
python3 -c "import torch" 2>/dev/null || { echo "Error: PyTorch not installed. Run: pip install torch"; exit 1; }
echo "  ✓ PyTorch found"

which cmake >/dev/null 2>&1 || { echo "Error: CMake not installed"; exit 1; }
echo "  ✓ CMake found"

pkg-config --exists gflags 2>/dev/null || echo "  ⚠ Warning: gflags not found (may cause build errors)"

echo ""

# 清理旧构建
if [ -d "build" ]; then
    echo "Cleaning old build directory..."
    rm -rf build
fi

# 创建构建目录
mkdir -p build
cd build

echo ""
echo "Configuring with CMake..."
echo "----------------------------------------"

# 运行 CMake 配置 (CPU only)
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DPYTHON_EXECUTABLE=$(which python3) \
    -DCMAKE_PREFIX_PATH="$(python3 -c 'import torch;print(torch.utils.cmake_prefix_path)')" \
    -DFAISS_ENABLE_GPU=OFF \
    -DFAISS_ENABLE_PYTHON=OFF \
    -DBUILD_TESTING=OFF \
    || { echo ""; echo "❌ CMake configuration failed"; exit 1; }

echo ""
echo "========================================="
echo "Building Thirdparty Libraries"
echo "========================================="
echo ""

# 计算并行编译数 (每个编译进程约需 1-2GB)
NPROC=$(nproc)
MAX_JOBS=$(($(free -g | awk '/^Mem:/{print $7}') / 2))  # 可用内存 / 2GB
JOBS=$((MAX_JOBS < NPROC ? MAX_JOBS : NPROC))
JOBS=$((JOBS < 1 ? 1 : JOBS))  # 至少 1 个
JOBS=$((JOBS > 4 ? 4 : JOBS))  # 最多 4 个(安全起见)

echo "Using -j${JOBS} for compilation (available cores: ${NPROC})"
echo ""

# 返回到 algorithms_impl 目录
cd ..

# === 1. Build GTI ===
if [ -d "gti/GTI" ]; then
    echo "Building GTI..."
    echo "----------------------------------------"

    # 先构建 GTI 的依赖库 n2
    if [ -d "gti/GTI/extern_libraries/n2" ]; then
        echo "  Building GTI dependency: n2 library..."
        cd gti/GTI/extern_libraries/n2
        if [ -d build ]; then
            rm -rf build
        fi
        mkdir -p build
        make shared_lib || { echo "❌ Failed to build n2 library"; exit 1; }
        echo "  ✓ n2 library built"
        cd ../../../..
    fi

    # 构建 GTI
    cd gti/GTI
    if [ -d build ]; then
        rm -rf build
    fi
    mkdir -p bin build
    cd build
    cmake -DCMAKE_BUILD_TYPE=Release .. || { echo "❌ GTI cmake failed"; exit 1; }
    make -j${JOBS} || { echo "❌ GTI build failed"; exit 1; }
    make install || echo "  ⚠ GTI install failed (not critical)"
    cd ../../..
    echo "✓ GTI built successfully"
    echo ""
else
    echo "⚠ GTI not found (git submodule may not be initialized)"
    echo ""
fi

# === 2. Build IP-DiskANN ===
if [ -d "ipdiskann" ]; then
    echo "Building IP-DiskANN..."
    echo "----------------------------------------"
    cd ipdiskann
    if [ -d build ]; then
        rm -rf build
    fi
    mkdir -p build
    cd build
    cmake .. || { echo "❌ IP-DiskANN cmake failed"; exit 1; }
    make -j${JOBS} || { echo "❌ IP-DiskANN build failed"; exit 1; }
    make install || echo "  ⚠ IP-DiskANN install failed (not critical)"
    cd ../..
    echo "✓ IP-DiskANN built successfully"
    echo ""
else
    echo "⚠ IP-DiskANN not found (git submodule may not be initialized)"
    echo ""
fi

# === 3. Build PLSH ===
if [ -d "plsh" ]; then
    echo "Building PLSH..."
    echo "----------------------------------------"
    cd plsh
    if [ -d build ]; then
        rm -rf build
    fi
    mkdir -p build
    cd build
    cmake .. || { echo "❌ PLSH cmake failed"; exit 1; }
    make -j${JOBS} || { echo "❌ PLSH build failed"; exit 1; }
    make install || echo "  ⚠ PLSH install failed (not critical)"
    cd ../..
    echo "✓ PLSH built successfully"
    echo ""
else
    echo "⚠ PLSH not found (git submodule may not be initialized)"
    echo ""
fi

# 返回到 build 目录
cd build

echo ""
echo "========================================="
echo "Building PyCANDYAlgo Main Module"
echo "========================================="
echo ""
echo "Compiling..."
echo "----------------------------------------"


# 编译 PyCANDYAlgo (JOBS 已经在前面计算好了)
make -j${JOBS} || { echo ""; echo "❌ Build failed"; exit 1; }

# 返回上级目录
cd ..

echo ""
echo "========================================="
echo "✅ Build Complete!"
echo "========================================="
echo ""

# 检查生成的文件
SO_FILE=$(ls PyCANDYAlgo*.so 2>/dev/null | head -1)

if [ -n "$SO_FILE" ]; then
    echo "PyCANDYAlgo module generated:"
    ls -lh "$SO_FILE"
    echo ""

    # 测试本地导入
    echo "Testing local import..."
    python3 -c "import sys; sys.path.insert(0, '.'); import PyCANDYAlgo; print('✅ Local import successful')" || {
        echo "⚠ Local import test failed"
        exit 1
    }

    # 询问是否安装到 site-packages
    echo ""
    read -p "Install PyCANDYAlgo to site-packages for global use? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        SITE_PACKAGES=$(python3 -c "import site; print(site.USER_SITE)")
        mkdir -p "$SITE_PACKAGES"
        cp "$SO_FILE" "$SITE_PACKAGES/"
        echo "✅ Installed to $SITE_PACKAGES"
        echo ""
        echo "Testing global import..."
        cd /tmp
        python3 -c "import PyCANDYAlgo; print('✅ Global import successful')" || echo "⚠ Global import failed"
        cd - > /dev/null
    fi
else
    echo "⚠ PyCANDYAlgo.so not found in current directory"
    echo "Check build/ directory:"
    find build -name "PyCANDYAlgo*.so" 2>/dev/null || echo "No .so file found"
    exit 1
fi

echo ""
echo "To use PyCANDYAlgo:"
echo "  python3 -c 'import PyCANDYAlgo'"
echo ""
