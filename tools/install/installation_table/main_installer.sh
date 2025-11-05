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
source "$(dirname "${BASH_SOURCE[0]}")/../fixes/cpp_extensions_fix.sh"

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

# 验证C++扩展函数（扩展已在 sage-middleware 安装时自动构建）
verify_cpp_extensions() {
    local log_file="$1"

    echo "$(date): 开始验证C++扩展" >> "$log_file"
    echo -e "${DIM}📝 详细日志: ${log_file}${NC}"
    echo -e "${DIM}   C++扩展已通过 sage-middleware 的 scikit-build-core 自动构建${NC}"
    echo -e "${DIM}   正在检查扩展可用性...${NC}"
    echo ""

    # 在CI环境中增加短暂延迟，确保文件系统同步
    if [[ -n "$CI" || -n "$GITHUB_ACTIONS" ]]; then
        sleep 1
    fi

    # 使用正确的 Python 命令
    local python_cmd="${PYTHON_CMD:-python3}"

    # 验证扩展是否可用
    local verify_output
    verify_output=$($python_cmd -c "
import sys
import warnings

try:
    from sage.middleware.components.extensions_compat import check_extensions_availability
    available = check_extensions_availability()
    total = sum(available.values())
    total_expected = len(available)

    print(f'🔍 C++扩展验证结果: {total}/{total_expected} 可用')
    for ext, status in available.items():
        symbol = '✅' if status else '❌'
        print(f'   {symbol} {ext}')

    # 检查失败的扩展并显示详细错误
    if total < total_expected:
        print('')
        print('⚠️  以下扩展不可用，检查详细错误：')
        failed_exts = [ext for ext, status in available.items() if not status]

        # 尝试导入失败的扩展以获取详细错误
        for ext in failed_exts:
            try:
                if ext == 'sage_db':
                    from sage.middleware.components.sage_db.python import _sage_db
                elif ext == 'sage_flow':
                    from sage.middleware.components.sage_flow.python import _sage_flow
                elif ext == 'sage_tsdb':
                    from sage.middleware.components.sage_tsdb.python import _sage_tsdb
            except Exception as e:
                print(f'   {ext}: {type(e).__name__}: {e}')

    # 只要有扩展可用就视为部分成功（允许降级）
    if total > 0:
        if total == total_expected:
            print('')
            print('✅ 所有 C++ 扩展验证成功')
        else:
            print('')
            print(f'⚠️  部分扩展不可用 ({total}/{total_expected})，功能将受限')
            print('💡 提示: 确保子模块已初始化并安装了所需的构建依赖')
        sys.exit(0)  # 部分成功也返回 0
    else:
        print('')
        print('❌ 没有任何 C++ 扩展可用')
        print('💡 这可能是因为：')
        print('   1. 子模块未初始化：git submodule update --init --recursive')
        print('   2. 缺少构建工具：apt-get install build-essential cmake')
        print('   3. 查看详细日志了解更多信息')
        sys.exit(1)
except Exception as e:
    print(f'❌ 扩展验证过程失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" 2>&1)
        validation_result=$?

        # 输出验证结果
        echo "$verify_output"

        if [ $validation_result -eq 0 ]; then
            echo -e "${CHECK} C++ 扩展可用 (sage_db, sage_flow, sage_tsdb)"
            echo -e "${DIM}现在可以使用高性能数据库和流处理功能${NC}"
            echo "$(date): C++扩展验证成功" >> "$log_file"
            return 0
        else
            echo -e "${WARNING} 扩展验证失败"
            echo "$(date): 扩展验证失败" >> "$log_file"
            echo -e "${DIM}💡 提示: C++扩展在 sage-middleware 安装时自动构建${NC}"
            echo -e "${DIM}   如果验证失败，可能是因为：${NC}"
            echo -e "${DIM}   1. 子模块未初始化：git submodule update --init --recursive${NC}"
            echo -e "${DIM}   2. 缺少构建工具：apt-get install build-essential cmake${NC}"
            echo -e "${DIM}   3. 查看详细日志：cat $log_file${NC}"
            return 1
        fi
}

# 主安装函数
install_sage() {
    local mode="${1:-dev}"
    local environment="${2:-conda}"
    local install_vllm="${3:-false}"
    local clean_cache="${4:-true}"

    # CI 环境特殊处理：双重保险，确保使用 pip
    # 即使参数解析阶段没有正确设置，这里也会修正
    if [[ (-n "$CI" || -n "$GITHUB_ACTIONS") && "$environment" = "conda" ]]; then
        echo -e "${INFO} CI 环境中检测到 environment='conda'，强制使用 pip（CI 优化）"
        environment="pip"
    fi

    # 获取项目根目录和日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/.sage/logs/install.log"

    echo ""
    echo -e "${GEAR} 开始安装 SAGE 包 (${mode} 模式, ${environment} 环境)..."
    if [ "$install_vllm" = "true" ]; then
        echo -e "${PURPLE}包含 VLLM 支持${NC}"
    fi
    echo ""
    mkdir -p "$(dirname "$log_file")"
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
            echo -e "${BLUE}标准安装模式：基础包 + 中间件 + 应用包${NC}"
            echo "$(date): 开始标准安装模式" >> "$log_file"

            # 在安装前确保 libstdc++ 符号满足要求
            echo -e "${DIM}预检查 libstdc++ 兼容性...${NC}"
            ensure_libstdcxx_compatibility "$log_file" "$environment" || echo -e "${WARNING} libstdc++ 检查未通过，继续尝试安装"

            install_core_packages "$mode"
            install_scientific_packages

            # 修复 C++ 扩展库安装（editable install 模式）
            echo ""
            echo -e "${BLUE}🔧 修复 C++ 扩展库安装...${NC}"
            fix_middleware_cpp_extensions "$log_file"

            # 验证C++扩展（已在 sage-middleware 安装时自动构建）
            echo ""
            echo -e "${BLUE}🧩 验证 C++ 扩展状态...${NC}"
            if verify_cpp_extensions "$log_file"; then
                echo -e "${CHECK} 标准安装模式完成（C++扩展已自动构建）"
            else
                echo -e "${WARNING} 标准安装完成，但C++扩展不可用"
            fi
            ;;
        "dev")
            echo -e "${BLUE}开发者安装模式：标准安装 + 开发工具${NC}"
            echo "$(date): 开始开发者安装模式" >> "$log_file"

            # 在安装前确保 libstdc++ 符号满足要求
            echo -e "${DIM}预检查 libstdc++ 兼容性...${NC}"
            ensure_libstdcxx_compatibility "$log_file" "$environment" || echo -e "${WARNING} libstdc++ 检查未通过，继续尝试安装"

            install_core_packages "$mode"
            install_scientific_packages

            # 修复 C++ 扩展库安装（editable install 模式）
            echo ""
            echo -e "${BLUE}🔧 修复 C++ 扩展库安装...${NC}"
            fix_middleware_cpp_extensions "$log_file"

            # 验证C++扩展（已在 sage-middleware 安装时自动构建）
            echo ""
            echo -e "${BLUE}🧩 验证 C++ 扩展状态...${NC}"
            if verify_cpp_extensions "$log_file"; then
                echo -e "${CHECK} C++扩展可用"
            else
                echo -e "${WARNING} C++扩展不可用，但继续安装开发工具"
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

    # C++扩展已在 sage-middleware 安装时通过 scikit-build-core 自动构建
    # 上面的验证步骤已检查扩展状态

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
