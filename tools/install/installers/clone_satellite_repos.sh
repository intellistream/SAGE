#!/bin/bash
# SAGE 附属仓库克隆模块
# 从 SAGE.code-workspace 文件动态读取要克隆的仓库列表

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 导入颜色定义
source "$SCRIPT_DIR/../ui/colors.sh"

# 获取 workspace 文件路径
SAGE_ROOT="${SAGE_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
WORKSPACE_FILE="$SAGE_ROOT/SAGE.code-workspace"

# 从 workspace 文件读取仓库配置
load_repos_from_workspace() {
    local workspace_file="$1"

    if [ ! -f "$workspace_file" ]; then
        echo -e "${RED}❌ Workspace 文件不存在: $workspace_file${NC}" >&2
        return 1
    fi

    # JSONC 兼容解析：直接从 path 字段提取仓库名（避免 jq/json 对注释报错）
    grep -oP '"path":\s*"\K[^"]+(?=")' "$workspace_file" | \
        grep -v '^\.$' | \
        awk -F'/' '{print $NF}'
}

# 构建仓库 URL
get_repo_url() {
    local repo_name="$1"
    # 标准的 GitHub 仓库 URL 格式
    echo "https://github.com/intellistream/${repo_name}.git"
}

ensure_canonical_branch() {
    local current_branch="$1"

    if [ "$current_branch" = "main" ]; then
        echo -e "${DIM}   ℹ️  当前已在默认分支: main${NC}"
        return 0
    fi

    if git rev-parse --verify main >/dev/null 2>&1; then
        if git checkout main >/dev/null 2>&1; then
            echo -e "${GREEN}   ✓ 已切换到默认分支: main${NC}"
            return 0
        fi
        echo -e "${YELLOW}   ⚠️  无法切换到默认分支: main${NC}"
        return 1
    fi

    if git fetch origin main >/dev/null 2>&1; then
        if git checkout -b main origin/main >/dev/null 2>&1; then
            echo -e "${GREEN}   ✓ 已创建并切换到默认分支: main${NC}"
            return 0
        fi
        echo -e "${YELLOW}   ⚠️  无法创建/切换到默认分支: main${NC}"
        return 1
    fi

    echo -e "${DIM}   ℹ️  保持当前分支: ${current_branch:-unknown}${NC}"
    return 0
}

# 克隆单个仓库
clone_single_repo() {
    local repo_name="$1"
    local repo_url="$2"
    local target_dir="$3"
    local repo_path="$target_dir/$repo_name"

    # 检查目录是否已存在
    if [ -d "$repo_path" ]; then
        echo -e "${YELLOW}⚠️  $repo_name 已存在${NC}"

        # 已存在仓库按 canonical branch(main) 处理，避免遗留 main-dev 误报。
        if cd "$repo_path" 2>/dev/null; then
            # 检查是否是 git 仓库
            if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
                # 获取当前分支
                local current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

                ensure_canonical_branch "$current_branch"
            else
                echo -e "${YELLOW}   ⚠️  不是有效的 git 仓库${NC}"
            fi
            cd - >/dev/null 2>&1
        else
            echo -e "${YELLOW}   ⚠️  无法进入目录${NC}"
        fi
        return 0
    fi

    echo -e "${BLUE}📥 克隆 $repo_name...${NC}"

    # 最多重试 3 次（应对首次连接超时等瞬态故障）
    local max_attempts=3
    local attempt=1
    local clone_ok=false
    local clone_error=""
    while [ $attempt -le $max_attempts ]; do
        clone_error=$(git clone "$repo_url" "$repo_path" 2>&1)
        if [ $? -eq 0 ]; then
            clone_ok=true
            break
        fi
        echo -e "${YELLOW}   ⚠️  第 $attempt 次克隆失败，${NC}${DIM}原因: $clone_error${NC}"
        if [ $attempt -lt $max_attempts ]; then
            echo -e "${DIM}   重试中 ($((attempt+1))/$max_attempts)...${NC}"
            sleep 2
        fi
        attempt=$((attempt + 1))
    done

    if $clone_ok; then
        echo -e "${GREEN}✅ $repo_name 克隆成功${NC}"

        # 新克隆仓库通常已在远端默认分支；若存在 canonical branch(main) 则对齐。
        if cd "$repo_path" 2>/dev/null; then
            local current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
            ensure_canonical_branch "$current_branch"
            cd - >/dev/null 2>&1
        fi
        return 0
    else
        echo -e "${RED}❌ $repo_name 克隆失败（已重试 $max_attempts 次）${NC}"
        echo -e "${DIM}   最后一次错误: $clone_error${NC}"
        return 1
    fi
}

# 克隆所有公开附属仓库
clone_all_public_repos() {
    local parent_dir="$1"
    local workspace_file="${2:-$WORKSPACE_FILE}"
    local failed_repos=()

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}📚 克隆 SAGE 附属仓库${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 检查网络连接
    if ! ping -c 1 github.com >/dev/null 2>&1; then
        echo -e "${RED}❌ 无网络连接到 GitHub，停止克隆${NC}"
        echo -e "${DIM}   请检查网络连接后重试${NC}"
        return 1
    fi

    # 从 workspace 读取仓库列表
    local repos_output
    if ! repos_output=$(load_repos_from_workspace "$workspace_file"); then
        echo -e "${RED}❌ 无法读取 workspace 文件: $workspace_file${NC}"
        return 1
    fi

    # 计算总仓库数
    local total_repos=$(echo "$repos_output" | wc -l)
    if [ "$total_repos" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  没有找到要克隆的仓库${NC}"
        return 1
    fi

    local current=0
    while IFS= read -r repo_name; do
        [ -z "$repo_name" ] && continue

        current=$((current + 1))
        echo -e "${DIM}[$current/$total_repos]${NC} $repo_name"

        local repo_url=$(get_repo_url "$repo_name")
        if clone_single_repo "$repo_name" "$repo_url" "$parent_dir"; then
            echo ""
        else
            failed_repos+=("$repo_name")
            echo ""
        fi
    done <<< "$repos_output"

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ ${#failed_repos[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ 全部 $total_repos 个附属仓库克隆成功！${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  $total_repos 个仓库中有 ${#failed_repos[@]} 个克隆失败：${failed_repos[*]}${NC}"
        return 1
    fi
}

# 克隆私有仓库（当前无私有仓库）
clone_private_repos() {
    echo -e "${DIM}暂无需要克隆的私有仓库${NC}"
}

# 交互式克隆选择
interactive_clone_repos() {
    local parent_dir="$1"
    local workspace_file="${2:-$WORKSPACE_FILE}"

    echo ""
    echo -e "${BOLD}是否克隆 SAGE 附属仓库到当前目录？${NC}"
    echo ""
    echo -e "${DIM}附属仓库将从 SAGE.code-workspace 文件读取，包括：${NC}"
    echo -e "${DIM}  • sage-examples, sage-tutorials, sagellm, sage-benchmark${NC}"
    echo -e "${DIM}  • sage-agentic, sage-agentic-tooluse${NC}"
    echo -e "${DIM}  • sage-anns, sage-eval, sage-finetune, sage-studio 等${NC}"
    echo ""
    echo -e "${YELLOW}💡 提示：${NC}"
    echo -e "${DIM}  如果不克隆，可以稍后手动克隆：${NC}"
    echo -e "${DIM}  git clone https://github.com/intellistream/sage-examples.git${NC}"
    echo ""

    read -p "是否现在克隆附属仓库？[y/N]: " -r response
    response=${response,,}

    if [[ "$response" =~ ^(y|yes)$ ]]; then
        clone_all_public_repos "$parent_dir" "$workspace_file"
        return 0
    else
        echo -e "${DIM}已取消克隆操作${NC}"
        return 1
    fi
}

# 导出函数供外部使用
export -f load_repos_from_workspace
export -f get_repo_url
export -f clone_single_repo
export -f clone_all_public_repos
export -f clone_private_repos
export -f interactive_clone_repos
