#!/bin/bash
# 🔧 解决 submodule 冲突的脚本
# 使用主仓库的版本（保留我们的版本）
#
# 注意：重构后的 submodule 路径：
# - packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB
# - packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow
# - packages/sage-common/src/sage/common/components/sage_vllm/sageLLM

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== 解决 Submodule 冲突 ===${NC}"
echo ""

# 当前有效的 submodule 路径
SUBMODULES=(
    "packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB"
    "packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow"
    "packages/sage-common/src/sage/common/components/sage_vllm/sageLLM"
    "docs-public"
)

# 1. 检查当前冲突状态
echo -e "${BLUE}📋 检查当前 git 状态...${NC}"
git status
echo ""

# 2. 检查是否有冲突的 submodule
echo -e "${BLUE}🔍 检查冲突的 submodules...${NC}"
conflicted_submodules=()

for submodule in "${SUBMODULES[@]}"; do
    if git ls-files -u | grep -q "^160000.*${submodule}$"; then
        conflicted_submodules+=("$submodule")
        echo -e "${YELLOW}  ⚠️  发现冲突: ${submodule}${NC}"
    fi
done

if [ ${#conflicted_submodules[@]} -eq 0 ]; then
    echo -e "${GREEN}  ✅ 没有发现 submodule 冲突${NC}"
    exit 0
fi
echo ""

# 3. 解决冲突
echo -e "${BLUE}🔧 解决冲突...${NC}"
for submodule in "${conflicted_submodules[@]}"; do
    echo -e "${YELLOW}处理: ${submodule}${NC}"

    # 使用我们的版本（--ours）
    echo -e "  📥 使用我们的版本..."
    git checkout --ours "$submodule"

    # 更新子模块到正确的 commit
    echo -e "  🔄 更新子模块..."
    git submodule update --init --recursive "$submodule"

    # 添加解决后的文件
    echo -e "  ✅ 添加解决后的文件..."
    git add "$submodule"
    echo ""
done

# 4. 检查解决后的状态
echo -e "${BLUE}📊 检查解决后的状态...${NC}"
git status
echo ""

echo -e "${GREEN}✅ 冲突解决完成${NC}"
echo -e "${YELLOW}📝 下一步：运行 ${GREEN}'git commit'${YELLOW} 来完成合并${NC}"
echo ""
