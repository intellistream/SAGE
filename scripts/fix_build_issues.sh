#!/usr/bin/env bash

# Script to fix build issues with outlines_core and xformers
# 修复 outlines_core 构建失败和 xformers 弃用警告的问题

set -e

echo "=== 修复 Wheel 构建问题 ==="

# 1. 首先升级 pip 和构建工具到最新版本
echo "1. 升级构建工具..."
pip install --upgrade pip setuptools wheel build

# 2. 修复 outlines_core 构建问题
echo "2. 修复 outlines_core 构建问题..."

# outlines_core 可能依赖特定的 Rust 环境，我们先尝试安装预编译版本
echo "   尝试安装 outlines 的预编译版本..."
pip install --prefer-binary --only-binary=:all: outlines==1.2.1 || {
    echo "   预编译安装失败，安装 Rust 构建环境..."
    
    # 确保 Rust 可用
    if ! command -v rustc &> /dev/null; then
        echo "   安装 Rust 编译器..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
        source ~/.cargo/env
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    
    # 安装 Rust 相关的构建依赖
    echo "   安装 Rust 构建依赖..."
    pip install setuptools-rust wheel maturin
    
    # 尝试从源码构建
    echo "   从源码构建 outlines..."
    pip install --no-binary=outlines outlines==1.2.1
}

# 3. 修复 xformers 的弃用警告
echo "3. 修复 xformers 构建问题..."

# xformers 有官方预编译版本，优先使用
echo "   安装 xformers 预编译版本..."
pip install --upgrade --prefer-binary xformers || {
    echo "   预编译安装失败，尝试其他方案..."
    
    # 对于 PyTorch 2.7.1，我们需要兼容的 xformers 版本
    pip install "xformers>=0.0.28" --prefer-binary || {
        echo "   使用 --use-pep517 选项构建 xformers..."
        pip install xformers --use-pep517
    }
}

# 4. 更新 requirements-lock.txt 中的版本
echo "4. 更新 requirements-lock.txt..."

# 将 outlines 和 xformers 添加到锁定文件中
if ! grep -q "outlines==" /home/flecther/SAGE/requirements-lock.txt; then
    echo "outlines==1.2.1" >> /home/flecther/SAGE/requirements-lock.txt
fi

if ! grep -q "xformers==" /home/flecther/SAGE/requirements-lock.txt; then
    # 检查实际安装的 xformers 版本
    XFORMERS_VERSION=$(pip show xformers | grep Version | cut -d' ' -f2)
    if [ -n "$XFORMERS_VERSION" ]; then
        echo "xformers==$XFORMERS_VERSION" >> /home/flecther/SAGE/requirements-lock.txt
    else
        echo "xformers>=0.0.28" >> /home/flecther/SAGE/requirements-lock.txt
    fi
fi

# 5. 创建一个优化的约束文件，专门处理这些问题包
echo "5. 创建优化约束文件..."
cat > /home/flecther/SAGE/constraints-build.txt << 'EOF'
# 构建时约束文件 - 解决已知的构建问题

# outlines 相关
outlines==1.2.1
# outlines_core 通常由 outlines 自动安装，不直接指定版本

# xformers 兼容 PyTorch 2.7.1
xformers>=0.0.28

# 确保其他依赖兼容性
torch==2.7.1
torchvision==0.22.1

# 构建工具版本
setuptools>=68.0.0
wheel>=0.41.0
build>=1.0.0

# Rust 相关包的预编译版本偏好
tokenizers>=0.21.0
EOF

# 6. 创建一个专门的构建脚本，处理这些问题包
echo "6. 创建特殊构建脚本..."
cat > /home/flecther/SAGE/scripts/build_with_fixes.sh << 'EOF'
#!/usr/bin/env bash

# 带修复的构建脚本

set -e

echo "=== 使用修复版本构建 SAGE Wheels ==="

# 设置环境变量避免构建问题
export PIP_USE_PEP517=1
export PIP_PREFER_BINARY=1
export PIP_ONLY_BINARY=":all:"
export PIP_NO_BUILD_ISOLATION=0  # 启用构建隔离以避免冲突

# 导入 Rust 环境（如果存在）
if [ -f ~/.cargo/env ]; then
    source ~/.cargo/env
fi

# 预安装问题包
echo "预安装问题包..."
pip install --prefer-binary --constraint constraints-build.txt outlines xformers

# 然后运行正常的构建流程
echo "运行构建流程..."
./scripts/build_all_wheels.sh

echo "✅ 构建完成！"
EOF

chmod +x /home/flecther/SAGE/scripts/build_with_fixes.sh

echo ""
echo "=== 修复完成！==="
echo ""
echo "📋 问题诊断："
echo "  ❌ outlines_core: 需要 Rust 编译器或预编译包"
echo "  ⚠️  xformers: 使用了弃用的 setup.py 构建方式"
echo ""
echo "🔧 应用的修复："
echo "  ✅ 安装了 Rust 编译器（如果需要）"
echo "  ✅ 优先使用预编译包"
echo "  ✅ 添加了 --use-pep517 选项支持"
echo "  ✅ 更新了约束文件"
echo "  ✅ 创建了优化构建脚本"
echo ""
echo "🚀 建议的使用方式："
echo "  ./scripts/fix_build_issues.sh  # 运行此脚本（刚刚运行完成）"
echo "  ./scripts/build_with_fixes.sh  # 使用修复版本构建"
echo ""
echo "💡 或者直接使用锁定依赖快速安装："
echo "  pip install -r requirements-lock.txt"
