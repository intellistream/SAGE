#!/bin/bash
# =============================================================================
# check_copilot_instructions_sync.sh
# =============================================================================
# Pre-commit hook to ensure copilot-instructions.md and my-agent.agent.md
# are kept in sync, and remind developers to update them when critical
# project files are modified.
#
# Related files:
#   - .github/copilot-instructions.md  (Main Copilot instructions - full knowledge)
#   - .github/agents/my-agent.agent.md (Agent definition - condensed version)
#
# This hook checks:
#   1. If copilot-instructions.md is modified, remind to update my-agent
#   2. If my-agent.agent.md is modified, remind to update copilot-instructions
#   3. If critical project files are modified, remind to check if docs need update
#
# Critical project files that may require doc updates:
#   - Installation: quickstart.sh, manage.sh, tools/install/*.sh
#   - CI/CD: .github/workflows/*.yml
#   - Config: pre-commit / ruff / project packaging / cluster config
#   - Meta package layout: pyproject.toml, src/sage/_version.py
#
# Exit codes:
#   0 - OK (allow commit, warnings only)
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# File paths
COPILOT_INSTRUCTIONS=".github/copilot-instructions.md"
MY_AGENT=".github/agents/my-agent.agent.md"

# Critical file patterns that may require documentation updates
# Format: "pattern|category|description"
CRITICAL_PATTERNS=(
    # Installation & Setup
    "^quickstart\.sh$|安装|主安装脚本"
    "^manage\.sh$|安装|Submodule 管理脚本"
    "^tools/install/.*\.sh$|安装|安装辅助脚本"
    "^Makefile$|安装|Make 快捷命令"

    # CI/CD
    "^\.github/workflows/.*\.yml$|CI/CD|GitHub Actions 工作流"

    # Development Tools Config
    "^tools/pre-commit-config\.yaml$|开发工具|Pre-commit 配置"
    "^tools/config/pre-commit-config\.yaml$|开发工具|Pre-commit 配置模板"
    "^tools/pytest\.ini$|测试|Pytest 配置"
    "^tools/ruff\.toml$|代码质量|Ruff 配置"

    # Meta Package & Config
    "^pyproject\.toml$|架构|Meta package 依赖与打包配置"
    "^src/sage/_version\.py$|架构|Meta package 版本定义"
    "^config/config\.yaml$|配置|主配置文件结构"
    "^config/cluster\.yaml$|配置|集群配置文件结构"
)

# Get all staged files
get_all_staged_files() {
    if [ -n "${PRE_COMMIT_FROM_REF:-}" ] && [ -n "${PRE_COMMIT_TO_REF:-}" ]; then
        # Running with --all-files or during push
        git diff --name-only "${PRE_COMMIT_FROM_REF}" "${PRE_COMMIT_TO_REF}" 2>/dev/null || true
    else
        # Running in normal commit mode
        git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true
    fi
}

# Check if a specific file is staged
is_file_staged() {
    local file="$1"
    local staged_files
    staged_files=$(get_all_staged_files)
    echo "$staged_files" | grep -q "^${file}$"
}

# Check if any file matching pattern is staged
check_pattern_staged() {
    local pattern="$1"
    local staged_files
    staged_files=$(get_all_staged_files)
    echo "$staged_files" | grep -qE "$pattern"
}

# Get files matching pattern
get_matching_files() {
    local pattern="$1"
    local staged_files
    staged_files=$(get_all_staged_files)
    echo "$staged_files" | grep -E "$pattern" || true
}

# Main logic
main() {
    local copilot_modified=false
    local agent_modified=false
    local has_warnings=false

    # Check if doc files are modified
    if is_file_staged "$COPILOT_INSTRUCTIONS"; then
        copilot_modified=true
    fi

    if is_file_staged "$MY_AGENT"; then
        agent_modified=true
    fi

    # =========================================================================
    # Check 1: Critical project files modified without doc updates
    # =========================================================================
    local critical_changes=""
    local categories_affected=""

    for entry in "${CRITICAL_PATTERNS[@]}"; do
        local pattern category description
        pattern=$(echo "$entry" | cut -d'|' -f1)
        category=$(echo "$entry" | cut -d'|' -f2)
        description=$(echo "$entry" | cut -d'|' -f3)

        local matching_files
        matching_files=$(get_matching_files "$pattern")

        if [ -n "$matching_files" ]; then
            # Add to critical changes list
            while IFS= read -r file; do
                [ -z "$file" ] && continue
                critical_changes="${critical_changes}  - ${file} (${category}: ${description})\n"
            done <<< "$matching_files"

            # Track affected categories
            if [[ ! "$categories_affected" =~ "$category" ]]; then
                categories_affected="${categories_affected}${category}, "
            fi
        fi
    done

    # If critical files changed but docs not updated, warn
    if [ -n "$critical_changes" ] && [ "$copilot_modified" = false ] && [ "$agent_modified" = false ]; then
        has_warnings=true
        echo ""
        echo -e "${YELLOW}⚠️  提醒: 检测到关键项目文件变更，请检查是否需要更新 Copilot 指令${NC}"
        echo ""
        echo -e "${CYAN}📝 变更的关键文件:${NC}"
        echo -e "$critical_changes"
        echo ""
        echo -e "${BLUE}📁 涉及的领域: ${categories_affected%%, }${NC}"
        echo ""
        echo "💡 请检查以下文档是否需要更新:"
        echo "   - ${COPILOT_INSTRUCTIONS}  (完整知识库)"
        echo "   - ${MY_AGENT}  (Agent 精简版)"
        echo ""
        echo "📖 文档应该记录的内容:"
        echo "   - 新的安装步骤或选项"
        echo "   - 新的 CLI 命令"
        echo "   - 端口配置变化"
        echo "   - CI/CD 流程变化"
        echo "   - 新的架构组件"
        echo ""
    fi

    # =========================================================================
    # Check 2: Doc files modified but not in sync with each other
    # =========================================================================
    if [ "$copilot_modified" = true ] && [ "$agent_modified" = false ]; then
        has_warnings=true
        echo ""
        echo -e "${YELLOW}⚠️  警告: copilot-instructions.md 已修改，但 my-agent.agent.md 未同步${NC}"
        echo ""
        echo "💡 建议操作:"
        echo "   1. my-agent.agent.md 是 copilot-instructions.md 的精简版"
        echo "   2. 关键变更应同步到 my-agent.agent.md"
        echo "   3. 如果是细节补充可以不同步"
        echo ""
    elif [ "$copilot_modified" = false ] && [ "$agent_modified" = true ]; then
        has_warnings=true
        echo ""
        echo -e "${YELLOW}⚠️  警告: my-agent.agent.md 已修改，但 copilot-instructions.md 未同步${NC}"
        echo ""
        echo "💡 建议操作:"
        echo "   1. copilot-instructions.md 是主要知识库"
        echo "   2. my-agent 的重要更新应该先更新 copilot-instructions"
        echo "   3. 确保两份文档的核心内容一致"
        echo ""
    elif [ "$copilot_modified" = true ] && [ "$agent_modified" = true ]; then
        echo -e "${GREEN}✓ copilot-instructions.md 和 my-agent.agent.md 都已修改，保持同步${NC}"
    fi

    # =========================================================================
    # Final message
    # =========================================================================
    if [ "$has_warnings" = true ]; then
        echo -e "${GREEN}✓ 提交将继续，请记得在后续提交中补充必要的文档更新${NC}"
        echo ""
    fi

    # Always exit 0 to allow commit (warnings only)
    exit 0
}

main "$@"
