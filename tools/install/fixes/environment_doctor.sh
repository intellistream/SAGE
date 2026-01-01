#!/bin/bash
# SAGE 环境医生 - 全面的Python环境诊断和修复工具
# 智能检测和解决各种常见的Python环境问题

# ================================
# 错误处理设置
# ================================
# 不使用 set -u，因为我们需要灵活处理未设置的环境变量
# 而是通过 ${VAR:-default} 语法来安全访问所有变量

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

# ================================
# 全局变量初始化
# ================================
# 项目路径相关
SAGE_DIR="${SAGE_DIR:-$(pwd)/.sage}"
DOCTOR_LOG="$SAGE_DIR/logs/environment_doctor.log"

# 计数器
ISSUES_FOUND=0
FIXES_APPLIED=0
CRITICAL_ISSUES=0
NEED_RESTART_SHELL=0

# 配置选项（支持通过环境变量传入）
AUTO_CONFIRM_FIX="${AUTO_CONFIRM_FIX:-false}"  # 是否自动确认修复（用于自动化测试）

# 环境变量安全默认值（避免 unbound variable 错误）
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
CONDA_DEFAULT_ENV="${CONDA_DEFAULT_ENV:-}"
CONDA_PREFIX="${CONDA_PREFIX:-}"
HOME="${HOME:-$(/usr/bin/env | grep ^HOME= | cut -d= -f2)}"

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
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        echo -e "  ${GREEN}${CHECK_MARK}${NC} 虚拟环境: $(basename "${VIRTUAL_ENV:-}")"
        log_message "INFO" "Using virtual environment: ${VIRTUAL_ENV:-}"
    elif [[ -n "${CONDA_DEFAULT_ENV:-}" ]]; then
        echo -e "  ${GREEN}${CHECK_MARK}${NC} Conda 环境: ${CONDA_DEFAULT_ENV:-}"
        log_message "INFO" "Using conda environment: ${CONDA_DEFAULT_ENV:-}"
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

# 2.5. CLI 工具冲突检查 (CI 残留检测)
check_cli_conflicts() {
    echo -e "\n${PURPLE}${BOLD}🛠️  CLI 工具冲突诊断${NC}"

    local conflict_found=false
    local local_bin="$HOME/.local/bin"

    # 仅在非 CI 环境或明确处于虚拟环境中时检查
    # 避免误删 CI 正在使用的工具
    if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" ]]; then
        return 0
    fi

    # 检查 sage 和 sage-dev
    for tool in "sage" "sage-dev"; do
        if [ -f "$local_bin/$tool" ]; then
            # 检查是否在虚拟环境中
            if [[ -n "${VIRTUAL_ENV:-}" || -n "${CONDA_PREFIX:-}" ]]; then
                # 如果在虚拟环境中，且 ~/.local/bin/$tool 存在，这通常是 CI 残留
                # 进一步检查：如果 which $tool 指向的是 ~/.local/bin/$tool，那么肯定有冲突
                # 或者如果当前环境应该有自己的 $tool 但被 ~/.local/bin 覆盖了

                echo -e "  ${YELLOW}${WARNING_MARK}${NC} 检测到 $local_bin/$tool"
                report_issue "cli_conflict_$tool" "检测到 CI/CD 残留的 $tool 命令，可能与当前开发环境冲突" "major" "fix_cli_conflicts"
                conflict_found=true
            fi
        fi
    done

    if [ "$conflict_found" = "false" ]; then
        echo -e "  ${GREEN}${CHECK_MARK}${NC} 未发现 CLI 工具冲突"
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
            echo -e "  ${BLUE}${INFO_MARK}${NC} $package: 未安装（将在安装过程中安装）"
            # 注意：不将缺少的包报告为 critical 问题，因为这些包会在后续安装步骤中自动安装
            # report_issue "missing_$package" "缺少必需的包: $package" "minor"
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

# 5. 开发工具检查
check_dev_tools() {
    echo -e "\n${PURPLE}${BOLD}🛠️  开发工具诊断${NC}"

    # 检查 pytest 及其相关插件
    declare -A dev_tools=(
        ["pytest"]="pytest>=7.0.0"
        ["pytest-cov"]="pytest-cov>=4.0.0"
        ["pytest-asyncio"]="pytest-asyncio>=0.21.0"
        ["pytest-mock"]="pytest-mock>=3.10.0"
        ["pytest-timeout"]="pytest-timeout>=2.1.0"
        ["pytest-benchmark"]="pytest-benchmark>=4.0.0"
        ["ruff"]="ruff==0.14.6"
        ["mypy"]="mypy>=1.0.0"
        ["pre-commit"]="pre-commit>=3.0.0"
    )

    local missing_tools=()
    local installed_tools=()

    for tool in "${!dev_tools[@]}"; do
        local version=""
        local package_name="$tool"

        # 使用 importlib.metadata 获取版本（Python 3.8+ 标准方法）
        # 这比直接 import 模块更可靠，因为不是所有包都有 __version__ 属性
        version=$(python3 -c "from importlib.metadata import version; print(version('$package_name'))" 2>/dev/null || echo "")

        if [ -n "$version" ]; then
            echo -e "  ${GREEN}${CHECK_MARK}${NC} $tool: $version"
            installed_tools+=("$tool")
            log_message "INFO" "$tool version: $version"
        else
            echo -e "  ${YELLOW}${CROSS_MARK}${NC} $tool: 未安装"
            missing_tools+=("$tool")
            log_message "WARN" "$tool is not installed"
        fi
    done

    # 如果有缺失的工具，报告问题
    if [ ${#missing_tools[@]} -gt 0 ]; then
        local tools_list=$(IFS=", "; echo "${missing_tools[*]}")
        report_issue "dev_tools_missing" "缺少开发工具: $tools_list" "major"

        # 特别强调 pytest
        for tool in "${missing_tools[@]}"; do
            if [[ "$tool" == pytest* ]]; then
                echo -e "    ${DIM}提示: pytest 是运行测试所必需的${NC}"
                break
            fi
        done
    else
        echo -e "\n  ${GREEN}${CHECK_MARK}${NC} 所有开发工具已安装"
    fi

    # 检查 pre-commit hooks 是否已安装
    if [ -d ".git" ]; then
        if [ -f ".git/hooks/pre-commit" ]; then
            echo -e "  ${GREEN}${CHECK_MARK}${NC} pre-commit hooks: 已安装"
        else
            if command -v pre-commit >/dev/null 2>&1; then
                echo -e "  ${YELLOW}${WARNING_MARK}${NC} pre-commit hooks: 未安装（pre-commit 工具可用）"
                report_issue "pre_commit_hooks_missing" "pre-commit hooks 未安装" "minor"
            fi
        fi
    fi
}

# ================================
# 自动修复模块
# ================================

# pip 缺失修复 - 提供创建 conda 环境或安装 Miniconda 的选项
fix_pip_missing() {
    echo -e "\n${TOOL_MARK} 修复 pip 缺失问题..."

    # CI 环境检测：如果在 CI 中且 pip 可用，不需要创建 conda 环境
    if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" ]]; then
        if command -v pip >/dev/null 2>&1 || command -v pip3 >/dev/null 2>&1; then
            echo -e "  ${INFO_MARK} CI 环境检测到 pip 可用，跳过 conda 环境创建"
            log_message "INFO" "CI environment detected with pip available, skipping conda setup"
            return 0
        fi
    fi

    # 检查是否已有 conda（包括未加入 PATH 的情况）
    local conda_cmd=""
    if command -v conda >/dev/null 2>&1; then
        conda_cmd="conda"
    elif [ -x "$HOME/miniconda3/bin/conda" ]; then
        conda_cmd="$HOME/miniconda3/bin/conda"
        echo -e "  ${INFO_MARK} 检测到已安装的 Miniconda（未加入 PATH）"
        # 初始化 conda 到当前 shell
        eval "$("$conda_cmd" shell.bash hook)"
    elif [ -x "$HOME/anaconda3/bin/conda" ]; then
        conda_cmd="$HOME/anaconda3/bin/conda"
        echo -e "  ${INFO_MARK} 检测到已安装的 Anaconda（未加入 PATH）"
        eval "$("$conda_cmd" shell.bash hook)"
    fi

    if [ -n "$conda_cmd" ]; then
        echo -e "  ${INFO_MARK} 检测到 conda 已安装"

        # 检查 sage 环境是否已存在
        if "$conda_cmd" env list 2>/dev/null | grep -q "^sage "; then
            echo -e "  ${GREEN}${CHECK_MARK}${NC} conda 环境 'sage' 已存在"

            # 检查是否已经在 sage 环境中
            if [[ "${CONDA_DEFAULT_ENV:-}" == "sage" ]]; then
                echo -e "  ${GREEN}${CHECK_MARK}${NC} 当前已在 sage 环境中，无需操作"
                FIXES_APPLIED=$((FIXES_APPLIED + 1))
                return 0
            fi

            # 检查是否已配置自动激活
            local bashrc="$HOME/.bashrc"
            local sage_activate_marker="# >>> SAGE conda environment auto-activate >>>"
            if ! grep -q "$sage_activate_marker" "$bashrc" 2>/dev/null; then
                echo -e "  ${INFO_MARK} 配置终端默认激活 sage 环境..."
                cat >> "$bashrc" << 'EOF'

# >>> SAGE conda environment auto-activate >>>
# 自动激活 sage conda 环境（由 SAGE quickstart 添加）
if command -v conda >/dev/null 2>&1 || [ -x "$HOME/miniconda3/bin/conda" ]; then
    conda activate sage 2>/dev/null || true
fi
# <<< SAGE conda environment auto-activate <<<
EOF
                echo -e "  ${GREEN}${CHECK_MARK}${NC} 已配置终端自动激活 sage 环境"
            fi

            echo -e "\n  ${YELLOW}${BOLD}请运行以下命令继续安装:${NC}"
            echo -e "    ${CYAN}source ~/.bashrc${NC}"
            echo -e "    ${CYAN}./quickstart.sh --dev --yes --pip${NC}"
            FIXES_APPLIED=$((FIXES_APPLIED + 1))
            NEED_RESTART_SHELL=1
            return 0
        fi

        echo -e "  ${YELLOW}建议创建新的 conda 环境来安装 SAGE:${NC}"
        echo -e "    ${DIM}conda create -n sage python=3.11 -y${NC}"
        echo -e "    ${DIM}conda activate sage${NC}"
        echo -e "    ${DIM}./quickstart.sh --dev --yes --pip${NC}"

        # 询问是否自动创建
        local response=""
        if [ "$AUTO_CONFIRM_FIX" = "true" ]; then
            response="y"
        else
            read -p "是否自动创建 conda 环境 'sage'？[Y/n] " -r response
            response=${response,,}
        fi

        if [[ ! "$response" =~ ^(n|no)$ ]]; then
            echo -e "  ${INFO_MARK} 配置 conda 使用清华镜像源..."
            # 完全移除 defaults 频道以避免 ToS 问题
            "$conda_cmd" config --remove channels defaults 2>/dev/null || true
            "$conda_cmd" config --set channel_priority strict 2>/dev/null || true
            "$conda_cmd" config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main 2>/dev/null || true
            "$conda_cmd" config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free 2>/dev/null || true
            "$conda_cmd" config --set show_channel_urls yes 2>/dev/null || true

            echo -e "  ${INFO_MARK} 正在创建 conda 环境..."
            # 使用 --override-channels 确保只使用清华镜像，绕过 ToS
            if "$conda_cmd" create -n sage python=3.11 -y --override-channels -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main; then
                echo -e "  ${GREEN}${CHECK_MARK}${NC} conda 环境 'sage' 创建成功"

                # 配置 .bashrc 默认激活 sage 环境
                local bashrc="$HOME/.bashrc"
                local sage_activate_marker="# >>> SAGE conda environment auto-activate >>>"
                if ! grep -q "$sage_activate_marker" "$bashrc" 2>/dev/null; then
                    echo -e "  ${INFO_MARK} 配置终端默认激活 sage 环境..."
                    cat >> "$bashrc" << 'EOF'

# >>> SAGE conda environment auto-activate >>>
# 自动激活 sage conda 环境（由 SAGE quickstart 添加）
if command -v conda >/dev/null 2>&1 || [ -x "$HOME/miniconda3/bin/conda" ]; then
    conda activate sage 2>/dev/null || true
fi
# <<< SAGE conda environment auto-activate <<<
EOF
                    echo -e "  ${GREEN}${CHECK_MARK}${NC} 已配置终端自动激活 sage 环境"
                fi

                echo -e "\n  ${YELLOW}${BOLD}请运行以下命令继续安装:${NC}"
                echo -e "    ${CYAN}source ~/.bashrc${NC}"
                echo -e "    ${CYAN}./quickstart.sh --dev --yes --pip${NC}"
                FIXES_APPLIED=$((FIXES_APPLIED + 1))
                NEED_RESTART_SHELL=1
                log_message "FIX" "Created conda environment 'sage'"
                return 0
            else
                echo -e "  ${RED}${CROSS_MARK}${NC} conda 环境创建失败"
                echo -e "\n  ${YELLOW}${BOLD}请手动创建环境:${NC}"
                echo -e "    ${CYAN}conda create -n sage python=3.11 -y${NC}"
                echo -e "    ${CYAN}conda activate sage${NC}"
                echo -e "    ${CYAN}./quickstart.sh --dev --yes --pip${NC}"
                NEED_RESTART_SHELL=1
                return 1
            fi
        fi
        return 0
    fi

    # 如果没有 conda，提供安装 Miniconda 的选项
    echo -e "  ${INFO_MARK} 未检测到 conda，推荐安装 Miniconda"
    echo -e "  ${DIM}Miniconda 是轻量级的 Python 环境管理器，可避免系统 Python 污染${NC}\n"

    local response=""
    if [ "$AUTO_CONFIRM_FIX" = "true" ]; then
        response="y"
    else
        read -p "是否自动安装 Miniconda？[Y/n] " -r response
        response=${response,,}
    fi

    if [[ ! "$response" =~ ^(n|no)$ ]]; then
        echo -e "  ${INFO_MARK} 正在下载 Miniconda..."

        # 检测是否在中国大陆，使用清华镜像
        local miniconda_url=""
        if curl -s --connect-timeout 3 https://www.google.com >/dev/null 2>&1; then
            miniconda_url="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
            echo -e "  ${DIM}使用官方源${NC}"
        else
            miniconda_url="https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh"
            echo -e "  ${DIM}使用清华镜像源（更快）${NC}"
        fi

        local miniconda_script="/tmp/miniconda.sh"

        if wget -q --show-progress "$miniconda_url" -O "$miniconda_script"; then
            echo -e "  ${INFO_MARK} 正在安装 Miniconda 到 \$HOME/miniconda3..."
            if bash "$miniconda_script" -b -p "$HOME/miniconda3"; then
                echo -e "  ${GREEN}${CHECK_MARK}${NC} Miniconda 安装成功"

                # 初始化 conda
                eval "$("$HOME/miniconda3/bin/conda" shell.bash hook)"
                "$HOME/miniconda3/bin/conda" init bash >/dev/null 2>&1

                # 配置清华镜像源（避免 ToS 问题）
                echo -e "  ${INFO_MARK} 配置 conda 使用清华镜像源..."
                "$HOME/miniconda3/bin/conda" config --remove channels defaults 2>/dev/null || true
                "$HOME/miniconda3/bin/conda" config --set channel_priority strict 2>/dev/null || true
                "$HOME/miniconda3/bin/conda" config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
                "$HOME/miniconda3/bin/conda" config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free
                "$HOME/miniconda3/bin/conda" config --set show_channel_urls yes

                echo -e "  ${INFO_MARK} 正在创建 conda 环境 'sage'..."
                # 使用 --override-channels 确保只使用清华镜像，绕过 ToS
                if "$HOME/miniconda3/bin/conda" create -n sage python=3.11 -y --override-channels -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main; then
                    echo -e "  ${GREEN}${CHECK_MARK}${NC} conda 环境 'sage' 创建成功"

                    # 配置 .bashrc 默认激活 sage 环境
                    local bashrc="$HOME/.bashrc"
                    local sage_activate_marker="# >>> SAGE conda environment auto-activate >>>"
                    if ! grep -q "$sage_activate_marker" "$bashrc" 2>/dev/null; then
                        echo -e "  ${INFO_MARK} 配置终端默认激活 sage 环境..."
                        cat >> "$bashrc" << 'EOF'

# >>> SAGE conda environment auto-activate >>>
# 自动激活 sage conda 环境（由 SAGE quickstart 添加）
if command -v conda >/dev/null 2>&1 || [ -x "$HOME/miniconda3/bin/conda" ]; then
    conda activate sage 2>/dev/null || true
fi
# <<< SAGE conda environment auto-activate <<<
EOF
                        echo -e "  ${GREEN}${CHECK_MARK}${NC} 已配置终端自动激活 sage 环境"
                    fi

                    FIXES_APPLIED=$((FIXES_APPLIED + 1))
                    NEED_RESTART_SHELL=1
                    log_message "FIX" "Installed Miniconda and created conda environment 'sage'"

                    echo -e "\n  ${YELLOW}${BOLD}请运行以下命令继续安装:${NC}"
                    echo -e "    ${CYAN}source ~/.bashrc${NC}"
                    echo -e "    ${CYAN}./quickstart.sh --dev --yes --pip${NC}"
                    rm -f "$miniconda_script"
                    return 0
                else
                    # Miniconda 已安装但创建环境失败
                    echo -e "  ${RED}${CROSS_MARK}${NC} conda 环境创建失败"
                    NEED_RESTART_SHELL=1
                    echo -e "\n  ${YELLOW}${BOLD}Miniconda 已安装成功，请手动创建环境:${NC}"
                    echo -e "    ${CYAN}conda create -n sage python=3.11 -y${NC}"
                    echo -e "    ${CYAN}conda activate sage${NC}"
                    echo -e "    ${CYAN}./quickstart.sh --dev --yes --pip${NC}"
                    rm -f "$miniconda_script"
                    return 1
                fi
            else
                echo -e "  ${RED}${CROSS_MARK}${NC} Miniconda 安装失败"
            fi
        else
            echo -e "  ${RED}${CROSS_MARK}${NC} Miniconda 下载失败，请检查网络连接"
        fi

        rm -f "$miniconda_script"
    fi

    # 只有在 Miniconda 未安装时才显示手动安装说明
    if [ ! -d "$HOME/miniconda3" ]; then
        echo -e "\n  ${BOLD}手动安装 Miniconda (使用清华镜像):${NC}"
        echo -e "    ${CYAN}wget https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh${NC}"
        echo -e "    ${CYAN}bash /tmp/miniconda.sh -b -p \$HOME/miniconda3${NC}"
        echo -e "    ${CYAN}source ~/.bashrc${NC}"
        echo -e "\n  然后运行:"
        echo -e "    ${CYAN}conda create -n sage python=3.11 -y${NC}"
        echo -e "    ${CYAN}conda activate sage${NC}"
        echo -e "    ${CYAN}./quickstart.sh --dev --yes --pip${NC}"
    fi

    return 1
}

# numpy 问题修复
fix_numpy_corrupted() {
    echo -e "\n${TOOL_MARK} 修复 numpy 安装问题..."

    # 首先检查 pip 是否可用
    if ! command -v pip3 >/dev/null 2>&1 && ! python3 -m pip --version >/dev/null 2>&1; then
        echo -e "  ${YELLOW}${WARNING_MARK}${NC} pip 不可用，无法修复 numpy"
        echo -e "  ${DIM}请先解决 pip 缺失问题${NC}"
        return 1
    fi

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

    # 重新安装（使用 SAGE 兼容版本：>=1.26.0,<2.3.0）
    # 尝试使用官方 PyPI（清华镜像可能有问题）
    if python3 -m pip install --no-cache-dir "numpy>=1.26.0,<2.3.0" --index-url https://pypi.org/simple >/dev/null 2>&1; then
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

# CLI 工具冲突修复
fix_cli_conflicts() {
    echo -e "\n${TOOL_MARK} 清理 CLI 工具冲突..."
    local local_bin="$HOME/.local/bin"

    for tool in "sage" "sage-dev"; do
        if [ -f "$local_bin/$tool" ]; then
            echo -e "  移除 $local_bin/$tool..."
            rm -f "$local_bin/$tool"
        fi
    done

    echo -e "  ${GREEN}${CHECK_MARK}${NC} CLI 工具冲突清理完成"
    FIXES_APPLIED=$((FIXES_APPLIED + 1))
}

# 开发工具缺失修复
fix_dev_tools_missing() {
    echo -e "\n${TOOL_MARK} 安装缺失的开发工具..."

    # 首先检查 pip 是否可用
    local pip_cmd=""
    if command -v pip3 >/dev/null 2>&1; then
        pip_cmd="pip3"
    elif command -v pip >/dev/null 2>&1; then
        pip_cmd="pip"
    elif python3 -m pip --version >/dev/null 2>&1; then
        pip_cmd="python3 -m pip"
    else
        echo -e "  ${RED}${CROSS_MARK}${NC} pip 不可用，无法安装开发工具"
        echo -e "  ${DIM}请先解决 pip 缺失问题${NC}"
        return 1
    fi

    # 准备安装参数（优先使用国内镜像）
    local pip_args=""
    if ! curl -s --connect-timeout 3 https://pypi.org >/dev/null 2>&1; then
        echo -e "  ${INFO_MARK} 使用清华 PyPI 镜像..."
        pip_args="-i https://pypi.tuna.tsinghua.edu.cn/simple"
    fi

    # 读取外部依赖文件（如果存在）
    local external_deps_file=".sage/external-deps-dev.txt"
    local dev_tools_installed=false

    if [ -f "$external_deps_file" ] && grep -q "pytest" "$external_deps_file"; then
        echo -e "  ${INFO_MARK} 从外部依赖文件安装开发工具..."

        # 提取开发工具相关的依赖
        local dev_deps=$(grep -E "pytest|ruff|mypy|pre-commit|black|isort|coverage|bandit" "$external_deps_file" || echo "")

        if [ -n "$dev_deps" ]; then
            echo "$dev_deps" > /tmp/sage_dev_tools.txt

            echo -e "  ${DIM}安装: pytest, ruff, mypy, pre-commit 等...${NC}"
            # 先执行安装，再检查结果
            local install_output=""
            install_output=$($pip_cmd install -r /tmp/sage_dev_tools.txt $pip_args 2>&1)
            local install_status=$?

            # 检查是否成功（退出码为0 或 输出包含成功/已安装消息）
            if [ $install_status -eq 0 ] || echo "$install_output" | grep -qE "(Successfully installed|Requirement already satisfied)"; then
                echo -e "  ${GREEN}${CHECK_MARK}${NC} 开发工具安装成功"
                dev_tools_installed=true
                FIXES_APPLIED=$((FIXES_APPLIED + 1))
                log_message "FIX" "Successfully installed dev tools from external deps file"
            else
                echo -e "  ${YELLOW}${WARNING_MARK}${NC} 从外部文件安装失败，将尝试逐个安装"
                log_message "WARN" "Failed to install from external deps file"
            fi

            rm -f /tmp/sage_dev_tools.txt
        fi
    fi

    # 如果外部依赖文件不存在或安装失败，手动安装核心开发工具
    local install_success_count=0
    local install_total=9  # 核心工具总数

    if [ "$dev_tools_installed" = false ]; then
        echo -e "  ${INFO_MARK} 手动安装核心开发工具..."

        local core_tools=(
            "pytest>=7.0.0"
            "pytest-cov>=4.0.0"
            "pytest-asyncio>=0.21.0"
            "pytest-mock>=3.10.0"
            "pytest-timeout>=2.1.0"
            "pytest-benchmark>=4.0.0"
            "ruff==0.14.6"
            "mypy>=1.0.0"
            "pre-commit>=3.0.0"
        )

        install_total=${#core_tools[@]}

        for tool in "${core_tools[@]}"; do
            local tool_name=$(echo "$tool" | sed 's/[<>=].*//')

            # 先检查是否已安装
            if python3 -c "import ${tool_name//-/_}" >/dev/null 2>&1; then
                echo -e "  ${GREEN}${CHECK_MARK}${NC} $tool_name: 已安装"
                install_success_count=$((install_success_count + 1))
                continue
            fi

            echo -e "  ${DIM}安装: $tool_name...${NC}"

            # 尝试安装，捕获输出
            local install_output=""
            install_output=$($pip_cmd install "$tool" $pip_args 2>&1)
            local install_status=$?

            # 检查是否成功（退出码为0 或 输出包含成功消息）
            if [ $install_status -eq 0 ] || echo "$install_output" | grep -qE "(Successfully installed|Requirement already satisfied)"; then
                echo -e "  ${GREEN}${CHECK_MARK}${NC} $tool_name 安装成功"
                install_success_count=$((install_success_count + 1))
                log_message "INFO" "Successfully installed $tool_name"
            else
                echo -e "  ${YELLOW}${WARNING_MARK}${NC} $tool_name 安装失败: $install_output"
                log_message "WARN" "Failed to install $tool_name: $install_output"
            fi
        done

        if [ $install_success_count -eq $install_total ]; then
            echo -e "  ${GREEN}${CHECK_MARK}${NC} 所有开发工具安装成功 ($install_success_count/$install_total)"
            FIXES_APPLIED=$((FIXES_APPLIED + 1))
            log_message "FIX" "Successfully installed all dev tools"
        elif [ $install_success_count -gt 0 ]; then
            echo -e "  ${YELLOW}${WARNING_MARK}${NC} 部分开发工具安装成功 ($install_success_count/$install_total)"
            FIXES_APPLIED=$((FIXES_APPLIED + 1))
            log_message "WARN" "Partially installed dev tools: $install_success_count/$install_total"
        else
            echo -e "  ${RED}${CROSS_MARK}${NC} 开发工具安装失败"
            log_message "ERROR" "Failed to install dev tools"
        fi
    else
        echo -e "  ${INFO_MARK} 跳过手动安装（外部依赖文件已处理）"
    fi

    # 验证 pytest 是否安装成功
    # 注意：在某些环境（如 CI）中，刚安装的包可能需要刷新环境才能导入
    # 如果开发工具从外部文件安装成功，或至少有一个工具安装成功，就认为修复是有效的

    # Debug logging
    echo -e "  ${DIM}[DEBUG] dev_tools_installed=$dev_tools_installed, install_success_count=$install_success_count${NC}"
    log_message "DEBUG" "dev_tools_installed=$dev_tools_installed, install_success_count=$install_success_count, install_total=$install_total"

    if [ "$dev_tools_installed" = true ] || [ $install_success_count -gt 0 ]; then
        if python3 -c "import pytest" >/dev/null 2>&1; then
            local pytest_version=$(python3 -c "import pytest; print(pytest.__version__)" 2>/dev/null)
            echo -e "  ${GREEN}${CHECK_MARK}${NC} pytest $pytest_version 已就绪"
        else
            echo -e "  ${YELLOW}${WARNING_MARK}${NC} 开发工具已安装，但需要刷新环境（安装流程完成后生效）"
            log_message "WARN" "Dev tools installed but not yet importable (environment refresh needed)"
        fi
        return 0
    else
        echo -e "  ${RED}${CROSS_MARK}${NC} 开发工具安装失败"
        log_message "ERROR" "Dev tools installation failed: dev_tools_installed=$dev_tools_installed, install_success_count=$install_success_count"
        return 1
    fi
}

# pre-commit hooks 安装修复
fix_pre_commit_hooks_missing() {
    echo -e "\n${TOOL_MARK} 安装 pre-commit hooks..."

    if ! command -v pre-commit >/dev/null 2>&1; then
        echo -e "  ${YELLOW}${WARNING_MARK}${NC} pre-commit 工具未安装，跳过 hooks 安装"
        return 0  # 不是错误，只是跳过
    fi

    if [ ! -d ".git" ]; then
        echo -e "  ${YELLOW}${WARNING_MARK}${NC} 不是 Git 仓库，无需安装 pre-commit hooks"
        return 0  # 不是错误，只是跳过
    fi

    echo -e "  ${DIM}正在安装 pre-commit hooks...${NC}"
    if pre-commit install --config tools/config/pre-commit-config.yaml >/dev/null 2>&1; then
        echo -e "  ${GREEN}${CHECK_MARK}${NC} pre-commit hooks 安装成功"
        FIXES_APPLIED=$((FIXES_APPLIED + 1))
        log_message "FIX" "Successfully installed pre-commit hooks"
        return 0
    else
        echo -e "  ${RED}${CROSS_MARK}${NC} pre-commit hooks 安装失败"
        return 1
    fi
}

# 环境优化建议
suggest_environment_optimization() {
    echo -e "\n${BLUE}${BOLD}💡 环境优化建议${NC}"

    if [[ -z "${VIRTUAL_ENV:-}" && -z "${CONDA_DEFAULT_ENV:-}" ]]; then
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
    register_issue "pip_missing" "pip包管理器缺失" "critical" "fix_pip_missing"
    register_issue "no_virtual_env" "未使用虚拟环境" "minor" ""
    register_issue "numpy_corrupted" "numpy安装损坏" "major" "fix_numpy_corrupted"
    register_issue "numpy_v1" "numpy版本过旧" "major" ""
    register_issue "torch_numpy_compat" "PyTorch与numpy版本不匹配" "major" ""
    register_issue "low_disk_space" "磁盘空间不足" "major" ""

    # 开发工具问题
    register_issue "dev_tools_missing" "缺少开发工具（pytest等）" "major" "fix_dev_tools_missing"
    register_issue "pre_commit_hooks_missing" "pre-commit hooks未安装" "minor" "fix_pre_commit_hooks_missing"

    # 动态注册混合包问题
    for package in "numpy" "torch" "transformers"; do
        register_issue "mixed_package_$package" "包管理器冲突" "major" "fix_mixed_packages"
    done

    # 注册 CLI 冲突问题
    register_issue "cli_conflict_sage" "CLI 工具冲突 (sage)" "major" "fix_cli_conflicts"
    register_issue "cli_conflict_sage-dev" "CLI 工具冲突 (sage-dev)" "major" "fix_cli_conflicts"
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
    check_cli_conflicts
    check_core_dependencies
    check_specific_issues
    check_dev_tools

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
    local response=""

    if [ "$AUTO_CONFIRM_FIX" = "true" ]; then
        response="y"
    elif [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
        echo -e "${YELLOW}CI 环境检测到问题，跳过交互式修复${NC}"
        return 0
    else
        read -p "是否允许 SAGE 尝试自动修复环境问题？[Y/n] " -r response
        response=${response,,}
    fi

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

        # 如果需要重启 shell（安装了 conda 或创建了环境）
        if [ "$NEED_RESTART_SHELL" -eq 1 ]; then
            echo -e "\n${YELLOW}${BOLD}⚠️  请重新加载终端配置${NC}"
            echo -e "${DIM}这是为了让 conda 环境变量生效${NC}"
            echo -e "\n${BOLD}运行以下命令继续安装:${NC}"
            echo -e "    ${CYAN}source ~/.bashrc${NC}"
            echo -e "    ${CYAN}./quickstart.sh --dev --yes --pip${NC}"
            echo -e "\n${DIM}或者关闭当前终端并重新打开，然后运行:${NC}"
            echo -e "    ${CYAN}cd $(pwd)${NC}"
            echo -e "    ${CYAN}./quickstart.sh --dev --yes --pip${NC}"
            return 42  # 特殊退出码，表示需要重启 shell
        fi

        echo -e "\n${INFO_MARK} 建议重新运行诊断以验证修复效果："
        echo -e "  ${DIM}./quickstart.sh --doctor${NC}"
    else
        echo -e "\n${YELLOW}${WARNING_MARK} 未能自动修复所有问题${NC}"
        suggest_environment_optimization
    fi

    return 0
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
