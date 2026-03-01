#!/bin/bash
# SAGE 安装脚本 - 主安装控制器
# 统一管理不同安装模式的安装流程

# 导入所有安装器
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/interface.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/logging.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../examination_tools/sage_check.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../download_tools/environment_config.sh"
source "$(dirname "${BASH_SOURCE[0]}")/core_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/scientific_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/dev_installer.sh"
# libstdcxx_fix.sh 已禁用 - 现代 conda 环境提供足够的 libstdc++ 版本
# source "$(dirname "${BASH_SOURCE[0]}")/../fixes/libstdcxx_fix.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../fixes/cpp_extensions_fix.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../fixes/build_cache_cleaner.sh"

# pip 缓存清理函数

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

clean_pip_cache() {
    log_info "开始清理 pip 缓存" "PIPCache"
    echo -e "${BLUE}🧹 清理 pip 缓存...${NC}"

    # 检查是否支持 pip cache 命令
    if ! $PIP_CMD cache --help &>/dev/null; then
        log_info "当前 pip 版本不支持 cache 命令，跳过缓存清理" "PIPCache"
        echo -e "${DIM}当前 pip 版本不支持 cache 命令，跳过缓存清理${NC}"
        echo ""
        return 0
    fi

    # 检查缓存是否被禁用 (CI 环境常见)
    local cache_info_output
    cache_info_output=$($PIP_CMD cache info 2>&1) || true
    if echo "$cache_info_output" | grep -q "cache is disabled"; then
        log_info "pip 缓存已禁用 (CI 环境)，跳过清理" "PIPCache"
        echo -e "${DIM}pip 缓存已禁用 (CI 环境)，跳过清理${NC}"
        echo ""
        return 0
    fi

    log_debug "使用 pip cache purge 清理缓存" "PIPCache"
    echo -e "${DIM}使用 pip cache purge 清理缓存${NC}"

    # 显示缓存大小
    local cache_info
    cache_info=$(echo "$cache_info_output" | grep -E "(Location|Size)" || true)
    if [ -n "$cache_info" ]; then
        log_debug "缓存信息: $cache_info" "PIPCache"
        echo -e "${DIM}缓存信息:${NC}"
        echo "$cache_info" | sed 's/^/  /'
    fi

    # 执行缓存清理
    if log_command "PIPCache" "MAIN" "$PIP_CMD cache purge"; then
        log_info "pip 缓存清理完成" "PIPCache"
        echo -e "${CHECK} pip 缓存清理完成"
    else
        log_warn "pip 缓存清理失败，但继续安装" "PIPCache"
        echo -e "${WARNING} pip 缓存清理失败，但继续安装"
    fi

    echo ""
}

# 验证C++扩展函数 - 已迁移为独立 PyPI 包
verify_cpp_extensions() {
    log_info "C++ 扩展已迁移为独立 PyPI 包" "CPPExt"
    echo -e "${DIM}ℹ️  C++ 扩展（sageVDB/sageFlow/sageTSDB）已迁移为独立 PyPI 包${NC}"
    echo -e "${DIM}   - isage-vdb (was sageVDB)${NC}"
    echo -e "${DIM}   - isage-flow (was sageFlow)${NC}"
    echo -e "${DIM}   - isage-tsdb (was sageTSDB)${NC}"
    echo -e "${DIM}   如需使用，请通过 pip 安装这些独立包${NC}"
    echo ""

    # sage-middleware 现在只包含 Python 兼容层，总是返回成功
    log_info "sage-middleware 安装完成（仅包含 Python 兼容层）" "CPPExt"
    return 0

    # 以下代码已废弃，保留供参考
    # ----------------------------------------------------------------

    # 在CI环境中增加短暂延迟，确保文件系统同步
    if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" ]]; then
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
        else
            print('')
            print(f'⚠️  部分扩展不可用 ({total}/{total_expected})，功能将受限')
            print('💡 提示: 确保已安装构建依赖 (cmake, build-essential) 并重新安装 isage-middleware')
        sys.exit(0)  # 部分成功也返回 0
    else:
        print('')
        print('❌ 没有任何 C++ 扩展可用')
        print('💡 这可能是因为：')
        print('   1. 缺少构建工具：apt-get install build-essential cmake')
        print('   2. 未按 --dev 安装或 isage-middleware 构建失败')
        print('   3. 查看详细日志了解更多信息')
        sys.exit(1)
except Exception as e:
    print(f'❌ 扩展验证过程失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" 2>&1)
        validation_result=$?
        log_debug "C++扩展验证输出:\n$verify_output" "CPPExt"

        # 输出验证结果
        echo "$verify_output"

        if [ $validation_result -eq 0 ]; then
            echo -e "${CHECK} C++ 扩展可用 (sage_db, sage_flow, sage_tsdb)"
            echo -e "${DIM}现在可以使用高性能数据库和流处理功能${NC}"
            log_info "C++扩展验证成功" "CPPExt"
            return 0
        else
            echo -e "${WARNING} 扩展验证失败"
            log_warn "扩展验证失败" "CPPExt"
            echo -e "${DIM}💡 提示: C++扩展在 sage-middleware 安装时自动构建${NC}"
            echo -e "${DIM}   如果验证失败，可能是因为：${NC}"
            echo -e "${DIM}   1. 缺少构建工具：apt-get install build-essential cmake${NC}"
            echo -e "${DIM}   2. 未按 --dev 模式或 isage-middleware 安装失败${NC}"
            echo -e "${DIM}   3. 查看详细日志：cat ${SAGE_INSTALL_LOG:-}${NC}"
            return 1
        fi
}

# 主安装函数
install_sage() {
    local mode="${1:-dev}"
    local environment="${2:-conda}"
    local clean_cache="${3:-true}"

    # CI 环境特殊处理：双重保险，确保使用 pip
    # 即使参数解析阶段没有正确设置，这里也会修正
    if [[ (-n "${CI:-}" || -n "${GITHUB_ACTIONS:-}") && "$environment" = "conda" ]]; then
        echo -e "${INFO} CI 环境中检测到 environment='conda'，强制使用 pip（CI 优化）"
        environment="pip"
    fi

    # 根据安装环境设置 SAGE_ENV_NAME
    # pip 模式不使用 conda 环境，清空 SAGE_ENV_NAME 避免验证脚本尝试使用 conda
    if [ "$environment" = "pip" ]; then
        export SAGE_ENV_NAME=""
        export PIP_CMD="python3 -m pip"
        export PYTHON_CMD="python3"
    fi

    # 获取项目根目录和日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/.sage/logs/install.log"

    echo ""
    echo -e "${GEAR} 开始安装 SAGE 包 (${mode} 模式, ${environment} 环境)..."
    echo ""
    mkdir -p "$(dirname "$log_file")"
    echo -e "${BLUE}📝 安装日志: ${log_file}${NC}"
    echo -e "${DIM}   可以使用以下命令实时查看日志:${NC}"
    echo -e "${DIM}   tail -f ${log_file}${NC}"
    echo ""

    # 配置安装环境（包含所有检查）
    log_phase_start "环境配置" "MAIN"
    configure_installation_environment "$environment" "$mode"
    log_phase_end "环境配置" "success" "MAIN"

    # 清理构建缓存（检测版本不一致的 egg-info）
    log_phase_start "构建缓存检查" "MAIN"
    detect_and_clean_cache false
    log_phase_end "构建缓存检查" "success" "MAIN"

    # 清理 pip 缓存（如果启用）
    if [ "$clean_cache" = "true" ]; then
        log_phase_start "缓存清理" "MAIN"
        clean_pip_cache "$log_file"
        log_phase_end "缓存清理" "success" "MAIN"
    else
        echo -e "${DIM}跳过 pip 缓存清理（使用 --no-cache-clean 选项）${NC}"
        log_info "跳过 pip 缓存清理（用户指定）" "MAIN"
        echo ""
    fi

    # 记录安装开始到日志
    echo "" >> "$log_file"
    echo "========================================" >> "$log_file"
    echo "SAGE 主要安装过程开始 - $(date)" >> "$log_file"
    echo "安装模式: $mode" >> "$log_file"
    echo "安装环境: $environment" >> "$log_file"
    echo "PIP 命令: $PIP_CMD" >> "$log_file"
    echo "Python 命令: $PYTHON_CMD" >> "$log_file"
    echo "========================================" >> "$log_file"

    # 安装前记录已安装包列表，便于后续卸载和清理
    local track_script="$project_root/tools/cleanup/track_install.sh"
    if [ -f "$track_script" ]; then
        echo -e "${DIM}记录安装前的 SAGE 包列表...${NC}"
        bash "$track_script" pre-install || true
    fi

    log_info "SAGE 主要安装过程开始" "MAIN"
    log_info "安装模式: $mode | 环境: $environment" "MAIN"

    echo ""
    case "$mode" in
        "standard")
            # standard 模式：仅核心包，不含 torch/GPU 依赖
            echo -e "${YELLOW}standard 安装模式：核心子包（无 torch/CUDA）${NC}"
            log_phase_start "standard 安装模式" "MAIN"

            if ! install_core_packages "standard"; then
                log_phase_end "standard 安装模式" "failure" "MAIN"
                return 1
            fi

            log_phase_end "standard 安装模式" "success" "MAIN"
            ;;
        "full")
            # full 模式：standard + 扩展能力集 via packages/sage[full]
            echo -e "${CYAN}full 安装模式：standard + 扩展能力集（packages/sage[full]）${NC}"
            log_phase_start "full 安装模式" "MAIN"

            if ! install_core_packages "full"; then
                log_phase_end "full 安装模式" "failure" "MAIN"
                return 1
            fi

            log_phase_end "full 安装模式" "success" "MAIN"
            ;;
        "dev")
            # dev 模式：full + 开发工具 + 本地 editable 优先
            echo -e "${GREEN}dev 安装模式：full + 开发工具 + 本地 editable（尽量）${NC}"
            log_phase_start "开发安装模式" "MAIN"

            if ! install_core_packages "dev"; then
                log_phase_end "开发安装模式" "failure" "MAIN"
                return 1
            fi

            # 验证开发工具可用性
            log_info "验证开发工具" "MAIN"
            install_dev_packages

            log_phase_end "开发安装模式" "success" "MAIN"
            echo ""
            ;;
        *)
            echo -e "${WARNING} 未知安装模式: $mode，使用 standard 安装"
            log_warn "未知安装模式 $mode，使用 standard 安装" "MAIN"
            log_phase_start "默认 standard 安装" "MAIN"

            install_core_packages "standard"

            log_phase_end "默认 standard 安装" "success" "MAIN"
            ;;
    esac

    echo ""
    echo -e "${CHECK} SAGE 基础安装完成！"
    log_info "SAGE 基础安装完成" "MAIN"

    # 自动清理空目录和临时构建文件
    echo ""
    echo -e "${BLUE}🧹 清理临时文件和空目录...${NC}"
    log_info "开始清理临时文件" "MAIN"

    # 确定正确的 sage-dev 命令
    local sage_dev_cmd="sage-dev"
    if [ "$environment" = "conda" ] && [ -n "$SAGE_ENV_NAME" ]; then
        sage_dev_cmd="conda run -n $SAGE_ENV_NAME sage-dev"
    elif [ "$environment" = "pip" ] && [ -x "$HOME/.local/bin/sage-dev" ]; then
        sage_dev_cmd="$HOME/.local/bin/sage-dev"
    fi

    # 执行清理
    if { [ "$environment" = "conda" ] && conda run -n "$SAGE_ENV_NAME" which sage-dev >/dev/null 2>&1; } || \
       { [ "$environment" = "pip" ] && command -v sage-dev >/dev/null 2>&1; } || \
       { [ "$environment" = "pip" ] && [ -x "$HOME/.local/bin/sage-dev" ]; }; then
        if $sage_dev_cmd project clean 2>&1 | tee -a "$log_file"; then
            echo -e "${CHECK} 清理完成"
            log_info "项目清理成功" "MAIN"
        else
            echo -e "${DIM}   清理跳过（非关键操作）${NC}"
            log_warn "项目清理失败，但不影响安装" "MAIN"
        fi
    else
        echo -e "${DIM}   sage-dev 命令不可用，跳过清理${NC}"
        log_warn "sage-dev 不可用，跳过清理" "MAIN"
    fi

    # C++扩展已在 sage-middleware 安装时通过 scikit-build-core 自动构建
    # 上面的验证步骤已检查扩展状态

    # 记录安装完成
    log_info "SAGE 安装完成" "MAIN"

    log_info "安装结束" "MAIN"

    # 🔍 CI/CD 检查：验证没有从 PyPI 下载本地包
    if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" || -n "${GITLAB_CI:-}" ]]; then
        echo ""
        echo -e "${BLUE}🔍 CI/CD 安全检查：验证依赖完整性...${NC}"
        log_phase_start "依赖完整性检查" "MAIN"

        local monitor_script="$project_root/tools/install/installation_table/pip_install_monitor.sh"
        if [ -f "$monitor_script" ] && [ -f "$log_file" ]; then
            if bash "$monitor_script" analyze "$log_file"; then
                log_info "依赖完整性检查通过" "MAIN"
                echo -e "${CHECK} 依赖完整性检查通过"
                log_phase_end "依赖完整性检查" "success" "MAIN"
            else
                log_error "依赖完整性检查失败！检测到从 PyPI 下载了本地包" "MAIN"
                echo -e "${WARNING} 依赖完整性检查失败！"
                echo -e "${RED}检测到从 PyPI 下载了本地包，这是一个严重的配置错误！${NC}"
                echo -e "${YELLOW}请检查 pyproject.toml 中的依赖声明${NC}"
                log_phase_end "依赖完整性检查" "failure" "MAIN"
                # 在 CI 中这是一个错误，但不中断安装（允许查看完整日志）
                echo "DEPENDENCY_VIOLATION_DETECTED=true" >> "$GITHUB_ENV" || true
            fi
        else
            log_warn "监控脚本或日志文件不存在，跳过检查" "MAIN"
            echo -e "${DIM}监控脚本或日志文件不存在，跳过检查${NC}"
            log_phase_end "依赖完整性检查" "skipped" "MAIN"
        fi
    fi

    # 安装后记录包列表和安装信息
    if [ -f "$track_script" ]; then
        echo "" >> "$log_file"
        echo "包追踪信息:" >> "$log_file"
        bash "$track_script" post-install "$mode" "$environment" "false" >> "$log_file" 2>&1 || true
    fi

    # 显示安装信息
    log_info "显示安装成功信息" "MAIN"
    show_install_success "$mode"
}
