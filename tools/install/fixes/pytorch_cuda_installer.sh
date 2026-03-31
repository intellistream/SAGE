#!/bin/bash
# GPU 检测和 CUDA 版本 PyTorch 安装脚本
# 在 pip install 之前调用，确保安装正确版本的 PyTorch

# 导入颜色定义（如果可用）

# ============================================================================
# 环境变量安全默认值（防止 set -u 报错）
# ============================================================================
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"
GITLAB_CI="${GITLAB_CI:-}"
JENKINS_URL="${JENKINS_URL:-}"
BUILDKITE="${BUILDKITE:-}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
CONDA_DEFAULT_ENV="${CONDA_DEFAULT_ENV:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
# ============================================================================

if [ -f "$(dirname "${BASH_SOURCE[0]}")/../ui/colors.sh" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/../ui/colors.sh"
else
    # 定义基本颜色
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    RED='\033[0;31m'
    DIM='\033[2m'
    NC='\033[0m'
fi

# 检测 NVIDIA GPU
detect_nvidia_gpu() {
    # 方法1: 检查 nvidia-smi
    if command -v nvidia-smi &>/dev/null; then
        if nvidia-smi &>/dev/null; then
            return 0
        fi
    fi

    # 方法2: 检查 /dev/nvidia*
    if ls /dev/nvidia* &>/dev/null 2>&1; then
        return 0
    fi

    # 方法3: 检查 lspci
    if command -v lspci &>/dev/null; then
        if lspci | grep -i nvidia &>/dev/null; then
            return 0
        fi
    fi

    return 1
}

# 获取 CUDA 版本
get_cuda_version() {
    local cuda_version=""

    # 方法1: 从 nvidia-smi 获取
    if command -v nvidia-smi &>/dev/null; then
        cuda_version=$(nvidia-smi 2>/dev/null | grep -oP "CUDA Version: \K[0-9]+\.[0-9]+" | head -1)
        if [ -n "$cuda_version" ]; then
            echo "$cuda_version"
            return 0
        fi
    fi

    # 方法2: 从 nvcc 获取
    if command -v nvcc &>/dev/null; then
        cuda_version=$(nvcc --version 2>/dev/null | grep -oP "release \K[0-9]+\.[0-9]+" | head -1)
        if [ -n "$cuda_version" ]; then
            echo "$cuda_version"
            return 0
        fi
    fi

    # 方法3: 从 CUDA_HOME 获取
    if [ -n "$CUDA_HOME" ] && [ -f "$CUDA_HOME/version.txt" ]; then
        cuda_version=$(cat "$CUDA_HOME/version.txt" | grep -oP "[0-9]+\.[0-9]+" | head -1)
        if [ -n "$cuda_version" ]; then
            echo "$cuda_version"
            return 0
        fi
    fi

    # 方法4: 检查常见路径
    for path in /usr/local/cuda /usr/local/cuda-*; do
        if [ -f "$path/version.txt" ]; then
            cuda_version=$(cat "$path/version.txt" | grep -oP "[0-9]+\.[0-9]+" | head -1)
            if [ -n "$cuda_version" ]; then
                echo "$cuda_version"
                return 0
            fi
        fi
    done

    return 1
}

# 根据 CUDA 版本选择 PyTorch 安装 URL
get_pytorch_index_url() {
    local cuda_version="$1"
    local major_version=$(echo "$cuda_version" | cut -d. -f1)
    local minor_version=$(echo "$cuda_version" | cut -d. -f2)

    # PyTorch 支持的 CUDA 版本映射
    # 参考: https://pytorch.org/get-started/locally/
    if [ "$major_version" -ge 12 ]; then
        if [ "$minor_version" -ge 4 ]; then
            echo "https://download.pytorch.org/whl/cu124"
        elif [ "$minor_version" -ge 1 ]; then
            echo "https://download.pytorch.org/whl/cu121"
        else
            echo "https://download.pytorch.org/whl/cu121"
        fi
    elif [ "$major_version" -eq 11 ]; then
        if [ "$minor_version" -ge 8 ]; then
            echo "https://download.pytorch.org/whl/cu118"
        else
            echo "https://download.pytorch.org/whl/cu118"
        fi
    else
        # 旧版本 CUDA，尝试使用 cu118
        echo "https://download.pytorch.org/whl/cu118"
    fi
}

# 预安装 CUDA 版本的 PyTorch
preinstall_pytorch_cuda() {
    local pip_cmd="${PIP_CMD:-pip}"
    local force_cpu="${SAGE_FORCE_CPU:-false}"

    echo ""
    echo -e "${BLUE}🔍 检测 GPU 环境...${NC}"

    # 检查是否强制使用 CPU 版本
    if [ "$force_cpu" = "true" ]; then
        echo -e "${DIM}SAGE_FORCE_CPU=true，跳过 GPU 检测${NC}"
        return 0
    fi

    # 检测 NVIDIA GPU
    if ! detect_nvidia_gpu; then
        echo -e "${YELLOW}⚠️  未检测到 NVIDIA GPU，将使用 CPU 版本 PyTorch${NC}"
        echo -e "${DIM}提示: 如果你的系统有 GPU，请确保安装了 NVIDIA 驱动${NC}"
        return 0
    fi

    echo -e "${GREEN}✅ 检测到 NVIDIA GPU${NC}"

    # 获取 CUDA 版本
    local cuda_version=$(get_cuda_version)
    if [ -z "$cuda_version" ]; then
        echo -e "${YELLOW}⚠️  无法获取 CUDA 版本，将使用默认 CUDA 12.1${NC}"
        cuda_version="12.1"
    fi

    echo -e "${GREEN}✅ CUDA 版本: $cuda_version${NC}"

    # 获取对应的 PyTorch 安装 URL
    local index_url=$(get_pytorch_index_url "$cuda_version")
    echo -e "${DIM}PyTorch 源: $index_url${NC}"

    # 检查是否已经安装了正确版本的 PyTorch
    local current_torch=$($pip_cmd show torch 2>/dev/null | grep -oP "Version: \K.*" || echo "")
    if [ -n "$current_torch" ]; then
        # 检查是否是 CUDA 版本
        local is_cuda=$(python3 -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')" 2>/dev/null || echo "unknown")
        if [ "$is_cuda" = "cuda" ]; then
            echo -e "${GREEN}✅ PyTorch CUDA 版本已安装 ($current_torch)${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  当前 PyTorch 是 CPU 版本，将升级为 CUDA 版本${NC}"
        fi
    fi

    # 安装 CUDA 版本的 PyTorch
    echo -e "${BLUE}📦 安装 PyTorch (CUDA $cuda_version)...${NC}"
    echo -e "${DIM}这可能需要几分钟，请耐心等待...${NC}"

    # 先卸载已有的 CPU 版本
    $pip_cmd uninstall -y torch torchvision torchaudio 2>/dev/null || true

    # 安装 CUDA 版本
    local install_cmd="$pip_cmd install torch torchvision torchaudio --index-url $index_url"
    echo -e "${DIM}执行: $install_cmd${NC}"

    if $install_cmd; then
        echo -e "${GREEN}✅ PyTorch CUDA 版本安装成功${NC}"

        # 验证安装
        local verify=$(python3 -c "import torch; print(f'PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}')" 2>/dev/null || echo "验证失败")
        echo -e "${DIM}验证: $verify${NC}"
    else
        echo -e "${RED}❌ PyTorch CUDA 版本安装失败${NC}"
        echo -e "${YELLOW}将继续安装，但 GPU 加速可能不可用${NC}"
        return 1
    fi

    return 0
}

# 显示 GPU 信息
show_gpu_info() {
    echo ""
    echo -e "${BLUE}🖥️  GPU 信息${NC}"

    if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null; then
        nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null | while read line; do
            echo -e "   ${GREEN}$line${NC}"
        done
    else
        echo -e "   ${DIM}无 NVIDIA GPU 或驱动未安装${NC}"
    fi
}

# 主函数（可单独运行此脚本）
main() {
    case "${1:-}" in
        "--detect")
            if detect_nvidia_gpu; then
                echo "GPU detected"
                get_cuda_version
                exit 0
            else
                echo "No GPU"
                exit 1
            fi
            ;;
        "--info")
            show_gpu_info
            ;;
        "--install"|"")
            preinstall_pytorch_cuda
            ;;
        *)
            echo "Usage: $0 [--detect|--info|--install]"
            exit 1
            ;;
    esac
}

# 如果直接运行脚本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
