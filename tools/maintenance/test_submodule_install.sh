#!/bin/bash
# 测试完整的 submodule 安装流程
# 用于验证在 main-dev 分支下，所有 submodule 都能正确初始化到 main-dev 分支

set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
cd "$REPO_ROOT"

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  🧪 Submodule 安装流程测试${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1. 检查当前分支
echo -e "${BLUE}1. 检查主仓库分支${NC}"
current_branch=$(git rev-parse --abbrev-ref HEAD)
echo -e "   当前分支: ${GREEN}${current_branch}${NC}"

if [ "$current_branch" != "main-dev" ] && [ "$current_branch" != "main" ]; then
    echo -e "${YELLOW}   ⚠️  警告: 当前不在 main 或 main-dev 分支${NC}"
fi
echo ""

# 2. 检查 .gitmodules 配置
echo -e "${BLUE}2. 检查 .gitmodules 配置${NC}"
expected_branch="main-dev"
if [ "$current_branch" = "main" ]; then
    expected_branch="main"
fi

echo -e "   期望的 submodule 分支: ${GREEN}${expected_branch}${NC}"
echo ""

# 获取所有 submodule
mapfile -t submodules < <(git config --file .gitmodules --get-regexp path | awk '{ print $2 }')
echo -e "   找到 ${#submodules[@]} 个 submodules"
echo ""

# 3. 检查 submodule 配置的分支
echo -e "${BLUE}3. 检查每个 submodule 的配置分支${NC}"
config_mismatch=0
for submodule_path in "${submodules[@]}"; do
    submodule_name=$(basename "$submodule_path")
    config_branch=$(git config --file .gitmodules --get "submodule.${submodule_path}.branch" || echo "N/A")
    
    if [ "$config_branch" = "$expected_branch" ]; then
        echo -e "   ${GREEN}✓${NC} ${submodule_name}: ${config_branch}"
    else
        echo -e "   ${RED}✗${NC} ${submodule_name}: ${config_branch} (期望: ${expected_branch})"
        ((config_mismatch++))
    fi
done
echo ""

if [ $config_mismatch -gt 0 ]; then
    echo -e "${YELLOW}   ⚠️  发现 ${config_mismatch} 个配置不匹配${NC}"
    echo -e "${DIM}   建议: 运行 ./manage.sh submodule switch 更新配置${NC}"
    echo ""
fi

# 4. 检查 submodule 实际状态
echo -e "${BLUE}4. 检查 submodule 实际分支状态${NC}"
initialized_count=0
correct_branch_count=0
wrong_branch_count=0
detached_count=0

for submodule_path in "${submodules[@]}"; do
    submodule_name=$(basename "$submodule_path")
    
    if [ -d "$submodule_path/.git" ] || [ -f "$submodule_path/.git" ]; then
        ((initialized_count++))
        
        # 获取当前分支
        cd "$submodule_path"
        actual_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached")
        cd - > /dev/null
        
        if [ "$actual_branch" = "$expected_branch" ]; then
            echo -e "   ${GREEN}✓${NC} ${submodule_name}: ${actual_branch}"
            ((correct_branch_count++))
        elif [ "$actual_branch" = "detached" ] || [ "$actual_branch" = "HEAD" ]; then
            echo -e "   ${YELLOW}⚠${NC} ${submodule_name}: detached HEAD"
            ((detached_count++))
        else
            echo -e "   ${RED}✗${NC} ${submodule_name}: ${actual_branch} (期望: ${expected_branch})"
            ((wrong_branch_count++))
        fi
    else
        echo -e "   ${YELLOW}⚠${NC} ${submodule_name}: 未初始化"
    fi
done
echo ""

# 5. 显示测试结果总结
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  📊 测试结果总结${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "总 submodules 数: ${BOLD}${#submodules[@]}${NC}"
echo -e "已初始化: ${BOLD}${initialized_count}${NC}"
echo -e "├─ 正确分支: ${GREEN}${BOLD}${correct_branch_count}${NC}"
echo -e "├─ 错误分支: ${RED}${BOLD}${wrong_branch_count}${NC}"
echo -e "└─ Detached HEAD: ${YELLOW}${BOLD}${detached_count}${NC}"
echo ""

# 6. 给出建议
if [ $initialized_count -eq 0 ]; then
    echo -e "${YELLOW}💡 建议操作：${NC}"
    echo -e "   运行以下命令初始化 submodules："
    echo -e "   ${GREEN}./manage.sh${NC}"
    echo -e "   或"
    echo -e "   ${GREEN}./quickstart.sh --sync-submodules${NC}"
elif [ $correct_branch_count -eq ${#submodules[@]} ]; then
    echo -e "${GREEN}${BOLD}✅ 所有 submodules 都在正确的分支上！${NC}"
    echo ""
    echo -e "${GREEN}安装流程验证通过 ✓${NC}"
else
    echo -e "${YELLOW}💡 建议操作：${NC}"
    echo -e "   运行以下命令切换分支："
    echo -e "   ${GREEN}./manage.sh submodule switch${NC}"
    echo ""
    echo -e "   或者重新初始化："
    echo -e "   ${GREEN}git submodule deinit -f --all${NC}"
    echo -e "   ${GREEN}rm -rf .git/modules${NC}"
    echo -e "   ${GREEN}./manage.sh${NC}"
fi

echo ""

# 返回合适的退出码
if [ $correct_branch_count -eq ${#submodules[@]} ]; then
    exit 0
else
    exit 1
fi
