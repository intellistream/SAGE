#!/bin/bash

# SAGE 快速启动脚本
# 为新手开发者提供最简单且安全的项目初始化方式

set -e

# 获取脚本所在目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "脚本目录: $PROJECT_ROOT"

# 引入工具模块 - 优先使用Python工具，fallback到bash
# 总是加载bash工具作为基础
source "$PROJECT_ROOT/scripts/logging.sh"
source "$PROJECT_ROOT/scripts/common_utils.sh"
source "$PROJECT_ROOT/scripts/conda_utils.sh"

# 尝试加载Python增强工具
if [ -f "$PROJECT_ROOT/scripts/python_bridge.sh" ]; then
    source "$PROJECT_ROOT/scripts/python_bridge.sh"
    if check_python_helper; then
        print_status "使用Python增强工具"
        USE_PYTHON_TOOLS=true
    else
        print_warning "Python工具不可用，使用bash工具"
        USE_PYTHON_TOOLS=false
    fi
else
    print_warning "Python工具不可用，使用bash工具"
    USE_PYTHON_TOOLS=false
fi

# 全局变量
SELECTED_ENV_NAME=""
INSTALL_TYPE="quick"
INSTALL_MODE="development"
ARGS_PROVIDED=false
UPDATE_SUBMODULES=false

# 解析命令行参数
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dev|--development)
                INSTALL_MODE="development"
                ARGS_PROVIDED=true
                shift
                ;;
            --prod|--production)
                INSTALL_MODE="production"
                ARGS_PROVIDED=true
                shift
                ;;
            --reinstall)
                INSTALL_MODE="reinstall"
                ARGS_PROVIDED=true
                shift
                ;;
            --update-submodules)
                UPDATE_SUBMODULES=true
                ARGS_PROVIDED=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                echo "未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# 显示使用说明
show_usage() {
    echo "SAGE 快速启动脚本"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  --dev, --development   开发模式 (默认) - requirements-dev.txt"
    echo "  --prod, --production   生产模式 - requirements.txt (仅核心包)"
    echo "  --reinstall           重新安装模式 - 卸载并重新安装"
    echo "  --update-submodules   强制更新所有子模块"
    echo "  --help, -h            显示此帮助信息"
    echo
    echo "注意: 所有模式都使用 -e 开发安装，代码修改立即生效"
    echo
    echo "示例:"
    echo "  $0                    # 交互式选择 (默认开发模式)"
    echo "  $0 --dev            # 开发环境 (包含开发工具和前端)"
    echo "  $0 --prod           # 生产环境 (仅核心包)"
    echo "  $0 --reinstall      # 重新安装开发环境"
    echo "  $0 --update-submodules  # 更新所有子模块并安装"
}

# 进度显示函数
show_progress() {
    local current=$1
    local total=$2
    local message="$3"
    local width=50
    
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "\r["
    printf "%*s" $filled | tr ' ' '='
    printf "%*s" $empty | tr ' ' '-'
    printf "] %d%% %s" $percentage "$message"
    
    if [ $current -eq $total ]; then
        echo ""
    fi
}

# 检查环境名称是否已存在
check_existing_env() {
    local env_name="$1"
    
    if [ "$USE_PYTHON_TOOLS" = true ]; then
        py_check_conda_env "$env_name"
        return $?
    else
        # 原始bash方法
        if conda env list | grep -q "^$env_name "; then
            return 0  # 环境存在
        else
            return 1  # 环境不存在
        fi
    fi
}

# 选择安装模式
select_install_mode() {
    # 如果已经通过命令行参数设置了模式，显示选择并跳过交互
    if [ "$ARGS_PROVIDED" = true ]; then
        case "$INSTALL_MODE" in
            "development")
                print_status "使用开发模式安装 (requirements-dev.txt)"
                ;;
            "production")
                print_status "使用生产模式安装 (requirements.txt)"
                ;;
            "reinstall")
                print_status "使用重新安装模式 (requirements-dev.txt)"
                ;;
        esac
        return
    fi
    
    print_header "⚙️ 安装模式选择"
    
    echo "请选择SAGE安装模式："
    echo "  1) 开发模式 (推荐) - 包含开发工具和前端 (requirements-dev.txt)"
    echo "  2) 生产模式 - 仅核心包 (requirements.txt)"
    echo "  3) 重新安装 - 卸载现有包并重新安装开发环境"
    echo
    echo "💡 所有模式都使用 -e 开发安装，代码修改立即生效"
    echo
    
    while true; do
        echo -n "请选择安装模式 [1-3，默认: 1]: "
        read mode_choice
        
        # 使用默认值
        if [ -z "$mode_choice" ]; then
            mode_choice="1"
        fi
        
        case $mode_choice in
            1)
                INSTALL_MODE="development"
                print_success "选择了开发模式安装"
                break
                ;;
            2)
                INSTALL_MODE="production"
                print_success "选择了生产模式安装"
                break
                ;;
            3)
                INSTALL_MODE="reinstall"
                print_success "选择了重新安装模式"
                break
                ;;
            *)
                print_error "无效选择，请输入 1、2 或 3"
                ;;
        esac
    done
    echo
}

# 获取用户选择的环境名称
get_environment_name() {
    print_header "🌐 Conda 环境配置"
    
    echo "SAGE需要在独立的conda环境中运行以避免依赖冲突。"
    echo
    
    while true; do
        echo -n "请输入conda环境名称 [默认: sage]: "
        read env_name
        
        # 使用默认值
        if [ -z "$env_name" ]; then
            env_name="sage"
        fi
        
        # 验证环境名称格式
        if [[ ! "$env_name" =~ ^[a-zA-Z][a-zA-Z0-9_-]*$ ]]; then
            print_error "环境名称格式无效。请使用字母开头，只包含字母、数字、下划线和连字符。"
            continue
        fi
        
        # 检查环境是否已存在
        if check_existing_env "$env_name"; then
            print_warning "⚠️  Conda环境 '$env_name' 已存在！"
            echo
            echo "如果继续，以下操作将被执行："
            echo "  • 现有环境将被保留"
            echo "  • 新的依赖包将安装到现有环境中"
            echo "  • 这可能会覆盖或更新现有的包版本"
            echo "  • 可能会导致版本冲突或依赖问题"
            echo
            echo "选项："
            echo "  1) 继续使用现有环境 (可能有风险)"
            echo "  2) 重新选择环境名称"
            echo "  3) 删除现有环境并重新创建"
            echo "  4) 退出安装"
            echo
            
            while true; do
                echo -n "请选择 [1-4]: "
                read choice
                
                case $choice in
                    1)
                        print_warning "将使用现有环境 '$env_name'"
                        SELECTED_ENV_NAME="$env_name"
                        return 0
                        ;;
                    2)
                        break  # 回到外层循环重新输入名称
                        ;;
                    3)
                        print_status "删除现有环境 '$env_name'..."
                        if conda env remove -n "$env_name" -y; then
                            print_success "环境删除成功"
                            SELECTED_ENV_NAME="$env_name"
                            return 0
                        else
                            print_error "环境删除失败"
                            continue
                        fi
                        ;;
                    4)
                        print_status "安装已取消"
                        exit 0
                        ;;
                    *)
                        print_error "无效选择，请输入 1-4"
                        ;;
                esac
            done
        else
            print_success "环境名称 '$env_name' 可用"
            SELECTED_ENV_NAME="$env_name"
            return 0
        fi
    done
}

# 带进度的包安装函数
install_packages_with_progress() {
    local env_name="$1"
    shift
    local packages=("$@")
    local total=${#packages[@]}
    
    print_status "安装Python包到环境 '$env_name'..."
    
    for i in "${!packages[@]}"; do
        local pkg="${packages[$i]}"
        local current=$((i + 1))
        
        show_progress $current $total "安装 $pkg..."
        
        if ! conda install -n "$env_name" -c conda-forge "$pkg" -y >/dev/null 2>&1; then
            echo
            print_warning "使用conda安装 '$pkg' 失败，尝试使用pip..."
            if ! conda run -n "$env_name" pip install "$pkg" >/dev/null 2>&1; then
                echo
                print_error "安装 '$pkg' 失败"
                return 1
            fi
        fi
    done
    
    echo
    print_success "所有包安装完成"
}

# 创建环境并安装基础依赖
setup_enhanced_sage_environment() {
    local env_name="$1"
    local python_version="${2:-3.11}"
    
    print_header "🛠️ 设置SAGE开发环境: $env_name"
    
    # 初始化conda
    print_status "初始化conda..."
    if ! init_conda; then
        print_error "Conda初始化失败"
        return 1
    fi
    
    # 如果环境不存在，创建它
    if ! check_existing_env "$env_name"; then
        print_status "创建conda环境 '$env_name' (Python $python_version)..."
        if ! conda create -n "$env_name" python="$python_version" -y; then
            print_error "环境创建失败"
            return 1
        fi
        print_success "环境创建完成"
    fi
    
    # 定义基础包列表
    local base_packages=(
        "pip"
        "setuptools" 
        "wheel"
        "build"
        "numpy"
        "pandas"
        "matplotlib"
        "jupyter"
        "notebook"
    )
    
    # 安装基础包
    if ! install_packages_with_progress "$env_name" "${base_packages[@]}"; then
        print_error "基础包安装失败"
        return 1
    fi
    
    print_success "SAGE环境 '$env_name' 设置完成"
    return 0
}

# 安装SAGE包的函数（使用requirements文件）
install_sage_packages() {
    local install_type="$1"
    
    print_header "📦 安装 SAGE 包到环境: $SELECTED_ENV_NAME"
    
    # 激活环境
    print_status "激活conda环境 '$SELECTED_ENV_NAME'..."
    if ! activate_conda_env "$SELECTED_ENV_NAME"; then
        print_error "无法激活环境 '$SELECTED_ENV_NAME'"
        return 1
    fi
    
    # 如果是重新安装模式，先卸载现有包
    if [ "$INSTALL_MODE" = "reinstall" ]; then
        print_status "卸载现有SAGE包..."
        conda run -n "$SELECTED_ENV_NAME" pip uninstall -y isage isage-kernel isage-middleware isage-apps isage-common 2>/dev/null || true
        print_success "卸载完成"
    fi
    
    # 选择合适的requirements文件
    local requirements_file="$PROJECT_ROOT/scripts/requirements/requirements-dev.txt"
    if [ "$INSTALL_MODE" = "production" ]; then
        requirements_file="$PROJECT_ROOT/scripts/requirements/requirements.txt"
    fi
    
    print_status "使用requirements文件: $(basename $requirements_file)"
    print_status "安装SAGE包 (开发模式: -e)..."
    
    # 显示要安装的SAGE核心组件
    echo "将要安装的SAGE核心组件:"
    echo "  • sage-common: 通用工具库和CLI工具"
    echo "  • sage-kernel: 核心计算引擎"
    echo "  • sage-middleware: 中间件和API服务"
    echo "  • sage-apps: 应用示例和模板"
    echo "  • sage: 主包（元包）"
    if [ "$INSTALL_MODE" = "development" ] || [ "$INSTALL_MODE" = "reinstall" ]; then
        echo "  • 开发工具: 包含dev和frontend扩展"
    fi
    echo
    
    # 统计实际的包数量
    local packages=($(cat "$requirements_file" | grep -E "^-e" | wc -l))
    local total=5  # sage-common, sage-kernel, sage-middleware, sage-apps, sage
    
    print_status "开始安装过程..."
    
    echo "总共需要安装 $total 个SAGE包组件"
    
    if conda run -n "$SELECTED_ENV_NAME" pip install -r "$requirements_file"; then
        print_success "所有SAGE包安装完成"
        
        # 显示安装模式信息
        case "$INSTALL_MODE" in
            "development"|"reinstall")
                print_status "✅ 开发模式安装完成 - 源码修改将立即生效"
                ;;
            "production")
                print_status "✅ 生产模式安装完成"
                ;;
        esac
        return 0
    else
        print_error "SAGE包安装失败"
        return 1
    fi
}

# 修改主流程
main() {
    print_header "🚀 SAGE 项目快速启动"
    
    # 欢迎信息
    print_success "欢迎使用 SAGE (Streaming Analytics and Graph Engine)"
    echo "这个脚本将帮助您快速设置SAGE开发环境。"
    echo
    
    # 0. 选择安装模式
    select_install_mode
    
    # 1. 获取环境名称
    get_environment_name
    
    # 2. 检查基础依赖
    print_header "🔍 检查系统依赖"
    check_dependencies
    
    # 3. 初始化和更新子模块
    initialize_submodules
    
    # 4. 安装Miniconda（如果需要）
    if ! is_conda_installed; then
        if ! install_miniconda; then
            print_error "Miniconda安装失败"
            exit 1
        fi
    else
        print_success "Conda已安装"
    fi
    
    # 5. 设置SAGE环境
    if ! setup_enhanced_sage_environment "$SELECTED_ENV_NAME"; then
        print_error "SAGE环境设置失败"
        exit 1
    fi
    
    # 6. 安装SAGE包
    if ! install_sage_packages "$INSTALL_TYPE"; then
        print_error "SAGE包安装失败"
        exit 1
    fi
    
    # 7. 验证安装
    print_header "✅ 验证安装"
    verify_installation
    
    # 8. 显示完成信息
    show_completion_info
}

# 验证安装函数
verify_installation() {
    print_status "验证SAGE安装..."
    
    if conda run -n "$SELECTED_ENV_NAME" python -c "import sage; print('✅ SAGE主包导入成功')" 2>/dev/null; then
        print_success "SAGE主包验证通过"
    else
        print_warning "SAGE主包导入有警告（可能是正常的）"
    fi
    
    # 验证子模块状态
    verify_submodules
}

# 验证子模块状态
verify_submodules() {
    print_status "验证子模块状态..."
    
    if [ ! -f "$PROJECT_ROOT/.gitmodules" ]; then
        print_warning "未发现子模块配置"
        return 0
    fi
    
    # 检查docs-public子模块
    if [ -d "$PROJECT_ROOT/docs-public" ]; then
        local doc_count=$(find "$PROJECT_ROOT/docs-public" -name "*.md" -type f | wc -l)
        if [ "$doc_count" -gt 0 ]; then
            print_success "docs-public 子模块包含 $doc_count 个文档文件"
            
            # 检查是否有示例
            if [ -d "$PROJECT_ROOT/docs-public/simple_examples" ]; then
                local example_count=$(find "$PROJECT_ROOT/docs-public/simple_examples" -name "*.py" -type f | wc -l)
                print_success "发现 $example_count 个示例文件"
            fi
        else
            print_warning "docs-public 目录存在但内容为空"
        fi
    else
        print_warning "docs-public 子模块目录不存在"
        echo "  可以手动初始化: git submodule update --init docs-public"
    fi
}

# 显示完成信息
show_completion_info() {
    print_header "🎉 安装完成！"
    
    echo "SAGE已成功安装到conda环境: $SELECTED_ENV_NAME"
    echo
    echo "🚀 可用的SAGE命令："
    echo "  sage --help                   # 查看所有可用命令"
    echo "  sage version                  # 查看版本信息"
    echo "  sage doctor                   # 系统诊断和健康检查"
    echo "  sage config show              # 查看当前配置"
    echo "  sage jobmanager start         # 启动作业管理器"
    echo "  sage-jobmanager status        # 检查JobManager状态"
    echo "  sage-server --help            # Web服务器帮助"
    echo "  sage-dev --help               # 开发工具帮助"
    echo "  sage-examples --help          # 应用示例帮助"
    echo
    echo "📋 下一步操作："
    echo "  1. 激活环境:    conda activate $SELECTED_ENV_NAME"
    echo "  2. 验证安装:    sage version"
    echo "  3. 启动服务:    sage jobmanager start"
    echo "  4. 运行诊断:    sage doctor"
    echo "  5. 查看示例:    sage-examples list"
    echo
    echo "🌐 Web界面 (可选)："
    echo "  sage-server start             # 启动Web界面 (需要frontend依赖)"
    echo "  sage server-info              # 查看Web服务器信息"
    echo
    echo "📚 文档和示例："
    echo "  • 在线文档: https://intellistream.github.io/SAGE-Pub/"
    if [ -d "$PROJECT_ROOT/docs-public" ]; then
        echo "  • 本地文档: cd docs-public && mkdocs serve"
        echo "  • 示例代码: 查看 docs-public/simple_examples/ 目录"
        echo "  • 文档同步: tools/sync_docs.sh (开发者使用)"
    else
        echo "  • 本地文档: 需要先初始化docs-public子模块"
        echo "    git submodule update --init docs-public"
    fi
    echo "  • CLI帮助: sage --help 或 sage <command> --help"
    echo
    print_success "欢迎开始您的SAGE之旅！ 🚀"
}

# 初始化和更新子模块
initialize_submodules() {
    print_header "📚 初始化 Git 子模块"
    
    # 检查是否在git仓库中
    if [ ! -d "$PROJECT_ROOT/.git" ]; then
        print_warning "当前目录不是git仓库，跳过子模块初始化"
        return 0
    fi
    
    # 检查是否有.gitmodules文件
    if [ ! -f "$PROJECT_ROOT/.gitmodules" ]; then
        print_warning "未找到.gitmodules文件，跳过子模块初始化"
        return 0
    fi
    
    print_status "检测到子模块配置，开始初始化..."
    
    # 如果指定了强制更新，先清理子模块
    if [ "$UPDATE_SUBMODULES" = true ]; then
        print_status "强制更新模式：重新初始化所有子模块..."
        git submodule deinit --all -f || true
    fi
    
    # 初始化子模块
    if git submodule init; then
        print_success "子模块初始化完成"
    else
        print_error "子模块初始化失败"
        return 1
    fi
    
    # 更新子模块
    print_status "更新子模块内容..."
    local update_flags="--recursive"
    if [ "$UPDATE_SUBMODULES" = true ]; then
        update_flags="--init --recursive --force"
    fi
    
    if git submodule update $update_flags; then
        print_success "子模块更新完成"
        
        # 特别检查docs-public子模块
        if [ -d "$PROJECT_ROOT/docs-public" ]; then
            print_status "✅ docs-public 子模块已就绪"
            
            # 检查docs-public的内容
            local doc_files=$(find "$PROJECT_ROOT/docs-public" -type f -name "*.md" | wc -l)
            if [ "$doc_files" -gt 0 ]; then
                print_success "docs-public 包含 $doc_files 个文档文件"
            else
                print_warning "docs-public 目录为空，可能需要手动同步"
            fi
        else
            print_warning "docs-public 子模块目录不存在"
        fi
    else
        print_error "子模块更新失败"
        
        # 提供故障排除建议
        echo
        print_warning "子模块更新失败的可能原因："
        echo "  • 网络连接问题"
        echo "  • 没有访问子模块仓库的权限"
        echo "  • 子模块URL配置错误"
        echo
        echo "解决方案："
        echo "  1. 检查网络连接: ping github.com"
        echo "  2. 手动更新: git submodule update --init --recursive"
        echo "  3. 检查权限: git submodule foreach git remote -v"
        echo "  4. 强制更新: $0 --update-submodules"
        echo
        
        # 询问是否继续
        echo -n "是否继续安装(忽略子模块)? [y/N]: "
        read continue_choice
        if [[ ! "$continue_choice" =~ ^[Yy]$ ]]; then
            print_status "安装已取消"
            exit 1
        fi
        
        print_warning "继续安装，但docs-public子模块未更新"
        return 0
    fi
    
    # 显示子模块状态
    print_status "子模块状态："
    git submodule status | while read line; do
        echo "  $line"
    done
    
    return 0
}

# 检查基础依赖
check_dependencies() {
    print_status "检查系统依赖..."
    
    if [ "$USE_PYTHON_TOOLS" = true ]; then
        # 使用Python增强检查
        local result=$(py_check_system)
        if [[ "$result" == SUCCESS:* ]]; then
            print_success "✅ 系统依赖检查通过"
            return 0
        else
            print_error "系统依赖检查失败:"
            if [[ "$result" == ERRORS:* ]]; then
                local errors="${result#ERRORS:}"
                IFS=',' read -ra error_array <<< "$errors"
                for error in "${error_array[@]}"; do
                    echo "  • $error"
                done
            fi
            echo
            echo "请安装这些依赖后重新运行脚本。"
            exit 1
        fi
    else
        # 原始bash检查
        local missing_deps=()
        
        if ! command -v git >/dev/null 2>&1; then
            missing_deps+=("git")
        fi
        
        if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
            missing_deps+=("curl 或 wget")
        fi
        
        if [ ${#missing_deps[@]} -gt 0 ]; then
            print_error "缺少必要的系统依赖:"
            for dep in "${missing_deps[@]}"; do
                echo "  • $dep"
            done
            echo
            echo "请安装这些依赖后重新运行脚本。"
            exit 1
        fi
        
        print_success "✅ 系统依赖检查通过"
    fi
    
    print_success "系统依赖检查通过"
}

# 运行主程序
parse_arguments "$@"
main
