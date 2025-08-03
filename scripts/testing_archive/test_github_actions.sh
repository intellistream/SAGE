#!/bin/bash

# 本地 GitHub Actions 测试脚本
# 模拟 build-release.yml 的构建过程

set -e

echo "🚀 开始本地 GitHub Actions 测试"
echo "==============================================="

# 设置环境变量
export PYTHON_VERSION="3.11"
export GITHUB_REF="refs/heads/main"
export GITHUB_OUTPUT="/tmp/github_output.txt"

echo "📋 环境信息:"
echo "Python版本: $PYTHON_VERSION"
echo "Git引用: $GITHUB_REF"
echo "工作目录: $(pwd)"
echo ""

# 步骤 1: 检查代码
echo "📦 Step 1: Checkout code (模拟)"
git status --porcelain || echo "不是git仓库或没有git"
echo ""

# 步骤 2: 设置 Python
echo "🐍 Step 2: Set up Python"
python3 --version
which python3
echo ""

# 步骤 3: 安装构建依赖
echo "📚 Step 3: Install build dependencies"
python3 -m pip install --upgrade pip
echo "尝试安装构建依赖..."

if [ -f "requirements.txt" ]; then
    echo "发现 requirements.txt，安装依赖..."
    python3 -m pip install build setuptools wheel
    python3 -m pip install -r requirements.txt
else
    echo "未找到 requirements.txt，仅安装基础构建工具..."
    python3 -m pip install build setuptools wheel
fi
echo ""

# 步骤 4: 获取版本
echo "🏷️  Step 4: Get version"
if [ -f "sage/__init__.py" ]; then
    VERSION=$(python3 -c "import sage; print(sage.__version__)" 2>/dev/null || echo "0.1.0")
else
    VERSION="0.1.0"
fi

# 如果是tag触发，使用tag版本
if [[ $GITHUB_REF == refs/tags/* ]]; then
    VERSION=${GITHUB_REF#refs/tags/v}
fi

echo "version=$VERSION" >> "$GITHUB_OUTPUT"
echo "检测到版本: $VERSION"
echo ""

# 步骤 5: 构建 C 扩展
echo "🔧 Step 5: Build C extensions"
if [ -d "sage/utils/mmap_queue" ]; then
    cd sage/utils/mmap_queue
    if [ -f "build.sh" ]; then
        echo "发现 build.sh，执行构建..."
        bash build.sh
    elif [ -f "Makefile" ]; then
        echo "发现 Makefile，执行构建..."
        make clean && make
    else
        echo "未找到构建系统，跳过 C 扩展构建"
    fi
    
    # 验证so文件存在
    if ls *.so 1> /dev/null 2>&1; then
        echo "✅ C 扩展构建成功:"
        ls -la *.so
    else
        echo "⚠️  警告: 构建后未找到 .so 文件"
    fi
    cd - > /dev/null
else
    echo "未找到 sage/utils/mmap_queue 目录，跳过 C 扩展构建"
fi
echo ""

# 步骤 6: 构建源码包
echo "📦 Step 6: Build source wheel"
if [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
    echo "构建源码包..."
    python3 -m build --sdist --wheel
    
    if [ -d "dist" ]; then
        echo "✅ 构建完成，生成的文件:"
        ls -la dist/
        
        # 获取生成的wheel文件名
        if ls dist/*.whl 1> /dev/null 2>&1; then
            WHEEL_FILE=$(ls dist/*.whl | head -1)
            WHEEL_NAME=$(basename "$WHEEL_FILE")
            echo "source-wheel=$WHEEL_NAME" >> "$GITHUB_OUTPUT"
            echo "源码包: $WHEEL_NAME"
        fi
    else
        echo "❌ 构建失败，未生成 dist 目录"
    fi
else
    echo "⚠️  未找到 pyproject.toml 或 setup.py，跳过构建"
fi
echo ""

# 步骤 7: 构建字节码包（如果存在 build_wheel.py）
echo "📦 Step 7: Build bytecode wheel"
if [ -f "build_wheel.py" ]; then
    echo "构建字节码包..."
    python3 build_wheel.py --clean || echo "字节码构建失败"
    
    # 检查字节码包
    if ls dist/*_bytecode.whl 1> /dev/null 2>&1; then
        BYTECODE_WHEEL=$(ls dist/*_bytecode.whl | head -1)
        BYTECODE_NAME=$(basename "$BYTECODE_WHEEL")
        echo "wheel-name=$BYTECODE_NAME" >> "$GITHUB_OUTPUT"
        echo "字节码包: $BYTECODE_NAME"
    else
        echo "未生成字节码包，使用源码包"
        if ls dist/*.whl 1> /dev/null 2>&1; then
            WHEEL_FILE=$(ls dist/*.whl | grep -v _bytecode | head -1)
            WHEEL_NAME=$(basename "$WHEEL_FILE")
            echo "wheel-name=$WHEEL_NAME" >> "$GITHUB_OUTPUT"
        fi
    fi
else
    echo "未找到 build_wheel.py，跳过字节码构建"
fi
echo ""

# 步骤 8: 验证包内容
echo "🔍 Step 8: Verify wheel contents"
if [ -d "dist" ] && ls dist/*.whl 1> /dev/null 2>&1; then
    pip install wheel || echo "wheel 包已安装"
    
    for wheel_file in dist/*.whl; do
        echo "=== $(basename $wheel_file) 的内容 ==="
        python3 -m wheel unpack "$wheel_file" --dest temp_unpack 2>/dev/null || echo "解包失败"
        if [ -d "temp_unpack" ]; then
            echo "SO 文件:"
            find temp_unpack -type f -name "*.so" | head -10 || echo "未找到 .so 文件"
            echo "Python 文件:"
            find temp_unpack -type f -name "*.py" | head -10 || echo "未找到 .py 文件"
            rm -rf temp_unpack
        fi
        echo ""
    done
else
    echo "未找到可验证的 wheel 文件"
fi

# 步骤 9: 测试包安装
echo "🧪 Step 9: Test wheel installation"
if [ -d "dist" ] && ls dist/*.whl 1> /dev/null 2>&1; then
    echo "测试包安装..."
    
    # 创建虚拟环境进行测试
    python3 -m venv test_env
    source test_env/bin/activate
    
    # 安装wheel
    WHEEL_FILE=$(ls dist/*.whl | head -1)
    echo "安装: $WHEEL_FILE"
    pip install "$WHEEL_FILE" || echo "安装失败"
    
    # 基本导入测试
    python3 -c "import sage; print('✅ SAGE 导入成功')" 2>/dev/null || echo "❌ SAGE 导入失败"
    
    # 测试C扩展（如果存在）
    python3 -c "
try:
    from sage.utils.mmap_queue import ring_buffer
    print('✅ C 扩展导入成功')
except ImportError as e:
    print(f'⚠️  C 扩展导入失败: {e}')
except Exception as e:
    print(f'❌ C 扩展错误: {e}')
" 2>/dev/null || echo "C 扩展测试完成"
    
    deactivate
    rm -rf test_env
else
    echo "未找到可测试的 wheel 文件"
fi

echo ""
echo "==============================================="
echo "🎉 本地 GitHub Actions 测试完成！"
echo ""
echo "📊 构建结果:"
if [ -f "$GITHUB_OUTPUT" ]; then
    echo "生成的输出变量:"
    cat "$GITHUB_OUTPUT"
else
    echo "未生成输出文件"
fi

if [ -d "dist" ]; then
    echo ""
    echo "📦 生成的包文件:"
    ls -la dist/
fi
