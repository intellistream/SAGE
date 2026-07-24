#!/bin/bash
# SAGE 附属仓库克隆模块
# 从显式清单读取适合公开开发环境的 SAGE 附属仓库

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 导入颜色定义
source "$SCRIPT_DIR/../ui/colors.sh"

# 获取仓库根目录与公开附属仓库清单
SAGE_ROOT="${SAGE_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
REPOSITORY_MANIFEST="$SAGE_ROOT/tools/install/satellite-repositories.json"

# 从公开仓库清单读取 name|clone_url，拒绝跨组织或不完整条目。
load_public_repos_from_manifest() {
    local manifest_file="${1:-$REPOSITORY_MANIFEST}"

    if [ ! -f "$manifest_file" ]; then
        echo -e "${RED}❌ 附属仓库清单不存在: $manifest_file${NC}" >&2
        return 1
    fi

    python3 - "$manifest_file" <<'PY'
import json
import sys
from pathlib import Path

manifest_file = Path(sys.argv[1])
try:
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"invalid satellite repository manifest: {exc}")

if data.get("version") != 1:
    raise SystemExit("invalid satellite repository manifest: version must be 1")

repositories = data.get("repositories")
if not isinstance(repositories, list):
    raise SystemExit("invalid satellite repository manifest: repositories must be a list")

seen_names: set[str] = set()
seen_full_names: set[str] = set()
for index, item in enumerate(repositories):
    if not isinstance(item, dict):
        raise SystemExit(f"invalid satellite repository manifest: entry {index} must be an object")

    name = item.get("name")
    full_name = item.get("full_name")
    category = item.get("category")
    clone_by_default = item.get("clone_by_default")
    if not all(isinstance(value, str) and value for value in (name, full_name, category)):
        raise SystemExit(
            f"invalid satellite repository manifest: entry {index} has missing fields"
        )
    if not isinstance(clone_by_default, bool):
        raise SystemExit(
            f"invalid satellite repository manifest: {name} clone_by_default must be boolean"
        )
    if not full_name.startswith("SAGE-Research/") or full_name.count("/") != 1:
        raise SystemExit(
            f"invalid satellite repository manifest: {name} must belong to SAGE-Research"
        )
    if full_name.rsplit("/", 1)[1] != name:
        raise SystemExit(
            f"invalid satellite repository manifest: {name} does not match {full_name}"
        )
    if name in seen_names or full_name.lower() in seen_full_names:
        raise SystemExit(f"invalid satellite repository manifest: duplicate {name}")
    seen_names.add(name)
    seen_full_names.add(full_name.lower())

    if clone_by_default:
        print(f"{name}|https://github.com/{full_name}.git")
PY
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
    local manifest_file="${2:-$REPOSITORY_MANIFEST}"
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

    # 从显式清单读取公开 SAGE 仓库，避免把个人 workspace 当作所有权清单。
    local repos_output
    if ! repos_output=$(load_public_repos_from_manifest "$manifest_file"); then
        echo -e "${RED}❌ 无法读取附属仓库清单: $manifest_file${NC}"
        return 1
    fi

    # 计算总仓库数
    local total_repos=$(echo "$repos_output" | wc -l)
    if [ "$total_repos" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  没有找到要克隆的仓库${NC}"
        return 1
    fi

    local current=0
    while IFS='|' read -r repo_name repo_url; do
        [ -z "$repo_name" ] && continue
        [ -z "$repo_url" ] && continue

        current=$((current + 1))
        echo -e "${DIM}[$current/$total_repos]${NC} $repo_name"

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
    local manifest_file="${2:-$REPOSITORY_MANIFEST}"

    echo ""
    echo -e "${BOLD}是否克隆 SAGE 附属仓库到当前目录？${NC}"
    echo ""
    echo -e "${DIM}附属仓库将从公开 SAGE 仓库清单读取，包括：${NC}"
    echo -e "${DIM}  • SAGE-Docs, sage-examples, sage-tutorials, sage-benchmark${NC}"
    echo -e "${DIM}  • sage-agentic, sage-agentic-tooluse, sage-rag${NC}"
    echo -e "${DIM}  • sage-eval, sage-finetune, sage-libs-intent, sage-studio${NC}"
    echo ""
    echo -e "${YELLOW}💡 提示：${NC}"
    echo -e "${DIM}  如果不克隆，可以稍后手动克隆：${NC}"
    echo -e "${DIM}  git clone https://github.com/SAGE-Research/sage-examples.git${NC}"
    echo ""

    read -p "是否现在克隆附属仓库？[y/N]: " -r response
    response=${response,,}

    if [[ "$response" =~ ^(y|yes)$ ]]; then
        clone_all_public_repos "$parent_dir" "$manifest_file"
        return 0
    else
        echo -e "${DIM}已取消克隆操作${NC}"
        return 1
    fi
}

# 导出函数供外部使用
export -f load_public_repos_from_manifest
export -f clone_single_repo
export -f clone_all_public_repos
export -f clone_private_repos
export -f interactive_clone_repos
