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
    # ⚠️  已废弃 (deprecated since 2025)
    # isage-middleware[ml/vdb/streaming/compression] 和 isage-kernel[ml] 等 extras
    # 在 PyPI 上不存在，pip 会静默忽略——实际什么都不安装。
    #
    # 重 GPU/ML 依赖（torch/accelerate/peft）现已统一收归
    # 至独立能力包（如 isagellm[cuda]）中；SAGE meta 不再强制提供。
    #
    # 此函数保留为空白 no-op，防止外部调用报错。
    log_info "install_optional_packages: 已废弃，无操作 (重型依赖已迁移至独立能力包)" "Optional"
    log_warn "如需 GPU/LLM 重型依赖，请按能力包文档单独安装（如 isagellm[cuda]）" "Optional"
}
