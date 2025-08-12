#!/bin/bash
#
# SAGE Framework 包状态检查脚本
# Package Status Check Script for SAGE Framework
#
# 检查所有包的当前状态，包括版本、依赖等信息
# Check current status of all packages including version, dependencies, etc.

set -euo pipefail

# 脚本目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/packages"

# 颜色配置
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}📋 SAGE Framework 包状态检查${NC}"
echo -e "====================================="

# 检查 sage-dev 是否可用
if ! command -v sage-dev &> /dev/null; then
    echo -e "${YELLOW}⚠️ sage-dev 命令未找到，将使用基础检查${NC}"
    BASIC_MODE=true
else
    BASIC_MODE=false
fi

# 获取包列表
packages=($(ls -1 "$PACKAGES_DIR" | grep -E '^sage-'))

echo -e "发现 ${BOLD}${#packages[@]}${NC} 个包:\n"

# 检查每个包
for package in "${packages[@]}"; do
    echo -e "${BOLD}📦 $package${NC}"
    package_path="$PACKAGES_DIR/$package"
    
    # 检查基本信息
    if [ -f "$package_path/pyproject.toml" ]; then
        echo -e "  ${GREEN}✅ pyproject.toml 存在${NC}"
        
        # 提取版本信息
        if command -v python3 &> /dev/null; then
            version=$(python3 -c "
try:
    import tomli
    with open('$package_path/pyproject.toml', 'rb') as f:
        data = tomli.load(f)
    project = data.get('project', {})
    print(f\"名称: {project.get('name', 'N/A')}\")
    print(f\"版本: {project.get('version', 'N/A')}\")
    print(f\"描述: {project.get('description', 'N/A')}\")
    dependencies = project.get('dependencies', [])
    print(f\"依赖: {len(dependencies)} 个\")
except Exception as e:
    print(f\"解析失败: {e}\")
" 2>/dev/null)
            echo -e "  ${BLUE}$version${NC}" | sed 's/^/  /'
        fi
    else
        echo -e "  ${YELLOW}⚠️ pyproject.toml 不存在${NC}"
    fi
    
    # 检查源码目录
    if [ -d "$package_path/src" ]; then
        py_files=$(find "$package_path/src" -name "*.py" | wc -l)
        echo -e "  ${CYAN}📁 源码文件: $py_files 个 Python 文件${NC}"
    else
        echo -e "  ${YELLOW}⚠️ src/ 目录不存在${NC}"
    fi
    
    # 检查测试目录
    if [ -d "$package_path/tests" ]; then
        test_files=$(find "$package_path/tests" -name "*.py" | wc -l)
        echo -e "  ${CYAN}🧪 测试文件: $test_files 个${NC}"
    fi
    
    # 使用 sage-dev info（如果可用）
    if [ "$BASIC_MODE" = false ]; then
        echo -e "  ${CYAN}🔍 详细信息:${NC}"
        if sage-dev info "$package_path" 2>/dev/null | grep -E "(构建文件|Python文件)" | sed 's/^/    /'; then
            :
        else
            echo -e "    ${YELLOW}获取详细信息失败${NC}"
        fi
    fi
    
    echo
done

echo -e "${BOLD}===== 摘要 =====${NC}"
echo -e "总包数: ${BOLD}${#packages[@]}${NC}"

# 检查是否有构建文件
built_packages=0
for package in "${packages[@]}"; do
    if [ -d "$PACKAGES_DIR/$package/dist" ] && [ -n "$(ls -A "$PACKAGES_DIR/$package/dist" 2>/dev/null)" ]; then
        ((built_packages++))
    fi
done

echo -e "已构建: ${BOLD}$built_packages${NC}"
echo -e "未构建: ${BOLD}$((${#packages[@]} - built_packages))${NC}"

if [ "$BASIC_MODE" = true ]; then
    echo -e "\n${YELLOW}💡 提示: 安装 sage-dev-toolkit 可获取更详细信息${NC}"
    echo -e "   pip install -e packages/sage-dev-toolkit"
fi

echo -e "\n${GREEN}✅ 检查完成${NC}"
