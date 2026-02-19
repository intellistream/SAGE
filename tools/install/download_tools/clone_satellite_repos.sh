#!/bin/bash
# SAGE 附属仓库克隆模块
# 从 SAGE.code-workspace 文件动态读取要克隆的仓库列表

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 导入颜色定义
source "$SCRIPT_DIR/../display_tools/colors.sh"

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

    # 尝试使用 jq（如果可用）
    if command -v jq >/dev/null 2>&1; then
        # 使用 jq 解析 JSON
        jq -r '.folders[] | select(.name != "SAGE") | "\(.name)|\(.path)"' "$workspace_file"
        return $?
    else
        # 降级方案：使用 python 解析 JSON
        if command -v python3 >/dev/null 2>&1; then
            python3 << 'PYTHON_EOF'
import json
import sys

workspace_file = sys.argv[1]
try:
    with open(workspace_file) as f:
        data = json.load(f)

    for folder in data.get('folders', []):
        if folder['name'] != 'SAGE':
            # 转换相对路径为仓库名
            path = folder['path']
            name = folder['name']
            # 清理路径（移除 ../ 前缀）
            print(f"{name}|{path.lstrip('./')}")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF
            return $?
        else
            # 最后的降级方案：简单的正则解析
            grep -oP '"name":\s*"\K[^"]+(?=")|"path":\s*"\K[^"]+(?=")' "$workspace_file" | \
            awk 'NR % 2 == 1 {name=$0; next} {print name "|" $0}' | \
            grep -v '^SAGE|'
            return $?
        fi
    fi
}

# 构建仓库 URL
get_repo_url() {
    local repo_name="$1"
    # 标准的 GitHub 仓库 URL 格式
    echo "https://github.com/intellistream/${repo_name}.git"
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

        # 尝试切换到 main-dev 分支
        if cd "$repo_path" 2>/dev/null; then
            # 检查是否是 git 仓库
            if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
                # 获取当前分支
                local current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

                # 检查 main-dev 分支是否存在（本地）
                if git rev-parse --verify main-dev 2>/dev/null; then
                    # 本地存在 main-dev，直接切换
                    if git checkout main-dev >/dev/null 2>&1; then
                        echo -e "${GREEN}   ✓ 已切换到 main-dev 分支${NC}"
                    else
                        echo -e "${YELLOW}   ⚠️  无法切换到 main-dev 分支${NC}"
                    fi
                elif git fetch origin main-dev 2>/dev/null; then
                    # 远程存在 main-dev，先 fetch 再创建
                    if git checkout -b main-dev origin/main-dev 2>/dev/null; then
                        echo -e "${GREEN}   ✓ 已创建并切换到 main-dev 分支${NC}"
                    else
                        echo -e "${YELLOW}   ⚠️  无法创建/切换到 main-dev 分支${NC}"
                    fi
                else
                    echo -e "${DIM}   ℹ️  main-dev 分支不存在（当前分支: $current_branch）${NC}"
                fi
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

    if git clone "$repo_url" "$repo_path" 2>/dev/null; then
        echo -e "${GREEN}✅ $repo_name 克隆成功${NC}"

        # 克隆成功后，尝试切换到 main-dev 分支
        if cd "$repo_path" 2>/dev/null; then
            # 检查远程是否有 main-dev 分支
            if git fetch origin main-dev 2>/dev/null && git rev-parse origin/main-dev 2>/dev/null; then
                if git checkout -b main-dev origin/main-dev 2>/dev/null; then
                    echo -e "${GREEN}   ✓ 已切换到 main-dev 分支${NC}"
                fi
            else
                # 如果没有 main-dev，保持默认分支
                local default_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
                echo -e "${DIM}   ℹ️  使用默认分支: $default_branch${NC}"
            fi
            cd - >/dev/null 2>&1
        fi
        return 0
    else
        echo -e "${RED}❌ $repo_name 克隆失败${NC}"
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
    while IFS='|' read -r repo_name repo_path; do
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
    echo -e "${DIM}  • sage-dev-tools, sage-agentic, sage-agentic-tooluse${NC}"
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
