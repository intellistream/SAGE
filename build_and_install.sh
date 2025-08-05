#!/usr/bin/env bash

# SAGE 一键构建和安装脚本
# 集成了所有构建和安装问题的修复

set -e

echo "🚀 SAGE 一键构建安装 - 已集成所有修复补丁"
echo "================================================"

# 检查是否在 SAGE 目录
if [ ! -f "scripts/build_all_wheels.sh" ] || [ ! -f "scripts/install_wheels.sh" ]; then
    echo "❌ 错误：请在 SAGE 项目根目录运行此脚本"
    exit 1
fi

# 选项处理
BUILD_ONLY=false
INSTALL_ONLY=false
SKIP_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --install-only)
            INSTALL_ONLY=true
            SKIP_BUILD=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --build-only    仅构建wheels，不安装"
            echo "  --install-only  仅安装（跳过构建）"
            echo "  --skip-build    跳过构建，直接安装现有wheels"
            echo "  --help, -h      显示帮助信息"
            echo ""
            echo "默认行为: 先构建，后安装"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 显示将要执行的操作
echo "📋 执行计划:"
if [ "$SKIP_BUILD" = false ]; then
    echo "  ✅ 构建所有wheels（已集成修复）"
fi
if [ "$BUILD_ONLY" = false ]; then
    echo "  ✅ 安装SAGE及依赖（已集成修复）"
fi
echo ""

# 开始执行
start_time=$(date +%s)

# 构建阶段
if [ "$SKIP_BUILD" = false ]; then
    echo "🔨 第1步: 构建所有wheels..."
    echo "----------------------------"
    
    if ! ./scripts/build_all_wheels.sh; then
        echo "❌ 构建失败！"
        exit 1
    fi
    
    echo ""
    echo "✅ 构建完成！"
    echo ""
    
    if [ "$BUILD_ONLY" = true ]; then
        echo "🎉 仅构建模式：wheels已构建完成"
        ls -la build/wheels/
        exit 0
    fi
fi

# 安装阶段
if [ "$BUILD_ONLY" = false ]; then
    echo "📦 第2步: 安装SAGE..."
    echo "-------------------"
    
    if ! ./scripts/install_wheels.sh; then
        echo "❌ 安装失败！"
        exit 1
    fi
    
    echo ""
    echo "✅ 安装完成！"
fi

# 完成
end_time=$(date +%s)
duration=$((end_time - start_time))

echo ""
echo "🎉 SAGE 构建安装完成！"
echo "================================================"
echo "⏱️  总耗时: ${duration}秒"
echo ""
echo "🔧 应用的修复:"
echo "  ✅ outlines_core 构建问题修复"
echo "  ✅ xformers PEP517 弃用警告修复"
echo "  ✅ Rust 编译环境自动配置"
echo "  ✅ 优先使用预编译包"
echo "  ✅ 智能约束文件应用"
echo ""
echo "📋 验证安装:"
echo "  python -c \"import sage; print('✅ SAGE installed:', sage.__version__)\""
echo "  python -c \"import outlines; print('✅ outlines installed:', outlines.__version__)\""
echo "  python -c \"import xformers; print('✅ xformers installed:', xformers.__version__)\""
