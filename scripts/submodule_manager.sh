#!/bin/bash

# SAGE 子模块管理工具
# 用于独立管理 SAGE 项目的 Git 子模块

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 引入工具模块
source "$SCRIPT_DIR/logging.sh"
source "$SCRIPT_DIR/common_utils.sh"

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
    else
        print_error "无法获取子模块状态"
        return 1
    fi
}

# 初始化子模块
init_submodules() {
    print_header "🔧 初始化子模块"
    
    print_status "正在初始化子模块..."
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

# 主函数
main() {
    # 切换到仓库根目录
    cd "$REPO_ROOT"
    
    # 检查git仓库
    check_git_repo
    
    # 解析命令
    case "${1:-status}" in
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
