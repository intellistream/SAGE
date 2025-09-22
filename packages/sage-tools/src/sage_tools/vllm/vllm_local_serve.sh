#!/usr/bin/env bash
set -euo pipefail

# VLLM 本地服务启动脚本
# 
# 使用方法:
#   ./vllm_local_serve.sh                          # 使用默认模型（交互式确认）
#   ./vllm_local_serve.sh <model_name>             # 使用指定模型（交互式确认）
#   ./vllm_local_serve.sh --yes                    # 使用默认模型（自动确认）
#   ./vllm_local_serve.sh --yes <model_name>       # 使用指定模型（自动确认）
#
# 示例:
#   ./vllm_local_serve.sh microsoft/DialoGPT-small   # 更小的模型 (~500MB)
#   ./vllm_local_serve.sh microsoft/DialoGPT-medium  # 中等模型 (~1.5GB) 
#   ./vllm_local_serve.sh microsoft/DialoGPT-large   # 较大模型 (~3GB)
#   ./vllm_local_serve.sh --yes meta-llama/Llama-2-7b-chat-hf  # 大模型，自动确认
#
# 功能:
#   - 自动检测和安装 vllm
#   - 检查模型是否存在，提示下载信息
#   - 自动设置 HuggingFace 镜像（当无法访问官网时）
#   - 友好的用户交互提示（可通过 --yes 跳过）

# 默认模型 (使用较小的模型便于快速启动和测试)
DEFAULT_MODEL="microsoft/DialoGPT-small"

# 解析命令行参数
AUTO_YES=false
MODEL=""

for arg in "$@"; do
    case $arg in
        --yes|-y)
            AUTO_YES=true
            shift
            ;;
        --help|-h)
            echo "用法: $0 [选项] [模型名称]"
            echo ""
            echo "选项:"
            echo "  --yes, -y       自动确认所有提示"
            echo "  --help, -h      显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                                    # 使用默认模型"
            echo "  $0 microsoft/DialoGPT-medium          # 使用指定模型"
            echo "  $0 --yes microsoft/DialoGPT-small     # 自动确认并使用指定模型"
            exit 0
            ;;
        *)
            if [[ -z "$MODEL" ]]; then
                MODEL="$arg"
            fi
            ;;
    esac
done

# 如果没有指定模型，使用默认模型
MODEL=${MODEL:-$DEFAULT_MODEL}

# 颜色输出函数
print_info() {
    echo -e "\033[32m[INFO]\033[0m $1"
}

print_warning() {
    echo -e "\033[33m[WARNING]\033[0m $1"
}

print_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

# 检查并设置 HuggingFace 镜像
setup_hf_mirror() {
    print_info "检查网络连接和 HuggingFace 访问..."
    
    # 测试是否可以访问 HuggingFace
    if ! curl -s --connect-timeout 5 https://huggingface.co > /dev/null 2>&1; then
        print_warning "无法连接到 HuggingFace.co，设置国内镜像..."
        export HF_ENDPOINT=https://hf-mirror.com
        print_info "已设置 HuggingFace 镜像: $HF_ENDPOINT"
    else
        print_info "HuggingFace 连接正常"
    fi
}

# 检查模型是否存在
check_model_exists() {
    local model_name=$1
    local cache_dir=${HF_HOME:-~/.cache/huggingface}
    local model_path="$cache_dir/hub/models--$(echo $model_name | tr '/' '-')"
    
    if [ -d "$model_path" ]; then
        print_info "模型 $model_name 已存在于本地缓存"
        return 0
    else
        return 1
    fi
}

# 提示用户下载模型
prompt_model_download() {
    local model_name=$1
    print_warning "模型 $model_name 在本地不存在"
    
    # 根据不同模型提供相应的大小信息
    case $model_name in
        "microsoft/DialoGPT-medium")
            print_info "该模型大约需要 1.5GB 存储空间"
            ;;
        "microsoft/DialoGPT-small")
            print_info "该模型大约需要 500MB 存储空间"
            ;;
        "microsoft/DialoGPT-large")
            print_info "该模型大约需要 3GB 存储空间"
            ;;
        *llama*13b*)
            print_info "该模型大约需要 26GB 存储空间"
            ;;
        *llama*7b*)
            print_info "该模型大约需要 14GB 存储空间"
            ;;
        *)
            print_info "模型大小取决于具体模型，请确保有足够磁盘空间"
            ;;
    esac
    
    print_info "首次使用时将自动从 HuggingFace 下载，请确保："
    print_info "  1. 有足够的磁盘空间"
    print_info "  2. 网络连接稳定（下载可能需要一些时间）"
    print_info "  3. 如果下载失败，请检查网络或考虑使用其他模型"
    
    echo
    
    if [[ "$AUTO_YES" == "true" ]]; then
        print_info "自动确认模式：继续启动服务..."
        return 0
    fi
    
    read -p "是否继续启动服务？模型将在启动时自动下载 [y/N]: " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "取消启动。您可以："
        print_info "  1. 使用其他已下载的模型: $0 <model_name>"
        print_info "  2. 手动下载模型: huggingface-cli download $model_name"
        print_info "  3. 使用更小的模型: $0 microsoft/DialoGPT-small"
        print_info "  4. 使用自动确认: $0 --yes $model_name"
        exit 0
    fi
}

# 检查 vllm 是否已安装
if ! command -v vllm >/dev/null 2>&1; then
    print_info "vllm 未找到，正在通过 conda 安装..."
    conda install -y -c conda-forge vllm
    if [ $? -ne 0 ]; then
        print_error "vllm 安装失败，请检查 conda 环境"
        exit 1
    fi
fi

print_info "=== VLLM 本地服务启动脚本 ==="
print_info "模型: $MODEL"

# 设置镜像
setup_hf_mirror

# 检查模型是否存在
if ! check_model_exists "$MODEL"; then
    prompt_model_download "$MODEL"
fi

print_info "正在启动 VLLM 服务..."
print_info "服务将在 http://localhost:8000 上运行"
print_info "API Key: token-abc123"
print_info "按 Ctrl+C 停止服务"

# 启动 vllm 本地服务
vllm serve "$MODEL" --dtype auto --api-key token-abc123