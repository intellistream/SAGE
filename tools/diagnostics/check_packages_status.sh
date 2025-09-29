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
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/packages"
export PROJECT_ROOT

# 颜色配置
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}📋 SAGE Framework 包状态检查${NC}"
echo -e "====================================="

# 检查是否可获取增强信息
ENHANCED_MODE=false
PACKAGE_INFO_JSON=""

if command -v python3 &> /dev/null; then
    if PACKAGE_INFO_JSON=$(python3 <<'PY'
import json
import os
import sys

try:
    from sage.tools.dev.tools.project_status_checker import ProjectStatusChecker
except Exception as e:
    print(f"Error importing ProjectStatusChecker: {e}", file=sys.stderr)
    raise SystemExit(1)

project_root = os.environ.get("PROJECT_ROOT")
checker = ProjectStatusChecker(project_root)
packages = checker._check_packages().get("packages", {})
print(json.dumps(packages, ensure_ascii=False))
PY
    ); then
        ENHANCED_MODE=true
        export PACKAGE_INFO_JSON
    fi
fi

if [ "$ENHANCED_MODE" = false ]; then
    echo -e "${YELLOW}⚠️ 未能加载增强检查模块，将显示基础信息${NC}"
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
    
    # 展示增强信息（如果可用）
    if [ "$ENHANCED_MODE" = true ]; then
        CURRENT_PACKAGE="$package"
        export CURRENT_PACKAGE
        if EXTRA_INFO=$(python3 <<'PY'
import json
import os

package = os.environ.get("CURRENT_PACKAGE")
packages = json.loads(os.environ.get("PACKAGE_INFO_JSON", "{}"))
info = packages.get(package)

if not info:
    raise SystemExit(0)

lines = []

installed = info.get("installed")
version = info.get("version")
if installed:
    if version:
        lines.append(f"✅ 已安装 (版本 {version})")
    else:
        lines.append("✅ 已安装")
else:
    lines.append("⚠️ 未安装")

if info.get("importable"):
    module = info.get("module_name", "未知模块")
    lines.append(f"✅ 可导入: {module}")
    import_path = info.get("import_path")
    if import_path:
        lines.append(f"📂 模块路径: {import_path}")
else:
    lines.append("⚠️ 无法导入主模块")

print("\n".join(f"    {line}" for line in lines))
PY
        ); then
            if [ -n "$EXTRA_INFO" ]; then
                echo "$EXTRA_INFO"
            fi
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

if [ "$ENHANCED_MODE" = false ]; then
    echo -e "\n${YELLOW}💡 提示: 安装并初始化项目后可使用 'sage dev status --packages --project-root ${PROJECT_ROOT}' 获取更详细信息${NC}"
fi

echo -e "\n${GREEN}✅ 检查完成${NC}"
