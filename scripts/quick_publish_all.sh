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

echo -e "${BOLD}🚀 SAGE Framework 快速闭源发布${NC}"
echo -e "====================================="

# 检查参数
DRY_RUN=false
FORCE=false

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
        -h|--help)
            echo "用法: $0 [--dry-run] [--force]"
            echo "  --dry-run  预演模式，不实际发布"
            echo "  --force    强制发布，跳过确认"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            exit 1
            ;;
    esac
done

# 获取包列表
packages=($(ls -1 "$PROJECT_ROOT/packages" | grep -E '^sage-'))

echo "发现 ${#packages[@]} 个包:"
for pkg in "${packages[@]}"; do
    echo "  - $pkg"
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
    if eval $cmd; then
        echo -e "${GREEN}✅ $package 发布成功${NC}"
        ((success_count++))
    else
        echo -e "${RED}❌ $package 发布失败${NC}"
        ((failed_count++))
        
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
