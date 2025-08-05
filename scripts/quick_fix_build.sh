#!/usr/bin/env bash

# 快速修复脚本 - 专门解决 outlines_core 和 xformers 构建问题

set -e

echo "🔧 快速修复 outlines_core 和 xformers 构建问题..."

# 方案1: 使用预编译包安装
echo "📦 方案1: 尝试使用预编译包..."
pip install --upgrade pip wheel setuptools

# 强制使用二进制包，避免源码编译
pip install --prefer-binary --only-binary=:all: \
    "outlines>=1.2.0,<1.3.0" \
    "xformers>=0.0.28" \
    2>/dev/null && {
    echo "✅ 预编译包安装成功！"
    exit 0
}

echo "⚠️  预编译包安装失败，尝试源码编译修复..."

# 方案2: 源码编译修复
echo "🛠️  方案2: 源码编译修复..."

# 2.1 确保 Rust 可用（outlines_core 需要）
if ! command -v rustc &> /dev/null; then
    echo "📥 安装 Rust 编译器..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
    source ~/.cargo/env
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "✅ Rust 安装完成"
fi

# 2.2 安装必要的构建依赖
echo "📥 安装构建依赖..."
pip install --upgrade \
    setuptools-rust \
    wheel \
    maturin \
    "pybind11[global]" \
    cmake

# 2.3 设置环境变量
export RUSTFLAGS="-C target-cpu=native"
export PIP_USE_PEP517=1

# 2.4 分别处理 outlines 和 xformers
echo "🔨 构建 outlines..."
pip install --no-binary=outlines "outlines>=1.2.0,<1.3.0" --verbose

echo "🔨 构建 xformers（使用 PEP517）..."
pip install --use-pep517 "xformers>=0.0.28" --verbose

echo "✅ 源码编译完成！"
