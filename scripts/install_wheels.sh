#!/usr/bin/env bash

# Enhanced install script with aggressive constraint options to prevent backtracking
# 🔧 集成了 outlines_core 和 xformers 安装问题的修复

set -e

echo "=== 安装 SAGE wheels - 已集成安装问题修复 ==="

# === 安装问题修复 - 开始 ===
echo "🔧 应用安装问题修复..."

# 设置环境变量避免安装问题
export PIP_USE_PEP517=1
export PIP_PREFER_BINARY=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_WARN_CONFLICTS=1
export PIP_ONLY_BINARY=":all:"

# 升级安装工具
echo "📦 升级 pip, setuptools, 和 wheel..."
pip install --upgrade pip setuptools wheel

# 预安装问题包，避免安装时冲突
echo "📦 预安装可能有问题的核心包..."
pip install --prefer-binary --only-binary=:all: \
    numpy==2.2.6 \
    scipy==1.15.3 \
    torch==2.7.1 \
    torchvision==0.22.1

echo "📦 预安装可能有构建问题的包..."
pip install --prefer-binary --only-binary=:all: \
    "outlines>=1.2.0,<1.3.0" \
    "xformers>=0.0.28" \
    2>/dev/null || {
    
    echo "⚠️  预编译包安装失败，使用源码编译..."
    
    # 确保构建环境
    if [ -f ~/.cargo/env ]; then
        source ~/.cargo/env
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    
    # 安装构建依赖
    pip install --upgrade setuptools-rust maturin "pybind11[global]"
    
    # 设置构建标志
    export RUSTFLAGS="-C target-cpu=native"
    
    # 从源码安装
    pip install --no-binary=outlines "outlines>=1.2.0,<1.3.0" --verbose
    pip install --use-pep517 "xformers>=0.0.28" --verbose
}

echo "✅ 安装问题修复完成"
# === 安装问题修复 - 结束 ===

# Create temp directory for environment variables (already set above)
# export PIP_DISABLE_PIP_VERSION_CHECK=1
# export PIP_NO_WARN_CONFLICTS=1

# Install sage with comprehensive constraints and options to speed up resolution
echo "📦 安装 SAGE 及其依赖（使用优化选项）..."

# 首先卸载任何现有的 SAGE 安装（包括开发模式）
echo "🗑️  卸载现有的 SAGE 安装..."
pip uninstall -y sage sage-kernel sage-middleware sage-userspace sage-cli sage-dev-toolkit 2>/dev/null || true

# 构建约束参数
constraint_args=""
if [ -f "constraints.txt" ]; then
    constraint_args="$constraint_args --constraint=constraints.txt"
fi
if [ -f "constraints-build.txt" ]; then
    constraint_args="$constraint_args --constraint=constraints-build.txt"
fi
if [ -f "./scripts/constraints.txt" ]; then
    constraint_args="$constraint_args --constraint=./scripts/constraints.txt"
fi

mkdir -p ~/.sage/makefile_logs
# 使用锁定依赖优先安装（如果存在）
if [ -f "requirements-lock.txt" ]; then
    echo "📋 使用锁定依赖文件进行快速安装..."
    pip install -r requirements-lock.txt \
        --find-links=./build/wheels \
        $constraint_args \
        --prefer-binary \
        --timeout=300 \
        --retries=3 \
        --cache-dir=/tmp/pip-cache \
        2>&1 | tee ~/.sage/makefile_logs/install.log
else
    echo "📋 混合安装策略：预处理依赖 + wheels安装..."
    
    # 策略1: 先安装基础依赖和可能有冲突的包
    echo "🔧 步骤1: 预安装核心依赖，避免解析冲突..."
    pip install \
        $constraint_args \
        --prefer-binary \
        --only-binary=:all: \
        --no-warn-conflicts \
        --timeout=300 \
        --retries=3 \
        --cache-dir=/tmp/pip-cache \
        torch==2.7.1 \
        torchvision==0.22.1 \
        transformers \
        fastapi \
        uvicorn \
        pydantic \
        numpy \
        2>&1 | tee ~/.sage/makefile_logs/install.log
    
    # 策略2: 使用我们的wheels安装SAGE包（非editable模式）
    echo "🔧 步骤2: 从wheels安装SAGE组件到site-packages..."
    if [ -d "./build/wheels" ] && [ "$(ls -A ./build/wheels/*.whl 2>/dev/null)" ]; then
        # 按依赖顺序安装wheels
        echo "📦 安装 sage-kernel..."
        pip install ./build/wheels/sage_kernel-*.whl \
            --force-reinstall \
            --no-deps \
            $constraint_args \
            --prefer-binary \
            2>&1 | tee -a ~/.sage/makefile_logs/install.log
            
        echo "📦 安装 sage-middleware..."
        pip install ./build/wheels/sage_middleware-*.whl \
            --force-reinstall \
            --no-deps \
            $constraint_args \
            --prefer-binary \
            2>&1 | tee -a ~/.sage/makefile_logs/install.log
            
        echo "📦 安装 sage-userspace..."
        pip install ./build/wheels/sage_userspace-*.whl \
            --force-reinstall \
            --no-deps \
            $constraint_args \
            --prefer-binary \
            2>&1 | tee -a ~/.sage/makefile_logs/install.log
            
        echo "📦 安装 sage (主包)..."
        pip install ./build/wheels/sage-1.*.whl \
            --force-reinstall \
            --no-deps \
            $constraint_args \
            --prefer-binary \
            2>&1 | tee -a ~/.sage/makefile_logs/install.log
    
    # 策略3: 最后解析任何缺失的依赖
    echo "🔧 步骤3: 解析剩余依赖..."
    pip install sage \
        $constraint_args \
        --prefer-binary \
        --no-warn-conflicts \
        --timeout=300 \
        --retries=3 \
        --cache-dir=/tmp/pip-cache \
        2>&1 | tee -a ~/.sage/makefile_logs/install.log
        
    else
        echo "❌ 没有找到wheels文件，请先运行 make build"
        exit 1
    fi
fi

echo "✅ 安装完成！"
echo ""
echo "🎉 SAGE 安装成功！已应用所有修复补丁。"
echo ""
echo "📋 验证安装："
echo "  python -c \"import sage; print('SAGE version:', sage.__version__)\""
echo "  python -c \"import outlines; print('outlines version:', outlines.__version__)\""
echo "  python -c \"import xformers; print('xformers version:', xformers.__version__)\"" 