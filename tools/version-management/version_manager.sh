#!/bin/bash
#
# SAGE Framework 版本管理脚本
# Version Management Script for SAGE Framework
#
# 用于批量管理所有包的版本号
# For batch version management of all packages

set -euo pipefail

# 脚本目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 颜色配置
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}🔢 SAGE Framework 版本管理${NC}"
echo -e "================================="

# 检查参数
ACTION=""
TARGET_PACKAGES=""
INCREMENT_TYPE="patch"  # major, minor, patch

while [[ $# -gt 0 ]]; do
    case $1 in
        list|show)
            ACTION="list"
            shift
            ;;
        increment|bump)
            ACTION="increment"
            shift
            ;;
        --packages)
            TARGET_PACKAGES="$2"
            shift 2
            ;;
        --type)
            INCREMENT_TYPE="$2"
            shift 2
            ;;
        -h|--help)
            echo "用法: $0 <action> [options]"
            echo ""
            echo "动作:"
            echo "  list                显示所有包的版本信息"
            echo "  increment           递增版本号"
            echo ""
            echo "选项:"
            echo "  --packages NAMES    指定包名，用逗号分隔 (默认: 所有包)"
            echo "  --type TYPE         版本递增类型: major|minor|patch (默认: patch)"
            echo ""
            echo "示例:"
            echo "  $0 list                          # 显示所有包版本"
            echo "  $0 increment                     # 递增所有包的patch版本"
            echo "  $0 increment --type minor        # 递增所有包的minor版本"
            echo "  $0 increment --packages sage-cli,sage-core  # 只递增指定包"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            exit 1
            ;;
    esac
done

if [[ -z "$ACTION" ]]; then
    echo "请指定动作: list 或 increment"
    echo "使用 --help 查看详细用法"
    exit 1
fi

# 获取包列表
if [[ -n "$TARGET_PACKAGES" ]]; then
    IFS=',' read -ra packages <<< "$TARGET_PACKAGES"
else
    packages=($(ls -1 "$PROJECT_ROOT/packages" | grep -E '^sage-'))
fi

# 获取包版本
get_package_version() {
    local package_path="$1"
    local pyproject_file="$package_path/pyproject.toml"
    
    if [[ ! -f "$pyproject_file" ]]; then
        echo "未知"
        return
    fi
    
    local version=$(grep -E '^version\s*=' "$pyproject_file" | sed 's/.*"\(.*\)".*/\1/' | head -n1)
    echo "${version:-未知}"
}

# 递增版本号
increment_package_version() {
    local package_path="$1"
    local package_name="$2"
    local pyproject_file="$package_path/pyproject.toml"
    
    if [[ ! -f "$pyproject_file" ]]; then
        echo -e "${RED}❌ $package_name: 未找到 pyproject.toml${NC}"
        return 1
    fi
    
    # 备份原文件
    cp "$pyproject_file" "$pyproject_file.backup"
    
    # 提取当前版本
    local current_version=$(get_package_version "$package_path")
    if [[ "$current_version" == "未知" ]]; then
        echo -e "${RED}❌ $package_name: 无法获取当前版本${NC}"
        return 1
    fi
    
    # 解析版本号
    local version_parts=(${current_version//./ })
    local major=${version_parts[0]:-0}
    local minor=${version_parts[1]:-0}
    local patch=${version_parts[2]:-0}
    
    # 根据类型递增
    case "$INCREMENT_TYPE" in
        major)
            ((major++))
            minor=0
            patch=0
            ;;
        minor)
            ((minor++))
            patch=0
            ;;
        patch)
            ((patch++))
            ;;
        *)
            echo -e "${RED}❌ 未知的递增类型: $INCREMENT_TYPE${NC}"
            return 1
            ;;
    esac
    
    local new_version="$major.$minor.$patch"
    
    # 更新版本号
    sed -i "s/version = \"$current_version\"/version = \"$new_version\"/" "$pyproject_file"
    
    echo -e "${GREEN}✅ $package_name: $current_version → $new_version${NC}"
    return 0
}

# 执行动作
case "$ACTION" in
    list)
        echo -e "${BOLD}📋 包版本信息:${NC}"
        echo
        for package in "${packages[@]}"; do
            package_path="$PROJECT_ROOT/packages/$package"
            if [[ -d "$package_path" ]]; then
                version=$(get_package_version "$package_path")
                printf "  %-25s %s\n" "$package" "$version"
            else
                echo -e "${RED}  ⚠️ $package: 包目录不存在${NC}"
            fi
        done
        ;;
        
    increment)
        echo -e "${BOLD}🔄 递增版本号 (类型: $INCREMENT_TYPE):${NC}"
        echo
        
        success_count=0
        failed_count=0
        
        for package in "${packages[@]}"; do
            package_path="$PROJECT_ROOT/packages/$package"
            if [[ -d "$package_path" ]]; then
                if increment_package_version "$package_path" "$package"; then
                    ((success_count++))
                else
                    ((failed_count++))
                fi
            else
                echo -e "${RED}❌ $package: 包目录不存在${NC}"
                ((failed_count++))
            fi
        done
        
        echo
        echo -e "${BOLD}===== 版本递增摘要 =====${NC}"
        echo -e "${GREEN}成功: $success_count${NC}"
        echo -e "${RED}失败: $failed_count${NC}"
        
        if [[ $failed_count -eq 0 ]]; then
            echo -e "\n${GREEN}🎉 所有包版本递增成功！${NC}"
        else
            echo -e "\n${RED}💥 有 $failed_count 个包版本递增失败${NC}"
            exit 1
        fi
        ;;
esac
