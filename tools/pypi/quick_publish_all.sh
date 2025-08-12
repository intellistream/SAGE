#!/bin/bash
#
# SAGE Framework 快速闭源发布脚本  
# Quick Proprietary Publishing Script for SAGE Framework
#
# 简化版的一键发布脚本，用于快速发布所有包
# Simplified one-click publishing script for quick publishing of all packages

set -euo pipefail

# 脚本目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色配置
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# 版本递增函数
increment_version() {
    local package_path="$1"
    local pyproject_file="$package_path/pyproject.toml"
    
    if [[ ! -f "$pyproject_file" ]]; then
        echo -e "${RED}❌ 未找到 pyproject.toml: $package_path${NC}"
        return 1
    fi
    
    # 备份原文件
    cp "$pyproject_file" "$pyproject_file.backup"
    
    # 提取当前版本
    local current_version=$(grep -E '^version\s*=' "$pyproject_file" | sed 's/.*"\(.*\)".*/\1/')
    if [[ -z "$current_version" ]]; then
        echo -e "${RED}❌ 无法获取当前版本${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}  当前版本: $current_version${NC}"
    
    # 递增补丁版本号 (x.y.z -> x.y.z+1)
    local version_parts=(${current_version//./ })
    local major=${version_parts[0]}
    local minor=${version_parts[1]}
    local patch=${version_parts[2]}
    
    # 递增patch版本
    ((patch++))
    local new_version="$major.$minor.$patch"
    
    # 更新版本号
    sed -i "s/version = \"$current_version\"/version = \"$new_version\"/" "$pyproject_file"
    
    echo -e "${GREEN}  新版本: $new_version${NC}"
    return 0
}

echo -e "${BOLD}🚀 SAGE Framework 快速闭源发布${NC}"
echo -e "====================================="

# 检查参数
DRY_RUN=false
FORCE=false
AUTO_INCREMENT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true  
            shift
            ;;
        --auto-increment)
            AUTO_INCREMENT=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [--dry-run] [--force] [--auto-increment]"
            echo "  --dry-run        预演模式，不实际发布"
            echo "  --force          强制发布，跳过确认"
            echo "  --auto-increment 自动递增版本号（当文件已存在时）"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            exit 1
            ;;
    esac
done

# 获取包列表 - 更新为新的包结构
packages=("sage" "sage-common" "sage-kernel" "sage-middleware" "sage-apps")

echo "发现 ${#packages[@]} 个包:"
for pkg in "${packages[@]}"; do
    if [[ -d "$PROJECT_ROOT/packages/$pkg" ]]; then
        echo "  - $pkg"
    else
        echo "  ⚠️ $pkg (目录不存在)"
    fi
done

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}模式: 预演 (不会实际发布)${NC}"
else
    echo -e "${RED}模式: 实际发布到 PyPI${NC}"
fi

# 确认
if [ "$FORCE" = false ]; then
    echo
    read -p "确认继续？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消发布"
        exit 0
    fi
fi

echo -e "${BOLD}开始发布...${NC}"
success_count=0
failed_count=0

# 发布每个包
for package in "${packages[@]}"; do
    echo -e "\n${BOLD}📦 发布 $package${NC}"
    
    package_path="$PROJECT_ROOT/packages/$package"
    
    # 构建命令
    cmd="sage-dev proprietary $package_path"
    
    if [ "$DRY_RUN" = true ]; then
        cmd="$cmd --dry-run"
    else
        cmd="$cmd --no-dry-run"
    fi
    
    if [ "$FORCE" = true ]; then
        cmd="$cmd --force"
    fi
    
    # 执行发布
    output=$(eval $cmd 2>&1)
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ $package 发布成功${NC}"
        ((success_count++))
    else
        # 检查是否为文件已存在错误
        if echo "$output" | grep -q "File already exists\|already exists"; then
            echo -e "${YELLOW}⚠️ $package 发布跳过: 文件已存在${NC}"
            
            if [ "$AUTO_INCREMENT" = true ]; then
                echo -e "${YELLOW}  🔄 尝试自动递增版本号...${NC}"
                
                if increment_version "$package_path"; then
                    echo -e "${YELLOW}  📦 重新尝试发布...${NC}"
                    
                    # 重新尝试发布
                    retry_output=$(eval $cmd 2>&1)
                    retry_exit_code=$?
                    
                    if [ $retry_exit_code -eq 0 ]; then
                        echo -e "${GREEN}✅ $package 发布成功 (版本已递增)${NC}"
                        ((success_count++))
                    else
                        echo -e "${RED}❌ $package 重试发布失败${NC}"
                        echo -e "${RED}   错误信息: ${retry_output}${NC}"
                        ((failed_count++))
                    fi
                else
                    echo -e "${RED}❌ 版本递增失败${NC}"
                    ((failed_count++))
                fi
            else
                echo -e "${YELLOW}   提示: 请手动在 pyproject.toml 中递增版本号，或使用 --auto-increment 选项${NC}"
                ((failed_count++))
            fi
        else
            echo -e "${RED}❌ $package 发布失败${NC}"
            echo -e "${RED}   错误信息: ${output}${NC}"
            ((failed_count++))
        fi
        
        if [ "$FORCE" = false ]; then
            read -p "继续发布其他包？ (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                break
            fi
        fi
    fi
done

# 显示摘要
echo -e "\n${BOLD}===== 发布摘要 =====${NC}"
echo -e "${GREEN}成功: $success_count${NC}"
echo -e "${RED}失败: $failed_count${NC}"
echo -e "总计: $((success_count + failed_count))"

if [ $failed_count -eq 0 ]; then
    echo -e "\n${GREEN}🎉 所有包发布成功！${NC}"
    exit 0
else
    echo -e "\n${RED}💥 有 $failed_count 个包发布失败${NC}"
    exit 1
fi
