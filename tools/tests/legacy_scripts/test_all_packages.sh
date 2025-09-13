#!/bin/bash
#
# SAGE Framework 一键测试所有包脚本
# Test All Packages Script for SAGE Framework
#
# ⚠️  DEPRECATION WARNING ⚠️
# 本脚本已被弃用，请使用新的统一测试命令：
#   sage dev test --test-type unit      # 单元测试
#   sage dev test --test-type integration  # 集成测试  
#   sage dev test --verbose            # 详细输出
# 详情请查看 tools/tests/MIGRATION.md 文档
#
# 自动发现并测试所有SAGE包，支持并行执行和详细配置
# Automatically discover and test all SAGE packages with parallel execution and detailed configuration

set -euo pipefail

# 脚本目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/packages"

# 引入工具模块
source "$PROJECT_ROOT/scripts/logging.sh" 2>/dev/null || {
    # 基础日志函数（如果logging.sh不可用）
    log_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
    log_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
    log_warning() { echo -e "\033[1;33m[WARNING]\033[0m $1"; }
    log_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }
}

# 默认配置
DEFAULT_JOBS=4
DEFAULT_TIMEOUT=300
DEFAULT_VERBOSE=false
DEFAULT_QUIET=false
DEFAULT_SUMMARY=false
DEFAULT_CONTINUE_ON_ERROR=true
DEFAULT_FAILED_ONLY=false

# 显示弃用警告
show_deprecation_warning() {
    echo -e "\033[1;33m⚠️  DEPRECATION WARNING ⚠️\033[0m"
    echo -e "\033[1;33m本脚本已被弃用，请使用新的统一测试命令：\033[0m"
    echo -e "  \033[0;36msage dev test --test-type unit\033[0m      # 单元测试"
    echo -e "  \033[0;36msage dev test --test-type integration\033[0m  # 集成测试"
    echo -e "  \033[0;36msage dev test --verbose\033[0m            # 详细输出"
    echo -e "\033[1;33m详情请查看 tools/tests/MIGRATION.md 文档\033[0m"
    echo
}

# 解析命令行参数
show_help() {
    cat << EOF
SAGE Framework 包测试工具

用法: $0 [选项] [包名...]

选项:
  -j, --jobs N              并行任务数量 (默认: $DEFAULT_JOBS)
  -t, --timeout N           每个包的超时时间(秒) (默认: $DEFAULT_TIMEOUT)
  -v, --verbose             详细输出模式
  -q, --quiet               静默模式，只显示结果
  -s, --summary             只显示摘要结果
  -c, --continue-on-error   遇到错误继续执行其他包 (默认)
  -x, --stop-on-error       遇到错误立即停止
  -f, --failed              只重新运行失败的测试
  -h, --help                显示此帮助信息

包名:
  如果不指定包名，将测试所有发现的包
  可以指定多个包名，如: sage-libs sage-kernel sage-middleware

示例:
  $0                                    # 测试所有包
  $0 sage-libs sage-kernel             # 只测试指定包
  $0 -j 8 -t 600 --verbose            # 8并发，10分钟超时，详细输出
  $0 --summary --continue-on-error     # 摘要模式，继续执行
  $0 --failed --verbose                # 重新运行失败的测试

EOF
}

# 初始化变量
JOBS=$DEFAULT_JOBS
TIMEOUT=$DEFAULT_TIMEOUT
VERBOSE=$DEFAULT_VERBOSE
QUIET=$DEFAULT_QUIET
SUMMARY=$DEFAULT_SUMMARY
CONTINUE_ON_ERROR=$DEFAULT_CONTINUE_ON_ERROR
FAILED_ONLY=$DEFAULT_FAILED_ONLY
PACKAGES=()

# 解析参数
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
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -s|--summary)
            SUMMARY=true
            shift
            ;;
        -c|--continue-on-error)
            CONTINUE_ON_ERROR=true
            shift
            ;;
        -x|--stop-on-error)
            CONTINUE_ON_ERROR=false
            shift
            ;;
        -f|--failed)
            FAILED_ONLY=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
        *)
            PACKAGES+=("$1")
            shift
            ;;
    esac
done

# 创建测试日志目录
TEST_LOG_DIR="$PROJECT_ROOT/.testlogs"
mkdir -p "$TEST_LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
MAIN_LOG="$TEST_LOG_DIR/test_run_${TIMESTAMP}.log"

# 测试结果跟踪
declare -A TEST_RESULTS
declare -A TEST_LOGS
TOTAL_PACKAGES=0
PASSED_PACKAGES=0
FAILED_PACKAGES=0
SKIPPED_PACKAGES=0

# 获取包列表
get_packages() {
    if [[ ${#PACKAGES[@]} -eq 0 ]]; then
        # 自动发现包
        for dir in "$PACKAGES_DIR"/sage-*; do
            if [[ -d "$dir" ]]; then
                PACKAGES+=($(basename "$dir"))
            fi
        done
    fi
    
    if [[ ${#PACKAGES[@]} -eq 0 ]]; then
        log_error "未找到任何包进行测试"
        exit 1
    fi
}

# 检查包是否有测试
has_tests() {
    local package="$1"
    local package_dir="$PACKAGES_DIR/$package"
    
    # 检查是否有tests目录或run_tests.py
    [[ -d "$package_dir/tests" ]] || [[ -f "$package_dir/tests/run_tests.py" ]] || [[ -f "$package_dir/run_tests.py" ]]
}

# 运行单个包的测试
test_package() {
    local package="$1"
    local package_dir="$PACKAGES_DIR/$package"
    local log_file="$TEST_LOG_DIR/${package}_${TIMESTAMP}.log"
    
    TEST_LOGS["$package"]="$log_file"
    
    if ! has_tests "$package"; then
        TEST_RESULTS["$package"]="NO_TESTS"
        echo "⚠️ $package: 未找到测试" >> "$log_file"
        return 0
    fi
    
    {
        echo "📦 开始测试包: $package"
        echo "时间: $(date)"
        echo "目录: $package_dir"
        echo "----------------------------------------"
    } >> "$log_file"
    
    cd "$package_dir"
    
    local test_cmd=""
    local exit_code=0
    
    # 确定测试命令
    if [[ -f "tests/run_tests.py" ]]; then
        test_cmd="cd tests && timeout $TIMEOUT python run_tests.py --unit --coverage"
    elif [[ -f "run_tests.py" ]]; then
        test_cmd="timeout $TIMEOUT python run_tests.py --unit --coverage"
    elif [[ -d "tests" ]]; then
        test_cmd="timeout $TIMEOUT python -m pytest tests/ -v"
    else
        TEST_RESULTS["$package"]="NO_TESTS"
        echo "⚠️ $package: 未找到合适的测试方法" >> "$log_file"
        return 0
    fi
    
    # 执行测试
    if eval "$test_cmd" >> "$log_file" 2>&1; then
        TEST_RESULTS["$package"]="PASSED"
        echo "✅ $package: 测试通过" >> "$log_file"
    else
        exit_code=$?
        TEST_RESULTS["$package"]="FAILED"
        echo "❌ $package: 测试失败 (退出码: $exit_code)" >> "$log_file"
    fi
    
    echo "完成时间: $(date)" >> "$log_file"
    return $exit_code
}

# 并行测试包
test_packages_parallel() {
    local pids=()
    local active_jobs=0
    
    for package in "${PACKAGES[@]}"; do
        # 等待空闲的job slot
        while [[ $active_jobs -ge $JOBS ]]; do
            for i in "${!pids[@]}"; do
                if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                    wait "${pids[$i]}"
                    unset pids[$i]
                    ((active_jobs--))
                fi
            done
            sleep 0.1
        done
        
        # 启动新的测试job
        if [[ $VERBOSE == true ]] && [[ $QUIET == false ]]; then
            log_info "启动测试: $package"
        fi
        
        test_package "$package" &
        pids+=($!)
        ((active_jobs++))
        ((TOTAL_PACKAGES++))
    done
    
    # 等待所有job完成
    for pid in "${pids[@]}"; do
        wait "$pid" || true
    done
}

# 生成测试报告
generate_report() {
    local report_file="$TEST_LOG_DIR/test_summary_${TIMESTAMP}.txt"
    
    # 统计结果
    for package in "${PACKAGES[@]}"; do
        case "${TEST_RESULTS[$package]}" in
            "PASSED")
                ((PASSED_PACKAGES++))
                ;;
            "FAILED")
                ((FAILED_PACKAGES++))
                ;;
            "NO_TESTS")
                ((SKIPPED_PACKAGES++))
                ;;
        esac
    done
    
    # 生成报告
    {
        echo "SAGE Framework 测试报告"
        echo "========================"
        echo "时间: $(date)"
        echo "总包数: $TOTAL_PACKAGES"
        echo "通过: $PASSED_PACKAGES"
        echo "失败: $FAILED_PACKAGES"
        echo "跳过: $SKIPPED_PACKAGES"
        echo ""
        echo "详细结果:"
        echo "--------"
        
        for package in "${PACKAGES[@]}"; do
            case "${TEST_RESULTS[$package]}" in
                "PASSED")
                    echo "✅ $package"
                    ;;
                "FAILED")
                    echo "❌ $package"
                    ;;
                "NO_TESTS")
                    echo "⚠️  $package (无测试)"
                    ;;
                *)
                    echo "❓ $package (未知状态)"
                    ;;
            esac
        done
        
        if [[ $FAILED_PACKAGES -gt 0 ]]; then
            echo ""
            echo "失败的包详细信息:"
            echo "----------------"
            for package in "${PACKAGES[@]}"; do
                if [[ "${TEST_RESULTS[$package]}" == "FAILED" ]]; then
                    echo "📋 $package: ${TEST_LOGS[$package]}"
                fi
            done
        fi
        
    } | tee "$report_file"
    
    # 控制台输出
    if [[ $QUIET == false ]]; then
        if [[ $SUMMARY == true ]]; then
            echo ""
            log_info "测试摘要: $PASSED_PACKAGES/$TOTAL_PACKAGES 通过"
            if [[ $FAILED_PACKAGES -gt 0 ]]; then
                log_warning "$FAILED_PACKAGES 个包测试失败"
            fi
        else
            echo ""
            log_info "详细报告已保存到: $report_file"
        fi
    fi
}

# 主函数
main() {
    # 显示弃用警告
    show_deprecation_warning
    
    if [[ $QUIET == false ]]; then
        log_info "SAGE Framework 包测试工具启动"
        log_info "项目根目录: $PROJECT_ROOT"
        log_info "并行任务数: $JOBS"
        log_info "超时时间: ${TIMEOUT}秒"
    fi
    
    get_packages
    
    if [[ $QUIET == false ]]; then
        log_info "发现 ${#PACKAGES[@]} 个包: ${PACKAGES[*]}"
    fi
    
    # 记录开始时间
    START_TIME=$(date +%s)
    
    # 并行测试
    test_packages_parallel
    
    # 记录结束时间
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    # 生成报告
    generate_report
    
    if [[ $QUIET == false ]]; then
        log_info "测试完成，耗时: ${DURATION}秒"
    fi
    
    # 根据结果设置退出码
    if [[ $FAILED_PACKAGES -gt 0 ]] && [[ $CONTINUE_ON_ERROR == false ]]; then
        exit 1
    fi
}

# 运行主函数
main "$@"
