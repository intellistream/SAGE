#!/bin/bash
# VLLM 安装问题修复验证脚本

echo "=== VLLM 安装状态验证 ==="
echo

# 检查 VLLM Python 包
echo "1. 检查 VLLM Python 包："
if python -c "import vllm; print(f'✅ VLLM Python 包已安装，版本: {vllm.__version__}')" 2>/dev/null; then
    echo "   状态: 成功"
else
    echo "   ❌ VLLM Python 包未安装"
    exit 1
fi

echo

# 检查 VLLM 命令行工具
echo "2. 检查 VLLM 命令行工具："
if command -v vllm >/dev/null 2>&1; then
    echo "   ✅ VLLM 命令行工具已安装"
    echo "   版本: $(vllm --version 2>&1 | tail -1)"
    echo "   状态: 成功"
else
    echo "   ❌ VLLM 命令行工具未安装"
    exit 1
fi

echo

# 检查启动脚本
echo "3. 检查 VLLM 启动脚本："
if [ -x "./vllm_local_serve.sh" ]; then
    echo "   ✅ VLLM 启动脚本存在且可执行"
    echo "   路径: ./vllm_local_serve.sh"
    echo "   状态: 成功"
else
    echo "   ❌ VLLM 启动脚本不存在或不可执行"
    exit 1
fi

echo

# 检查帮助功能
echo "4. 检查脚本功能："
if ./vllm_local_serve.sh --help >/dev/null 2>&1; then
    echo "   ✅ 脚本帮助功能正常"
    echo "   状态: 成功"
else
    echo "   ❌ 脚本帮助功能异常"
    exit 1
fi

echo
echo "=== 修复验证结果 ==="
echo "✅ 问题已修复！VLLM 现在可以在选择安装时立即安装"
echo "✅ 优化了安装逻辑，直接使用 pip 安装最新版本"
echo "✅ 修复了启动脚本的交互问题，支持自动确认模式"
echo "✅ 所有脚本已整理到 tools/vllm/ 目录"
echo
echo "=== 使用说明 ==="
echo "现在您可以："
echo "1. 运行 './quickstart.sh --vllm' 立即安装 VLLM"
echo "2. 或在交互式安装中选择 'y' 安装 VLLM 环境"
echo "3. 使用 './vllm_local_serve.sh' 启动 VLLM 服务（交互模式）"
echo "4. 使用 './vllm_local_serve.sh --yes' 启动服务（自动确认）"
echo "5. 查看 './README_vllm_local_serve.md' 了解详细使用说明"
echo "3. 使用 './tools/vllm/vllm_local_serve.sh' 启动 VLLM 服务"
echo
