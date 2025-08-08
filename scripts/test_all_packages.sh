#!/bin/bash
#
# SAGE Framework 一键测试脚本
# All-in-One Test Script for SAGE Framework
#
# 为所有包运行测试，支持并行执行和详细报告
# Run tests for all packages with parallel execution and detailed reporting

set -euo pipefail

# 脚本目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/packages"

# 引入通用工具
source "$SCRIPT_DIR/common_utils.sh"

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# 默认配置
DEFAULT_TIMEOUT=300
DEFAULT_JOBS=4
DEFAULT_PATTERN="test_*.py"

# 使用说明
show_usage() {
    echo -e "${BOLD}🧪 SAGE Framework 一键测试脚本${NC}"
    echo -e "==========================================="
    echo ""
    echo -e "${BOLD}用法:${NC}"
    echo "  $0 [OPTIONS] [PACKAGES...]"
    echo ""
    echo -e "${BOLD}选项:${NC}"
    echo "  -j, --jobs NUMBER     并行测试数量 (默认: $DEFAULT_JOBS)"
    echo "  -t, --timeout NUMBER  测试超时时间 (默认: $DEFAULT_TIMEOUT 秒)"
    echo "  -p, --pattern PATTERN 测试文件模式 (默认: $DEFAULT_PATTERN)"
    echo "  -f, --failed          只运行之前失败的测试"
    echo "  -v, --verbose         详细输出"
    echo "  -q, --quiet           静默模式，只显示结果"
    echo "  -s, --summary         只显示测试结果摘要"
    echo "  --skip-install        跳过包安装检查"
    echo "  --continue-on-error   遇到错误时继续执行其他包"
    echo "  -h, --help           显示此帮助信息"
    echo ""
    echo -e "${BOLD}包列表 (可选):${NC}"
    echo "  如果不指定包名，将测试所有包："
    echo "  - sage-cli"
    echo "  - sage-core" 
    echo "  - sage-dev-toolkit"
    echo "  - sage-frontend"
    echo "  - sage-kernel"
    echo "  - sage-middleware"
    echo "  - sage-utils"
    echo ""
    echo -e "${BOLD}示例:${NC}"
    echo "  $0                                    # 测试所有包"
    echo "  $0 sage-core sage-kernel              # 只测试指定包"
    echo "  $0 -j 8 -t 600                       # 8个并行任务，10分钟超时"
    echo "  $0 --failed -v                       # 重新运行失败的测试，详细输出"
    echo "  $0 --summary sage-frontend            # 只显示frontend包的测试摘要"
}

# 参数解析
JOBS=$DEFAULT_JOBS
TIMEOUT=$DEFAULT_TIMEOUT
PATTERN=$DEFAULT_PATTERN
FAILED_ONLY=false
VERBOSE=false
QUIET=false
SUMMARY_ONLY=false
SKIP_INSTALL=false
CONTINUE_ON_ERROR=false
SPECIFIC_PACKAGES=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -j|--jobs)
            JOBS="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -p|--pattern)
            PATTERN="$2"
            shift 2
            ;;
        -f|--failed)
            FAILED_ONLY=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -s|--summary)
            SUMMARY_ONLY=true
            shift
            ;;
        --skip-install)
            SKIP_INSTALL=true
            shift
            ;;
        --continue-on-error)
            CONTINUE_ON_ERROR=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -*)
            echo -e "${RED}❌ 未知选项: $1${NC}"
            show_usage
            exit 1
            ;;
        *)
            SPECIFIC_PACKAGES+=("$1")
            shift
            ;;
    esac
done

# 所有可用的包
ALL_PACKAGES=(
    "sage-cli"
    "sage-core"
    "sage-dev-toolkit"
    "sage-frontend"
    "sage-kernel"
    "sage-middleware"
    "sage-utils"
)

# 确定要测试的包
if [[ ${#SPECIFIC_PACKAGES[@]} -eq 0 ]]; then
    PACKAGES_TO_TEST=("${ALL_PACKAGES[@]}")
else
    PACKAGES_TO_TEST=("${SPECIFIC_PACKAGES[@]}")
fi

# 测试结果跟踪
declare -A TEST_RESULTS
declare -A TEST_DURATIONS
declare -A TEST_ERROR_MESSAGES

# 日志函数
log_info() {
    [[ "$QUIET" == "true" ]] || echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_header() {
    if [[ "$QUIET" == "false" ]]; then
        echo -e "\n${BOLD}${CYAN}$1${NC}"
        echo -e "${CYAN}$(printf '=%.0s' {1..60})${NC}"
    fi
}

# 检查 sage-dev 命令
check_sage_dev() {
    if ! command -v sage-dev &> /dev/null; then
        log_error "sage-dev 命令未找到！"
        log_info "请先安装 sage-dev-toolkit:"
        log_info "cd $PACKAGES_DIR/sage-dev-toolkit && pip install -e ."
        exit 1
    fi
}

# 检查包是否存在
check_package_exists() {
    local package_name=$1
    local package_path="$PACKAGES_DIR/$package_name"
    
    if [[ ! -d "$package_path" ]]; then
        log_error "包不存在: $package_name (路径: $package_path)"
        return 1
    fi
    
    if [[ ! -f "$package_path/pyproject.toml" ]] && [[ ! -f "$package_path/setup.py" ]]; then
        log_warning "包 $package_name 缺少 pyproject.toml 或 setup.py"
    fi
    
    return 0
}

# 检查包是否有测试
check_has_tests() {
    local package_name=$1
    local package_path="$PACKAGES_DIR/$package_name"
    
    # 检查常见的测试目录
    for test_dir in "tests" "test" "Tests" "Test"; do
        if [[ -d "$package_path/$test_dir" ]]; then
            local test_files=$(find "$package_path/$test_dir" -name "$PATTERN" 2>/dev/null | wc -l)
            if [[ $test_files -gt 0 ]]; then
                return 0
            fi
        fi
    done
    
    # 检查根目录下的测试文件
    local test_files=$(find "$package_path" -maxdepth 1 -name "$PATTERN" 2>/dev/null | wc -l)
    if [[ $test_files -gt 0 ]]; then
        return 0
    fi
    
    return 1
}

# 运行单个包的测试
run_package_test() {
    local package_name=$1
    local package_path="$PACKAGES_DIR/$package_name"
    
    log_header "测试包: $package_name"
    
    # 检查包是否存在
    if ! check_package_exists "$package_name"; then
        TEST_RESULTS[$package_name]="NOT_FOUND"
        TEST_ERROR_MESSAGES[$package_name]="包不存在"
        return 1
    fi
    
    # 检查是否有测试
    if ! check_has_tests "$package_name"; then
        log_warning "包 $package_name 没有找到测试文件 (模式: $PATTERN)"
        TEST_RESULTS[$package_name]="NO_TESTS"
        TEST_ERROR_MESSAGES[$package_name]="没有找到测试文件"
        return 0
    fi
    
    # 进入包目录
    cd "$package_path"
    
    # 构建测试命令
    local test_cmd="sage-dev test"
    test_cmd+=" --timeout $TIMEOUT"
    test_cmd+=" --jobs $JOBS"
    test_cmd+=" --pattern '$PATTERN'"
    
    if [[ "$FAILED_ONLY" == "true" ]]; then
        test_cmd+=" --failed"
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        test_cmd+=" -v"
    fi
    
    # 记录开始时间
    local start_time=$(date +%s)
    
    # 运行测试
    log_info "运行命令: $test_cmd"
    local exit_code=0
    
    if [[ "$VERBOSE" == "true" ]] || [[ "$QUIET" == "false" ]]; then
        eval "$test_cmd" || exit_code=$?
    else
        eval "$test_cmd" >/dev/null 2>&1 || exit_code=$?
    fi
    
    # 记录结束时间
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    TEST_DURATIONS[$package_name]=$duration
    
    # 记录结果
    if [[ $exit_code -eq 0 ]]; then
        TEST_RESULTS[$package_name]="PASSED"
        log_success "包 $package_name 测试通过 (${duration}s)"
    else
        TEST_RESULTS[$package_name]="FAILED"
        TEST_ERROR_MESSAGES[$package_name]="测试失败，退出代码: $exit_code"
        log_error "包 $package_name 测试失败 (${duration}s)"
        
        if [[ "$CONTINUE_ON_ERROR" == "false" ]]; then
            log_error "由于测试失败停止执行 (使用 --continue-on-error 继续执行)"
            return $exit_code
        fi
    fi
    
    return 0
}

# 显示测试摘要
show_summary() {
    log_header "📊 测试结果摘要"
    
    local total_packages=${#PACKAGES_TO_TEST[@]}
    local passed_count=0
    local failed_count=0
    local no_tests_count=0
    local not_found_count=0
    local total_duration=0
    
    echo -e "\n${BOLD}包测试结果:${NC}"
    printf "%-20s %-10s %-10s %s\n" "包名" "状态" "耗时" "说明"
    printf "%-20s %-10s %-10s %s\n" "----" "----" "----" "----"
    
    for package in "${PACKAGES_TO_TEST[@]}"; do
        local status=${TEST_RESULTS[$package]:-"UNKNOWN"}
        local duration=${TEST_DURATIONS[$package]:-0}
        local message=${TEST_ERROR_MESSAGES[$package]:-""}
        
        case $status in
            "PASSED")
                printf "%-20s ${GREEN}%-10s${NC} %-10s %s\n" "$package" "✅ 通过" "${duration}s" ""
                ((passed_count++))
                ;;
            "FAILED")
                printf "%-20s ${RED}%-10s${NC} %-10s %s\n" "$package" "❌ 失败" "${duration}s" "$message"
                ((failed_count++))
                ;;
            "NO_TESTS")
                printf "%-20s ${YELLOW}%-10s${NC} %-10s %s\n" "$package" "⚠️  无测试" "0s" "$message"
                ((no_tests_count++))
                ;;
            "NOT_FOUND")
                printf "%-20s ${RED}%-10s${NC} %-10s %s\n" "$package" "❌ 未找到" "0s" "$message"
                ((not_found_count++))
                ;;
            *)
                printf "%-20s ${YELLOW}%-10s${NC} %-10s %s\n" "$package" "❓ 未知" "0s" ""
                ;;
        esac
        
        total_duration=$((total_duration + duration))
    done
    
    echo ""
    echo -e "${BOLD}总体统计:${NC}"
    echo -e "  总包数:     ${BOLD}$total_packages${NC}"
    echo -e "  测试通过:   ${GREEN}$passed_count${NC}"
    echo -e "  测试失败:   ${RED}$failed_count${NC}"
    echo -e "  无测试:     ${YELLOW}$no_tests_count${NC}"
    echo -e "  包未找到:   ${RED}$not_found_count${NC}"
    echo -e "  总耗时:     ${BOLD}${total_duration}s${NC}"
    
    # 计算成功率
    local testable_packages=$((total_packages - no_tests_count - not_found_count))
    if [[ $testable_packages -gt 0 ]]; then
        local success_rate=$((passed_count * 100 / testable_packages))
        echo -e "  成功率:     ${BOLD}$success_rate%${NC}"
    fi
    
    # 返回适当的退出代码
    if [[ $failed_count -gt 0 ]] || [[ $not_found_count -gt 0 ]]; then
        return 1
    fi
    return 0
}

# 主函数
main() {
    # 显示脚本头部
    if [[ "$QUIET" == "false" ]]; then
        echo -e "${BOLD}${MAGENTA}🧪 SAGE Framework 一键测试脚本${NC}"
        echo -e "${MAGENTA}=======================================${NC}"
        echo ""
    fi
    
    # 检查 sage-dev 命令
    check_sage_dev
    
    # 显示配置信息
    if [[ "$QUIET" == "false" ]] && [[ "$SUMMARY_ONLY" == "false" ]]; then
        log_info "配置信息:"
        log_info "  并行任务数: $JOBS"
        log_info "  超时时间:   ${TIMEOUT}s"
        log_info "  测试模式:   $PATTERN"
        log_info "  测试包数:   ${#PACKAGES_TO_TEST[@]}"
        log_info "  测试包:     ${PACKAGES_TO_TEST[*]}"
        echo ""
    fi
    
    # 执行测试
    local overall_success=true
    
    for package in "${PACKAGES_TO_TEST[@]}"; do
        if [[ "$SUMMARY_ONLY" == "false" ]]; then
            if ! run_package_test "$package"; then
                overall_success=false
                [[ "$CONTINUE_ON_ERROR" == "true" ]] || break
            fi
        else
            # 摘要模式：静默运行测试
            local original_quiet=$QUIET
            QUIET=true
            run_package_test "$package" || overall_success=false
            QUIET=$original_quiet
        fi
    done
    
    # 显示摘要
    if ! show_summary; then
        overall_success=false
    fi
    
    # 返回最终结果
    if [[ "$overall_success" == "true" ]]; then
        log_success "🎉 所有测试执行完成！"
        exit 0
    else
        log_error "💥 测试执行过程中遇到了问题"
        exit 1
    fi
}

# 执行主函数
main "$@"
