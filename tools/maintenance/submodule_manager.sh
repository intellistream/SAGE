#!/bin/bash

# SAGE 子模块管理工具
# 用于独立管理 SAGE 项目的 Git 子模块

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 引入工具模块（使用绝对路径，保证从任意目录执行）
source "$SCRIPT_DIR/../utils/logging.sh"
source "$SCRIPT_DIR/../utils/common_utils.sh"

# 显示使用说明
show_usage() {
    echo "SAGE 子模块管理工具"
    echo
    echo "用法: $0 [命令]"
    echo
    echo "命令:"
    echo "  init              初始化所有子模块"
    echo "  update            更新所有子模块到最新版本"
    echo "  reset             重置所有子模块（强制重新下载）"
    echo "  status            显示子模块状态"
    echo "  sync              同步子模块URL配置"
    echo "  clean             清理未跟踪的子模块文件"
    echo "  docs-update       专门更新docs-public子模块"
    # 以下命令已内置到常规流程，不再单独展示：repair-sage-db / clean-legacy-sage-db / migrate-sage-db
    echo "  help, -h, --help  显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0 status         # 查看当前子模块状态"
    echo "  $0 init          # 初始化所有子模块"
    echo "  $0 update        # 更新到最新版本"
    echo "  $0 reset         # 强制重置所有子模块"
    echo "  $0 docs-update   # 只更新文档子模块"
}

# 检查是否在git仓库中
check_git_repo() {
    if [ ! -d "$REPO_ROOT/.git" ]; then
        print_error "错误：当前目录不是git仓库"
        exit 1
    fi
    
    if [ ! -f "$REPO_ROOT/.gitmodules" ]; then
        print_warning "未找到.gitmodules文件"
        echo "当前项目没有配置任何子模块。"
        exit 0
    fi
}

# 显示子模块状态
show_submodule_status() {
    print_header "📊 子模块状态"
    
    if git submodule status; then
        echo
        print_status "子模块详细信息："
        git submodule foreach 'echo "  模块: $name | 路径: $sm_path | URL: $(git remote get-url origin)"'

        # 如果 .gitmodules 声明了 sage_db，但索引中不是 gitlink，给出提示
        local sd_path="packages/sage-middleware/src/sage/middleware/components/sage_db"
        if git config -f .gitmodules --get "submodule.${sd_path}.path" >/dev/null 2>&1; then
            if ! git ls-files -s -- "$sd_path" 2>/dev/null | grep -q "^160000 "; then
                echo
                print_warning "检测到 $sd_path 未以子模块形式注册（可能被当作普通目录或被删除）。"
                print_status "运行: $0 update  将自动修复并恢复为子模块。"
            fi
        fi
    else
        print_error "无法获取子模块状态"
        return 1
    fi
}

# 初始化子模块
init_submodules() {
    print_header "🔧 初始化子模块"
    
    print_status "正在初始化子模块..."
    # 在初始化前确保 sage_db 路径为子模块（防止目录/子模块混淆）
    ensure_sage_db_submodule || true
    if git submodule init; then
        print_success "子模块初始化完成"
        
        print_status "正在下载子模块内容..."
        if git submodule update; then
            print_success "子模块内容下载完成"
        else
            print_error "子模块内容下载失败"
            return 1
        fi
    else
        print_error "子模块初始化失败"
        return 1
    fi
}

# 更新子模块
update_submodules() {
    print_header "🔄 更新子模块"
    
    print_status "正在更新所有子模块到最新版本..."
    # 在更新前自动修复 sage_db 状态
    ensure_sage_db_submodule || true
    if git submodule update --recursive --remote; then
        print_success "所有子模块更新完成"
        
        # 显示更新后的状态
        echo
        show_submodule_status
    else
        print_error "子模块更新失败"
        return 1
    fi
}

# 重置子模块
reset_submodules() {
    print_header "🔄 重置子模块"
    
    print_warning "这将强制重新下载所有子模块，本地未提交的更改将丢失！"
    echo -n "确定要继续吗？ [y/N]: "
    read -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "操作已取消"
        return 0
    fi
    
    print_status "正在重置子模块..."
    
    # 清理子模块
    if git submodule deinit --all -f; then
        print_success "子模块清理完成"
    else
        print_warning "子模块清理部分失败，继续..."
    fi
    
    # 重置前修复 sage_db 的路径形态（避免目录/子模块形态不一致）
    ensure_sage_db_submodule || true

    # 重新初始化
    if git submodule update --init --recursive --force; then
        print_success "子模块重置完成"
    else
        print_error "子模块重置失败"
        return 1
    fi
}

# 同步子模块URL
sync_submodules() {
    print_header "🔗 同步子模块URL"
    
    print_status "正在同步子模块URL配置..."
    if git submodule sync --recursive; then
        print_success "子模块URL同步完成"
    else
        print_error "子模块URL同步失败"
        return 1
    fi
}

# 清理子模块
clean_submodules() {
    print_header "🧹 清理子模块"
    
    print_status "正在清理未跟踪的子模块文件..."
    git submodule foreach 'git clean -fd' || true
    print_success "子模块清理完成"
}

# 专门更新docs-public子模块
update_docs_submodule() {
    print_header "📚 更新 docs-public 子模块"
    
    if [ ! -d "$REPO_ROOT/docs-public" ]; then
        print_warning "docs-public 子模块不存在，尝试初始化..."
        if git submodule update --init docs-public; then
            print_success "docs-public 子模块初始化完成"
        else
            print_error "docs-public 子模块初始化失败"
            return 1
        fi
    fi
    
    print_status "正在更新 docs-public 到最新版本..."
    if git submodule update --remote docs-public; then
        print_success "docs-public 更新完成"
        
        # 显示文档统计
        local doc_count=$(find "$REPO_ROOT/docs-public" -name "*.md" -type f | wc -l)
        local example_count=$(find "$REPO_ROOT/docs-public/simple_examples" -name "*.py" -type f 2>/dev/null | wc -l)
        
        print_status "文档统计："
        echo "  • Markdown文档: $doc_count 个"
        echo "  • 示例代码: $example_count 个"
        
        # 检查是否可以构建文档
        if [ -f "$REPO_ROOT/docs-public/requirements.txt" ]; then
            echo
            print_status "💡 构建本地文档："
            echo "  cd docs-public && pip install -r requirements.txt && mkdocs serve"
        fi
    else
        print_error "docs-public 更新失败"
        return 1
    fi
}

# 确保 sage_db 为真正的 Git 子模块（修复常见的目录/子模块冲突）
ensure_sage_db_submodule() {
    local path="packages/sage-middleware/src/sage/middleware/components/sage_db"
    local name="packages/sage-middleware/src/sage/middleware/components/sage_db"
    local url branch

    print_header "🧩 修复/确保 sage_db 为 Git 子模块"

    # 从 .gitmodules 读取 URL/branch，若缺失则给默认值
    if [ -f .gitmodules ]; then
        url=$(git config -f .gitmodules --get "submodule.${name}.url" || true)
        branch=$(git config -f .gitmodules --get "submodule.${name}.branch" || true)
    fi
    : "${url:=https://github.com/intellistream/sageDB.git}"
    : "${branch:=main}"

    print_status "目标路径: $path"
    print_status "远程URL:  $url (branch: $branch)"

    # 如果索引中是 gitlink (160000)，说明已经是子模块
    if git ls-files -s -- "$path" 2>/dev/null | grep -q "^160000 "; then
        print_success "已检测到 $path 为有效子模块"
        print_status "执行初始化/更新..."
        git submodule sync -- "$path" || true
        git submodule update --init --recursive -- "$path"
        return 0
    fi

    # 若不是 gitlink，则可能是普通文件/目录或不存在
    print_warning "检测到 $path 不是子模块 (可能是普通目录或不存在)，开始修复..."

    # 若存在旧的子模块绑定，先反初始化
    git submodule deinit -f -- "$path" >/dev/null 2>&1 || true

    # 若该路径下有已跟踪的普通文件，从索引中移除（保留工作区文件）
    if git ls-files -- "$path" >/dev/null 2>&1 && [ -n "$(git ls-files -- "$path")" ]; then
        print_status "从索引中移除已跟踪的普通文件 (不删除工作区)：$path"
        git rm -r --cached "$path" || true
    fi

    # 清理可能残留的 .git/modules 记录
    if [ -d ".git/modules/$path" ]; then
        print_status "清理残留的 .git/modules/$path"
        rm -rf ".git/modules/$path"
    fi

    # 删除工作区目录，准备重新添加为子模块
    if [ -d "$path" ] || [ -f "$path" ]; then
        print_status "删除工作区的旧目录/文件：$path"
        rm -rf "$path"
    fi

    # 确保父目录存在
    mkdir -p "$(dirname "$path")"

    # 添加为子模块
    print_status "添加子模块：git submodule add -b $branch $url $path"
    if git submodule add -f -b "$branch" "$url" "$path"; then
        print_success "子模块添加成功"
    else
        print_error "子模块添加失败，请检查网络/权限/URL"
        return 1
    fi

    # 初始化并更新
    print_status "初始化并更新子模块内容..."
    git submodule update --init --recursive -- "$path"

    print_success "sage_db 子模块修复完成"
    print_status "现在可以运行: git submodule status"
}

# 主函数
main() {
    # 切换到仓库根目录
    cd "$REPO_ROOT"
    
    # 解析命令（默认显示状态）
    CMD="${1:-status}"

    # 基础检查：必须是git仓库（help除外）
    if [[ "$CMD" != "help" && "$CMD" != "-h" && "$CMD" != "--help" ]]; then
        if [ ! -d "$REPO_ROOT/.git" ]; then
            print_error "错误：当前目录不是git仓库"
            exit 1
        fi
    fi

    # 针对需要.gitmodules的命令进行特殊检查
    REQUIRES_GITMODULES=(init update reset status sync clean docs-update)
    for need in "${REQUIRES_GITMODULES[@]}"; do
        if [[ "$CMD" == "$need" ]]; then
            if [ ! -f "$REPO_ROOT/.gitmodules" ]; then
                print_warning "未找到 .gitmodules，命令 '$CMD' 无可操作的子模块"
                print_status "如需添加子模块，请先执行: git submodule add <URL> <PATH>"
                exit 0
            fi
            break
        fi
    done

    # 执行命令
    case "$CMD" in
        "init")
            init_submodules
            ;;
        "update")
            update_submodules
            ;;
        "reset")
            reset_submodules
            ;;
        "status")
            show_submodule_status
            ;;
        "sync")
            sync_submodules
            ;;
        "clean")
            clean_submodules
            ;;
        "docs-update")
            update_docs_submodule
            ;;
        "repair-sage-db")
            # 单独修复/确保 sage_db 为子模块
            check_git_repo
            ensure_sage_db_submodule
            ;;
        "clean-legacy-sage-db")
            shift || true
            CLEAN_FORCE="false"
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    -y|--yes)
                        CLEAN_FORCE="true"; shift ;;
                    *) break ;;
                esac
            done
            legacy_dir="packages/sage-middleware/src/sage/middleware/components/sage_db"
            if [[ -d "$legacy_dir" ]]; then
                print_header "🧹 清理旧版内置 sage_db 目录"
                if [[ "$CLEAN_FORCE" != "true" ]]; then
                    print_warning "即将删除 $legacy_dir。该目录应已迁移为子模块。"
                    echo -n "确定要删除吗？ [y/N]: "
                    read -r ans
                    if [[ ! $ans =~ ^[Yy]$ ]]; then
                        print_status "已取消清理"
                        exit 0
                    fi
                fi
                # 保护：如果是子模块路径则禁止直接rm -rf
                if git ls-files --stage | grep -q "\s$legacy_dir$"; then
                    if git submodule status -- "$legacy_dir" >/dev/null 2>&1; then
                        print_error "检测到 $legacy_dir 是子模块，请不要直接删除。"
                        print_status "可使用: git submodule deinit -f -- $legacy_dir && rm -rf .git/modules/$legacy_dir && git rm -f $legacy_dir"
                        exit 1
                    fi
                fi
                rm -rf "$legacy_dir"
                print_success "已删除旧目录: $legacy_dir"
            else
                print_status "未发现旧目录 (无需清理): $legacy_dir"
            fi
            ;;
        "migrate-sage-db")
            # 迁移流程：清理旧目录 -> 同步/初始化子模块 -> 拉取最新
            print_header "🚚 迁移 sage_db 到 Git 子模块"
            "$0" clean-legacy-sage-db -y || true
            print_status "同步子模块配置 (.gitmodules)"
            git submodule sync --recursive
            print_status "修复/确保 sage_db 为 Git 子模块"
            ensure_sage_db_submodule
            print_status "初始化并更新所有子模块"
            git submodule update --init --recursive || true
            print_success "迁移完成。可执行: git submodule status"
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "未知命令: $1"
            echo
            show_usage
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
