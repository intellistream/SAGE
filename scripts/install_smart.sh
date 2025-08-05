#!/usr/bin/env bash

# 智能SAGE安装脚本 - 混合策略
# 结合wheels安装和依赖解析的优点

set -e

echo "=== 智能SAGE安装 - 混合策略 ==="

# 设置环境变量
export PIP_USE_PEP517=1
export PIP_PREFER_BINARY=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_WARN_CONFLICTS=1
export PIP_ONLY_BINARY=":all:"

# 创建日志目录
mkdir -p ~/.sage/makefile_logs

# 卸载现有安装
echo "🗑️  卸载现有的 SAGE 安装..."
pip uninstall -y sage sage-kernel sage-middleware sage-userspace sage-cli sage-dev-toolkit 2>/dev/null || true

# 构建约束参数
constraint_args=""
if [ -f "constraints.txt" ]; then
    constraint_args="$constraint_args --constraint=constraints.txt"
fi
if [ -f "./scripts/constraints.txt" ]; then
    constraint_args="$constraint_args --constraint=./scripts/constraints.txt"
fi
if [ -f "./scripts/constraints-build.txt" ]; then
    constraint_args="$constraint_args --constraint=./scripts/constraints-build.txt"
fi

echo "🚀 开始混合安装策略..."

# 策略1: 预安装核心依赖，避免版本冲突
echo "🔧 步骤1: 预安装核心依赖..."
pip install \
    $constraint_args \
    --prefer-binary \
    --timeout=300 \
    --retries=3 \
    torch==2.7.1 \
    torchvision==0.22.1 \
    numpy \
    scipy \
    transformers \
    fastapi \
    uvicorn \
    pydantic \
    pyyaml \
    2>&1 | tee ~/.sage/makefile_logs/install.log

# 策略2: 检查并安装wheels
if [ -d "./build/wheels" ] && [ "$(ls -A ./build/wheels/sage*.whl 2>/dev/null)" ]; then
    echo "🔧 步骤2: 从wheels安装SAGE组件..."
    
    # 按依赖顺序安装wheels，避免循环依赖
    for wheel_pattern in "sage_kernel-*.whl" "sage_middleware-*.whl" "sage_userspace-*.whl" "sage-1.*.whl"; do
        wheel_file=$(ls ./build/wheels/$wheel_pattern 2>/dev/null | head -n1)
        if [ -n "$wheel_file" ]; then
            echo "📦 安装 $(basename $wheel_file)..."
            pip install "$wheel_file" \
                --force-reinstall \
                --no-deps \
                $constraint_args \
                2>&1 | tee -a ~/.sage/makefile_logs/install.log
        fi
    done
    
    # 策略3: 解析剩余依赖
    echo "🔧 步骤3: 解析剩余依赖..."
    pip install sage \
        $constraint_args \
        --prefer-binary \
        --timeout=300 \
        --retries=3 \
        2>&1 | tee -a ~/.sage/makefile_logs/install.log
        
else
    echo "⚠️  没有找到wheels，尝试从requirements-prod.txt安装..."
    if [ -f "requirements-prod.txt" ]; then
        pip install -r requirements-prod.txt \
            $constraint_args \
            --prefer-binary \
            --timeout=300 \
            --retries=3 \
            2>&1 | tee ~/.sage/makefile_logs/install.log
    else
        echo "❌ 既没有wheels也没有requirements-prod.txt，请先运行 make build"
        exit 1
    fi
fi

echo "✅ 混合安装完成！"

# 验证安装
echo "🔍 验证安装..."
python -c "
import sage
import sys
print(f'✅ SAGE 安装位置: {sage.__file__}')
if 'site-packages' in sage.__file__:
    print('✅ SAGE 已正确安装到 site-packages')
else:
    print('⚠️  SAGE 可能仍在开发模式')
try:
    print(f'✅ SAGE 版本: {sage.__version__}')
except:
    print('⚠️  无法获取版本信息')
"

echo ""
echo "🎉 安装验证完成！"
