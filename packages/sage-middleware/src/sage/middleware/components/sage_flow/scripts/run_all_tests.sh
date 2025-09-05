#!/bin/bash

# SAGE Flow 完整测试执行脚本
# 该脚本运行所有测试套件并生成综合报告

set -euo pipefail

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# 日志函数
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

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/build"
REPORTS_DIR="$PROJECT_ROOT/test_reports"

# 测试配置
RUN_UNIT_TESTS="${RUN_UNIT_TESTS:-true}"
RUN_INTEGRATION_TESTS="${RUN_INTEGRATION_TESTS:-true}"
RUN_CANDYFLOW_TESTS="${RUN_CANDYFLOW_TESTS:-true}"
RUN_PYTHON_TESTS="${RUN_PYTHON_TESTS:-true}"
RUN_PERFORMANCE_TESTS="${RUN_PERFORMANCE_TESTS:-false}"
GENERATE_COVERAGE="${GENERATE_COVERAGE:-false}"
PARALLEL_JOBS="${PARALLEL_JOBS:-$(nproc)}"

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

log_info "开始 SAGE Flow 完整测试执行..."
log_info "项目根目录: $PROJECT_ROOT"
log_info "构建目录: $BUILD_DIR"
log_info "报告目录: $REPORTS_DIR"

# 创建报告目录
mkdir -p "$REPORTS_DIR"

# 检查构建目录
check_build_directory() {
    log_info "检查构建目录..."
    
    if [[ ! -d "$BUILD_DIR" ]]; then
        log_error "构建目录不存在: $BUILD_DIR"
        log_info "请先运行构建脚本: ./scripts/build_test.sh"
        exit 1
    fi
    
    if [[ ! -f "$BUILD_DIR/libsage_flow_core.so" ]]; then
        log_warning "核心库未找到，尝试构建..."
        cd "$BUILD_DIR"
        make -j"$PARALLEL_JOBS"
    fi
    
    log_success "构建目录检查通过"
}

# 运行单元测试
run_unit_tests() {
    if [[ "$RUN_UNIT_TESTS" != "true" ]]; then
        log_info "跳过单元测试"
        return 0
    fi
    
    log_info "运行单元测试..."
    
    cd "$BUILD_DIR"
    
    local unit_report="$REPORTS_DIR/unit_test_results.xml"
    local unit_log="$REPORTS_DIR/unit_test.log"
    
    # 运行单元测试
    if ctest -L unit --output-junit "$unit_report" --output-on-failure > "$unit_log" 2>&1; then
        log_success "单元测试完成"
        
        # 解析测试结果
        local unit_stats=$(parse_test_results "$unit_report")
        log_info "单元测试结果: $unit_stats"
        
    else
        log_error "单元测试失败，详细信息请查看: $unit_log"
        return 1
    fi
}

# 运行集成测试
run_integration_tests() {
    if [[ "$RUN_INTEGRATION_TESTS" != "true" ]]; then
        log_info "跳过集成测试"
        return 0
    fi
    
    log_info "运行集成测试..."
    
    cd "$BUILD_DIR"
    
    local integration_report="$REPORTS_DIR/integration_test_results.xml"
    local integration_log="$REPORTS_DIR/integration_test.log"
    
    # 设置 Python 路径
    export PYTHONPATH="$BUILD_DIR:${PYTHONPATH:-}"
    
    # 运行集成测试
    if ctest -L integration --output-junit "$integration_report" --output-on-failure > "$integration_log" 2>&1; then
        log_success "集成测试完成"
        
        local integration_stats=$(parse_test_results "$integration_report")
        log_info "集成测试结果: $integration_stats"
        
    else
        log_warning "集成测试部分失败，详细信息请查看: $integration_log"
        # 集成测试失败不阻止其他测试
    fi
}

# 运行 CandyFlow 功能测试
run_candyflow_tests() {
    if [[ "$RUN_CANDYFLOW_TESTS" != "true" ]]; then
        log_info "跳过 CandyFlow 功能测试"
        return 0
    fi
    
    log_info "运行 CandyFlow 功能测试..."
    
    cd "$BUILD_DIR"
    
    local candyflow_report="$REPORTS_DIR/candyflow_test_results.xml"
    local candyflow_log="$REPORTS_DIR/candyflow_test.log"
    
    # 运行 CandyFlow 测试
    if ctest -L candyflow --output-junit "$candyflow_report" --output-on-failure > "$candyflow_log" 2>&1; then
        log_success "CandyFlow 功能测试完成"
        
        local candyflow_stats=$(parse_test_results "$candyflow_report")
        log_info "CandyFlow 测试结果: $candyflow_stats"
        
    else
        log_warning "CandyFlow 功能测试部分失败，详细信息请查看: $candyflow_log"
    fi
}

# 运行 Python API 测试
run_python_tests() {
    if [[ "$RUN_PYTHON_TESTS" != "true" ]]; then
        log_info "跳过 Python API 测试"
        return 0
    fi
    
    log_info "运行 Python API 测试..."
    
    local python_report="$REPORTS_DIR/python_test_results.xml"
    local python_log="$REPORTS_DIR/python_test.log"
    
    # 设置 Python 路径
    export PYTHONPATH="$BUILD_DIR:${PYTHONPATH:-}"
    
    cd "$PROJECT_ROOT"
    
    # 运行 Python 测试
    if python -m pytest tests/python/ --junitxml="$python_report" -v > "$python_log" 2>&1; then
        log_success "Python API 测试完成"
        
        local python_stats=$(parse_pytest_results "$python_report")
        log_info "Python 测试结果: $python_stats"
        
    else
        log_warning "Python API 测试部分失败，详细信息请查看: $python_log"
    fi
}

# 运行性能基准测试
run_performance_tests() {
    if [[ "$RUN_PERFORMANCE_TESTS" != "true" ]]; then
        log_info "跳过性能基准测试"
        return 0
    fi
    
    log_info "运行性能基准测试..."
    
    cd "$BUILD_DIR"
    
    local performance_report="$REPORTS_DIR/performance_test_results.xml"
    local performance_log="$REPORTS_DIR/performance_test.log"
    
    # 运行性能测试
    if ctest -L performance --output-junit "$performance_report" --output-on-failure > "$performance_log" 2>&1; then
        log_success "性能基准测试完成"
        
        local performance_stats=$(parse_test_results "$performance_report")
        log_info "性能测试结果: $performance_stats"
        
    else
        log_warning "性能基准测试部分失败，详细信息请查看: $performance_log"
    fi
}

# 生成代码覆盖率报告
generate_coverage_report() {
    if [[ "$GENERATE_COVERAGE" != "true" ]]; then
        log_info "跳过代码覆盖率报告生成"
        return 0
    fi
    
    log_info "生成代码覆盖率报告..."
    
    cd "$BUILD_DIR"
    
    # 检查是否有覆盖率工具
    if command -v lcov &> /dev/null && command -v genhtml &> /dev/null; then
        local coverage_dir="$REPORTS_DIR/coverage"
        mkdir -p "$coverage_dir"
        
        # 收集覆盖率数据
        lcov --capture --directory . --output-file coverage.info
        lcov --remove coverage.info '/usr/*' --output-file coverage.info
        lcov --remove coverage.info '*/tests/*' --output-file coverage.info
        
        # 生成 HTML 报告
        genhtml coverage.info --output-directory "$coverage_dir"
        
        log_success "代码覆盖率报告已生成: $coverage_dir/index.html"
    else
        log_warning "lcov/genhtml 未找到，跳过覆盖率报告生成"
    fi
}

# 解析 CTest 结果
parse_test_results() {
    local xml_file="$1"
    
    if [[ ! -f "$xml_file" ]]; then
        echo "无结果文件"
        return
    fi
    
    # 简单的 XML 解析（使用 grep 和 awk）
    local tests=$(grep -c '<testcase' "$xml_file" 2>/dev/null || echo "0")
    local failures=$(grep -c '<failure' "$xml_file" 2>/dev/null || echo "0")
    local errors=$(grep -c '<error' "$xml_file" 2>/dev/null || echo "0")
    local skipped=$(grep -c '<skipped' "$xml_file" 2>/dev/null || echo "0")
    
    local passed=$((tests - failures - errors - skipped))
    
    # 更新全局统计
    TOTAL_TESTS=$((TOTAL_TESTS + tests))
    PASSED_TESTS=$((PASSED_TESTS + passed))
    FAILED_TESTS=$((FAILED_TESTS + failures + errors))
    SKIPPED_TESTS=$((SKIPPED_TESTS + skipped))
    
    echo "总计: $tests, 通过: $passed, 失败: $((failures + errors)), 跳过: $skipped"
}

# 解析 Pytest 结果
parse_pytest_results() {
    local xml_file="$1"
    
    if [[ ! -f "$xml_file" ]]; then
        echo "无结果文件"
        return
    fi
    
    # Pytest XML 格式解析
    local tests=$(grep -o 'tests="[0-9]*"' "$xml_file" | grep -o '[0-9]*' || echo "0")
    local failures=$(grep -o 'failures="[0-9]*"' "$xml_file" | grep -o '[0-9]*' || echo "0")
    local errors=$(grep -o 'errors="[0-9]*"' "$xml_file" | grep -o '[0-9]*' || echo "0")
    local skipped=$(grep -o 'skipped="[0-9]*"' "$xml_file" | grep -o '[0-9]*' || echo "0")
    
    local passed=$((tests - failures - errors - skipped))
    
    # 更新全局统计
    TOTAL_TESTS=$((TOTAL_TESTS + tests))
    PASSED_TESTS=$((PASSED_TESTS + passed))
    FAILED_TESTS=$((FAILED_TESTS + failures + errors))
    SKIPPED_TESTS=$((SKIPPED_TESTS + skipped))
    
    echo "总计: $tests, 通过: $passed, 失败: $((failures + errors)), 跳过: $skipped"
}

# 生成综合测试报告
generate_comprehensive_report() {
    log_info "生成综合测试报告..."
    
    local report_file="$REPORTS_DIR/comprehensive_test_report.md"
    local summary_file="$REPORTS_DIR/test_summary.json"
    
    # 生成 Markdown 报告
    cat > "$report_file" << EOF
# SAGE Flow 测试执行报告

## 测试摘要

- **执行时间**: $(date)
- **总测试数**: $TOTAL_TESTS
- **通过测试**: $PASSED_TESTS
- **失败测试**: $FAILED_TESTS
- **跳过测试**: $SKIPPED_TESTS
- **成功率**: $(( TOTAL_TESTS > 0 ? (PASSED_TESTS * 100) / TOTAL_TESTS : 0 ))%

## 测试套件结果

### 单元测试
- 状态: $([ "$RUN_UNIT_TESTS" = "true" ] && echo "已执行" || echo "跳过")
- 报告: [unit_test_results.xml](unit_test_results.xml)
- 日志: [unit_test.log](unit_test.log)

### 集成测试
- 状态: $([ "$RUN_INTEGRATION_TESTS" = "true" ] && echo "已执行" || echo "跳过")
- 报告: [integration_test_results.xml](integration_test_results.xml)
- 日志: [integration_test.log](integration_test.log)

### CandyFlow 功能测试
- 状态: $([ "$RUN_CANDYFLOW_TESTS" = "true" ] && echo "已执行" || echo "跳过")
- 报告: [candyflow_test_results.xml](candyflow_test_results.xml)
- 日志: [candyflow_test.log](candyflow_test.log)

### Python API 测试
- 状态: $([ "$RUN_PYTHON_TESTS" = "true" ] && echo "已执行" || echo "跳过")
- 报告: [python_test_results.xml](python_test_results.xml)
- 日志: [python_test.log](python_test.log)

### 性能基准测试
- 状态: $([ "$RUN_PERFORMANCE_TESTS" = "true" ] && echo "已执行" || echo "跳过")
- 报告: [performance_test_results.xml](performance_test_results.xml)
- 日志: [performance_test.log](performance_test.log)

## 代码覆盖率
- 状态: $([ "$GENERATE_COVERAGE" = "true" ] && echo "已生成" || echo "跳过")
- 报告: [coverage/index.html](coverage/index.html)

## 环境信息

- **操作系统**: $(uname -a)
- **编译器**: $(gcc --version | head -n1)
- **Python**: $(python --version)
- **CMake**: $(cmake --version | head -n1)
- **并行任务数**: $PARALLEL_JOBS

## 构建信息

- **项目根目录**: $PROJECT_ROOT
- **构建目录**: $BUILD_DIR
- **构建类型**: $(cd "$BUILD_DIR" && grep CMAKE_BUILD_TYPE CMakeCache.txt | cut -d= -f2 || echo "未知")

EOF

    # 生成 JSON 摘要
    cat > "$summary_file" << EOF
{
  "execution_time": "$(date -Iseconds)",
  "total_tests": $TOTAL_TESTS,
  "passed_tests": $PASSED_TESTS,
  "failed_tests": $FAILED_TESTS,
  "skipped_tests": $SKIPPED_TESTS,
  "success_rate": $(( TOTAL_TESTS > 0 ? (PASSED_TESTS * 100) / TOTAL_TESTS : 0 )),
  "test_suites": {
    "unit_tests": $([ "$RUN_UNIT_TESTS" = "true" ] && echo "true" || echo "false"),
    "integration_tests": $([ "$RUN_INTEGRATION_TESTS" = "true" ] && echo "true" || echo "false"),
    "candyflow_tests": $([ "$RUN_CANDYFLOW_TESTS" = "true" ] && echo "true" || echo "false"),
    "python_tests": $([ "$RUN_PYTHON_TESTS" = "true" ] && echo "true" || echo "false"),
    "performance_tests": $([ "$RUN_PERFORMANCE_TESTS" = "true" ] && echo "true" || echo "false")
  },
  "coverage_generated": $([ "$GENERATE_COVERAGE" = "true" ] && echo "true" || echo "false"),
  "environment": {
    "os": "$(uname -s)",
    "arch": "$(uname -m)",
    "parallel_jobs": $PARALLEL_JOBS
  }
}
EOF

    log_success "综合测试报告已生成:"
    log_info "  Markdown 报告: $report_file"
    log_info "  JSON 摘要: $summary_file"
}

# 主函数
main() {
    local start_time=$(date +%s)
    
    # 检查环境
    check_build_directory || exit 1
    
    # 运行各种测试套件
    run_unit_tests || true
    run_integration_tests || true
    run_candyflow_tests || true
    run_python_tests || true
    run_performance_tests || true
    
    # 生成覆盖率报告
    generate_coverage_report || true
    
    # 生成综合报告
    generate_comprehensive_report
    
    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))
    
    # 显示最终结果
    echo ""
    log_success "测试执行完成！总耗时: ${total_duration}秒"
    echo ""
    log_info "测试统计:"
    log_info "  总计: $TOTAL_TESTS 个测试"
    log_info "  通过: $PASSED_TESTS 个测试"
    log_info "  失败: $FAILED_TESTS 个测试"
    log_info "  跳过: $SKIPPED_TESTS 个测试"
    
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        local success_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
        log_info "  成功率: ${success_rate}%"
        
        if [[ $success_rate -ge 90 ]]; then
            log_success "测试成功率优秀！"
        elif [[ $success_rate -ge 75 ]]; then
            log_warning "测试成功率良好，建议检查失败的测试"
        else
            log_error "测试成功率较低，需要修复失败的测试"
        fi
    fi
    
    echo ""
    log_info "详细报告请查看: $REPORTS_DIR/"
    
    # 返回适当的退出代码
    if [[ $FAILED_TESTS -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# 处理命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-unit)
            RUN_UNIT_TESTS="false"
            shift
            ;;
        --no-integration)
            RUN_INTEGRATION_TESTS="false"
            shift
            ;;
        --no-candyflow)
            RUN_CANDYFLOW_TESTS="false"
            shift
            ;;
        --no-python)
            RUN_PYTHON_TESTS="false"
            shift
            ;;
        --performance)
            RUN_PERFORMANCE_TESTS="true"
            shift
            ;;
        --coverage)
            GENERATE_COVERAGE="true"
            shift
            ;;
        --jobs)
            PARALLEL_JOBS="$2"
            shift 2
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo "选项:"
            echo "  --no-unit         跳过单元测试"
            echo "  --no-integration  跳过集成测试"
            echo "  --no-candyflow    跳过 CandyFlow 测试"
            echo "  --no-python       跳过 Python 测试"
            echo "  --performance     运行性能测试"
            echo "  --coverage        生成代码覆盖率报告"
            echo "  --jobs N          设置并行任务数"
            echo "  --help            显示帮助信息"
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            exit 1
            ;;
    esac
done

# 执行主函数
main "$@"