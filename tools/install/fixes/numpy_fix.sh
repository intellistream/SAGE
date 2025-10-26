#!/bin/bash
# numpy依赖冲突检测和修复脚本
# 专门处理numpy安装冲突问题，提供友好的用户体验

# 颜色定义
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

    echo -e "${DIM}正在检测 numpy 安装状态...${NC}"

    # 检查conda安装的numpy
    if command -v conda >/dev/null 2>&1; then
        conda_numpy=$(conda list numpy 2>/dev/null | grep "^numpy" | awk '{print $2}' | head -1)
    fi

    # 检查pip安装的numpy
    pip_numpy=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "not_found")

    # 检查numpy的RECORD文件是否存在（判断是否损坏）
    local numpy_corrupted=false
    if [ "$pip_numpy" != "not_found" ]; then
        # 尝试检查pip的numpy记录
        if ! python3 -c "import pkg_resources; pkg_resources.get_distribution('numpy')" >/dev/null 2>&1; then
            numpy_corrupted=true
        fi
    fi

    # 返回状态信息
    echo "conda_numpy:$conda_numpy|pip_numpy:$pip_numpy|corrupted:$numpy_corrupted"
}

# 修复numpy安装问题
fix_numpy_installation() {
    local log_file="${1:-install.log}"

    echo -e "\n${YELLOW}${BOLD}🔍 SAGE 依赖环境检测${NC}"
    echo -e "${DIM}为了提供最佳体验，我们需要检查并优化您的 Python 数值计算环境...${NC}\n"

    local status_info=$(check_numpy_installation)
    local conda_numpy=$(echo "$status_info" | cut -d'|' -f1 | cut -d':' -f2)
    local pip_numpy=$(echo "$status_info" | cut -d'|' -f2 | cut -d':' -f2)
    local corrupted=$(echo "$status_info" | cut -d'|' -f3 | cut -d':' -f2)

    echo "$(date): numpy状态检测 - conda版本: $conda_numpy, pip版本: $pip_numpy, 损坏状态: $corrupted" >> "$log_file"

    # 如果检测到问题，提供友好的解释和解决方案
    if [ "$corrupted" = "true" ] || [ "$conda_numpy" != "" -a "$pip_numpy" != "not_found" ]; then
        echo -e "${BLUE}📋 环境状态分析：${NC}"

        if [ "$corrupted" = "true" ]; then
            echo -e "  ${YELLOW}▸${NC} 检测到 numpy 安装记录不完整"
            echo -e "    ${DIM}这通常是由于包管理器切换或不完整的安装导致的${NC}"
        fi

        if [ "$conda_numpy" != "" -a "$pip_numpy" != "not_found" ]; then
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
            echo -e "${YELLOW}⚠️  跳过自动修复，安装可能遇到兼容性问题${NC}"
            echo "$(date): 用户选择跳过numpy修复" >> "$log_file"
            return 1
        fi

        echo -e "\n${BLUE}🔄 正在优化数值计算环境...${NC}"
        echo "$(date): 开始numpy环境修复" >> "$log_file"

        # Step 1: 清理conda安装的numpy（如果存在）
        if [ "$conda_numpy" != "" ] && command -v conda >/dev/null 2>&1; then
            echo -e "  ${DIM}清理 conda numpy 安装...${NC}"
            conda uninstall numpy -y >/dev/null 2>&1 || true
            echo "$(date): 已清理conda numpy" >> "$log_file"
        fi

        # Step 2: 强制清理pip numpy
        if [ "$pip_numpy" != "not_found" ]; then
            echo -e "  ${DIM}清理 pip numpy 安装...${NC}"
            # 使用多种方法清理
            pip uninstall numpy -y >/dev/null 2>&1 || true
            python3 -m pip uninstall numpy -y >/dev/null 2>&1 || true
            # 如果还是失败，尝试强制清理
            python3 -c "
import os, shutil, sys
try:
    import numpy
    numpy_path = os.path.dirname(numpy.__file__)
    if 'site-packages' in numpy_path:
        shutil.rmtree(numpy_path, ignore_errors=True)
        print('Forcibly removed numpy directory')
except Exception:
    pass
" 2>/dev/null || true
            echo "$(date): 已清理pip numpy" >> "$log_file"
        fi

        # Step 3: 安装兼容版本的numpy
        echo -e "  ${DIM}安装优化版本的 numpy...${NC}"
        python3 -m pip install --no-cache-dir numpy==2.3.3 >/dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ 数值计算环境优化完成${NC}"
            echo "$(date): numpy环境修复成功" >> "$log_file"

            # 验证安装
            local new_version=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "验证失败")
            echo -e "  ${GREEN}▸${NC} ${DIM}numpy 版本: $new_version${NC}"

            return 0
        else
            echo -e "${RED}❌ 自动修复失败，将尝试继续安装${NC}"
            echo "$(date): numpy环境修复失败，继续后续安装" >> "$log_file"
            return 1
        fi
    else
        echo -e "${GREEN}✅ numpy 环境状态良好${NC}"
        echo "$(date): numpy环境检查通过" >> "$log_file"
        return 0
    fi
}

# 在安装开始前进行numpy环境预检查
precheck_numpy_environment() {
    local log_file="${1:-install.log}"

    echo -e "${BLUE}🔍 预检查：Python数值计算环境${NC}"

    # 检查是否存在已知的numpy问题
    local status_info=$(check_numpy_installation)
    local corrupted=$(echo "$status_info" | cut -d'|' -f3 | cut -d':' -f2)

    if [ "$corrupted" = "true" ]; then
        echo -e "${YELLOW}⚠️  检测到潜在的依赖环境问题${NC}"
        echo -e "${DIM}   这可能会影响 SAGE 的安装过程${NC}"
        fix_numpy_installation "$log_file"
        return $?
    else
        echo -e "${GREEN}✅ 环境检查通过${NC}"
        return 0
    fi
}

# 提供用户友好的错误信息和解决方案
show_numpy_error_help() {
    local log_file="${1:-install.log}"

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

    echo "$(date): 已显示numpy错误帮助信息" >> "$log_file"
}
