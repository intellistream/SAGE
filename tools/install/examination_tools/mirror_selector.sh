#!/bin/bash
# SAGE 网络镜像自动选择模块
# 功能：测试多个 PyPI 镜像速度，自动选择最快的

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# PyPI 镜像列表（官方 + 常用国内镜像）
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

        if [ "$verbose" = "true" ]; then
            if [ "$response_time" -lt 99999 ]; then
                echo -e "${GREEN}   ✅ $mirror_name: ${response_time}ms${NC}"
            else
                echo -e "${RED}   ❌ $mirror_name: 超时或不可达${NC}"
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
        if [ -n "$VIRTUAL_ENV" ]; then
            # 虚拟环境配置
            pip_config_dir="$VIRTUAL_ENV/pip.conf"
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
