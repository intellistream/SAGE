#!/bin/bash
# numpy依赖冲突检测和修复脚本
# 专门处理numpy安装冲突问题，提供友好的用户体验

# 颜色定义

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

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'
DIM='\033[2m'

# 检测numpy安装状态
check_numpy_installation() {
    local numpy_status=""
    local conda_numpy=""
    local pip_numpy=""

    echo -e "${DIM}正在检测 numpy 安装状态...${NC}" >&2

    # 检查conda安装的numpy
    if command -v conda >/dev/null 2>&1; then
        conda_numpy=$(conda list numpy 2>/dev/null | grep "^numpy" | awk '{print $2}' | head -1)
    fi

    # 检查pip安装的numpy
    pip_numpy=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "not_found")

    # 检查 numpy 元数据与 dist-info 完整性（判断是否损坏）
    local numpy_corrupted=false
    local mixed_conflict=false
    if [ "$pip_numpy" != "not_found" ]; then
        if ! python3 -c "from importlib.metadata import version; version('numpy')" >/dev/null 2>&1; then
            numpy_corrupted=true
        fi

        if ! python3 -c "
import glob
import os
import site
import sys

paths = []
for p in site.getsitepackages() + [site.getusersitepackages()]:
    if p not in paths and os.path.isdir(p):
        paths.append(p)

for root in paths:
    for candidate in glob.glob(os.path.join(root, '~umpy*')):
        if os.path.exists(candidate):
            sys.exit(1)
    for dist_info in glob.glob(os.path.join(root, 'numpy-*.dist-info')):
        if not os.path.isfile(os.path.join(dist_info, 'RECORD')):
            sys.exit(1)
" >/dev/null 2>&1; then
            numpy_corrupted=true
        fi
    fi

    if [ -n "$conda_numpy" ] && [ "$pip_numpy" != "not_found" ] && [ "$conda_numpy" != "$pip_numpy" ]; then
        mixed_conflict=true
    fi

    # 返回状态信息
    echo "conda_numpy:$conda_numpy|pip_numpy:$pip_numpy|corrupted:$numpy_corrupted|mixed_conflict:$mixed_conflict"
}

# 修复numpy安装问题
fix_numpy_installation() {
    echo -e "\n${YELLOW}${BOLD}🔍 SAGE 依赖环境检测${NC}"
    echo -e "${DIM}为了提供最佳体验，我们需要检查并优化您的 Python 数值计算环境...${NC}\n"

    local status_info=$(check_numpy_installation)
    local conda_numpy=$(echo "$status_info" | cut -d'|' -f1 | cut -d':' -f2)
    local pip_numpy=$(echo "$status_info" | cut -d'|' -f2 | cut -d':' -f2)
    local corrupted=$(echo "$status_info" | cut -d'|' -f3 | cut -d':' -f2)
    local mixed_conflict=$(echo "$status_info" | cut -d'|' -f4 | cut -d':' -f2)

    log_info "numpy状态检测 - conda版本: $conda_numpy, pip版本: $pip_numpy, 损坏状态: $corrupted, 混合冲突: $mixed_conflict" "NumpyFix"

    # 如果检测到问题，提供友好的解释和解决方案
    if [ "$corrupted" = "true" ] || [ "$mixed_conflict" = "true" ]; then
        echo -e "${BLUE}📋 环境状态分析：${NC}"

        if [ "$corrupted" = "true" ]; then
            log_warn "检测到 numpy 安装记录不完整" "NumpyFix"
            echo -e "  ${YELLOW}▸${NC} 检测到 numpy 安装记录不完整"
            echo -e "    ${DIM}这通常是由于包管理器切换或不完整的安装导致的${NC}"
        fi

        if [ "$mixed_conflict" = "true" ]; then
            log_warn "检测到 conda 和 pip 混合管理的 numpy" "NumpyFix"
            echo -e "  ${YELLOW}▸${NC} 检测到 conda 和 pip 混合管理的 numpy"
            echo -e "    ${DIM}conda版本: $conda_numpy, pip版本: $pip_numpy${NC}"
            echo -e "    ${DIM}为避免冲突，建议统一使用pip管理SAGE的Python依赖${NC}"
        fi

        echo -e "\n${GREEN}🔧 自动修复方案：${NC}"
        echo -e "  ${GREEN}▸${NC} 清理现有的 numpy 安装"
        echo -e "  ${GREEN}▸${NC} 重新安装兼容版本的 numpy (2.3.3)"
        echo -e "  ${GREEN}▸${NC} 确保与 SAGE 的深度学习组件完全兼容"

        # 询问用户是否同意修复
        echo -e "\n${BOLD}是否允许 SAGE 自动修复此环境问题？${NC} ${DIM}[Y/n]${NC}"
        read -r -t 10 response || response="y"
        response=${response,,} # 转换为小写

        if [[ "$response" =~ ^(n|no)$ ]]; then
            log_info "用户选择跳过numpy修复" "NumpyFix"
            echo -e "${YELLOW}⚠️  跳过自动修复，安装可能遇到兼容性问题${NC}"
            return 1
        fi

        log_info "开始numpy环境修复" "NumpyFix"
        echo -e "\n${BLUE}🔄 正在优化数值计算环境...${NC}"

        # Step 1: 清理conda安装的numpy（如果存在）
        if [ "$conda_numpy" != "" ] && command -v conda >/dev/null 2>&1; then
            log_info "清理 conda numpy 安装..." "NumpyFix"
            echo -e "  ${DIM}清理 conda numpy 安装...${NC}"
            log_command "NumpyFix" "Fix" "conda uninstall numpy -y" || true
        fi

        # Step 2: 强制清理pip numpy
        if [ "$pip_numpy" != "not_found" ] || [ "$corrupted" = "true" ]; then
            log_info "清理 pip numpy 安装..." "NumpyFix"
            echo -e "  ${DIM}清理 pip numpy 安装...${NC}"
            log_command "NumpyFix" "Fix" "pip uninstall numpy -y" || true
            log_command "NumpyFix" "Fix" "python3 -m pip uninstall numpy -y" || true
            log_info "尝试强制移除 numpy 目录和损坏元数据" "NumpyFix"
            python3 -c "
import glob
import os
import shutil
import site

paths = []
for p in site.getsitepackages() + [site.getusersitepackages()]:
    if p not in paths and os.path.isdir(p):
        paths.append(p)

for root in paths:
    for candidate in glob.glob(os.path.join(root, 'numpy')):
        shutil.rmtree(candidate, ignore_errors=True)
    for candidate in glob.glob(os.path.join(root, 'numpy-*.dist-info')):
        shutil.rmtree(candidate, ignore_errors=True)
    for candidate in glob.glob(os.path.join(root, '~umpy*')):
        if os.path.isdir(candidate):
            shutil.rmtree(candidate, ignore_errors=True)
        elif os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass
" 2>/dev/null || true
        fi

        # Step 3: 安装兼容版本的numpy
        log_info "安装优化版本的 numpy..." "NumpyFix"
        echo -e "  ${DIM}安装优化版本的 numpy...${NC}"
        if log_command "NumpyFix" "Fix" "python3 -m pip install --no-cache-dir numpy==2.3.3"; then
            log_info "numpy环境修复成功" "NumpyFix"
            echo -e "${GREEN}✅ 数值计算环境优化完成${NC}"

            # 验证安装
            local new_version=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "验证失败")
            log_info "numpy 版本: $new_version" "NumpyFix"
            echo -e "  ${GREEN}▸${NC} ${DIM}numpy 版本: $new_version${NC}"

            return 0
        else
            log_error "自动修复失败，将尝试继续安装" "NumpyFix"
            echo -e "${RED}❌ 自动修复失败，将尝试继续安装${NC}"
            return 1
        fi
    else
        log_info "numpy环境检查通过" "NumpyFix"
        echo -e "${GREEN}✅ numpy 环境状态良好${NC}"
        return 0
    fi
}

# 在安装开始前进行numpy环境预检查
precheck_numpy_environment() {
    echo -e "${BLUE}🔍 预检查：Python数值计算环境${NC}"

    # 检查是否存在已知的numpy问题
    local status_info=$(check_numpy_installation)
    local corrupted=$(echo "$status_info" | cut -d'|' -f3 | cut -d':' -f2)

    if [ "$corrupted" = "true" ]; then
        log_warn "检测到潜在的依赖环境问题" "NumpyFix"
        echo -e "${YELLOW}⚠️  检测到潜在的依赖环境问题${NC}"
        echo -e "${DIM}   这可能会影响 SAGE 的安装过程${NC}"
        fix_numpy_installation
        return $?
    else
        log_info "环境检查通过" "NumpyFix"
        echo -e "${GREEN}✅ 环境检查通过${NC}"
        return 0
    fi
}

# 提供用户友好的错误信息和解决方案
show_numpy_error_help() {
    log_error "检测到 numpy 相关的安装冲突" "NumpyFix"
    echo -e "\n${RED}${BOLD}🚨 安装遇到依赖问题${NC}"
    echo -e "${YELLOW}检测到 numpy 相关的安装冲突，这是一个常见的 Python 环境问题，不是 SAGE 本身的问题。${NC}\n"

    echo -e "${BLUE}📋 问题说明：${NC}"
    echo -e "  ${YELLOW}▸${NC} 您的系统中可能存在多个版本的 numpy"
    echo -e "  ${YELLOW}▸${NC} conda 和 pip 的混合管理导致了包冲突"
    echo -e "  ${YELLOW}▸${NC} 这是 Python 生态系统中的常见问题，影响很多科学计算包\n"

    echo -e "${GREEN}🔧 推荐解决方案：${NC}"
    echo -e "  ${GREEN}1.${NC} 运行 SAGE 的自动修复工具："
    echo -e "     ${DIM}./quickstart.sh --fix-env${NC}"
    echo -e "  ${GREEN}2.${NC} 手动清理并重新安装："
    echo -e "     ${DIM}conda uninstall numpy -y${NC}"
    echo -e "     ${DIM}pip uninstall numpy -y${NC}"
    echo -e "     ${DIM}pip install numpy==2.3.3${NC}"
    echo -e "  ${GREEN}3.${NC} 使用新的虚拟环境："
    echo -e "     ${DIM}conda create -n sage-fresh python=3.11 -y${NC}"
    echo -e "     ${DIM}conda activate sage-fresh${NC}"
    echo -e "     ${DIM}./quickstart.sh${NC}\n"

    echo -e "${BLUE}💡 了解更多：${NC}"
    echo -e "  ${DIM}https://github.com/intellistream/SAGE/wiki/Installation-Troubleshooting${NC}\n"

    log_info "已显示numpy错误帮助信息" "NumpyFix"
}
