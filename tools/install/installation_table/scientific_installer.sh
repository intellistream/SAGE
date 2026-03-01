#!/bin/bash
# SAGE 安装脚本 - 科学计算包安装器
# 负责安装科学计算相关的依赖包

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 导入核心安装器函数
source "$(dirname "${BASH_SOURCE[0]}")/core_installer.sh"

# 安装科学计算包

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

install_scientific_packages() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  🔬 正在安装科学计算库...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    log_info "开始安装科学计算库" "Scientific"

    local packages=(
        "numpy>=2.0.0,<3.0.0"  # 与SAGE包保持一致的numpy版本
        "pandas>=1.3.0"
        "matplotlib>=3.4.0"
        "scipy>=1.15.0,<2.0.0"  # 与SAGE包保持一致的scipy版本
        "jupyter>=1.0.0"
        "ipykernel>=6.0.0"
    )

    for package in "${packages[@]}"; do
        echo -e "${BOLD}  📊 正在安装 $package${NC}"
        echo -e "${DIM}运行命令: $PIP_CMD install \"$package\"${NC}"
        echo ""

        if log_command "Scientific" "Install" "$PIP_CMD install \"$package\""; then
            log_info "$package 安装成功！" "Scientific"
            echo ""
            echo -e "${CHECK} $package 安装成功！"
            echo ""
        else
            log_warn "$package 安装可能失败，继续安装其他包..." "Scientific"
            echo ""
            echo -e "${WARNING} $package 安装可能失败，继续安装其他包..."
            echo ""
        fi
    done

    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  🎉 科学计算库安装完成！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    log_info "科学计算库安装完成" "Scientific"
}

# 安装可选依赖（完整安装模式）
# 包含 ML、VDB、streaming、compression 等重型依赖
install_optional_packages() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  🔧 正在安装可选依赖（完整安装模式）...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    log_info "开始安装可选依赖" "Optional"

    local pip_args="--disable-pip-version-check --no-input --prefer-binary --upgrade-strategy only-if-needed"
    if [ "${USE_PIP_MIRROR:-true}" = "false" ]; then
        pip_args="$pip_args --no-cache-dir"
    fi
    if [ -n "${SAGE_PIP_CONSTRAINT_FILE:-}" ] && [ -f "${SAGE_PIP_CONSTRAINT_FILE:-}" ]; then
        pip_args="$pip_args -c ${SAGE_PIP_CONSTRAINT_FILE}"
    fi

    # 安装各个可选依赖组
    local optional_groups=(
        "isage-middleware[ml]"          # ML: transformers, sentence-transformers, accelerate
        "isage-middleware[vdb]"         # VDB: isage-vdb, faiss-cpu
        "isage-middleware[streaming]"   # Streaming: isage-flow, isage-tsdb
        "isage-middleware[compression]" # Compression: llmlingua
        "isage-kernel[ml]"              # Kernel ML: torch, torchvision
    )

    for group in "${optional_groups[@]}"; do
        echo -e "${BOLD}  📦 正在安装 $group${NC}"
        echo -e "${DIM}运行命令: $PIP_CMD install \"$group\" $pip_args${NC}"
        echo ""

        if log_command "Optional" "Install" "$PIP_CMD install \"$group\" $pip_args"; then
            log_info "$group 安装成功！" "Optional"
            echo -e "${CHECK} $group 安装成功！"
        else
            log_warn "$group 安装失败，继续安装其他组..." "Optional"
            echo -e "${WARNING} $group 安装失败（非关键，继续安装）"
        fi
        echo ""
    done

    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  🎉 可选依赖安装完成！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    log_info "可选依赖安装完成" "Optional"
    return 0
}
