#!/bin/bash
# 🛠️ SAGE 维护工具主脚本
# 统一的维护工具入口，整合所有常用维护功能
# Unified maintenance tool entry point, integrating all common maintenance functions

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
DIM='\033[0;2m'
BOLD='\033[1m'
NC='\033[0m'

# Emoji
CHECK='✅'
CROSS='❌'
INFO='ℹ️'
ROCKET='🚀'
WRENCH='🔧'
BROOM='🧹'
SHIELD='🛡️'
PACKAGE='📦'

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
HELPERS_DIR="${SCRIPT_DIR}/helpers"

# 加载辅助函数
if [ -f "${HELPERS_DIR}/common.sh" ]; then
    source "${HELPERS_DIR}/common.sh"
fi

# ============================================================================
# 显示帮助信息
# ============================================================================
show_help() {
    echo -e "${ROCKET} ${BOLD}SAGE 维护工具${NC}"
    echo ""
    echo -e "${BOLD}用法:${NC}"
    echo -e "  $(basename "$0") <命令> [选项]"
    echo ""
    echo -e "${BOLD}${ROCKET} 快速开始:${NC}"
    echo -e "  ${GREEN}submodule bootstrap${NC}      一键初始化并切换所有 submodule"
    echo -e "  ${GREEN}bootstrap${NC}               与上面命令等效的简写"
    echo ""
    echo -e "${BOLD}${PACKAGE} Submodule 管理:${NC}"
    echo -e "  ${GREEN}submodule status${NC}          显示 submodule 状态"
    echo -e "  ${GREEN}submodule switch${NC}          切换 submodule 分支（根据当前 SAGE 分支）"
    echo -e "  ${GREEN}submodule init${NC}            初始化所有 submodules"
    echo -e "  ${GREEN}submodule update${NC}          更新所有 submodules"
    echo -e "  ${GREEN}submodule bootstrap${NC}      初始化 + 切换分支，首选入口"
    echo -e "  ${GREEN}submodule fix-conflict${NC}    解决 submodule 冲突"
    echo -e "  ${GREEN}submodule cleanup${NC}         清理旧的 submodule 配置"
    echo ""
    echo -e "${BOLD}🔧 项目维护:${NC}"
    echo -e "  ${GREEN}clean${NC}                     清理构建产物和缓存"
    echo -e "  ${GREEN}clean-deep${NC}                深度清理（包括 Python 缓存、日志等）"
    echo -e "  ${GREEN}security-check${NC}            检查配置文件中的敏感信息"
    echo -e "  ${GREEN}setup-hooks${NC}               安装/重新安装 Git hooks"
    echo ""
    echo -e "${BOLD}🔍 诊断工具:${NC}"
    echo -e "  ${GREEN}doctor${NC}                    运行完整的健康检查"
    echo -e "  ${GREEN}status${NC}                    显示项目整体状态"
    echo ""
    echo -e "${BOLD}示例:${NC}"
    echo -e "  # 显示 submodule 状态"
    echo -e "  $(basename "$0") submodule status"
    echo ""
    echo -e "  # 清理项目"
    echo -e "  $(basename "$0") clean"
    echo ""
    echo -e "  # 运行完整健康检查"
    echo -e "  $(basename "$0") doctor"
    echo ""
    echo -e "  # 解决 submodule 冲突"
    echo -e "  $(basename "$0") submodule fix-conflict"
    echo ""
    echo -e "${BOLD}选项:${NC}"
    echo -e "  -h, --help               显示此帮助信息"
    echo -e "  -v, --verbose            显示详细输出"
    echo -e "  -f, --force              强制执行（跳过确认）"
    echo ""
    echo -e "${BOLD}环境要求:${NC}"
    echo -e "  - Git 仓库根目录"
    echo -e "  - 开发模式下建议先运行: ${DIM}./quickstart.sh --dev${NC}"
    echo ""
    echo -e "${BOLD}更多信息:${NC}"
    echo -e "  查看文档: ${DIM}tools/maintenance/README.md${NC}"
    echo -e "  快捷入口: ${DIM}仓库根目录执行 ./manage.sh${NC}"
}

# ============================================================================
# Submodule 管理功能
# ============================================================================

submodule_status() {
    echo -e "${BLUE}${PACKAGE} Submodule 状态${NC}"
    echo ""

    bash "${HELPERS_DIR}/manage_submodule_branches.sh" status
}

submodule_switch() {
    echo -e "${BLUE}${PACKAGE} 切换 Submodule 分支${NC}"
    echo ""

    bash "${HELPERS_DIR}/manage_submodule_branches.sh" switch
}

submodule_init_steps() {
    # 初始化 submodules
    git submodule update --init --recursive
    echo -e "${GREEN}${CHECK} Submodules 初始化完成${NC}"
    echo ""

    # 自动切换到正确的分支
    echo -e "${BLUE}${INFO} 切换 submodules 到正确的分支...${NC}"
    bash "${HELPERS_DIR}/manage_submodule_branches.sh" switch
}

submodule_init() {
    echo -e "${BLUE}${PACKAGE} 初始化 Submodules${NC}"
    echo ""

    submodule_init_steps
}

submodule_update() {
    echo -e "${BLUE}${PACKAGE} 更新 Submodules${NC}"
    echo ""

    git submodule update --remote --recursive
    echo -e "${GREEN}${CHECK} Submodules 更新完成${NC}"
}

submodule_fix_conflict() {
    echo -e "${BLUE}${WRENCH} 解决 Submodule 冲突${NC}"
    echo ""

    bash "${HELPERS_DIR}/resolve_submodule_conflict.sh"
}

submodule_cleanup() {
    echo -e "${BLUE}${BROOM} 清理旧 Submodule 配置${NC}"
    echo ""

    bash "${HELPERS_DIR}/cleanup_old_submodules.sh"
}

submodule_bootstrap() {
    echo -e "${BLUE}${ROCKET} 引导 Submodules${NC}"
    echo ""

    submodule_init_steps

    echo -e "${GREEN}${CHECK} Submodule 引导完成，可继续运行 quickstart${NC}"
}

# ============================================================================
# 项目清理功能
# ============================================================================

clean_project() {
    echo -e "${BLUE}${BROOM} 清理项目${NC}"
    echo ""

    bash "${HELPERS_DIR}/quick_cleanup.sh"
}

clean_deep() {
    echo -e "${BLUE}${BROOM} 深度清理项目${NC}"
    echo ""

    local confirm="n"
    if [ "${FORCE}" != "true" ]; then
        echo -e "${YELLOW}${INFO} 这将删除:${NC}"
        echo -e "  - 所有 __pycache__ 目录"
        echo -e "  - 所有 .pyc, .pyo 文件"
        echo -e "  - 所有 .egg-info 目录"
        echo -e "  - 构建产物和缓存"
        echo -e "  - 日志文件"
        echo ""
        read -p "$(echo -e ${YELLOW}是否继续? [y/N]: ${NC})" confirm
    else
        confirm="y"
    fi

    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        # 运行标准清理
        bash "${HELPERS_DIR}/quick_cleanup.sh"

        # 额外的深度清理
        echo -e "${DIM}清理 Python 缓存...${NC}"
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        find . -type f -name "*.pyo" -delete 2>/dev/null || true
        find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

        echo -e "${DIM}清理日志文件...${NC}"
        find logs -type f -name "*.log" -delete 2>/dev/null || true

        echo -e "${GREEN}${CHECK} 深度清理完成${NC}"
    else
        echo -e "${YELLOW}已取消${NC}"
    fi
}

# ============================================================================
# 安全检查
# ============================================================================

security_check() {
    echo -e "${BLUE}${SHIELD} 安全检查${NC}"
    echo ""

    bash "${HELPERS_DIR}/check_config_security.sh"
}

# ============================================================================
# Git Hooks 设置
# ============================================================================

setup_hooks() {
    echo -e "${BLUE}${WRENCH} 设置 Git Hooks${NC}"
    echo ""

    local force_flag=""
    if [ "${FORCE}" = "true" ]; then
        force_flag="--force"
    fi

    bash "${SCRIPT_DIR}/setup_hooks.sh" ${force_flag}
}

# ============================================================================
# 健康检查
# ============================================================================

run_doctor() {
    echo -e "${BOLD}${CYAN}${ROCKET} SAGE 项目健康检查${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    local issues=0

    # 1. 检查 Git 仓库
    echo -e "${BLUE}1. 检查 Git 仓库...${NC}"
    if git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${GREEN}   ${CHECK} Git 仓库正常${NC}"
        local branch=$(git rev-parse --abbrev-ref HEAD)
        echo -e "${DIM}   当前分支: ${branch}${NC}"
    else
        echo -e "${RED}   ${CROSS} 不是 Git 仓库${NC}"
        ((issues++))
    fi
    echo ""

    # 2. 检查 Git Hooks
    echo -e "${BLUE}2. 检查 Git Hooks...${NC}"
    if [ -f ".git/hooks/post-checkout" ]; then
        echo -e "${GREEN}   ${CHECK} Git hooks 已安装${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Git hooks 未安装${NC}"
        echo -e "${DIM}   运行: ./tools/maintenance/sage-maintenance.sh setup-hooks${NC}"
        ((issues++))
    fi
    echo ""

    # 3. 检查 Submodules
    echo -e "${BLUE}3. 检查 Submodules...${NC}"
    if [ -f ".gitmodules" ]; then
        local total_submodules=$(git config --file .gitmodules --get-regexp path | wc -l)
        local initialized_submodules=0

        # 使用 git submodule status 来检查
        while IFS= read -r line; do
            # 检查行首是否有 '-' (未初始化)
            if [[ ! "$line" =~ ^- ]]; then
                ((initialized_submodules++))
            fi
        done < <(git submodule status 2>/dev/null || echo "")

        if [ "$initialized_submodules" -eq "$total_submodules" ] && [ "$total_submodules" -gt 0 ]; then
            echo -e "${GREEN}   ${CHECK} 所有 submodules 已初始化 (${initialized_submodules}/${total_submodules})${NC}"
        else
            echo -e "${YELLOW}   ⚠️  部分 submodules 未初始化 (${initialized_submodules}/${total_submodules})${NC}"
            echo -e "${DIM}   运行: ./tools/maintenance/sage-maintenance.sh submodule init${NC}"
            ((issues++)) || true
        fi
    else
        echo -e "${YELLOW}   ⚠️  未找到 .gitmodules${NC}"
    fi
    echo ""

    # 4. 检查旧的 submodule 配置
    echo -e "${BLUE}4. 检查旧的 submodule 配置...${NC}"
    local old_configs=0
    if git config --local --get "submodule.packages/sage-middleware/src/sage/middleware/components/sage_db.url" &>/dev/null; then
        ((old_configs++)) || true
    fi
    if git config --local --get "submodule.packages/sage-middleware/src/sage/middleware/components/sage_flow.url" &>/dev/null; then
        ((old_configs++)) || true
    fi

    if [ "$old_configs" -eq 0 ]; then
        echo -e "${GREEN}   ${CHECK} 无旧配置${NC}"
    else
        echo -e "${YELLOW}   ⚠️  发现 ${old_configs} 个旧 submodule 配置${NC}"
        echo -e "${DIM}   运行: ./tools/maintenance/sage-maintenance.sh submodule cleanup${NC}"
        ((issues++)) || true
    fi
    echo ""

    # 5. 检查 Python 环境
    echo -e "${BLUE}5. 检查 Python 环境...${NC}"
    if command -v python &> /dev/null; then
        local python_version=$(python --version 2>&1 | awk '{print $2}')
        echo -e "${GREEN}   ${CHECK} Python 可用: ${python_version}${NC}"
    else
        echo -e "${RED}   ${CROSS} Python 未找到${NC}"
        ((issues++)) || true
    fi
    echo ""

    # 6. 检查构建产物
    echo -e "${BLUE}6. 检查构建产物...${NC}"
    local build_dirs=$(find . -maxdepth 3 -type d \( -name "dist" -o -name "build" -o -name "*.egg-info" \) 2>/dev/null | wc -l)
    if [ "$build_dirs" -gt 0 ]; then
        echo -e "${YELLOW}   ⚠️  发现 ${build_dirs} 个构建目录${NC}"
        echo -e "${DIM}   建议运行: ./tools/maintenance/sage-maintenance.sh clean${NC}"
    else
        echo -e "${GREEN}   ${CHECK} 无需清理${NC}"
    fi
    echo ""

    # 总结
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    if [ "$issues" -eq 0 ]; then
        echo -e "${GREEN}${BOLD}${CHECK} 所有检查通过！项目状态良好。${NC}"
    else
        echo -e "${YELLOW}${BOLD}⚠️  发现 ${issues} 个潜在问题，请查看上述建议。${NC}"
    fi
    echo ""
}

# ============================================================================
# 显示项目状态
# ============================================================================

show_status() {
    echo -e "${BOLD}${CYAN}${INFO} SAGE 项目状态${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Git 信息
    if git rev-parse --git-dir > /dev/null 2>&1; then
        local branch=$(git rev-parse --abbrev-ref HEAD)
        local commit=$(git rev-parse --short HEAD)
        echo -e "${BLUE}Git:${NC}"
        echo -e "  分支: ${GREEN}${branch}${NC}"
        echo -e "  提交: ${DIM}${commit}${NC}"
        echo ""
    fi

    # Submodule 简要状态
    echo -e "${BLUE}Submodules:${NC}"
    git submodule status | head -5
    if [ "$(git submodule status | wc -l)" -gt 5 ]; then
        echo -e "${DIM}  ... 还有更多，运行 'submodule status' 查看完整列表${NC}"
    fi
    echo ""

    # 工作区状态
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        echo -e "${YELLOW}${INFO} 工作区有未提交的更改${NC}"
        echo ""
    fi
}

# ============================================================================
# 主程序
# ============================================================================

main() {
    # 检查是否在 Git 仓库中
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}${CROSS} 错误：当前目录不是 Git 仓库${NC}"
        exit 1
    fi

    # 切换到仓库根目录
    cd "$REPO_ROOT"

    # 解析全局选项
    VERBOSE=false
    FORCE=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                break
                ;;
        esac
    done

    # 获取命令
    local command="${1:-help}"
    shift || true

    # 执行命令
    case "$command" in
        # Submodule 命令
        submodule)
            local subcommand="${1:-status}"
            case "$subcommand" in
                status)
                    submodule_status
                    ;;
                switch)
                    submodule_switch
                    ;;
                init)
                    submodule_init
                    ;;
                update)
                    submodule_update
                    ;;
                bootstrap)
                    submodule_bootstrap
                    ;;
                fix-conflict|conflict)
                    submodule_fix_conflict
                    ;;
                cleanup)
                    submodule_cleanup
                    ;;
                *)
                    echo -e "${RED}${CROSS} 未知的 submodule 命令: $subcommand${NC}"
                    echo -e "运行 '$(basename "$0") --help' 查看可用命令"
                    exit 1
                    ;;
            esac
            ;;

        # 清理命令
        clean)
            clean_project
            ;;
        clean-deep)
            clean_deep
            ;;

        # 安全检查
        security-check|security)
            security_check
            ;;

        # Git Hooks
        setup-hooks|hooks)
            setup_hooks
            ;;

        # 诊断
        doctor)
            run_doctor
            ;;

        # 状态
        status)
            show_status
            ;;
        bootstrap)
            submodule_bootstrap
            ;;

        # 帮助
        help|--help|-h)
            show_help
            ;;

        *)
            echo -e "${RED}${CROSS} 未知命令: $command${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主程序
main "$@"
