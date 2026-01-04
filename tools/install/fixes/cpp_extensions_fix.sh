#!/bin/bash
# C++ 扩展库修复工具
# 处理 editable install 模式下 C++ 扩展库(.so)的安装问题

# 加载日志和颜色函数（logging.sh 会自动 source colors.sh）
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/logging.sh"

# 修复 sage-middleware C++ 扩展库的安装

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

fix_middleware_cpp_extensions() {
    # 注意: C++ 扩展已迁移为独立 PyPI 包，不再需要修复
    # - isagevdb (was sageVDB)
    # - isage-flow (was sageFlow)
    # - isage-tsdb (was sageTSDB)
    # sage-middleware 现在只包含 Python 兼容层

    log_info "C++ 扩展已迁移为独立 PyPI 包，跳过修复" "CPPExtFix"
    echo -e "${DIM}ℹ️  C++ 扩展（sageVDB/sageFlow/sageTSDB）已迁移为独立 PyPI 包${NC}"
    echo -e "${DIM}   如需使用，请通过 pip install isagevdb isage-flow isage-tsdb 安装${NC}"
    return 0

    # 以下代码已废弃，保留供参考
    # ----------------------------------------------------------------
    local fixed_count=0
    local total_count=0
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"

    for ext_lib in "${extensions_libs[@]}"; do
        total_count=$((total_count + 1))

        # 分离扩展名和库文件列表
        local ext="${ext_lib%%:*}"
        local lib_names="${ext_lib#*:}"

        # 目标目录（Python 包的位置）
        local target_dir="$project_root/packages/sage-middleware/src/sage/middleware/components/${ext}/python"

        # 检查目标目录是否存在
        if [ ! -d "$target_dir" ]; then
            log_debug "跳过 ${ext}: 目标目录不存在" "CPPExtFix"
            echo -e "${DIM}  跳过 ${ext}: 目标目录不存在${NC}"
            continue
        fi

        # 处理多个库文件（用逗号分隔）
        local all_libs_ok=true
        IFS=',' read -ra lib_array <<< "$lib_names"

        for lib_name in "${lib_array[@]}"; do
            # 检查库文件是否已经存在于目标目录
            if [ -f "$target_dir/$lib_name" ]; then
                log_debug "${ext}: ${lib_name} 已存在" "CPPExtFix"
                echo -e "${DIM}  ${CHECK} ${ext}: ${lib_name} 已存在${NC}"
                continue
            fi

            # 查找构建目录中的库文件
            local build_lib=""
            local search_paths=(
                "$project_root/packages/sage-middleware/build"
                "$project_root/packages/sage-middleware/src/sage/middleware/components/${ext}"
                "$project_root/.sage/build/${ext}"
                "$project_root/.sage/build/middleware"
            )

            for search_path in "${search_paths[@]}"; do
                if [ -d "$search_path" ]; then
                    build_lib=$(find "$search_path" -name "$lib_name" -type f 2>/dev/null | head -1)
                    if [ -n "$build_lib" ] && [ -f "$build_lib" ]; then
                        break
                    fi
                fi
            done

            if [ -z "$build_lib" ] || [ ! -f "$build_lib" ]; then
                log_warn "${ext}: ${lib_name} 未找到" "CPPExtFix"
                log_debug "已搜索路径: ${search_paths[*]}" "CPPExtFix"
                echo -e "${WARNING} ${ext}: ${lib_name} 未找到"
                echo -e "${DIM}    已搜索路径: ${search_paths[*]}${NC}"
                all_libs_ok=false
                continue
            fi

            # 复制库文件到目标目录
            log_info "复制 ${lib_name} 到 ${target_dir}" "CPPExtFix"
            echo -e "${DIM}  复制 ${lib_name} 到 ${target_dir}${NC}"
            if cp "$build_lib" "$target_dir/"; then
                log_info "${ext}: ${lib_name} 已修复" "CPPExtFix"
                echo -e "  ${CHECK} ${ext}: ${lib_name} 已修复"
            else
                log_error "${ext}: 复制 ${lib_name} 失败" "CPPExtFix"
                echo -e "  ${CROSS} ${ext}: 复制 ${lib_name} 失败"
                all_libs_ok=false
            fi
        done

        if [ "$all_libs_ok" = true ]; then
            fixed_count=$((fixed_count + 1))
        fi
    done

    echo ""
    if [ $fixed_count -eq $total_count ]; then
        log_info "所有 C++ 扩展库检查完成 (${fixed_count}/${total_count})" "CPPExtFix"
        echo -e "${CHECK} 所有 C++ 扩展库检查完成 (${fixed_count}/${total_count})"
        return 0
    else
        log_warn "部分 C++ 扩展库可能不可用 (${fixed_count}/${total_count})" "CPPExtFix"
        echo -e "${WARNING} 部分 C++ 扩展库可能不可用 (${fixed_count}/${total_count})"

        if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" ]]; then
            log_debug "CI 环境提示：如果子模块已初始化但库文件仍未找到，可能是 CMake 安装配置问题或构建失败" "CPPExtFix"
            echo -e "${DIM}💡 CI 环境提示：${NC}"
            echo -e "${DIM}   如果子模块已初始化但库文件仍未找到，${NC}"
            echo -e "${DIM}   可能是 CMake 安装配置问题或构建失败${NC}"
            echo -e "${DIM}   请检查上方的构建日志中的 CMake 输出${NC}"
        fi
        return 0
    fi
}

# 导出函数供其他脚本使用
export -f fix_middleware_cpp_extensions
