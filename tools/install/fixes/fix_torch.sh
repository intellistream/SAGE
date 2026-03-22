#!/bin/bash
# 修复 PyTorch 版本冲突问题
#
# 用法:
#   ./tools/install/fixes/fix_torch.sh
#   ./tools/install/fixes/fix_torch.sh --non-interactive  # 非交互模式（用于 CI/CD）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info()    { echo -e "${BLUE}ℹ  $1${NC}"; }
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠  $1${NC}"; }
print_error()   { echo -e "${RED}✗ $1${NC}"; }

# 获取当前 torch 版本
get_torch_version() {
    python -c "import torch; print(torch.__version__)" 2>&1 || echo "not_installed"
}

# 主修复函数
fix_torch() {
    local non_interactive="${1:-false}"
    local TORCH_VERSION

    echo ""
    echo "🔧 PyTorch 版本修复脚本"
    echo "================================================"
    echo "  SAGE 使用 isagellm 作为推理引擎。"
    echo "  此脚本仅修复 PyTorch 版本。"
    echo "================================================"
    echo ""

    TORCH_VERSION=$(get_torch_version)
    echo "  当前 PyTorch 版本: $TORCH_VERSION"

    if [ "$non_interactive" != "--non-interactive" ]; then
        print_warning "此脚本将卸载并重新安装 torch"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "操作已取消"
            exit 0
        fi
    fi

    print_info "卸载现有的 torch 包..."
    pip uninstall -y torch torchaudio torchvision xformers 2>/dev/null || true

    print_info "安装推荐版本 torch 2.7.1..."
    if pip install "torch>=2.7.0,<3.0.0" torchaudio torchvision; then
        TORCH_VERSION=$(get_torch_version)
        print_success "PyTorch 安装成功: $TORCH_VERSION"
    else
        print_error "PyTorch 安装失败"
        echo "  请访问 https://pytorch.org 获取适合您系统的安装命令"
        exit 1
    fi

    echo ""
    print_success "修复完成！"
    echo ""
    echo "  推理引擎请使用 sagellm 相关组件。"
}

fix_torch "$@"
