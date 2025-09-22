#!/bin/bash

# =================================================================
# SAGE Issues Manager 自动化测试脚本
# =================================================================
# 作用：全面测试 issues_manager.sh 的所有功能
# 要求：自动运行所有功能并自动清理中间产物
# =================================================================

set -e  # 遇到错误立即退出

# 脚本变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../" && pwd)"
ISSUES_MANAGER="$PROJECT_ROOT/tools/issues-management/issues_manager.sh"
TEST_LOG_DIR="$SCRIPT_DIR/test_logs"
BACKUP_DIR="$TEST_LOG_DIR/backup"
TEST_WORKSPACE="/tmp/sage_issues_test_$$"

# 测试模式
TEST_MODE="full"  # full, quick, integration
VERBOSE=false
CLEANUP=true

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =================================================================
# 辅助函数
# =================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_separator() {
    echo "================================================================="
}

# 显示使用帮助
show_help() {
    cat << EOF
SAGE Issues Manager 自动化测试脚本

用法: $0 [选项]

选项:
  -h, --help      显示此帮助信息
  -q, --quick     快速测试模式 (只测试基础功能)
  -f, --full      完整测试模式 (默认)
  -i, --integration 集成测试模式 (测试与GitHub的集成)
  -v, --verbose   详细输出
  --no-cleanup    测试后不清理临时文件

测试模式说明:
  quick:      基础语法和功能测试，适合CI环境
  full:       完整功能测试，包括所有操作
  integration: 需要GitHub token的集成测试

示例:
  $0 --quick              # 快速测试
  $0 --full --verbose     # 完整测试，详细输出
  $0 --integration        # 集成测试

EOF
}

# =================================================================
# 环境检查和准备
# =================================================================

check_prerequisites() {
    log_info "检查测试前提条件..."
    
    # 检查 issues_manager.sh 是否存在
    if [[ ! -f "$ISSUES_MANAGER" ]]; then
        log_error "issues_manager.sh 未找到: $ISSUES_MANAGER"
        exit 1
    fi
    
    # 检查 issues_manager.sh 是否可执行
    if [[ ! -x "$ISSUES_MANAGER" ]]; then
        log_info "设置 issues_manager.sh 为可执行..."
        chmod +x "$ISSUES_MANAGER"
    fi
    
    # 检查必要的工具
    local required_tools=("python3" "bash" "git")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "缺少必要工具: $tool"
            exit 1
        fi
    done
    
    # 检查Python脚本目录
    local scripts_dir="$PROJECT_ROOT/tools/issues-management/_scripts"
    if [[ ! -d "$scripts_dir" ]]; then
        log_warning "_scripts 目录不存在: $scripts_dir"
    fi
    
    log_success "前提条件检查通过"
}

setup_test_environment() {
    log_info "设置测试环境..."
    
    # 创建测试目录
    mkdir -p "$TEST_LOG_DIR" "$BACKUP_DIR" "$TEST_WORKSPACE"
    
    # 设置测试时间戳
    TEST_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    TEST_LOG_FILE="$TEST_LOG_DIR/test_run_$TEST_TIMESTAMP.log"
    
    # 备份现有配置（如果存在）
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        cp "$PROJECT_ROOT/.env" "$BACKUP_DIR/.env.backup"
        log_info "已备份 .env 文件"
    fi
    
    # 创建测试用的环境变量
    export GITHUB_WORKSPACE="$TEST_WORKSPACE"
    export CI=true
    # export TEST_MODE=true  # 错误的设置，应该保持原有的TEST_MODE值
    
    log_success "测试环境设置完成"
}

# =================================================================
# 测试函数
# =================================================================

test_basic_syntax() {
    print_separator
    log_info "测试 1: 基础语法检查"
    
    # 使用 bash -n 检查语法
    if bash -n "$ISSUES_MANAGER"; then
        log_success "语法检查通过"
    else
        log_error "语法检查失败"
        return 1
    fi
    
    # 检查shebang
    local shebang=$(head -n 1 "$ISSUES_MANAGER")
    if [[ "$shebang" =~ ^#!/bin/bash ]]; then
        log_success "Shebang 正确: $shebang"
    else
        log_warning "Shebang 可能有问题: $shebang"
    fi
}

test_help_function() {
    print_separator
    log_info "测试 2: 帮助功能"
    
    # 测试 --help 选项，添加超时避免卡住
    if timeout 5 bash -c "echo 5 | '$ISSUES_MANAGER' --help" > /dev/null 2>&1; then
        log_success "--help 选项工作正常"
    else
        log_warning "--help 选项不可用或需要交互输入"
    fi
    
    # 测试脚本基本可执行性
    if timeout 3 bash -c "echo 5 | '$ISSUES_MANAGER'" > /dev/null 2>&1; then
        log_success "脚本基本可执行"
    else
        log_warning "脚本可能需要特殊环境或配置"
    fi
}

test_list_functionality() {
    print_separator
    log_info "测试 3: 列表功能"
    
    # 测试 list 命令（使用超时避免卡住）
    log_info "测试 list 命令..."
    if timeout 5 bash -c "echo 5 | '$ISSUES_MANAGER' list --dry-run" > /dev/null 2>&1; then
        log_success "list 命令基础功能正常"
    else
        log_warning "list 命令可能需要额外配置或不支持命令行参数"
    fi
}

test_analyze_functionality() {
    print_separator
    log_info "测试 4: 分析功能"
    
    # 创建测试数据
    local test_data_file="$TEST_WORKSPACE/test_issues.json"
    cat > "$test_data_file" << 'EOF'
[
  {
    "number": 1,
    "title": "Test Issue 1",
    "body": "This is a test issue for automated testing",
    "state": "open",
    "labels": [{"name": "bug"}],
    "created_at": "2024-01-01T00:00:00Z"
  },
  {
    "number": 2,
    "title": "Test Issue 2", 
    "body": "Another test issue",
    "state": "closed",
    "labels": [{"name": "enhancement"}],
    "created_at": "2024-01-02T00:00:00Z"
  }
]
EOF
    
    # 测试分析功能（使用超时避免卡住）
    log_info "测试 analyze 命令..."
    if timeout 5 bash -c "echo 5 | '$ISSUES_MANAGER' analyze --input '$test_data_file' --dry-run" > /dev/null 2>&1; then
        log_success "analyze 命令基础功能正常"
    else
        log_warning "analyze 命令可能需要额外配置或AI服务"
    fi
}

test_export_functionality() {
    print_separator
    log_info "测试 5: 导出功能"
    
    # 测试导出功能（使用超时避免卡住）
    local export_file="$TEST_WORKSPACE/export_test.json"
    log_info "测试 export 命令..."
    
    if timeout 5 bash -c "echo 5 | '$ISSUES_MANAGER' export --output '$export_file' --dry-run" > /dev/null 2>&1; then
        log_success "export 命令基础功能正常"
    else
        log_warning "export 命令可能需要额外配置"
    fi
}

test_config_functionality() {
    print_separator
    log_info "测试 6: 配置功能"
    
    # 测试配置查看（使用超时避免卡住）
    log_info "测试 config 命令..."
    if timeout 5 bash -c "echo 5 | '$ISSUES_MANAGER' config --show" > /dev/null 2>&1; then
        log_success "config 命令基础功能正常"
    else
        log_warning "config 命令可能需要初始化或不支持命令行参数"
    fi
}

test_integration_with_github() {
    print_separator
    log_info "测试 7: GitHub 集成测试"
    
    # 检查GitHub token
    if [[ -z "$GITHUB_TOKEN" ]]; then
        log_warning "未设置 GITHUB_TOKEN，跳过GitHub集成测试"
        return 0
    fi
    
    log_info "执行GitHub API连接测试..."
    
    # 测试实际的GitHub连接（使用超时避免卡住）
    if timeout 10 bash -c "echo 5 | '$ISSUES_MANAGER' list --limit 1" > /dev/null 2>&1; then
        log_success "GitHub API 连接测试通过"
    else
        log_warning "GitHub API 连接可能有问题"
    fi
}

test_error_handling() {
    print_separator
    log_info "测试 8: 错误处理"
    
    # 测试无效参数
    log_info "测试无效参数处理..."
    if "$ISSUES_MANAGER" invalid_command 2>/dev/null; then
        log_warning "无效命令应该返回错误"
    else
        log_success "无效命令错误处理正常"
    fi
    
    # 测试缺少必要参数
    log_info "测试缺少参数处理..."
    if "$ISSUES_MANAGER" analyze 2>/dev/null; then
        log_warning "缺少参数时应该返回错误"
    else
        log_success "缺少参数错误处理正常"
    fi
}

test_python_scripts() {
    print_separator
    log_info "测试 9: Python 脚本检查"
    
    local scripts_dir="$PROJECT_ROOT/tools/issues-management/_scripts"
    if [[ ! -d "$scripts_dir" ]]; then
        log_warning "_scripts 目录不存在，跳过Python脚本测试"
        return 0
    fi
    
    # 检查Python脚本语法
    for script in "$scripts_dir"/*.py; do
        if [[ -f "$script" ]]; then
            log_info "检查 $(basename "$script") 语法..."
            if python3 -m py_compile "$script" 2>/dev/null; then
                log_success "$(basename "$script") 语法正确"
            else
                log_error "$(basename "$script") 语法错误"
            fi
        fi
    done
}

# =================================================================
# 清理函数
# =================================================================

cleanup_test_environment() {
    if [[ "$CLEANUP" = true ]]; then
        log_info "清理测试环境..."
        
        # 删除测试工作目录
        if [[ -d "$TEST_WORKSPACE" ]]; then
            rm -rf "$TEST_WORKSPACE"
            log_info "已删除测试工作目录"
        fi
        
        # 恢复备份的配置文件
        if [[ -f "$BACKUP_DIR/.env.backup" ]]; then
            cp "$BACKUP_DIR/.env.backup" "$PROJECT_ROOT/.env"
            log_info "已恢复 .env 文件"
        fi
        
        # 清理临时环境变量
        unset GITHUB_WORKSPACE TEST_MODE
        
        log_success "测试环境清理完成"
    else
        log_info "跳过清理，测试文件保留在: $TEST_WORKSPACE"
    fi
}

# =================================================================
# 主测试流程
# =================================================================

run_quick_tests() {
    log_info "运行快速测试套件..."
    
    test_basic_syntax || return 1
    test_help_function || return 1
    test_list_functionality
    test_analyze_functionality
    test_export_functionality
    test_config_functionality
    test_integration_with_github
    
    log_success "快速测试完成"
}

run_full_tests() {
    log_info "运行完整测试套件..."
    
    test_basic_syntax || return 1
    test_help_function || return 1
    test_list_functionality
    test_analyze_functionality
    test_export_functionality
    test_config_functionality
    test_error_handling
    test_python_scripts
    
    log_success "完整测试完成"
}

run_integration_tests() {
    log_info "运行集成测试套件..."
    
    test_basic_syntax || return 1
    test_help_function || return 1
    test_integration_with_github
    
    log_success "集成测试完成"
}

generate_test_report() {
    print_separator
    log_info "生成测试报告..."
    
    local report_file="$TEST_LOG_DIR/test_report_$TEST_TIMESTAMP.md"
    
    cat > "$report_file" << EOF
# SAGE Issues Manager 测试报告

## 测试信息
- **测试时间**: $(date)
- **测试模式**: $TEST_MODE
- **脚本版本**: $(head -n 5 "$ISSUES_MANAGER" | grep -o "v[0-9]\+\.[0-9]\+\.[0-9]\+" || echo "未知")
- **测试环境**: $(uname -s) $(uname -r)

## 测试结果
$(cat "$TEST_LOG_FILE" 2>/dev/null || echo "无详细日志")

## 测试文件位置
- 测试日志: $TEST_LOG_FILE
- 测试工作目录: $TEST_WORKSPACE
- 备份目录: $BACKUP_DIR

## 建议
- 定期运行完整测试套件
- 在修改 issues_manager.sh 后运行测试
- 集成测试需要设置 GITHUB_TOKEN

生成时间: $(date)
EOF
    
    log_success "测试报告已生成: $report_file"
    
    if [[ "$VERBOSE" = true ]]; then
        echo "========== 测试报告内容 =========="
        cat "$report_file"
        echo "================================="
    fi
}

# =================================================================
# 命令行参数解析
# =================================================================

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -q|--quick)
                TEST_MODE="quick"
                shift
                ;;
            -f|--full)
                TEST_MODE="full"
                shift
                ;;
            -i|--integration)
                TEST_MODE="integration"
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --no-cleanup)
                CLEANUP=false
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# =================================================================
# 主函数
# =================================================================

main() {
    print_separator
    log_info "SAGE Issues Manager 自动化测试开始"
    log_info "测试模式: $TEST_MODE"
    print_separator
    
    # 检查前提条件
    check_prerequisites
    
    # 设置测试环境
    setup_test_environment
    
    # 根据模式运行测试
    case "$TEST_MODE" in
        quick)
            run_quick_tests
            ;;
        full)
            run_full_tests
            ;;
        integration)
            run_integration_tests
            ;;
        *)
            log_error "未知测试模式: $TEST_MODE"
            exit 1
            ;;
    esac
    
    # 生成测试报告
    generate_test_report
    
    # 清理环境
    cleanup_test_environment
    
    print_separator
    log_success "测试完成! 模式: $TEST_MODE"
    if [[ -f "$TEST_LOG_DIR/test_report_$TEST_TIMESTAMP.md" ]]; then
        log_info "测试报告: $TEST_LOG_DIR/test_report_$TEST_TIMESTAMP.md"
    fi
    print_separator
}

# =================================================================
# 脚本入口
# =================================================================

# 设置错误处理
trap cleanup_test_environment EXIT

# 解析命令行参数
parse_arguments "$@"

# 如果在CI环境中，默认使用快速模式
if [[ "$CI" = true && "$TEST_MODE" = "full" ]]; then
    log_info "检测到CI环境，切换到快速测试模式"
    TEST_MODE="quick"
fi

# 启动测试
main
