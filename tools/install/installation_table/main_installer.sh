#!/bin/bash
# SAGE 安装脚本 - 主安装控制器
# 统一管理不同安装模式的安装流程

# 导入所有安装器
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/interface.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../examination_tools/sage_check.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../download_tools/environment_config.sh"
source "$(dirname "${BASH_SOURCE[0]}")/core_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/scientific_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/dev_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/vllm_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../fixes/libstdcxx_fix.sh"

# pip 缓存清理函数
clean_pip_cache() {
    local log_file="${1:-install.log}"

    echo -e "${BLUE}🧹 清理 pip 缓存...${NC}"
    echo "$(date): 开始清理 pip 缓存" >> "$log_file"

    # 检查是否支持 pip cache 命令
    if $PIP_CMD cache --help &>/dev/null; then
        echo -e "${DIM}使用 pip cache purge 清理缓存${NC}"

        # 显示缓存大小（如果支持）
        if $PIP_CMD cache info &>/dev/null; then
            local cache_info=$($PIP_CMD cache info 2>/dev/null | grep -E "(Location|Size)" || true)
            if [ -n "$cache_info" ]; then
                echo -e "${DIM}缓存信息:${NC}"
                echo "$cache_info" | sed 's/^/  /'
            fi
        fi

        # 执行缓存清理
        if $PIP_CMD cache purge >> "$log_file" 2>&1; then
            echo -e "${CHECK} pip 缓存清理完成"
            echo "$(date): pip 缓存清理成功" >> "$log_file"
        else
            echo -e "${WARNING} pip 缓存清理失败，但继续安装"
            echo "$(date): pip 缓存清理失败" >> "$log_file"
        fi
    else
        echo -e "${DIM}当前 pip 版本不支持 cache 命令，跳过缓存清理${NC}"
        echo "$(date): pip 版本不支持 cache 命令，跳过缓存清理" >> "$log_file"
    fi

    echo ""
}

# 安装C++扩展函数
install_cpp_extensions() {
    local log_file="$1"

    echo "$(date): 开始安装C++扩展" >> "$log_file"
    echo -e "${BLUE}🧩 安装C++扩展 (sage_db, sage_flow)...${NC}"
    echo -e "${DIM}📝 详细日志: ${log_file}${NC}"
    echo -e "${YELLOW}⏱️  注意: C++扩展构建可能需要几分钟时间，请耐心等待...${NC}"
    echo -e "${DIM}   - 正在编译C++代码和依赖库${NC}"
    echo -e "${DIM}   - 可以在另一个终端查看实时日志: tail -f ${log_file}${NC}"
    echo ""

    # C++扩展通过 setup.py 的 build_ext 自动构建
    # 在 pip install -e 时会自动调用 CustomDevelop.run() -> build_ext
    # 这里只需要重新触发构建（如果需要的话）
    
    echo -e "${DIM}C++扩展已通过 setup.py 自动构建${NC}"
    echo -e "${DIM}检查构建结果...${NC}"
    echo "$(date): C++扩展应该已在 pip install 阶段自动构建" >> "$log_file"
    
    # 对于开发模式，扩展已经在 pip install -e 时构建
    # 对于标准模式，扩展已经在 pip install 时构建
    # 这里只需验证扩展是否可用
    
    install_success=true
    exit_code=0

    # 注意: 段错误(退出码139)可能在清理阶段发生，但扩展已成功安装
    # 通过检查扩展状态来确定实际结果
    if [ "$install_success" = "true" ]; then
        echo "$(date): C++扩展应该已在安装阶段构建" >> "$log_file"

        # 验证扩展是否真的可用
        echo -e "${DIM}验证扩展可用性...${NC}"

        # 在CI环境中增加短暂延迟，确保文件系统同步
        if [[ -n "$CI" || -n "$GITHUB_ACTIONS" ]]; then
            sleep 1
        fi

        # 验证扩展
        python3 -c "
import sys
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

try:
    from sage.middleware.components.extensions_compat import check_extensions_availability
    available = check_extensions_availability()
    total = sum(available.values())

    if total > 0:
        print(f'✅ C++扩展验证成功: {total}/{len(available)} 可用')
        for ext, status in available.items():
            symbol = '✅' if status else '❌'
            print(f'   {symbol} {ext}')
    else:
        print('⚠️  没有C++扩展可用')
        print('💡 这可能是因为子模块未初始化或构建失败')
        sys.exit(1)
except Exception as e:
    print(f'⚠️ 扩展验证失败: {e}')
    sys.exit(1)
"
        validation_result=$?

        if [ $validation_result -eq 0 ]; then
            echo -e "${CHECK} C++ 扩展安装成功 (sage_db, sage_flow)"
            echo -e "${DIM}现在可以使用高性能数据库和流处理功能${NC}"
            return 0
        else
            echo -e "${WARNING} 扩展构建完成但验证失败"
            echo "$(date): 扩展验证失败" >> "$log_file"
            return 1
        fi
    else
        echo -e "${WARNING} C++ 扩展安装失败"
        echo "$(date): C++扩展安装失败" >> "$log_file"

        # 在CI环境中显示详细的错误信息和调试信息
        if [[ -n "$CI" || -n "$GITHUB_ACTIONS" ]]; then
            echo -e "${RED} ==================== CI环境扩展安装失败调试信息 ===================="
            echo -e "${INFO} 1. 系统依赖检查:"
            echo -e "${DIM}GCC 版本:${NC}"
            gcc --version 2>/dev/null || echo -e "${WARNING}❌ gcc 不可用"
            echo -e "${DIM}CMake 版本:${NC}"
            cmake --version 2>/dev/null || echo -e "${WARNING}❌ cmake 不可用"
            echo -e "${DIM}BLAS/LAPACK 库:${NC}"
            find /usr/lib* -name "*blas*" -o -name "*lapack*" 2>/dev/null | head -5 || echo -e "${WARNING}❌ 未找到BLAS/LAPACK"

            echo -e "${INFO} 2. Python 环境检查:"
            echo -e "${DIM}Python 版本: $(python3 --version)${NC}"
            echo -e "${DIM}Python 路径: $(which python3)${NC}"
            echo -e "${DIM}Pip 版本: $(pip --version)${NC}"

            echo -e "${INFO} 3. SAGE CLI 状态:"
            echo -e "${DIM}SAGE 命令: $SAGE_CMD${NC}"
            echo -e "${DIM}SAGE 位置: $(which sage || echo '未找到')${NC}"

            echo -e "${INFO} 4. 工作目录和权限:"
            echo -e "${DIM}当前目录: $(pwd)${NC}"
            echo -e "${DIM}目录权限: $(ls -ld .)${NC}"

            echo -e "${INFO} 5. 最近安装日志 (最后50行):"
            echo -e "${DIM}=============== 安装日志开始 ===============${NC}"
            tail -50 "$log_file" 2>/dev/null || echo "无法读取日志文件"
            echo -e "${DIM}=============== 安装日志结束 ===============${NC}"

            echo -e "${INFO} 6. 尝试单独安装 sage_db 以获取详细错误:"
            echo -e "${DIM}单独安装 sage_db...${NC}"
            echo -e "${DIM}================================ 单独安装开始 ================================${NC}"
            $SAGE_CMD extensions install sage_db --force 2>&1 || echo "单独安装也失败"
            echo -e "${DIM}================================ 单独安装结束 ================================${NC}"

            echo -e "${INFO} 7. 检查 sage_db 构建目录状态:"
            # 尝试找到项目根目录
            if [ -n "${GITHUB_WORKSPACE:-}" ]; then
                sage_db_dir="${GITHUB_WORKSPACE}/packages/sage-middleware/src/sage/middleware/components/sage_db"
            elif [ -f "$(pwd)/packages/sage-middleware/src/sage/middleware/components/sage_db/CMakeLists.txt" ]; then
                sage_db_dir="$(pwd)/packages/sage-middleware/src/sage/middleware/components/sage_db"
            else
                sage_db_dir="packages/sage-middleware/src/sage/middleware/components/sage_db"
            fi

            echo -e "${DIM}检查目录: $sage_db_dir${NC}"
            if [ -d "$sage_db_dir" ]; then
                echo -e "${DIM}sage_db 目录存在${NC}"
                echo -e "${DIM}目录内容:${NC}"
                ls -la "$sage_db_dir" | head -10
                if [ -d "$sage_db_dir/build" ]; then
                    echo -e "${DIM}构建目录存在，检查错误日志:${NC}"
                    if [ -f "$sage_db_dir/build/CMakeFiles/CMakeError.log" ]; then
                        echo -e "${DIM}CMake错误日志 (最后20行):${NC}"
                        tail -20 "$sage_db_dir/build/CMakeFiles/CMakeError.log" 2>/dev/null || echo "无法读取CMake错误日志"
                    fi
                    if [ -f "$sage_db_dir/build/make_output.log" ]; then
                        echo -e "${DIM}Make输出日志 (最后20行):${NC}"
                        tail -20 "$sage_db_dir/build/make_output.log" 2>/dev/null || echo "无法读取Make输出日志"
                    fi
                else
                    echo -e "${DIM}构建目录不存在${NC}"
                fi
            else
                echo -e "${DIM}sage_db 目录不存在: $sage_db_dir${NC}"
            fi

            echo -e "${RED} ===============================================================${NC}"
        else
            echo -e "${DIM}稍后可手动安装: sage extensions install all${NC}"
        fi
        return 1
    fi
}

# 主安装函数
install_sage() {
    local mode="${1:-dev}"
    local environment="${2:-conda}"
    local install_vllm="${3:-false}"
    local clean_cache="${4:-true}"

    # 获取项目根目录和日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/install.log"

    echo ""
    echo -e "${GEAR} 开始安装 SAGE 包 (${mode} 模式, ${environment} 环境)..."
    if [ "$install_vllm" = "true" ]; then
        echo -e "${PURPLE}包含 VLLM 支持${NC}"
    fi
    echo ""
    echo -e "${BLUE}📝 安装日志: ${log_file}${NC}"
    echo -e "${DIM}   可以使用以下命令实时查看日志:${NC}"
    echo -e "${DIM}   tail -f ${log_file}${NC}"
    echo ""

    # 配置安装环境（包含所有检查）
    configure_installation_environment "$environment" "$mode"

    # 清理 pip 缓存（如果启用）
    if [ "$clean_cache" = "true" ]; then
        clean_pip_cache "$log_file"
    else
        echo -e "${DIM}跳过 pip 缓存清理（使用 --no-cache-clean 选项）${NC}"
        echo "$(date): 跳过 pip 缓存清理（用户指定）" >> "$log_file"
        echo ""
    fi

    # 记录安装开始到日志
    echo "" >> "$log_file"
    echo "========================================" >> "$log_file"
    echo "SAGE 主要安装过程开始 - $(date)" >> "$log_file"
    echo "安装模式: $mode" >> "$log_file"
    echo "安装环境: $environment" >> "$log_file"
    echo "安装 VLLM: $install_vllm" >> "$log_file"
    echo "PIP 命令: $PIP_CMD" >> "$log_file"
    echo "Python 命令: $PYTHON_CMD" >> "$log_file"
    echo "========================================" >> "$log_file"

    echo ""
    case "$mode" in
        "core")
            echo -e "${BLUE}核心运行时模式：仅安装基础 SAGE 包${NC}"
            echo "$(date): 开始核心运行时模式" >> "$log_file"
            install_core_packages "$mode"
            ;;
        "standard")
            echo -e "${BLUE}标准安装模式：基础包 + 中间件 + 应用包 + C++扩展${NC}"
            echo "$(date): 开始标准安装模式" >> "$log_file"
            install_core_packages "$mode"
            install_scientific_packages

            # 在安装 C++ 扩展前确保 libstdc++ 符号满足要求
            echo -e "${DIM}预检查 libstdc++ 兼容性...${NC}"
            ensure_libstdcxx_compatibility "$log_file" "$environment" || echo -e "${WARNING} libstdc++ 检查未通过，继续尝试构建扩展"

            # 安装C++扩展（标准功能）
            echo ""
            if install_cpp_extensions "$log_file"; then
                echo -e "${CHECK} 标准安装模式完成（包含C++扩展）"
            else
                echo -e "${WARNING} 标准安装完成，但C++扩展安装失败"
            fi
            ;;
        "dev")
            echo -e "${BLUE}开发者安装模式：标准安装 + C++扩展 + 开发工具${NC}"
            echo "$(date): 开始开发者安装模式" >> "$log_file"
            install_core_packages "$mode"
            install_scientific_packages

            # 在安装 C++ 扩展前确保 libstdc++ 符号满足要求
            echo -e "${DIM}预检查 libstdc++ 兼容性...${NC}"
            ensure_libstdcxx_compatibility "$log_file" "$environment" || echo -e "${WARNING} libstdc++ 检查未通过，继续尝试构建扩展"

            # 安装C++扩展（标准功能）
            echo ""
            if install_cpp_extensions "$log_file"; then
                echo -e "${CHECK} C++扩展安装完成"
            else
                echo -e "${WARNING} C++扩展安装失败，但继续安装开发工具"
            fi

            # 安装开发工具
            install_dev_packages
            ;;
        *)
            echo -e "${WARNING} 未知安装模式: $mode，使用开发者模式"
            echo "$(date): 未知安装模式 $mode，使用开发者模式" >> "$log_file"
            install_core_packages "dev"
            install_scientific_packages
            install_dev_packages
            ;;
    esac

    echo ""
    echo -e "${CHECK} SAGE 基础安装完成！"

    # 尝试安装C++扩展（开发者模式已在dev_installer.sh中处理）
    # 这里不需要额外操作

    # 安装 VLLM（如果需要）
    if [ "$install_vllm" = "true" ]; then
        echo ""
        install_vllm_packages
    fi

    # 记录安装完成
    echo "$(date): SAGE 安装完成" >> "$log_file"
    if [ "$install_vllm" = "true" ]; then
        echo "$(date): VLLM 安装请求已处理" >> "$log_file"
    fi
    echo "安装结束时间: $(date)" >> "$log_file"
    echo "========================================" >> "$log_file"

    # 显示安装信息
    show_install_success "$mode"
}
