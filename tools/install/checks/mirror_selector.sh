#!/bin/bash
# SAGE 网络镜像自动选择模块
# 功能：测试多个 PyPI 镜像速度，自动选择最快的

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# PyPI 镜像列表（官方 + 常用国内镜像）

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
PIP_CONCURRENT_DOWNLOADS="${PIP_CONCURRENT_DOWNLOADS:-}"
PIP_PREFER_BINARY="${PIP_PREFER_BINARY:-}"
PIP_NO_WARN_SCRIPT_LOCATION="${PIP_NO_WARN_SCRIPT_LOCATION:-}"
PIP_DISABLE_PIP_VERSION_CHECK="${PIP_DISABLE_PIP_VERSION_CHECK:-}"
PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-}"
PIP_NO_CACHE_DIR="${PIP_NO_CACHE_DIR:-}"
PIP_INDEX_URL="${PIP_INDEX_URL:-}"
HF_ENDPOINT="${HF_ENDPOINT:-}"
# ============================================================================

declare -A PYPI_MIRRORS=(
    ["官方源"]="https://pypi.org/simple"
    ["清华大学"]="https://pypi.tuna.tsinghua.edu.cn/simple"
    ["阿里云"]="https://mirrors.aliyun.com/pypi/simple"
    ["腾讯云"]="https://mirrors.cloud.tencent.com/pypi/simple"
    ["华为云"]="https://repo.huaweicloud.com/repository/pypi/simple"
    ["豆瓣"]="https://pypi.doubanio.com/simple"
    ["中国科技大学"]="https://pypi.mirrors.ustc.edu.cn/simple"
)

# 测试镜像速度（使用 HTTP 响应时间）
test_mirror_speed() {
    local mirror_url="$1"
    local test_package="${2:-pip}"  # 默认测试 pip 包

    # 构造测试 URL
    local test_url="${mirror_url}/${test_package}/"

    # 使用 curl 测试（如果可用）
    if command -v curl &> /dev/null; then
        local start_time=$(date +%s%3N)
        if curl -s --connect-timeout 5 --max-time 10 -o /dev/null -w "%{http_code}" "$test_url" 2>/dev/null | grep -q "200\|301\|302"; then
            local end_time=$(date +%s%3N)
            local duration=$((end_time - start_time))
            echo "$duration"
            return 0
        else
            echo "99999"  # 失败返回极大值
            return 1
        fi
    # 使用 wget 测试（备选）
    elif command -v wget &> /dev/null; then
        local start_time=$(date +%s%3N)
        if wget -q --spider --timeout=10 --tries=1 "$test_url" 2>/dev/null; then
            local end_time=$(date +%s%3N)
            local duration=$((end_time - start_time))
            echo "$duration"
            return 0
        else
            echo "99999"
            return 1
        fi
    else
        echo -e "${WARNING} 无法测试镜像速度：未安装 curl 或 wget"
        echo "99999"
        return 1
    fi
}

extract_mirror_artifact_url() {
    local mirror_url="$1"
    local test_package="${2:-pip}"
    local test_url="${mirror_url}/${test_package}/"

    if ! command -v curl >/dev/null 2>&1; then
        return 1
    fi

    local html
    html="$(curl -L -s --connect-timeout 5 --max-time 12 "$test_url" 2>/dev/null || true)"
    [ -n "$html" ] || return 1

    local href
    href="$(printf '%s' "$html" | tr '\n' ' ' | grep -oE 'href="[^"]+"' | head -n 1 | sed 's/^href="//;s/"$//')"
    [ -n "$href" ] || return 1

    python3 - <<PY
from urllib.parse import urljoin
print(urljoin(${test_url@Q}, ${href@Q}))
PY
}

verify_mirror_download_capability() {
    local mirror_url="$1"
    local test_package="${2:-pip}"

    local artifact_url
    artifact_url="$(extract_mirror_artifact_url "$mirror_url" "$test_package" 2>/dev/null || true)"
    [ -n "$artifact_url" ] || return 0

    if ! command -v curl >/dev/null 2>&1; then
        return 1
    fi

    local status
    status="$(curl -L -s -I --connect-timeout 5 --max-time 12 -o /dev/null -w "%{http_code}" "$artifact_url" 2>/dev/null || echo "000")"

    case "$status" in
        200|204|206|301|302)
            return 0
            ;;
        405|000)
            status="$(curl -L -s --range 0-0 --connect-timeout 5 --max-time 12 -o /dev/null -w "%{http_code}" "$artifact_url" 2>/dev/null || echo "000")"
            case "$status" in
                200|204|206|301|302)
                    return 0
                    ;;
                *)
                    return 1
                    ;;
            esac
            ;;
        *)
            return 1
            ;;
    esac
}

# 自动选择最快的镜像
auto_select_fastest_mirror() {
    local test_package="${1:-pip}"
    local verbose="${2:-true}"

    if [ "$verbose" = "true" ]; then
        echo -e "${BLUE}🔍 测试 PyPI 镜像速度...${NC}"
        echo ""
    fi

    local fastest_mirror=""
    local fastest_mirror_url=""
    local fastest_time=99999

    # 测试每个镜像
    for mirror_name in "${!PYPI_MIRRORS[@]}"; do
        local mirror_url="${PYPI_MIRRORS[$mirror_name]}"

        if [ "$verbose" = "true" ]; then
            echo -e "${DIM}   测试 $mirror_name...${NC}"
        fi

        local response_time=$(test_mirror_speed "$mirror_url" "$test_package")
        local download_ok=true
        if [ "$response_time" -lt 99999 ]; then
            if ! verify_mirror_download_capability "$mirror_url" "$test_package"; then
                download_ok=false
                response_time=99999
            fi
        fi

        if [ "$verbose" = "true" ]; then
            if [ "$response_time" -lt 99999 ]; then
                echo -e "${GREEN}   ✅ $mirror_name: ${response_time}ms${NC}"
            else
                if [ "$download_ok" = "false" ]; then
                    echo -e "${RED}   ❌ $mirror_name: 元信息可达，但包下载不可用（疑似 403）${NC}"
                else
                    echo -e "${RED}   ❌ $mirror_name: 超时或不可达${NC}"
                fi
            fi
        fi

        # 更新最快镜像
        if [ "$response_time" -lt "$fastest_time" ]; then
            fastest_time=$response_time
            fastest_mirror="$mirror_name"
            fastest_mirror_url="$mirror_url"
        fi
    done

    echo ""

    # 返回最快镜像信息
    if [ -n "$fastest_mirror" ] && [ "$fastest_time" -lt 99999 ]; then
        if [ "$verbose" = "true" ]; then
            echo -e "${GREEN}🚀 推荐使用: $fastest_mirror (响应时间: ${fastest_time}ms)${NC}"
            echo -e "${DIM}   URL: $fastest_mirror_url${NC}"
        fi

        echo "$fastest_mirror_url"
        return 0
    else
        if [ "$verbose" = "true" ]; then
            echo -e "${YELLOW}⚠️  无法访问任何镜像，将使用默认官方源${NC}"
        fi

        echo "https://pypi.org/simple"
        return 1
    fi
}

# 配置 pip 使用指定镜像
configure_pip_mirror() {
    local mirror_url="$1"
    local permanent="${2:-false}"  # 是否永久配置（写入 pip.conf）

    if [ "$permanent" = "true" ]; then
        echo -e "${INFO} 永久配置 pip 镜像..."

        # 获取 pip 配置目录
        local pip_config_dir=""
        if [ -n "${VIRTUAL_ENV:-}" ]; then
            # 虚拟环境配置
            pip_config_dir="${VIRTUAL_ENV:-}/pip.conf"
        elif [ "$(uname)" = "Darwin" ]; then
            # macOS
            pip_config_dir="$HOME/Library/Application Support/pip/pip.conf"
        else
            # Linux
            pip_config_dir="$HOME/.config/pip/pip.conf"
        fi

        # 创建目录
        mkdir -p "$(dirname "$pip_config_dir")"

        # 写入配置
        cat > "$pip_config_dir" << EOF
[global]
index-url = $mirror_url
trusted-host = $(echo "$mirror_url" | sed 's|https\?://||' | cut -d'/' -f1)

[install]
trusted-host = $(echo "$mirror_url" | sed 's|https\?://||' | cut -d'/' -f1)
EOF

        echo -e "${CHECK} ✓ 已配置 pip 镜像: $pip_config_dir"
    else
        # 临时配置（通过环境变量）
        echo -e "${INFO} 临时配置 pip 镜像..."
        export PIP_INDEX_URL="$mirror_url"
        export PIP_TRUSTED_HOST=$(echo "$mirror_url" | sed 's|https\?://||' | cut -d'/' -f1)
        echo -e "${CHECK} ✓ 已设置环境变量 PIP_INDEX_URL"
    fi
}

# 应用 pip 下载优化配置（新增）
apply_pip_optimizations() {
    echo -e "${BLUE}🚀 应用 pip 下载优化...${NC}"

    # 1. 并行下载（pip 20.3+）
    if [ -z "${PIP_CONCURRENT_DOWNLOADS}" ]; then
        export PIP_CONCURRENT_DOWNLOADS=8
        echo -e "${CHECK} 并行下载: 8 线程"
    fi

    # 2. 优先使用预编译包（避免编译耗时）
    if [ -z "${PIP_PREFER_BINARY}" ]; then
        export PIP_PREFER_BINARY=1
        echo -e "${CHECK} 优先使用预编译包"
    fi

    # 3. 禁用 pip 版本检查（减少网络请求）
    if [ -z "${PIP_DISABLE_PIP_VERSION_CHECK}" ]; then
        export PIP_DISABLE_PIP_VERSION_CHECK=1
        echo -e "${CHECK} 禁用版本检查"
    fi

    # 4. 设置合理的超时时间
    if [ -z "${PIP_DEFAULT_TIMEOUT}" ]; then
        export PIP_DEFAULT_TIMEOUT=60
        echo -e "${CHECK} 超时设置: 60 秒"
    fi

    # 5. CI 环境中禁用缓存（节省磁盘空间）
    if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" ]]; then
        if [ -z "${PIP_NO_CACHE_DIR}" ]; then
            export PIP_NO_CACHE_DIR=1
            echo -e "${DIM}CI 环境: 禁用 pip 缓存${NC}"
        fi
    fi

    echo ""
}

# 智能配置 pip（镜像 + 优化）
smart_configure_pip() {
    local auto_detect="${1:-true}"
    local apply_optimizations="${2:-true}"

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🌐 智能 pip 配置${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 检测网络环境（复用 Python 模块）
    local use_china_mirror=false
    if [ "$auto_detect" = "true" ]; then
        local python_cmd="${PYTHON_CMD:-python3}"

        # 优先使用环境变量强制标记
        if [ "${SAGE_FORCE_CHINA_MIRROR}" = "true" ]; then
            use_china_mirror=true
            echo -e "${INFO} 环境变量强制启用中国镜像"
        # 调用 Python 模块检测
        elif $python_cmd -c "from sage.common.config.network import detect_china_mainland; exit(0 if detect_china_mainland() else 1)" 2>/dev/null; then
            use_china_mirror=true
            echo -e "${INFO} 检测到中国大陆网络环境"
        # 降级方案：简单网络测试
        elif ! curl -s --connect-timeout 2 https://pypi.org >/dev/null 2>&1; then
            if curl -s --connect-timeout 2 https://pypi.tuna.tsinghua.edu.cn >/dev/null 2>&1; then
                use_china_mirror=true
                echo -e "${INFO} 网络测试：建议使用国内镜像"
            fi
        fi
    fi

    # 配置镜像源
    if [ "$use_china_mirror" = "true" ]; then
        # 默认使用清华镜像（稳定可靠）
        local mirror_url="https://pypi.tuna.tsinghua.edu.cn/simple"
        echo -e "${CHECK} 使用清华 PyPI 镜像"
        configure_pip_mirror "$mirror_url" "false"
    else
        echo -e "${DIM}使用 PyPI 官方源${NC}"
    fi

    echo ""

    # 应用下载优化
    if [ "$apply_optimizations" = "true" ]; then
        apply_pip_optimizations
    fi

    # 显示配置摘要
    show_config_summary

    # 估算加速效果
    estimate_speedup

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# 显示当前配置摘要
show_config_summary() {
    echo -e "${BLUE}📊 当前配置摘要:${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ -n "${PIP_INDEX_URL}" ]; then
        echo -e "  PyPI 源: ${GREEN}$PIP_INDEX_URL${NC}"
    else
        echo -e "  PyPI 源: ${DIM}默认（https://pypi.org/simple）${NC}"
    fi

    if [ -n "${HF_ENDPOINT}" ]; then
        echo -e "  HF 镜像: ${GREEN}$HF_ENDPOINT${NC}"
    else
        echo -e "  HF 镜像: ${DIM}默认（https://huggingface.co）${NC}"
    fi

    echo -e "  并行下载: ${CYAN}${PIP_CONCURRENT_DOWNLOADS:-1}${NC} 线程"
    echo -e "  优先二进制: ${CYAN}${PIP_PREFER_BINARY:-0}${NC}"
    echo -e "  超时设置: ${CYAN}${PIP_DEFAULT_TIMEOUT:-15}${NC} 秒"

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# 估算加速效果
estimate_speedup() {
    local use_mirror=false
    if [ -n "${PIP_INDEX_URL}" ] && [[ "${PIP_INDEX_URL}" =~ (tuna|aliyun|ustc|tencent|huawei|douban) ]]; then
        use_mirror=true
    fi

    echo -e "${BLUE}⚡ 预期加速效果:${NC}"

    if [ "$use_mirror" = "true" ]; then
        echo -e "  ${GREEN}▸${NC} 下载速度: ${GREEN}5-10 倍提升${NC} (国内镜像)"
        echo -e "  ${GREEN}▸${NC} 依赖解析: ${GREEN}2-3 倍提升${NC} (低延迟)"
    fi

    if [ "${PIP_CONCURRENT_DOWNLOADS:-0}" -gt 1 ]; then
        echo -e "  ${GREEN}▸${NC} 并行下载: ${GREEN}30-50% 提升${NC}"
    fi

    if [ "${PIP_PREFER_BINARY:-0}" -eq 1 ]; then
        echo -e "  ${GREEN}▸${NC} 避免编译: ${GREEN}节省 10-20 分钟${NC}"
    fi

    local total_speedup="2-3 倍"
    if [ "$use_mirror" = "true" ]; then
        total_speedup="3-5 倍"
    fi

    echo -e "  ${BOLD}${GREEN}总体预期: ${total_speedup} 安装加速${NC}"
    echo ""
}

# 获取 pip install 命令的镜像参数
get_pip_mirror_args() {
    local mirror_url="$1"

    local trusted_host=$(echo "$mirror_url" | sed 's|https\?://||' | cut -d'/' -f1)

    echo "-i $mirror_url --trusted-host $trusted_host"
}

# 显示所有镜像列表
show_mirror_list() {
    echo -e "${BLUE}📋 可用的 PyPI 镜像列表:${NC}"
    echo ""

    local index=1
    for mirror_name in "${!PYPI_MIRRORS[@]}"; do
        local mirror_url="${PYPI_MIRRORS[$mirror_name]}"
        echo -e "${DIM}$index. ${NC}${GREEN}$mirror_name${NC}"
        echo -e "${DIM}   $mirror_url${NC}"
        echo ""
        index=$((index + 1))
    done
}

# 交互式选择镜像
interactive_select_mirror() {
    echo -e "${BLUE}${BOLD}选择 PyPI 镜像源${NC}"
    echo ""

    # 显示镜像列表
    local mirror_names=()
    local mirror_urls=()
    local index=1

    for mirror_name in "${!PYPI_MIRRORS[@]}"; do
        mirror_names+=("$mirror_name")
        mirror_urls+=("${PYPI_MIRRORS[$mirror_name]}")
        echo -e "${DIM}$index.${NC} ${GREEN}$mirror_name${NC} ${DIM}(${PYPI_MIRRORS[$mirror_name]})${NC}"
        index=$((index + 1))
    done

    echo ""
    echo -e "${YELLOW}0.${NC} ${GREEN}自动选择最快镜像${NC} ${DIM}(推荐)${NC}"
    echo ""

    # 读取用户选择
    read -p "请选择镜像 [0-$((${#mirror_names[@]}))]: " -r choice

    if [ "$choice" = "0" ] || [ -z "$choice" ]; then
        # 自动选择
        echo ""
        auto_select_fastest_mirror
    elif [ "$choice" -ge 1 ] && [ "$choice" -le "${#mirror_names[@]}" ]; then
        # 手动选择
        local selected_index=$((choice - 1))
        echo "${mirror_urls[$selected_index]}"
    else
        # 无效选择，使用官方源
        echo -e "${YELLOW}⚠️  无效选择，使用官方源${NC}"
        echo "https://pypi.org/simple"
    fi
}

# 测试特定镜像是否可用
test_mirror_availability() {
    local mirror_url="$1"
    local mirror_name="${2:-镜像}"

    echo -e "${INFO} 测试 $mirror_name 可用性..."

    local response_time=$(test_mirror_speed "$mirror_url")

    if [ "$response_time" -lt 99999 ]; then
        echo -e "${GREEN}   ✅ $mirror_name 可用 (${response_time}ms)${NC}"
        return 0
    else
        echo -e "${RED}   ❌ $mirror_name 不可用或超时${NC}"
        return 1
    fi
}

# 主函数（用于脚本直接运行）
main() {
    local command="${1:-help}"

    case "$command" in
        auto|a)
            # 自动选择最快镜像
            auto_select_fastest_mirror
            ;;
        list|l)
            # 显示镜像列表
            show_mirror_list
            ;;
        interactive|i)
            # 交互式选择
            interactive_select_mirror
            ;;
        test|t)
            # 测试指定镜像
            local mirror_url="${2:-https://pypi.org/simple}"
            test_mirror_availability "$mirror_url" "指定镜像"
            ;;
        configure|c)
            # 配置 pip 镜像
            local mirror_url="${2:-$(auto_select_fastest_mirror)}"
            local permanent="${3:-false}"
            configure_pip_mirror "$mirror_url" "$permanent"
            ;;
        args)
            # 获取 pip 命令参数
            local mirror_url="${2:-$(auto_select_fastest_mirror "pip" "false")}"
            get_pip_mirror_args "$mirror_url"
            ;;
        help|h|*)
            echo "SAGE PyPI 镜像选择工具"
            echo ""
            echo "用法: $0 <command> [options]"
            echo ""
            echo "命令:"
            echo "  auto, a                    自动选择最快的镜像"
            echo "  list, l                    显示所有可用镜像"
            echo "  interactive, i             交互式选择镜像"
            echo "  test, t <url>              测试指定镜像"
            echo "  configure, c <url> [perm]  配置 pip 使用镜像"
            echo "  args <url>                 获取 pip install 参数"
            echo "  help, h                    显示此帮助"
            echo ""
            echo "示例:"
            echo "  $0 auto                    # 自动选择并显示最快镜像"
            echo "  $0 interactive             # 交互式选择镜像"
            echo "  $0 configure auto true     # 永久配置自动选择的镜像"
            echo ""
            ;;
    esac
}

# 如果脚本被直接运行，执行主函数
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
