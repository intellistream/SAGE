#!/bin/bash
#
# SAGE Framework 快速测试脚本
# 针对常见测试问题进行优化
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 颜色输出函数
log_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
log_warning() { echo -e "\033[1;33m[WARNING]\033[0m $1"; }
log_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

echo "🧪 Running unit tests..."
echo "📊 Using unified test runner..."

# 测试配置
declare -A PACKAGES=(
    ["sage-common"]="packages/sage-common"
    ["sage-libs"]="packages/sage-libs"  
    ["sage-middleware"]="packages/sage-middleware"
    ["sage-kernel"]="packages/sage-kernel"
)

PASSED=0
FAILED=0
TOTAL=${#PACKAGES[@]}
TIMEOUT=180  # 增加超时时间到180秒
PARALLEL_JOBS=4

log_info "发现 $TOTAL 个包: ${!PACKAGES[*]}"
log_info "测试类型: unit"
log_info "并行任务: $PARALLEL_JOBS"
log_info "超时时间: ${TIMEOUT}秒"

# 测试结果数组
declare -A TEST_RESULTS

# 运行单个包的测试
test_package() {
    local pkg_name="$1"
    local pkg_path="$2"
    local full_path="$PROJECT_ROOT/$pkg_path"
    
    if [[ ! -d "$full_path" ]]; then
        TEST_RESULTS["$pkg_name"]="NO_PACKAGE"
        return 1
    fi
    
    cd "$full_path"
    
    # 检查测试目录
    if [[ ! -d "tests" ]] || [[ $(find tests -name "*.py" | wc -l) -eq 0 ]]; then
        TEST_RESULTS["$pkg_name"]="NO_TESTS"
        return 0
    fi
    
    # 根据包选择测试策略
    local test_cmd
    case "$pkg_name" in
        "sage-kernel")
            # sage-kernel: 排除slow测试，增加超时时间，覆盖pytest.ini中的超时设置
            test_cmd="timeout $TIMEOUT python -m pytest tests/ -v -m 'not slow and not ray' --tb=short -x --disable-warnings --timeout=300"
            ;;
        "sage-common")
            # sage-common: 运行基础测试
            test_cmd="timeout $TIMEOUT python -m pytest tests/ -v --tb=short --disable-warnings"
            ;;
        *)
            # 其他包: 标准单元测试
            if [[ -f "tests/run_tests.py" ]]; then
                test_cmd="cd tests && timeout $TIMEOUT python run_tests.py --unit"
            else
                test_cmd="timeout $TIMEOUT python -m pytest tests/ -v -m 'not slow' --tb=short --disable-warnings"
            fi
            ;;
    esac
    
    # 执行测试并捕获退出码
    local exit_code
    eval "$test_cmd" >/dev/null 2>&1
    exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        TEST_RESULTS["$pkg_name"]="PASSED"
        return 0
    elif [[ $exit_code -eq 124 ]]; then
        # timeout命令的退出码124表示超时
        TEST_RESULTS["$pkg_name"]="TIMEOUT"
        return 1
    else
        TEST_RESULTS["$pkg_name"]="FAILED"
        return 1
    fi
}

# 并行运行测试
pids=()
for pkg_name in "${!PACKAGES[@]}"; do
    pkg_path="${PACKAGES[$pkg_name]}"
    test_package "$pkg_name" "$pkg_path" &
    pids+=($!)
done

# 等待所有测试完成
for pid in "${pids[@]}"; do
    wait "$pid" || true
done

# 输出结果
for pkg_name in "${!PACKAGES[@]}"; do
    result="${TEST_RESULTS[$pkg_name]}"
    case "$result" in
        "PASSED")
            echo "✅ $pkg_name: PASSED"
            ((PASSED++))
            ;;
        "FAILED")
            echo "❌ $pkg_name: FAILED"
            ((FAILED++))
            ;;
        "NO_TESTS")
            echo "⚠️ $pkg_name: NO_TESTS"
            ;;
        "NO_PACKAGE")
            echo "❓ $pkg_name: NO_PACKAGE"
            ((FAILED++))
            ;;
        *)
            echo "⏰ $pkg_name: TIMEOUT"
            ((FAILED++))
            ;;
    esac
done

# 生成报告
REPORT_FILE="unit_test_report.html"
cat > "$REPORT_FILE" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>SAGE Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .passed { color: green; }
        .failed { color: red; }
        .warning { color: orange; }
        .summary { background: #f5f5f5; padding: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>SAGE Framework Test Report</h1>
    <div class="summary">
        <h2>测试摘要</h2>
        <p>总包数: $TOTAL</p>
        <p>通过: $PASSED</p>
        <p>失败: $FAILED</p>
        <p>通过率: $(( PASSED * 100 / TOTAL ))%</p>
    </div>
    <h2>详细结果</h2>
    <ul>
EOF

for pkg_name in "${!PACKAGES[@]}"; do
    result="${TEST_RESULTS[$pkg_name]}"
    case "$result" in
        "PASSED")
            echo "        <li class=\"passed\">✅ $pkg_name: PASSED</li>" >> "$REPORT_FILE"
            ;;
        "FAILED")
            echo "        <li class=\"failed\">❌ $pkg_name: FAILED</li>" >> "$REPORT_FILE"
            ;;
        *)
            echo "        <li class=\"warning\">⚠️ $pkg_name: $result</li>" >> "$REPORT_FILE"
            ;;
    esac
done

cat >> "$REPORT_FILE" << EOF
    </ul>
</body>
</html>
EOF

log_info "报告已保存到: $REPORT_FILE"

# 输出最终结果
echo ""
echo "📊 测试摘要: $PASSED/$TOTAL 通过"

if [[ $FAILED -eq 0 ]]; then
    log_success "所有测试通过!"
    echo "[SUCCESS] 所有测试通过!"
    exit 0
else
    log_warning "$FAILED 个包测试失败"
    echo "[FAILED] $FAILED 个包测试失败"
    exit 1
fi
