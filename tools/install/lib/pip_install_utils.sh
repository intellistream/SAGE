#!/usr/bin/env bash
# ============================================================================
# PIP Installation Utilities - 智能代理处理和镜像源管理
# ============================================================================
# 核心功能：
# - 智能代理检测和自动规避（代理失效时临时禁用）
# - 多镜像源降级策略（清华 PyPI → 阿里云 → 官方）
# - 自动重试机制
#
# 设计原则：
# - 国内用户优先使用 PyPI 镜像（速度快，无需代理）
# - 检测代理是否干扰镜像源连接，若干扰则临时禁用
# - 多源降级确保安装成功率
# ============================================================================

# Include guard - 防止重复 source
if [ -n "${_SAGE_PIP_INSTALL_UTILS_LOADED:-}" ]; then
    return 0
fi
_SAGE_PIP_INSTALL_UTILS_LOADED=1

set -euo pipefail

# 颜色定义
if [ -z "${BLUE:-}" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    DIM='\033[2m'
    NC='\033[0m'
    CHECK='✓'
    CROSS='✗'
fi

# ============================================================================
# PyPI 镜像源配置
# ============================================================================
readonly TSINGHUA_PYPI="https://pypi.tuna.tsinghua.edu.cn/simple"
readonly ALIYUN_PYPI="https://mirrors.aliyun.com/pypi/simple"
readonly OFFICIAL_PYPI="https://pypi.org/simple"

# 网络状态缓存
_PIP_PROXY_CHECKED=0
_PIP_PROXY_AVAILABLE=0

# ============================================================================
# 智能代理检测（复用 conda 的逻辑）
# ============================================================================
check_and_fix_pip_proxy() {
    if [ $_PIP_PROXY_CHECKED -eq 1 ]; then
        return $_PIP_PROXY_AVAILABLE
    fi
    export _PIP_PROXY_CHECKED=1

    local proxy_vars=("http_proxy" "https_proxy" "HTTP_PROXY" "HTTPS_PROXY")

    for var in "${proxy_vars[@]}"; do
        if [ -n "${!var:-}" ]; then
            local proxy_url="${!var}"
            local host=$(echo "$proxy_url" | sed -E 's|.*://||; s|:.*||')
            local port=$(echo "$proxy_url" | sed -E 's|.*:||; s|/.*||')

            if timeout 2 bash -c "exec 3<>/dev/tcp/$host/$port 2>/dev/null" 2>/dev/null; then
                export _PIP_PROXY_AVAILABLE=0
                return 0
            else
                echo -e "${YELLOW}⚠${NC} 检测到代理配置 ($proxy_url) 但代理服务不可达" >&2
                echo -e "${DIM}  → 临时禁用代理，避免阻塞 PyPI 镜像源直连（国内镜像无需代理）${NC}" >&2

                unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
                export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
                export _PIP_PROXY_AVAILABLE=1
                return 1
            fi
        fi
    done

    export _PIP_PROXY_AVAILABLE=0
    return 0
}

# ============================================================================
# 增强的 pip install（多源降级）
# ============================================================================
pip_install_robust() {
    if [ $# -eq 0 ]; then
        echo -e "${RED}错误：未指定要安装的包${NC}" >&2
        return 1
    fi

    # 智能代理检测
    check_and_fix_pip_proxy || true

    local pip_cmd="${1}"
    shift
    local args=("$@")

    # 定义降级策略
    local -a mirror_strategies=(
        "清华PyPI:$TSINGHUA_PYPI"
        "阿里云PyPI:$ALIYUN_PYPI"
        "官方PyPI:$OFFICIAL_PYPI"
    )

    echo -e "${DIM}安装 Python 包（多源降级策略）${NC}" >&2

    for strategy in "${mirror_strategies[@]}"; do
        IFS=':' read -r name mirror <<< "$strategy"

        echo -e "${DIM}尝试 $name...${NC}" >&2

        # 尝试安装（静默失败）
        local install_output
        install_output=$($pip_cmd install -i "$mirror" "${args[@]}" 2>&1 || true)
        local exit_code=$?

        # 检查是否成功
        if [ $exit_code -eq 0 ] && ! echo "$install_output" | grep -qE "(ProxyError|Connection refused|Failed to establish|ERROR:)"; then
            echo -e "${GREEN}${CHECK}${NC} 使用 $name 成功安装${NC}" >&2
            return 0
        else
            if echo "$install_output" | grep -qE "(ProxyError|Connection refused)"; then
                echo -e "${DIM}  → 网络连接失败，切换下一个源${NC}" >&2
            fi
        fi
    done

    # 所有策略都失败
    echo -e "${RED}${CROSS}${NC} Python 包安装失败${NC}" >&2
    echo -e "${DIM}  已尝试所有 PyPI 源（清华、阿里云、官方），均失败${NC}" >&2
    return 1
}

# 导出函数
export -f check_and_fix_pip_proxy
export -f pip_install_robust

echo -e "${GREEN}${CHECK}${NC} PIP install utils loaded" >&2
