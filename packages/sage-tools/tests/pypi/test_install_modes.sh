#!/bin/bash
# PyPI 安装模式测试脚本
# 测试 pip install isage[] 的各种选项是否正常工作

set -e

echo "🔍 测试 PyPI 安装模式配置..."
echo "========================================"

# 切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 测试函数
test_install_mode() {
    local mode="$1"
    local description="$2"

    echo ""
    echo "📦 测试安装模式: $mode"
    echo "   描述: $description"

    # 构建正确的pip命令
    local pip_cmd
    if [ -z "$mode" ]; then
        pip_cmd="pip install -e packages/sage --dry-run"
        echo "   命令: $pip_cmd"
    else
        pip_cmd="pip install -e \"packages/sage[$mode]\" --dry-run"
        echo "   命令: pip install -e packages/sage[$mode] --dry-run"
    fi

    if eval "$pip_cmd" 2>/dev/null; then
        echo "   ✅ $mode 模式验证通过"
        return 0
    else
        echo "   ❌ $mode 模式验证失败"
        return 1
    fi
}

# 测试所有安装模式
echo "测试主包 (isage) 的安装模式:"

# 基本安装模式 (对应quickstart.sh的模式)
test_install_mode "minimal" "最小安装 (仅sage-common, sage-kernel)"
test_install_mode "standard" "标准安装 (包含所有核心组件)"
test_install_mode "dev" "开发者安装 (标准安装 + 开发工具)"

echo ""
echo "========================================"
echo "🎉 PyPI 安装模式测试完成！"

# 显示使用示例
echo ""
echo "💡 使用示例:"
echo "  pip install isage[minimal]          # 最小安装 (仅核心组件)"
echo "  pip install isage[standard]         # 标准安装 (所有核心组件)"
echo "  pip install isage[dev]              # 开发者安装 (标准 + 开发工具)"
