#!/bin/bash
# SAGE 安装脚本 - 核心包安装器 (重构版本)
# 负责通过主sage包统一安装所有依赖

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/logging.sh"

# 导入友好错误处理

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
CONDA_ENV_NAME="${CONDA_ENV_NAME:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
# ============================================================================

if [ -f "$(dirname "${BASH_SOURCE[0]}")/../fixes/friendly_error_handler.sh" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/../fixes/friendly_error_handler.sh"
fi

# CI环境检测
if [ "${CI:-}" = "true" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${GITLAB_CI:-}" ] || [ -n "${JENKINS_URL:-}" ]; then
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    # 确保在CI环境中禁用可能导致问题的进度条设置
    unset PIP_PROGRESS_BAR
elif [ "${SAGE_REMOTE_DEPLOY:-}" = "true" ]; then
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    # 远程部署环境也禁用可能导致问题的进度条设置
    unset PIP_PROGRESS_BAR
else
    export PYTHONNOUSERSITE=1
    # 非CI环境清除可能存在的全局进度条配置
    unset PIP_PROGRESS_BAR
fi

# 设置pip命令
PYTHON_CMD="${PYTHON_CMD:-python3}"
PIP_CMD="${PIP_CMD:-$PYTHON_CMD -m pip}"

# ============================================================================
# 版本比较辅助函数
# ============================================================================

# 版本比较函数（语义版本）
version_gte() {
    # 比较 $1 >= $2（语义版本）
    # 返回 0（true）如果 $1 >= $2，否则返回 1（false）
    local ver1="$1"
    local ver2="$2"

    # 移除版本号中的非数字前缀（如 v2.7.0 -> 2.7.0）
    ver1="${ver1#v}"
    ver2="${ver2#v}"

    # 使用 Python 进行语义版本比较（更可靠）
    python3 -c "
from packaging import version
import sys
try:
    result = version.parse('$ver1') >= version.parse('$ver2')
    sys.exit(0 if result else 1)
except Exception:
    # 如果 packaging 不可用，使用简单字符串比较
    sys.exit(0 if '$ver1' >= '$ver2' else 1)
" 2>/dev/null
    return $?
}

# ============================================================================
# 核心安装函数
# ============================================================================

# 安装核心包
# SAGE 已重构为独立 meta-package（polyrepo 架构）：
# - packages/sage 是本仓库维护的 meta-package，-e editable 安装
# - 所有子包（isage-common/platform/kernel/libs/middleware/cli 等）均通过 PyPI 版本号拉取
# - 子包更新后需先发布到 PyPI，然后在 packages/sage/pyproject.toml 中更新版本号
install_core_packages() {
    local install_mode="${1:-dev}"  # default: dev

    # 根据 install_mode 选择安装目标（extras）
    # standard: pip install -e "packages/sage"
    # dev:      pip install -e "packages/sage[dev]"
    local install_target
    case "$install_mode" in
        "dev")
            install_target='packages/sage[dev]'
            ;;
        "standard"|*)
            install_mode="standard"
            install_target='packages/sage'
            ;;
    esac

    # 准备 pip 参数
    local pip_args="--disable-pip-version-check --no-input --progress-bar=off"

    # CI 环境额外处理
    if [ "${CI:-}" = "true" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${GITLAB_CI:-}" ] || [ -n "${JENKINS_URL:-}" ]; then
        pip_args="$pip_args --user"
        if $PYTHON_CMD -c "import sys; print(1 if '/usr' in sys.prefix else 0)" 2>/dev/null | grep -q "1"; then
            pip_args="$pip_args --break-system-packages"
            echo -e "${DIM}CI环境: 添加 --break-system-packages${NC}"
        fi
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "${DIM}CI环境: 使用 --user 安装，PATH+=~/.local/bin${NC}"
    fi

    # 获取项目根目录并初始化日志
    local project_root
    project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/.sage/logs/install.log"
    export SAGE_INSTALL_LOG="$log_file"
    mkdir -p "$project_root/.sage/logs" "$project_root/.sage/tmp" "$project_root/.sage/cache"

    log_info "SAGE 安装日志" "INSTALL"
    log_info "开始时间: $(date '+%Y-%m-%d %H:%M:%S')" "INSTALL"
    log_info "安装模式: $install_mode" "INSTALL"
    log_info "项目路径: $project_root" "INSTALL"

    echo -e "${INFO} 安装 SAGE ($install_mode 模式)..."
    echo -e "${DIM}安装日志: $log_file${NC}"
    echo ""

    # 配置 pip 镜像源
    echo -e "${BLUE}🌐 配置 pip 镜像源...${NC}"
    configure_pip_mirror "auto"
    echo ""

    # 记录环境信息
    log_phase_start_enhanced "环境信息收集" "INSTALL" 5
    log_environment "INSTALL"
    log_phase_end_enhanced "环境信息收集" "true" "INSTALL"

    case "$install_mode" in
        "standard")
            echo -e "${YELLOW}standard 安装：核心功能 + 所有可选依赖${NC}"
            echo -e "${DIM}包含: isage 及所有子包依赖（从 PyPI 版本拉取）${NC}"
            ;;
        "dev")
            echo -e "${GREEN}dev 安装：standard + 开发工具${NC}"
            echo -e "${DIM}包含: standard 功能 + pytest, ruff, mypy, pre-commit, isage-dev-tools${NC}"
            ;;
    esac
    echo ""

    # 检查 meta-package 目录
    if [ ! -d "packages/sage" ]; then
        log_error "找不到 meta-package 目录: packages/sage" "INSTALL"
        log_error "当前工作目录: $(pwd)" "INSTALL"
        echo -e "${CROSS} 错误：找不到 meta-package 目录 (packages/sage)"
        return 1
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  📦 安装 SAGE ($install_mode 模式：$install_target + PyPI 子包)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${DIM}安装策略: editable install 本地 packages/sage，所有子包依赖从 PyPI 版本拉取${NC}"
    echo -e "${DIM}子包更新需先发布到 PyPI，再在 packages/sage/pyproject.toml 中更新版本号${NC}"
    echo ""

    log_info "安装目标: $install_target" "INSTALL"
    log_phase_start_enhanced "SAGE meta-package 安装" "INSTALL" 120
    log_debug "PIP命令: $PIP_CMD install -e \"$install_target\" $pip_args --upgrade" "INSTALL"

    if ! log_command "INSTALL" "Core" "$PIP_CMD install -e \"$install_target\" $pip_args --upgrade"; then
        log_error "安装失败: $install_target" "INSTALL"
        echo -e "${CROSS} SAGE meta-package 安装失败！"
        log_phase_end_enhanced "SAGE meta-package 安装" "failure" "INSTALL"
        return 1
    fi

    log_info "安装成功: $install_target" "INSTALL"
    log_pip_package_info "isage" "INSTALL"
    log_phase_end_enhanced "SAGE meta-package 安装" "success" "INSTALL"

    echo ""
    echo -e "${CHECK} SAGE ($install_mode 模式) 安装成功"
    echo -e "${DIM}      子包依赖已从 PyPI 解析并安装${NC}"
    echo ""

    log_info "SAGE ($install_mode 模式) 安装完成" "INSTALL"
    return 0
}

# 安装科学计算包（保持向后兼容）
install_scientific_packages() {
    echo -e "${DIM}科学计算包已包含在标准/开发模式中，跳过单独安装${NC}"
    return 0
}

# 安装开发工具（保持向后兼容）
install_dev_tools() {
    echo -e "${DIM}开发工具已包含在开发模式中，跳过单独安装${NC}"
    return 0
}

# 导出函数
export -f install_core_packages
export -f install_scientific_packages
export -f install_dev_tools
