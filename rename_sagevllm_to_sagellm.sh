#!/bin/bash
# 批量重命名 sage_llm → sage_llm
#
# 用法:
#   ./rename_sagellm_to_sagellm.sh --dry-run  # 预览
#   ./rename_sagellm_to_sagellm.sh            # 执行

set -e

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 DRY RUN 模式 - 仅预览不执行"
    echo ""
fi

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. 重命名目录结构
log_info "步骤 1: 重命名目录 sage_llm → sage_llm"
echo ""

OLD_DIR="packages/sage-common/src/sage/common/components/sage_llm"
NEW_DIR="packages/sage-common/src/sage/common/components/sage_llm"

if [ -d "$OLD_DIR" ]; then
    if [ "$DRY_RUN" = true ]; then
        log_warning "将执行: mv $OLD_DIR $NEW_DIR"
    else
        log_info "重命名目录: $OLD_DIR → $NEW_DIR"
        git mv "$OLD_DIR" "$NEW_DIR"
        log_success "目录重命名完成"
    fi
else
    log_warning "目录不存在: $OLD_DIR (可能已重命名)"
fi

echo ""

# 2. 替换文件内容中的引用
log_info "步骤 2: 替换文件内容中的 sage_llm → sage_llm"
echo ""

# 需要替换的模式
declare -A PATTERNS=(
    ["sage_llm"]="sage_llm"
    ["sage-llm"]="sage-llm"
    ["SAGE_LLM"]="SAGE_LLM"
    ["sagellm"]="sagellm"
)

# 排除的目录和文件
EXCLUDE_DIRS=(
    ".git"
    ".sage"
    "node_modules"
    "__pycache__"
    ".pytest_cache"
    ".mypy_cache"
    ".ruff_cache"
    "htmlcov"
    "dist"
    "build"
    "*.egg-info"
)

# 构建 find 排除参数
EXCLUDE_ARGS=()
for dir in "${EXCLUDE_DIRS[@]}"; do
    EXCLUDE_ARGS+=(-not -path "*/$dir/*")
done

# 查找所有文本文件（排除二进制文件）
FILES=$(find . -type f \
    "${EXCLUDE_ARGS[@]}" \
    \( -name "*.py" -o -name "*.md" -o -name "*.sh" -o -name "*.yaml" \
       -o -name "*.yml" -o -name "*.json" -o -name "*.toml" -o -name "*.ini" \
       -o -name "*.txt" -o -name "*.rst" -o -name ".gitmodules" \) \
    2>/dev/null)

total_files=0
modified_files=0

for file in $FILES; do
    if [ ! -f "$file" ]; then
        continue
    fi

    total_files=$((total_files + 1))
    needs_modification=false

    # 检查文件是否包含任何需要替换的模式
    for old_pattern in "${!PATTERNS[@]}"; do
        if grep -q "$old_pattern" "$file" 2>/dev/null; then
            needs_modification=true
            break
        fi
    done

    if [ "$needs_modification" = true ]; then
        modified_files=$((modified_files + 1))

        if [ "$DRY_RUN" = true ]; then
            echo "  将修改: $file"
            # 显示将要进行的替换
            for old_pattern in "${!PATTERNS[@]}"; do
                new_pattern="${PATTERNS[$old_pattern]}"
                count=$(grep -o "$old_pattern" "$file" 2>/dev/null | wc -l)
                if [ "$count" -gt 0 ]; then
                    echo "    - $old_pattern → $new_pattern ($count 处)"
                fi
            done
        else
            log_info "修改文件: $file"

            # 执行替换
            for old_pattern in "${!PATTERNS[@]}"; do
                new_pattern="${PATTERNS[$old_pattern]}"
                # 使用 sed 进行替换（Mac 和 Linux 兼容）
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s/${old_pattern}/${new_pattern}/g" "$file"
                else
                    sed -i "s/${old_pattern}/${new_pattern}/g" "$file"
                fi
            done
        fi
    fi
done

echo ""
log_info "扫描了 $total_files 个文件，需要修改 $modified_files 个文件"
echo ""

# 3. 特殊处理：.gitmodules 中的 submodule 路径
log_info "步骤 3: 更新 .gitmodules submodule 路径"
echo ""

GITMODULES_FILE=".gitmodules"
if [ -f "$GITMODULES_FILE" ]; then
    if grep -q "sage_llm" "$GITMODULES_FILE"; then
        if [ "$DRY_RUN" = true ]; then
            log_warning "将更新 $GITMODULES_FILE 中的 submodule 路径"
            grep -n "sage_llm" "$GITMODULES_FILE" || true
        else
            log_info "更新 .gitmodules"
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' 's|sage_llm|sage_llm|g' "$GITMODULES_FILE"
            else
                sed -i 's|sage_llm|sage_llm|g' "$GITMODULES_FILE"
            fi
            log_success ".gitmodules 已更新"
        fi
    else
        log_info ".gitmodules 中未找到 sage_llm 引用"
    fi
fi

echo ""

# 4. 总结
if [ "$DRY_RUN" = true ]; then
    echo "═══════════════════════════════════════════════════════════"
    log_warning "DRY RUN 完成 - 未执行任何修改"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "如果预览结果正确，执行以下命令进行实际重命名："
    echo ""
    echo "  ./rename_sagellm_to_sagellm.sh"
    echo ""
else
    echo "═══════════════════════════════════════════════════════════"
    log_success "重命名完成！"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "下一步操作："
    echo ""
    echo "1. 检查修改："
    echo "   git status"
    echo "   git diff"
    echo ""
    echo "2. 测试构建："
    echo "   sage-dev project test --quick"
    echo ""
    echo "3. 提交修改："
    echo "   git add -A"
    echo "   git commit -m 'refactor: Rename sage_llm to sage_llm'"
    echo "   git push"
    echo ""
    log_warning "⚠️  注意: submodule 路径已变更，可能需要手动更新 submodule 配置"
    echo ""
fi
