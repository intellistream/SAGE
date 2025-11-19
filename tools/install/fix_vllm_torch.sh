#!/bin/bash
# 修复 vLLM 和 Torch 版本冲突问题
#
# 用法:
#   ./tools/install/fix_vllm_torch.sh
#   ./tools/install/fix_vllm_torch.sh --latest  # 安装最新版本
#   ./tools/install/fix_vllm_torch.sh --non-interactive  # 非交互模式（用于 CI/CD）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 默认参数
NON_INTERACTIVE=false
INSTALL_LATEST=false

# 解析命令行参数
for arg in "$@"; do
    case $arg in
        --non-interactive|-y)
            NON_INTERACTIVE=true
            shift
            ;;
        --latest)
            INSTALL_LATEST=true
            shift
            ;;
        *)
            ;;
    esac
done

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查是否在虚拟环境中
check_virtual_env() {
    if [ "$NON_INTERACTIVE" = true ]; then
        # 非交互模式下，只打印警告但继续执行
        if [ -z "$VIRTUAL_ENV" ] && [ -z "$CONDA_DEFAULT_ENV" ]; then
            print_warning "未检测到虚拟环境（非交互模式）"
        fi
        return 0
    fi

    if [ -z "$VIRTUAL_ENV" ] && [ -z "$CONDA_DEFAULT_ENV" ]; then
        print_warning "未检测到虚拟环境"
        print_warning "建议在虚拟环境中运行此脚本"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        if [ -n "$CONDA_DEFAULT_ENV" ]; then
            print_info "当前 Conda 环境: $CONDA_DEFAULT_ENV"
        elif [ -n "$VIRTUAL_ENV" ]; then
            print_info "当前虚拟环境: $VIRTUAL_ENV"
        fi
    fi
}

# 检查当前版本
check_current_versions() {
    print_info "检查当前安装的版本..."

    TORCH_VERSION=$(python -c "import torch; print(torch.__version__)" 2>/dev/null || echo "未安装")
    VLLM_VERSION=$(python -c "try:
    import vllm
    print(vllm.__version__)
except:
    print('未安装')" 2>/dev/null || echo "未安装")

    echo "  Torch: $TORCH_VERSION"
    echo "  vLLM: $VLLM_VERSION"
    echo
}

# 卸载冲突的包
uninstall_packages() {
    print_info "卸载现有的 torch 和 vllm 包..."

    pip uninstall -y torch torchaudio torchvision vllm xformers 2>/dev/null || true

    print_success "卸载完成"
}

# 安装兼容的版本
install_compatible_versions() {
    local install_latest=$1

    print_info "安装兼容的版本..."

    if [ "$install_latest" = "true" ]; then
        print_info "安装最新版本的 vLLM（会自动安装兼容的 torch）"
        pip install vllm
    else
        print_info "安装推荐版本 vLLM 0.10.1.1 + torch 2.7.1"

        # 检查是否需要 CUDA 版本
        if command -v nvidia-smi &> /dev/null; then
            print_info "检测到 NVIDIA GPU，安装 CUDA 版本"
            pip install torch==2.7.1 torchaudio==2.7.1 torchvision==0.22.1
        else
            print_info "未检测到 NVIDIA GPU，安装 CPU 版本"
            pip install torch==2.7.1+cpu torchaudio==2.7.1+cpu torchvision==0.22.1+cpu \
                --index-url https://download.pytorch.org/whl/cpu
        fi

        pip install vllm==0.10.1.1
    fi

    print_success "安装完成"
}

# 验证安装
verify_installation() {
    print_info "验证安装..."

    # 验证版本
    TORCH_VERSION=$(python -c "import torch; print(torch.__version__)" 2>&1)
    if [ $? -ne 0 ]; then
        print_error "Torch 导入失败"
        return 1
    fi
    print_success "Torch 版本: $TORCH_VERSION"

    # 验证 vLLM
    VLLM_VERSION=$(python -c "import vllm; print(vllm.__version__)" 2>&1)
    if [ $? -ne 0 ]; then
        print_error "vLLM 导入失败"
        echo "$VLLM_VERSION"
        return 1
    fi
    print_success "vLLM 版本: $VLLM_VERSION"

    # 验证 torch._inductor.config
    python -c "import torch._inductor.config; print('torch._inductor.config 可用')" 2>&1
    if [ $? -eq 0 ]; then
        print_success "torch._inductor.config 可用"
    else
        print_error "torch._inductor.config 不可用"
        return 1
    fi

    # 运行完整的依赖验证脚本
    if [ -f "$PROJECT_ROOT/tools/install/verify_dependencies.py" ]; then
        print_info "运行完整依赖验证..."
        python "$PROJECT_ROOT/tools/install/verify_dependencies.py"
    fi

    return 0
}

# 主函数
main() {
    echo "=========================================="
    echo "🔧 vLLM & Torch 版本冲突修复脚本"
    echo "=========================================="
    echo

    # 检查虚拟环境
    check_virtual_env
    echo

    # 检查当前版本
    check_current_versions

    # 确认操作（非交互模式下自动继续）
    if [ "$NON_INTERACTIVE" = false ]; then
        print_warning "此脚本将卸载并重新安装 torch 和 vllm"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "操作已取消"
            exit 0
        fi
        echo
    else
        print_info "非交互模式：自动继续执行修复"
    fi

    # 执行修复步骤
    uninstall_packages
    echo

    install_compatible_versions "$INSTALL_LATEST"
    echo

    # 验证安装
    if verify_installation; then
        echo
        print_success "=========================================="
        print_success "✨ 修复完成！所有依赖已正确安装"
        print_success "=========================================="
        echo
        print_info "你现在可以使用 sage-dev 命令了:"
        echo "  sage-dev --help"
        echo
        print_info "相关文档:"
        echo "  cat docs/dev-notes/l0-infra/vllm-torch-version-conflict.md"
    else
        echo
        print_error "=========================================="
        print_error "修复失败，请检查错误信息"
        print_error "=========================================="
        echo
        print_info "手动修复步骤:"
        echo "  1. pip uninstall -y torch torchaudio torchvision vllm"
        echo "  2. pip install vllm"
        echo "  3. python tools/install/verify_dependencies.py"
        echo
        exit 1
    fi
}

# 运行主函数
main "$@"
