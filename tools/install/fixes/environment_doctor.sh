#!/bin/bash
# SAGE 环境医生 - 全面的Python环境诊断和修复工具
# 智能检测和解决各种常见的Python环境问题

# 颜色和样式定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
UNDERLINE='\033[4m'

# 状态标识符
CHECK_MARK="✓"
CROSS_MARK="✗"
WARNING_MARK="⚠"
INFO_MARK="ℹ"
TOOL_MARK="🔧"
ROCKET_MARK="🚀"

# 全局变量
SAGE_DIR="${SAGE_DIR:-$(pwd)/.sage}"
DOCTOR_LOG="$SAGE_DIR/logs/environment_doctor.log"
ISSUES_FOUND=0
FIXES_APPLIED=0
CRITICAL_ISSUES=0

# 确保 .sage 目录结构存在
ensure_sage_directories() {
    mkdir -p "$SAGE_DIR/logs"
    mkdir -p "$SAGE_DIR/tmp"
    mkdir -p "$SAGE_DIR/cache"
}

# ================================
# 核心诊断框架
# ================================

# 日志记录函数
log_message() {
    local level="$1"
    shift
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$level] $*" >> "$DOCTOR_LOG"
}

# 问题报告结构
declare -A ISSUE_REGISTRY
declare -A FIX_REGISTRY
declare -A ISSUE_SEVERITY

# 注册问题和修复方案
register_issue() {
    local issue_id="$1"
    local description="$2"
    local severity="$3"  # critical, major, minor
    local fix_function="$4"

    ISSUE_REGISTRY["$issue_id"]="$description"
    FIX_REGISTRY["$issue_id"]="$fix_function"
    ISSUE_SEVERITY["$issue_id"]="$severity"
}

# 报告发现的问题
report_issue() {
    local issue_id="$1"
    local details="$2"

    ISSUES_FOUND=$((ISSUES_FOUND + 1))

    case "${ISSUE_SEVERITY[$issue_id]}" in
        "critical")
            CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
            echo -e "${RED}${BOLD}${CROSS_MARK} 严重问题${NC}: ${ISSUE_REGISTRY[$issue_id]}"
            ;;
        "major")
            echo -e "${YELLOW}${BOLD}${WARNING_MARK} 重要问题${NC}: ${ISSUE_REGISTRY[$issue_id]}"
            ;;
        "minor")
            echo -e "${BLUE}${INFO_MARK} 建议优化${NC}: ${ISSUE_REGISTRY[$issue_id]}"
            ;;
    esac

    if [ -n "$details" ]; then
        echo -e "    ${DIM}$details${NC}"
    fi

    log_message "ISSUE" "$issue_id: ${ISSUE_REGISTRY[$issue_id]} - $details"
}

# ================================
# 具体诊断模块
# ================================

# 1. Python环境基础检查
check_python_environment() {
    echo -e "\n${BLUE}${BOLD}🐍 Python 环境诊断${NC}"

    # 检查Python版本
    local python_version=""
    if command -v python3 >/dev/null 2>&1; then
        python_version=$(python3 --version 2>&1 | grep -oP 'Python \K[0-9]+\.[0-9]+\.[0-9]+')
        echo -e "  ${GREEN}${CHECK_MARK}${NC} Python 版本: $python_version"
        log_message "INFO" "Python version: $python_version"

        # 检查是否为推荐版本
        if [[ ! "$python_version" =~ ^3\.(9|10|11|12) ]]; then
            report_issue "python_version" "推荐使用 Python 3.9-3.12，当前版本可能存在兼容性问题" "major"
        fi
    else
        report_issue "python_missing" "未找到 Python3 安装" "critical"
        return 1
    fi

    # 检查pip
    if command -v pip >/dev/null 2>&1 || command -v pip3 >/dev/null 2>&1; then
        local pip_version=""
        if command -v pip3 >/dev/null 2>&1; then
            pip_version=$(pip3 --version 2>&1 | grep -oP 'pip \K[0-9]+\.[0-9]+\.[0-9]+')
        else
            pip_version=$(pip --version 2>&1 | grep -oP 'pip \K[0-9]+\.[0-9]+\.[0-9]+')
        fi
        echo -e "  ${GREEN}${CHECK_MARK}${NC} pip 版本: $pip_version"
        log_message "INFO" "pip version: $pip_version"
    else
        report_issue "pip_missing" "未找到 pip 包管理器" "critical"
    fi

    # 检查虚拟环境
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo -e "  ${GREEN}${CHECK_MARK}${NC} 虚拟环境: $(basename "$VIRTUAL_ENV")"
        log_message "INFO" "Using virtual environment: $VIRTUAL_ENV"
    elif [[ -n "$CONDA_DEFAULT_ENV" ]]; then
        echo -e "  ${GREEN}${CHECK_MARK}${NC} Conda 环境: $CONDA_DEFAULT_ENV"
        log_message "INFO" "Using conda environment: $CONDA_DEFAULT_ENV"
    else
        report_issue "no_virtual_env" "建议使用虚拟环境以避免包冲突" "minor"
    fi
}

# 2. 包管理器冲突检查
check_package_manager_conflicts() {
    echo -e "\n${PURPLE}${BOLD}📦 包管理器诊断${NC}"

    local conda_available=$(command -v conda >/dev/null 2>&1 && echo "true" || echo "false")
    local pip_available=$(command -v pip3 >/dev/null 2>&1 && echo "true" || echo "false")

    echo -e "  ${INFO_MARK} Conda 可用: $conda_available"
    echo -e "  ${INFO_MARK} Pip 可用: $pip_available"

    # 检查混合安装的关键包
    local mixed_packages=()

    for package in "numpy" "torch" "transformers" "scipy"; do
        local conda_installed=""
        local pip_installed=""

        if [ "$conda_available" = "true" ]; then
            conda_installed=$(conda list "$package" 2>/dev/null | grep "^$package" | head -1 | awk '{print $2}' || echo "")
        fi

        if [ "$pip_available" = "true" ]; then
            pip_installed=$(python3 -c "import $package; print($package.__version__)" 2>/dev/null || echo "")
        fi

        if [ -n "$conda_installed" ] && [ -n "$pip_installed" ] && [ "$conda_installed" != "$pip_installed" ]; then
            mixed_packages+=("$package(conda:$conda_installed,pip:$pip_installed)")
            report_issue "mixed_package_$package" "包 $package 同时被 conda 和 pip 管理，版本不一致" "major"
        fi
    done

    if [ ${#mixed_packages[@]} -eq 0 ]; then
        echo -e "  ${GREEN}${CHECK_MARK}${NC} 未发现包管理器冲突"
    fi
}

# 3. 核心依赖检查
check_core_dependencies() {
    echo -e "\n${CYAN}${BOLD}🔍 核心依赖诊断${NC}"

    # 关键包及其要求
    declare -A required_packages=(
        ["numpy"]=">=1.20.0,<3.0.0"
        ["torch"]=">=2.0.0"
        ["transformers"]=">=4.20.0"
        ["accelerate"]=""
    )

    for package in "${!required_packages[@]}"; do
        local version=""
        local status="missing"

        # 尝试获取包版本
        version=$(python3 -c "import $package; print($package.__version__)" 2>/dev/null || echo "")

        if [ -n "$version" ]; then
            status="installed"
            echo -e "  ${GREEN}${CHECK_MARK}${NC} $package: $version"
            log_message "INFO" "$package version: $version"

            # 特殊版本检查
            case "$package" in
                "numpy")
                    if [[ "$version" =~ ^1\. ]]; then
                        report_issue "numpy_v1" "numpy 1.x 版本可能与某些深度学习库不兼容，建议升级到 2.x" "major"
                    fi
                    ;;
                "torch")
                    # 检查CUDA支持
                    local cuda_available=$(python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null || echo "False")
                    if [ "$cuda_available" = "True" ]; then
                        local cuda_version=$(python3 -c "import torch; print(torch.version.cuda)" 2>/dev/null || echo "unknown")
                        echo -e "    ${GREEN}${CHECK_MARK}${NC} CUDA 支持: $cuda_version"
                    else
                        echo -e "    ${YELLOW}${WARNING_MARK}${NC} 未检测到 CUDA 支持"
                    fi
                    ;;
            esac
        else
            echo -e "  ${RED}${CROSS_MARK}${NC} $package: 未安装"
            report_issue "missing_$package" "缺少必需的包: $package" "critical"
        fi
    done
}

# 4. 特定错误检查
check_specific_issues() {
    echo -e "\n${YELLOW}${BOLD}🔎 特定问题诊断${NC}"

    # 检查numpy RECORD文件问题
    if python3 -c "import numpy" >/dev/null 2>&1; then
        if ! python3 -c "import pkg_resources; pkg_resources.get_distribution('numpy')" >/dev/null 2>&1; then
            report_issue "numpy_corrupted" "numpy 安装记录损坏，可能导致升级失败" "major"
        fi
    fi

    # 检查torch版本兼容性
    local torch_version=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null || echo "")
    local numpy_version=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "")

    if [ -n "$torch_version" ] && [ -n "$numpy_version" ]; then
        # 检查已知的不兼容组合
        if [[ "$torch_version" =~ ^2\. ]] && [[ "$numpy_version" =~ ^1\. ]]; then
            report_issue "torch_numpy_compat" "PyTorch 2.x 建议使用 numpy 2.x 以获得最佳性能" "major"
        fi
    fi

    # 检查CUDA环境
    if command -v nvidia-smi >/dev/null 2>&1; then
        local driver_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits 2>/dev/null | head -1)
        echo -e "  ${INFO_MARK} NVIDIA 驱动版本: $driver_version"

        # 检查CUDA工具包
        if [ -d "/usr/local/cuda" ]; then
            local cuda_version=$(cat /usr/local/cuda/version.txt 2>/dev/null | grep -oP 'CUDA Version \K[0-9]+\.[0-9]+' || echo "unknown")
            echo -e "  ${INFO_MARK} CUDA 工具包版本: $cuda_version"
        fi
    fi

    # 检查磁盘空间
    local available_space=$(df . | tail -1 | awk '{print $4}')
    local available_gb=$((available_space / 1024 / 1024))

    if [ "$available_gb" -lt 5 ]; then
        report_issue "low_disk_space" "磁盘空间不足 ($available_gb GB)，建议至少 5GB 可用空间" "major"
    fi
}

# ================================
# 自动修复模块
# ================================

# numpy 问题修复
fix_numpy_corrupted() {
    echo -e "\n${TOOL_MARK} 修复 numpy 安装问题..."

    # 清理损坏的numpy
    pip3 uninstall numpy -y >/dev/null 2>&1 || true
    python3 -c "
import os, shutil, sys
try:
    import numpy
    numpy_path = os.path.dirname(numpy.__file__)
    if 'site-packages' in numpy_path:
        shutil.rmtree(numpy_path, ignore_errors=True)
        print('清理了损坏的 numpy 安装')
except Exception:
    pass
" 2>/dev/null || true

    # 重新安装
    if python3 -m pip install --no-cache-dir numpy>=2.0.0 >/dev/null 2>&1; then
        echo -e "  ${GREEN}${CHECK_MARK}${NC} numpy 修复成功"
        FIXES_APPLIED=$((FIXES_APPLIED + 1))
        log_message "FIX" "Successfully fixed numpy installation"
        return 0
    else
        echo -e "  ${RED}${CROSS_MARK}${NC} numpy 修复失败"
        return 1
    fi
}

# 混合包管理器问题修复
fix_mixed_packages() {
    echo -e "\n${TOOL_MARK} 清理包管理器冲突..."

    local packages_to_fix=("numpy" "torch" "transformers")

    for package in "${packages_to_fix[@]}"; do
        # 如果conda和pip都有，优先使用pip
        if conda list "$package" >/dev/null 2>&1 && pip3 show "$package" >/dev/null 2>&1; then
            echo -e "  清理 $package 的 conda 安装..."
            conda uninstall "$package" -y >/dev/null 2>&1 || true
        fi
    done

    echo -e "  ${GREEN}${CHECK_MARK}${NC} 包管理器冲突清理完成"
    FIXES_APPLIED=$((FIXES_APPLIED + 1))
}

# 环境优化建议
suggest_environment_optimization() {
    echo -e "\n${BLUE}${BOLD}💡 环境优化建议${NC}"

    if [[ -z "$VIRTUAL_ENV" && -z "$CONDA_DEFAULT_ENV" ]]; then
        echo -e "  ${YELLOW}${WARNING_MARK}${NC} 建议创建虚拟环境："
        echo -e "    ${DIM}conda create -n sage-env python=3.11 -y${NC}"
        echo -e "    ${DIM}conda activate sage-env${NC}"
    fi

    echo -e "  ${INFO_MARK} 定期更新包管理器："
    echo -e "    ${DIM}python3 -m pip install --upgrade pip${NC}"

    echo -e "  ${INFO_MARK} 清理pip缓存："
    echo -e "    ${DIM}pip3 cache purge${NC}"
}

# ================================
# 主要诊断流程
# ================================

# 注册所有已知问题和修复方案
register_all_issues() {
    register_issue "python_version" "Python版本兼容性问题" "major" ""
    register_issue "python_missing" "Python解释器缺失" "critical" ""
    register_issue "pip_missing" "pip包管理器缺失" "critical" ""
    register_issue "no_virtual_env" "未使用虚拟环境" "minor" ""
    register_issue "numpy_corrupted" "numpy安装损坏" "major" "fix_numpy_corrupted"
    register_issue "numpy_v1" "numpy版本过旧" "major" ""
    register_issue "torch_numpy_compat" "PyTorch与numpy版本不匹配" "major" ""
    register_issue "low_disk_space" "磁盘空间不足" "major" ""

    # 动态注册混合包问题
    for package in "numpy" "torch" "transformers"; do
        register_issue "mixed_package_$package" "包管理器冲突" "major" "fix_mixed_packages"
    done
}

# 执行完整诊断
run_full_diagnosis() {
    echo -e "${BLUE}${BOLD}${ROCKET_MARK} SAGE 环境医生 - 开始全面诊断${NC}\n"

    # 确保目录结构存在
    ensure_sage_directories

    log_message "START" "Starting SAGE environment diagnosis"

    # 初始化
    register_all_issues

    # 执行所有检查
    check_python_environment
    check_package_manager_conflicts
    check_core_dependencies
    check_specific_issues

    # 诊断总结
    echo -e "\n${BLUE}${BOLD}📋 诊断总结${NC}"
    echo -e "  发现问题: $ISSUES_FOUND 个"
    echo -e "  严重问题: $CRITICAL_ISSUES 个"

    if [ "$ISSUES_FOUND" -eq 0 ]; then
        echo -e "\n${GREEN}${BOLD}${CHECK_MARK} 恭喜！您的环境状况良好${NC}"
        echo -e "${DIM}SAGE 应该能够正常安装和运行${NC}"
        return 0
    else
        echo -e "\n${YELLOW}${BOLD}${WARNING_MARK} 发现了一些需要注意的问题${NC}"
        return 1
    fi
}

# 执行自动修复
run_auto_fixes() {
    if [ "$ISSUES_FOUND" -eq 0 ]; then
        return 0
    fi

    echo -e "\n${TOOL_MARK} ${BOLD}自动修复选项${NC}"
    echo -e "${DIM}SAGE 可以尝试自动修复某些检测到的问题${NC}\n"

    # 询问是否进行自动修复
    read -p "是否允许 SAGE 尝试自动修复环境问题？[Y/n] " -r response
    response=${response,,}

    if [[ "$response" =~ ^(n|no)$ ]]; then
        echo -e "${YELLOW}跳过自动修复${NC}"
        return 0
    fi

    echo -e "\n${TOOL_MARK} 开始自动修复..."

    # 使用集合来避免重复执行相同的修复函数
    local executed_fixes=()

    # 执行修复
    for issue_id in "${!FIX_REGISTRY[@]}"; do
        local fix_function="${FIX_REGISTRY[$issue_id]}"
        if [ -n "$fix_function" ] && declare -f "$fix_function" >/dev/null; then
            # 检查是否已经执行过这个修复函数
            local already_executed=false
            for executed in "${executed_fixes[@]}"; do
                if [ "$executed" = "$fix_function" ]; then
                    already_executed=true
                    break
                fi
            done

            # 如果没有执行过，则执行修复
            if [ "$already_executed" = false ]; then
                "$fix_function"
                executed_fixes+=("$fix_function")
            fi
        fi
    done

    if [ "$FIXES_APPLIED" -gt 0 ]; then
        echo -e "\n${GREEN}${BOLD}${CHECK_MARK} 修复完成${NC}"
        echo -e "  应用修复: $FIXES_APPLIED 个"
        echo -e "\n${INFO_MARK} 建议重新运行诊断以验证修复效果："
        echo -e "  ${DIM}./quickstart.sh --doctor${NC}"
    else
        echo -e "\n${YELLOW}${WARNING_MARK} 未能自动修复所有问题${NC}"
        suggest_environment_optimization
    fi
}

# 显示详细帮助
show_help() {
    echo -e "${BLUE}${BOLD}SAGE 环境医生 - 使用指南${NC}\n"

    echo -e "${BOLD}用法:${NC}"
    echo -e "  ./quickstart.sh --doctor              # 完整诊断"
    echo -e "  ./quickstart.sh --doctor --fix        # 诊断并自动修复"
    echo -e "  ./quickstart.sh --doctor --check-only # 仅检查，不修复\n"

    echo -e "${BOLD}功能特点:${NC}"
    echo -e "  ${CHECK_MARK} 智能检测 Python 环境问题"
    echo -e "  ${CHECK_MARK} 识别包管理器冲突"
    echo -e "  ${CHECK_MARK} 验证深度学习库兼容性"
    echo -e "  ${CHECK_MARK} 自动修复常见问题"
    echo -e "  ${CHECK_MARK} 提供优化建议\n"

    echo -e "${BOLD}常见问题解决:${NC}"
    echo -e "  • numpy 安装损坏或版本冲突"
    echo -e "  • PyTorch 与 CUDA 兼容性问题"
    echo -e "  • conda 与 pip 混合安装冲突"
    echo -e "  • 磁盘空间不足"
    echo -e "  • Python 版本兼容性\n"
}

# ================================
# 主入口函数
# ================================

main() {
    case "${1:-}" in
        "--help"|"-h")
            show_help
            ;;
        "--check-only")
            run_full_diagnosis
            ;;
        "--fix")
            run_full_diagnosis
            run_auto_fixes
            ;;
        *)
            run_full_diagnosis
            if [ "$ISSUES_FOUND" -gt 0 ]; then
                run_auto_fixes
            fi
            ;;
    esac

    log_message "END" "Diagnosis completed. Issues: $ISSUES_FOUND, Fixes: $FIXES_APPLIED"
}

# 如果直接运行此脚本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
