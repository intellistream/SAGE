#!/bin/bash
# C++ 扩展库修复工具
# 处理 editable install 模式下 C++ 扩展库(.so)的安装问题

source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 修复 sage-middleware C++ 扩展库的安装
fix_middleware_cpp_extensions() {
    local log_file="${1:-install.log}"
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"

    echo -e "${BLUE}🔧 检查并修复 C++ 扩展库安装...${NC}"
    echo "$(date): 开始检查 C++ 扩展库" >> "$log_file"

    # 检查是否是 editable install
    local pip_output=$(pip show isage-middleware 2>/dev/null)
    local is_editable=false

    if echo "$pip_output" | grep -q "Editable project location:"; then
        is_editable=true
        echo -e "${DIM}  检测到 editable install 模式${NC}"
    fi

    if [ "$is_editable" = false ]; then
        echo -e "${DIM}  非 editable install 模式，跳过修复${NC}"
        return 0
    fi

    # 定义需要检查的扩展和它们的库文件
    # 格式: "扩展名:库文件1,库文件2,..."
    local extensions_libs=(
        "sage_flow:libsageflow.so"
        "sage_db:libsage_db.so"
        "sage_tsdb:libsage_tsdb_core.so,libsage_tsdb_algorithms.so"
    )
    local fixed_count=0
    local total_count=0

    for ext_lib in "${extensions_libs[@]}"; do
        total_count=$((total_count + 1))

        # 分离扩展名和库文件列表
        local ext="${ext_lib%%:*}"
        local lib_names="${ext_lib#*:}"

        # 目标目录（Python 包的位置）
        local target_dir="$project_root/packages/sage-middleware/src/sage/middleware/components/${ext}/python"

        # 检查目标目录是否存在
        if [ ! -d "$target_dir" ]; then
            echo -e "${DIM}  跳过 ${ext}: 目标目录不存在${NC}"
            continue
        fi

        # 处理多个库文件（用逗号分隔）
        local all_libs_ok=true
        IFS=',' read -ra lib_array <<< "$lib_names"

        for lib_name in "${lib_array[@]}"; do
            # 检查库文件是否已经存在于目标目录
            if [ -f "$target_dir/$lib_name" ]; then
                echo -e "${DIM}  ${CHECK} ${ext}: ${lib_name} 已存在${NC}"
                continue
            fi

            # 查找构建目录中的库文件
            # 搜索多个可能的位置：
            # 1. 本地构建目录
            # 2. 子模块的 python 目录（CMake 可能已安装到这里）
            # 3. 子模块的构建目录
            local build_lib=""
            local search_paths=(
                "$project_root/packages/sage-middleware/build"
                "$project_root/packages/sage-middleware/src/sage/middleware/components/${ext}"
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
                echo -e "${WARNING} ${ext}: ${lib_name} 未找到"
                echo -e "${DIM}    已搜索路径: ${search_paths[*]}${NC}"
                echo "$(date): ${lib_name} 未找到，已搜索: ${search_paths[*]}" >> "$log_file"
                all_libs_ok=false
                continue
            fi

            # 复制库文件到目标目录
            echo -e "${DIM}  复制 ${lib_name} 到 ${target_dir}${NC}"
            if cp "$build_lib" "$target_dir/"; then
                echo -e "  ${CHECK} ${ext}: ${lib_name} 已修复"
                echo "$(date): 成功复制 ${lib_name} 到 ${target_dir}" >> "$log_file"
            else
                echo -e "  ${CROSS} ${ext}: 复制 ${lib_name} 失败"
                echo "$(date): 复制 ${lib_name} 失败" >> "$log_file"
                all_libs_ok=false
            fi
        done

        if [ "$all_libs_ok" = true ]; then
            fixed_count=$((fixed_count + 1))
        fi
    done

    echo ""
    if [ $fixed_count -eq $total_count ]; then
        echo -e "${CHECK} 所有 C++ 扩展库检查完成 (${fixed_count}/${total_count})"
        echo "$(date): C++ 扩展库修复完成，${fixed_count}/${total_count} 可用" >> "$log_file"
        return 0
    else
        echo -e "${WARNING} 部分 C++ 扩展库可能不可用 (${fixed_count}/${total_count})"
        echo "$(date): C++ 扩展库部分可用，${fixed_count}/${total_count}" >> "$log_file"

        # 在 CI 环境中，如果库文件找不到，可能是因为：
        # 1. 子模块未初始化
        # 2. CMake 安装路径配置问题
        # 3. scikit-build-core 的临时构建目录已被清理
        if [[ -n "$CI" || -n "$GITHUB_ACTIONS" ]]; then
            echo -e "${DIM}💡 CI 环境提示：${NC}"
            echo -e "${DIM}   如果子模块已初始化但库文件仍未找到，${NC}"
            echo -e "${DIM}   可能是 CMake 安装配置问题或构建失败${NC}"
            echo -e "${DIM}   请检查上方的构建日志中的 CMake 输出${NC}"
        fi

        # 不返回错误，让验证步骤来判断是否真的有问题
        return 0
    fi
}

# 导出函数供其他脚本使用
export -f fix_middleware_cpp_extensions
