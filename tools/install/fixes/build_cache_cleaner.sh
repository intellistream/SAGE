#!/bin/bash
# SAGE 构建缓存清理工具
# 清理可能导致版本不一致的 egg-info 和其他构建缓存

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 导入颜色定义
if [ -f "${SAGE_ROOT:-}/tools/install/display_tools/colors.sh" ]; then
    source "${SAGE_ROOT:-}/tools/install/display_tools/colors.sh"
fi

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
CONDA_PREFIX="${CONDA_PREFIX:-}"
WSL_DISTRO_NAME="${WSL_DISTRO_NAME:-}"
SAGE_AUTO_CONFIRM="${SAGE_AUTO_CONFIRM:-}"
SAGE_INSTALL_LOG="${SAGE_INSTALL_LOG:-}"
SAGE_ENV_NAME="${SAGE_ENV_NAME:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
PYTHON_CMD="${PYTHON_CMD:-}"
PIP_CMD="${PIP_CMD:-}"
LANG="${LANG:-}"
LC_ALL="${LC_ALL:-}"
LC_CTYPE="${LC_CTYPE:-}"
HOME="${HOME:-$(/usr/bin/env | grep ^HOME= | cut -d= -f2 || echo /root)}"
# ============================================================================

# 导入日志工具
if [ -f "${SAGE_ROOT:-}/tools/install/display_tools/logging.sh" ]; then
    source "${SAGE_ROOT:-}/tools/install/display_tools/logging.sh"
fi

# 清理 egg-info 缓存
clean_egg_info_cache() {
    local packages_dir="${SAGE_ROOT:-}/packages"

    echo -e "${INFO} 检查 egg-info 缓存..."
    log_info "开始检查 egg-info 缓存" "BuildCache"

    # 查找所有 egg-info 目录
    local egg_info_dirs=$(find "$packages_dir" -type d -name "*.egg-info" 2>/dev/null || true)

    if [ -z "$egg_info_dirs" ]; then
        echo -e "${DIM}  未发现 egg-info 缓存${NC}"
        log_debug "未发现 egg-info 缓存" "BuildCache"
        return 0
    fi

    # 统计数量
    local count=$(echo "$egg_info_dirs" | wc -l)
    echo -e "${YELLOW}  发现 $count 个 egg-info 缓存目录${NC}"
    log_warn "发现 $count 个 egg-info 缓存目录" "BuildCache"

    # 检查是否存在版本不一致
    local has_version_mismatch=false
    echo -e "${DIM}  检查版本一致性...${NC}"

    while IFS= read -r egg_info_dir; do
        if [ -f "$egg_info_dir/PKG-INFO" ]; then
            local pkg_name=$(basename "$egg_info_dir" | sed 's/\.egg-info$//')
            local cached_version=$(grep "^Version:" "$egg_info_dir/PKG-INFO" 2>/dev/null | cut -d' ' -f2)

            # 从 egg-info 路径推导包路径
            # 例如: src/isage.egg-info -> 项目根目录 / 当前包目录
            local pkg_dir=$(dirname "$(dirname "$egg_info_dir")")

            # 查找对应的 _version.py（在该包的 src 目录下）
            local version_file=$(find "$pkg_dir/src" -name "_version.py" 2>/dev/null | head -1)

            if [ -f "$version_file" ]; then
                local source_version=$(grep "^__version__" "$version_file" 2>/dev/null | sed -E 's/.*["'\''"]([0-9.]+)["'\''"]/\1/')

                if [ -n "$cached_version" ] && [ -n "$source_version" ] && [ "$cached_version" != "$source_version" ]; then
                    echo -e "${YELLOW}  ⚠️  版本不一致: $pkg_name${NC}"
                    echo -e "${DIM}     缓存: $cached_version | 源码: $source_version${NC}"
                    log_warn "版本不一致: $pkg_name (缓存: $cached_version, 源码: $source_version)" "BuildCache"
                    has_version_mismatch=true
                fi
            fi
        fi
    done <<< "$egg_info_dirs"

    # 如果发现版本不一致，执行清理
    if [ "$has_version_mismatch" = true ]; then
        echo -e "${YELLOW}  检测到版本不一致，清理 egg-info 缓存...${NC}"
        log_warn "检测到版本不一致，执行清理" "BuildCache"

        find "$packages_dir" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

        echo -e "${CHECK} egg-info 缓存已清理"
        log_info "egg-info 缓存清理完成" "BuildCache"
    else
        echo -e "${DIM}  版本一致，保留缓存${NC}"
        log_debug "版本一致，保留缓存" "BuildCache"
    fi

    return 0
}

# 清理构建目录
clean_build_dirs() {
    local packages_dir="${SAGE_ROOT:-}/packages"

    echo -e "${INFO} 检查构建目录..."
    log_info "开始检查构建目录" "BuildCache"

    # 查找所有包级别的 build 目录（不包括项目根目录的 build）
    local build_dirs=$(find "$packages_dir" -mindepth 2 -maxdepth 3 -type d -name "build" 2>/dev/null || true)

    if [ -z "$build_dirs" ]; then
        echo -e "${DIM}  未发现构建缓存${NC}"
        log_debug "未发现构建缓存" "BuildCache"
        return 0
    fi

    # 统计数量和大小
    local count=$(echo "$build_dirs" | wc -l)
    local total_size=$(du -sh "$packages_dir"/*/build 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo "0")

    echo -e "${DIM}  发现 $count 个构建目录${NC}"
    log_debug "发现 $count 个构建目录" "BuildCache"

    # 询问是否清理（在自动模式下跳过）
    if [ "${SAGE_AUTO_CLEAN:-false}" != "true" ]; then
        echo -e "${DIM}  构建目录通常可以安全删除${NC}"
        return 0
    fi

    echo -e "${DIM}  清理构建目录...${NC}"
    find "$packages_dir" -mindepth 2 -maxdepth 3 -type d -name "build" -exec rm -rf {} + 2>/dev/null || true

    echo -e "${CHECK} 构建目录已清理"
    log_info "构建目录清理完成" "BuildCache"

    return 0
}

# 清理 dist 目录
clean_dist_dirs() {
    local packages_dir="${SAGE_ROOT:-}/packages"

    log_info "开始检查 dist 目录" "BuildCache"

    # 查找所有 dist 目录
    local dist_dirs=$(find "$packages_dir" -mindepth 2 -maxdepth 3 -type d -name "dist" 2>/dev/null || true)

    if [ -z "$dist_dirs" ]; then
        log_debug "未发现 dist 目录" "BuildCache"
        return 0
    fi

    local count=$(echo "$dist_dirs" | wc -l)
    log_debug "发现 $count 个 dist 目录" "BuildCache"

    if [ "${SAGE_AUTO_CLEAN:-false}" = "true" ]; then
        find "$packages_dir" -mindepth 2 -maxdepth 3 -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
        log_info "dist 目录清理完成" "BuildCache"
    fi

    return 0
}

# 检测并清理所有缓存
detect_and_clean_cache() {
    local force_clean="${1:-false}"

    echo ""
    echo -e "${BLUE}🧹 检查构建缓存...${NC}"
    log_phase_start "构建缓存检查" "BuildCache"

    # 设置自动清理标志
    if [ "$force_clean" = "true" ]; then
        export SAGE_AUTO_CLEAN=true
    fi

    # 清理 egg-info（这是最重要的）
    clean_egg_info_cache

    # 清理 build 和 dist（可选）
    if [ "$force_clean" = "true" ]; then
        echo ""
        clean_build_dirs
        echo ""
        clean_dist_dirs
    fi

    log_phase_end "构建缓存检查" "success" "BuildCache"
    echo ""

    return 0
}

# 主函数
main() {
    local command="${1:-detect}"

    case "$command" in
        detect)
            # 自动检测并清理（仅清理有问题的 egg-info）
            detect_and_clean_cache false
            ;;
        clean)
            # 强制清理所有缓存
            detect_and_clean_cache true
            ;;
        egg-info)
            # 仅清理 egg-info
            clean_egg_info_cache
            ;;
        build)
            # 仅清理 build
            export SAGE_AUTO_CLEAN=true
            clean_build_dirs
            ;;
        dist)
            # 仅清理 dist
            export SAGE_AUTO_CLEAN=true
            clean_dist_dirs
            ;;
        help|*)
            echo "SAGE 构建缓存清理工具"
            echo ""
            echo "用法: $0 <command>"
            echo ""
            echo "命令:"
            echo "  detect      自动检测版本不一致并清理 egg-info（默认）"
            echo "  clean       强制清理所有缓存（egg-info + build + dist）"
            echo "  egg-info    仅清理 egg-info 缓存"
            echo "  build       仅清理 build 目录"
            echo "  dist        仅清理 dist 目录"
            echo "  help        显示此帮助"
            echo ""
            ;;
    esac
}

# 如果直接运行，执行主函数
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
