#!/bin/bash
# SAGE 一键测试启动脚本
# 这是 run_all_tests.py 的简化bash版本，提供快速访问功能

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_ROOT=$(pwd)
VENV_PATH="$PROJECT_ROOT/test_env"
TEST_LOGS_DIR="$PROJECT_ROOT/test_logs"
REPORTS_DIR="$PROJECT_ROOT/test_reports"

# 创建必要目录
mkdir -p "$TEST_LOGS_DIR" "$REPORTS_DIR"

# 打印格式化标题
print_header() {
    echo -e "\n${BLUE}======================================${NC}"
    echo -e "${CYAN}🚀 $1${NC}"
    echo -e "${BLUE}======================================${NC}"
}

print_section() {
    echo -e "\n${YELLOW}📋 $1${NC}"
    echo -e "${YELLOW}$(printf '%.40s' "----------------------------------------")${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 激活虚拟环境的函数
activate_venv() {
    if [ -f "$VENV_PATH/bin/activate" ]; then
        source "$VENV_PATH/bin/activate"
        return 0
    else
        print_error "虚拟环境不存在: $VENV_PATH"
        return 1
    fi
}

# 环境检查
check_environment() {
    print_section "环境检查"
    
    local all_ok=true
    
    # 检查虚拟环境
    if [ -d "$VENV_PATH" ]; then
        print_success "虚拟环境存在"
    else
        print_error "虚拟环境不存在"
        all_ok=false
    fi
    
    # 检查Python版本
    if activate_venv; then
        local python_version=$(python --version 2>&1)
        if [[ $python_version == *"3.11"* ]]; then
            print_success "Python版本: $python_version"
        else
            print_error "Python版本不符合要求: $python_version"
            all_ok=false
        fi
    else
        all_ok=false
    fi
    
    # 检查关键依赖
    local packages=("pytest" "torch" "ray" "fastapi")
    if activate_venv; then
        local installed_packages=$(pip list 2>/dev/null)
        for package in "${packages[@]}"; do
            if echo "$installed_packages" | grep -i "$package" > /dev/null; then
                print_success "$package 已安装"
            else
                print_error "$package 未安装"
                all_ok=false
            fi
        done
    fi
    
    # 检查测试运行器
    if [ -f "scripts/test_runner.py" ]; then
        print_success "测试运行器存在"
    else
        print_error "测试运行器不存在"
        all_ok=false
    fi
    
    # 检查act工具
    if command -v act &> /dev/null; then
        local act_version=$(act --version 2>&1)
        print_success "Act工具可用: $act_version"
    else
        print_error "Act工具不可用"
        all_ok=false
    fi
    
    if [ "$all_ok" = true ]; then
        print_success "所有环境检查通过！"
        return 0
    else
        print_error "环境检查发现问题，请修复后重试"
        return 1
    fi
}

# 设置环境
setup_environment() {
    print_section "环境设置"
    
    # 创建虚拟环境
    if [ ! -d "$VENV_PATH" ]; then
        print_info "创建虚拟环境..."
        python3 -m venv test_env
        if [ $? -eq 0 ]; then
            print_success "虚拟环境创建成功"
        else
            print_error "虚拟环境创建失败"
            return 1
        fi
    fi
    
    # 激活并安装依赖
    print_info "激活虚拟环境并安装依赖..."
    if activate_venv; then
        pip install -e .
        if [ $? -eq 0 ]; then
            print_success "依赖安装成功"
            return 0
        else
            print_error "依赖安装失败"
            return 1
        fi
    else
        return 1
    fi
}

# 快速测试
run_quick_tests() {
    print_section "快速测试模式"
    
    if ! activate_venv; then
        return 1
    fi
    
    print_info "运行智能差异测试..."
    python scripts/test_runner.py --diff
    
    print_info "列出所有测试文件..."
    python scripts/test_runner.py --list
}

# 完整测试
run_full_tests() {
    local workers=${1:-4}
    print_section "完整测试套件 (使用 $workers 个并行进程)"
    
    if ! activate_venv; then
        return 1
    fi
    
    print_info "运行所有测试..."
    local start_time=$(date +%s)
    
    python scripts/test_runner.py --all --workers "$workers"
    local test_result=$?
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ $test_result -eq 0 ]; then
        print_success "测试完成，耗时: ${duration}秒"
    else
        print_error "测试执行失败"
    fi
    
    return $test_result
}

# GitHub Actions 模拟
simulate_github_actions() {
    print_section "GitHub Actions 本地模拟"
    
    # 检查工作流文件
    if [ -d ".github/workflows" ]; then
        local workflow_count=$(find .github/workflows -name "*.yml" | wc -l)
        print_info "发现 $workflow_count 个工作流文件:"
        find .github/workflows -name "*.yml" -exec basename {} \; | sed 's/^/  - /'
    fi
    
    # 列出可用工作流
    print_info "列出可用的GitHub Actions..."
    if command -v act &> /dev/null; then
        act --list
        
        print_info "模拟CI工作流 (干运行)..."
        act -n --workflows .github/workflows/ci.yml 2>/dev/null || {
            print_error "GitHub Actions模拟失败（可能是Docker连接问题）"
            return 1
        }
    else
        print_error "Act工具不可用，无法模拟GitHub Actions"
        return 1
    fi
}

# 生成测试报告
generate_report() {
    print_section "生成测试报告"
    
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local report_file="$REPORTS_DIR/test_report_$timestamp.md"
    
    # 统计测试日志
    local log_count=0
    local passed_count=0
    local failed_count=0
    
    if [ -d "$TEST_LOGS_DIR" ]; then
        log_count=$(find "$TEST_LOGS_DIR" -name "*.log" | wc -l)
        
        # 简单统计通过/失败的测试
        for log_file in "$TEST_LOGS_DIR"/*.log; do
            if [ -f "$log_file" ]; then
                if grep -q "PASSED" "$log_file" && ! grep -q "FAILED" "$log_file"; then
                    ((passed_count++))
                elif grep -q "FAILED" "$log_file"; then
                    ((failed_count++))
                fi
            fi
        done
    fi
    
    local success_rate=0
    if [ $log_count -gt 0 ]; then
        success_rate=$((passed_count * 100 / log_count))
    fi
    
    # 生成报告
    cat > "$report_file" << EOF
# SAGE 测试报告

## 📊 执行概览
- **生成时间**: $(date "+%Y-%m-%d %H:%M:%S")
- **项目路径**: $PROJECT_ROOT
- **测试日志数量**: $log_count
- **通过测试**: $passed_count
- **失败测试**: $failed_count
- **成功率**: ${success_rate}%

## 🏗️ 环境信息
- **Python版本**: $(python --version 2>&1 || echo "未知")
- **虚拟环境**: $VENV_PATH
- **CPU核心数**: $(nproc)
- **内存使用**: $(free -h | grep '^Mem:' | awk '{print $3 "/" $2}')
- **磁盘空间**: $(df -h . | tail -1 | awk '{print $4}') 可用

## 📈 最新测试日志
EOF
    
    # 添加最新的几个日志文件
    if [ -d "$TEST_LOGS_DIR" ]; then
        echo "### 最新日志文件:" >> "$report_file"
        ls -lt "$TEST_LOGS_DIR"/*.log 2>/dev/null | head -5 | while read line; do
            echo "- $line" >> "$report_file"
        done
    fi
    
    cat >> "$report_file" << EOF

## 📋 推荐操作
1. 检查失败的测试日志: \`ls -la test_logs/\`
2. 重新运行失败的测试: \`./quick_test.sh --diff\`
3. 查看详细日志: \`cat test_logs/specific_test.log\`
4. 运行完整测试: \`./quick_test.sh --full\`

---
*报告由 SAGE 测试自动化系统生成*
EOF
    
    print_success "测试报告已生成: $report_file"
    echo "$report_file"
}

# 交互式菜单
interactive_menu() {
    while true; do
        print_header "SAGE 测试自动化 - 交互式菜单"
        
        echo "请选择操作:"
        echo "1. 🔍 环境检查"
        echo "2. ⚡ 快速测试"
        echo "3. 🚀 完整测试"
        echo "4. 🎯 智能差异测试"
        echo "5. 🎭 GitHub Actions 模拟"
        echo "6. 📊 生成测试报告"
        echo "7. 🛠️ 设置环境"
        echo "8. 📋 查看测试日志"
        echo "0. 🚪 退出"
        
        read -p $'\n请输入选择 (0-8): ' choice
        
        case $choice in
            0)
                echo "👋 再见！"
                break
                ;;
            1)
                check_environment
                ;;
            2)
                run_quick_tests
                ;;
            3)
                read -p "请输入并行进程数 (默认4): " workers
                workers=${workers:-4}
                run_full_tests "$workers"
                ;;
            4)
                if activate_venv; then
                    python scripts/test_runner.py --diff
                fi
                ;;
            5)
                simulate_github_actions
                ;;
            6)
                generate_report
                ;;
            7)
                setup_environment
                ;;
            8)
                if [ -d "$TEST_LOGS_DIR" ]; then
                    print_info "最新的测试日志:"
                    ls -lt "$TEST_LOGS_DIR"/*.log 2>/dev/null | head -10
                else
                    print_error "测试日志目录不存在"
                fi
                ;;
            *)
                print_error "无效选择，请重试"
                ;;
        esac
        
        echo -e "\n按Enter键继续..."
        read
    done
}

# 显示帮助信息
show_help() {
    cat << EOF
SAGE 一键测试启动脚本

用法: $0 [选项]

选项:
    --check          环境检查
    --setup          设置测试环境
    --quick          快速测试模式
    --full           完整测试套件
    --diff           智能差异测试
    --github         GitHub Actions 模拟
    --report         生成测试报告
    --interactive    交互式菜单模式
    --workers N      设置并行进程数 (默认: 4)
    --help           显示此帮助信息

示例:
    $0                       # 默认模式（环境检查 + 快速测试）
    $0 --quick              # 快速测试
    $0 --full --workers 8   # 完整测试，使用8个并发进程
    $0 --interactive        # 交互式菜单
    $0 --setup              # 仅设置环境

更多信息请查看: python run_all_tests.py --help
EOF
}

# 主函数
main() {
    local mode="default"
    local workers=4
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --check)
                mode="check"
                shift
                ;;
            --setup)
                mode="setup"
                shift
                ;;
            --quick)
                mode="quick"
                shift
                ;;
            --full)
                mode="full"
                shift
                ;;
            --diff)
                mode="diff"
                shift
                ;;
            --github)
                mode="github"
                shift
                ;;
            --report)
                mode="report"
                shift
                ;;
            --interactive)
                mode="interactive"
                shift
                ;;
            --workers)
                workers="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 根据模式执行相应操作
    case $mode in
        check)
            check_environment
            ;;
        setup)
            setup_environment
            ;;
        quick)
            check_environment && run_quick_tests
            ;;
        full)
            check_environment && run_full_tests "$workers"
            ;;
        diff)
            if activate_venv; then
                python scripts/test_runner.py --diff
            fi
            ;;
        github)
            simulate_github_actions
            ;;
        report)
            generate_report
            ;;
        interactive)
            interactive_menu
            ;;
        default)
            print_header "SAGE 测试自动化 - 默认模式"
            check_environment && run_quick_tests && generate_report
            ;;
    esac
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
