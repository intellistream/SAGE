#!/bin/bash
# 🧹 清理旧的 sage_db、sage_flow 和 sage_vllm submodule 配置
# 背景：重构后相关组件下沉到子目录中，需要清理旧配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧹 清理旧的 submodule 配置${NC}"
echo ""

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# 旧的 submodule 路径（不再使用）
OLD_SUBMODULES=(
    "packages/sage-middleware/src/sage/middleware/components/sage_db"
    "packages/sage-middleware/src/sage/middleware/components/sage_flow"
    "packages/sage-middleware/src/sage/middleware/components/sage_vllm"
    "packages/sage-middleware/src/sage/middleware/components/sage_vllm/sageLLM"
)

# 新的 submodule 路径（需要清理重建）
NEW_SUBMODULES=(
    "packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB"
    "packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow"
    "packages/sage-common/src/sage/common/components/sage_vllm/sageLLM"
)

for submodule_path in "${OLD_SUBMODULES[@]}"; do
    echo -e "${YELLOW}处理旧 submodule: ${submodule_path}${NC}"

    # 1. 从 .git/config 中删除配置
    if git config --local --get "submodule.${submodule_path}.url" &>/dev/null; then
        echo -e "  ⚙️  从 .git/config 中移除配置..."
        git config --local --remove-section "submodule.${submodule_path}" 2>/dev/null || true
    fi

    # 2. 从 .git/modules 中删除缓存
    module_dir=".git/modules/${submodule_path}"
    if [ -d "$module_dir" ]; then
        echo -e "  🗑️  删除 .git/modules 缓存..."
        rm -rf "$module_dir"
    fi

    # 3. 清理工作目录中的 .git 文件（如果存在）
    if [ -f "${submodule_path}/.git" ]; then
        echo -e "  🗑️  清理工作目录中的 .git 文件..."
        rm -f "${submodule_path}/.git"
    fi

    echo -e "${GREEN}  ✅ 已清理${NC}"
    echo ""
done

# 清理新 submodule 路径中的残留文件
echo -e "${YELLOW}清理新 submodule 路径中的残留文件...${NC}"
for submodule_path in "${NEW_SUBMODULES[@]}"; do
    if [ -f "${submodule_path}/.git" ]; then
        echo -e "  🗑️  删除 ${submodule_path}/.git"
        rm -f "${submodule_path}/.git"
    fi

    # 如果目录存在但不是有效的 git 仓库，清空它
    if [ -d "${submodule_path}" ] && [ ! -d "${submodule_path}/.git" ]; then
        echo -e "  🗑️  清空无效目录 ${submodule_path}"
        rm -rf "${submodule_path}"
        mkdir -p "${submodule_path}"
    fi
done
echo ""

echo -e "${GREEN}✅ 旧 submodule 配置清理完成${NC}"
echo ""
echo -e "${BLUE}ℹ️  当前有效的 submodules:${NC}"
git config --file .gitmodules --get-regexp path | awk '{ print "  - " $2 }'
echo ""
echo -e "${YELLOW}📝 下一步操作：${NC}"
echo -e "  1. 运行: ${GREEN}git submodule sync${NC}"
echo -e "  2. 运行: ${GREEN}git submodule update --init --recursive${NC}"
echo -e "  3. 如果还有问题，运行: ${GREEN}./tools/maintenance/manage_submodule_branches.sh switch${NC}"
echo ""
