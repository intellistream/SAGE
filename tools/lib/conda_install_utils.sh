#!/usr/bin/env bash
# ============================================================================
# Conda Installation Utilities - 统一的 Conda ToS Bypass 工具集
# ============================================================================
# 提供绕过 Conda 25.x ToS 限制的统一接口
# 核心原理：使用清华镜像源 + --override-channels 标志
# ============================================================================

# Include guard - 防止重复 source
if [ -n "${_SAGE_CONDA_INSTALL_UTILS_LOADED:-}" ]; then
    return 0
fi
_SAGE_CONDA_INSTALL_UTILS_LOADED=1

set -euo pipefail

# 颜色定义（如果未加载 logging.sh）
if [ -z "${BLUE:-}" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    DIM='\033[2m'
    NC='\033[0m'
    CHECK='✓'
    CROSS='✗'
    GEAR='⚙'
fi

# ============================================================================
# 镜像源配置
# ============================================================================
readonly TSINGHUA_MIRROR_MAIN="https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main"
readonly TSINGHUA_MIRROR_FORGE="https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge"
readonly ALIYUN_MIRROR_MAIN="https://mirrors.aliyun.com/anaconda/pkgs/main"
readonly ALIYUN_MIRROR_FORGE="https://mirrors.aliyun.com/anaconda/cloud/conda-forge"

# ============================================================================
# 网络诊断和自动修复
# ============================================================================

# 检测代理是否真实可用
check_and_fix_proxy() {
    # 只检测一次（使用全局变量缓存结果）
    if [ "${_PROXY_CHECKED:-0}" -eq 1 ]; then
        return "${_PROXY_AVAILABLE:-0}"
    fi
    export _PROXY_CHECKED=1

    # 检查是否配置了代理
    local proxy_vars=("http_proxy" "https_proxy" "HTTP_PROXY" "HTTPS_PROXY")

    for var in "${proxy_vars[@]}"; do
        if [ -n "${!var:-}" ]; then
            local proxy_url="${!var}"

            # 提取主机和端口
            local host=$(echo "$proxy_url" | sed -E 's|.*://||; s|:.*||')
            local port=$(echo "$proxy_url" | sed -E 's|.*:||; s|/.*||')

            # 快速测试代理是否可达（2秒超时）
            if timeout 2 bash -c "exec 3<>/dev/tcp/$host/$port 2>/dev/null" 2>/dev/null; then
                export _PROXY_AVAILABLE=0
                return 0
            else
                echo -e "${YELLOW}⚠${NC} 检测到代理配置 ($proxy_url) 但代理服务不可达" >&2
                echo -e "${DIM}  → 临时禁用代理，避免阻塞镜像源直连（国内镜像无需代理）${NC}" >&2

                # 临时禁用代理（仅对当前进程）
                unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
                export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
                export _PROXY_AVAILABLE=1
                return 1
            fi
        fi
    done

    # 没有配置代理
    export _PROXY_AVAILABLE=0
    return 0
}


# ============================================================================
# 1. Conda 包安装（绕过 ToS）
# ============================================================================
# 用法：conda_install_bypass nodejs python=3.11 numpy
# 功能：自动尝试主频道和 conda-forge 频道
conda_install_bypass() {
    if [ $# -eq 0 ]; then
        echo -e "${RED}错误：未指定要安装的包${NC}" >&2
        return 1
    fi

    # 智能代理检测和修复
    check_and_fix_proxy || true

    local packages=("$@")
    local env_flag=""

    # 检查是否指定了环境（-n 或 --name 参数）
    local i=0
    while [ $i -lt ${#packages[@]} ]; do
        if [[ "${packages[$i]}" == "-n" || "${packages[$i]}" == "--name" ]]; then
            env_flag="-n ${packages[$((i+1))]}"
            # 移除 -n 和环境名
            unset 'packages[i]'
            unset 'packages[i+1]'
            packages=("${packages[@]}")
            break
        fi
        ((i++))
    done

    echo -e "${DIM}使用国内镜像源安装包（绕过 ToS，加速下载）: ${packages[*]}${NC}" >&2

    # 首先尝试主频道
    if conda install $env_flag -y --override-channels -c "$TSINGHUA_MIRROR_MAIN" "${packages[@]}" 2>/dev/null; then
        echo -e "${GREEN}${CHECK}${NC} 使用主频道成功安装${NC}" >&2
        return 0
    fi

    # 回退到 conda-forge 频道
    echo -e "${YELLOW}主频道失败，尝试 conda-forge...${NC}" >&2
    if conda install $env_flag -y --override-channels -c "$TSINGHUA_MIRROR_FORGE" "${packages[@]}" 2>/dev/null; then
        echo -e "${GREEN}${CHECK}${NC} 使用 conda-forge 成功安装${NC}" >&2
        return 0
    fi

    # 回退到阿里云主频道
    echo -e "${YELLOW}清华镜像失败，尝试阿里云...${NC}" >&2
    if conda install $env_flag -y --override-channels -c "$ALIYUN_MIRROR_MAIN" "${packages[@]}" 2>/dev/null; then
        echo -e "${GREEN}${CHECK}${NC} 使用阿里云主频道成功安装${NC}" >&2
        return 0
    fi

    # 回退到阿里云 conda-forge
    if conda install $env_flag -y --override-channels -c "$ALIYUN_MIRROR_FORGE" "${packages[@]}" 2>/dev/null; then
        echo -e "${GREEN}${CHECK}${NC} 使用阿里云 conda-forge 成功安装${NC}" >&2
        return 0
    fi

    # 最后尝试官方源（不使用 --override-channels）
    echo -e "${YELLOW}镜像源均失败，尝试官方源...${NC}" >&2
    if conda install $env_flag -y -c conda-forge "${packages[@]}"; then
        echo -e "${GREEN}${CHECK}${NC} 使用官方源成功安装${NC}" >&2
        return 0
    else
        echo -e "${RED}${CROSS}${NC} 包安装失败: ${packages[*]}${NC}" >&2
        echo -e "${DIM}  已尝试所有镜像源（清华、阿里云、官方），均失败${NC}" >&2
        return 1
    fi
}

# ============================================================================
# 2. Conda 环境创建（绕过 ToS）
# ============================================================================
# 用法：conda_create_bypass my-env python=3.11
# 功能：创建新环境，自动使用清华镜像源
conda_create_bypass() {
    if [ $# -lt 2 ]; then
        echo -e "${RED}错误：用法 conda_create_bypass <env_name> <python_version> [packages...]${NC}" >&2
        return 1
    fi

    local env_name="$1"
    shift
    local packages=("$@")

    # 检查环境是否已存在
    if conda env list | grep -q "^${env_name} "; then
        echo -e "${YELLOW}环境 '$env_name' 已存在，跳过创建${NC}" >&2
        return 0
    fi

    echo -e "${DIM}使用清华镜像源创建环境（绕过 ToS）: $env_name${NC}" >&2

    # 首先尝试主频道
    if conda create -n "$env_name" -y --override-channels -c "$TSINGHUA_MIRROR_MAIN" "${packages[@]}" 2>/dev/null; then
        echo -e "${GREEN}${CHECK}${NC} 使用主频道成功创建环境${NC}" >&2
        return 0
    fi

    # 回退到 conda-forge 频道
    echo -e "${YELLOW}主频道失败，尝试 conda-forge...${NC}" >&2
    if conda create -n "$env_name" -y --override-channels -c "$TSINGHUA_MIRROR_FORGE" "${packages[@]}"; then
        echo -e "${GREEN}${CHECK}${NC} 使用 conda-forge 成功创建环境${NC}" >&2
        return 0
    else
        echo -e "${RED}${CROSS}${NC} 环境创建失败: $env_name${NC}" >&2
        return 1
    fi
}

# ============================================================================
# 3. 带进度显示的包安装（推荐用于长时间安装）
# ============================================================================
# 用法：conda_install_with_progress "安装 Node.js" nodejs
conda_install_with_progress() {
    local task_desc="$1"
    shift
    local packages=("$@")

    # 加载进度工具（如果可用）
    if declare -f run_with_progress >/dev/null 2>&1; then
        run_with_progress "$task_desc" conda_install_bypass "${packages[@]}"
    else
        echo -e "${BLUE}${GEAR}${NC} $task_desc..." >&2
        conda_install_bypass "${packages[@]}"
    fi
}

# ============================================================================
# 4. 静默安装（禁止输出，适合批处理）
# ============================================================================
# 用法：conda_install_silent nodejs python=3.11
conda_install_silent() {
    conda_install_bypass "$@" >/dev/null 2>&1
}

# ============================================================================
# 5. 获取推荐的镜像源（根据频道类型）
# ============================================================================
# 用法：
#   mirror=$(get_conda_mirror "main")     # 主频道
#   mirror=$(get_conda_mirror "forge")    # conda-forge
get_conda_mirror() {
    local channel="${1:-main}"

    case "$channel" in
        main|Main|MAIN)
            echo "$TSINGHUA_MIRROR_MAIN"
            ;;
        forge|conda-forge|Forge)
            echo "$TSINGHUA_MIRROR_FORGE"
            ;;
        *)
            echo -e "${YELLOW}警告：未知频道 '$channel'，返回主频道${NC}" >&2
            echo "$TSINGHUA_MIRROR_MAIN"
            ;;
    esac
}

# ============================================================================
# 6. 测试 Conda 环境是否可用（创建临时环境测试）
# ============================================================================
# 用法：test_conda_bypass
# 返回：0 成功，1 失败
test_conda_bypass() {
    local test_env="sage_test_$$"

    echo -e "${BLUE}测试 Conda ToS bypass...${NC}" >&2

    if conda_create_bypass "$test_env" python=3.11 >/dev/null 2>&1; then
        conda env remove -n "$test_env" -y >/dev/null 2>&1
        echo -e "${GREEN}${CHECK}${NC} Conda ToS bypass 测试通过${NC}" >&2
        return 0
    else
        echo -e "${RED}${CROSS}${NC} Conda ToS bypass 测试失败${NC}" >&2
        return 1
    fi
}

# ============================================================================
# 导出函数
# ============================================================================
export -f conda_install_bypass 2>/dev/null || true
export -f conda_create_bypass 2>/dev/null || true
export -f conda_install_with_progress 2>/dev/null || true
export -f conda_install_silent 2>/dev/null || true
export -f get_conda_mirror 2>/dev/null || true
export -f test_conda_bypass 2>/dev/null || true

# ============================================================================
# 使用示例（注释掉）
# ============================================================================
# # 1. 安装单个包
# conda_install_bypass nodejs
#
# # 2. 安装多个包
# conda_install_bypass python=3.11 numpy pandas
#
# # 3. 安装到指定环境
# conda_install_bypass -n myenv python=3.11
#
# # 4. 创建新环境
# conda_create_bypass myenv python=3.11 numpy pandas
#
# # 5. 带进度显示的安装（需要先加载 progress_utils.sh）
# source "$(dirname "${BASH_SOURCE[0]}")/progress_utils.sh"
# conda_install_with_progress "安装 Node.js" nodejs
#
# # 6. 测试 bypass 是否工作
# if test_conda_bypass; then
#     echo "Conda bypass 工作正常"
# fi
