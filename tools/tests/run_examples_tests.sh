#!/bin/bash
# SAGE Examples 测试运行脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
SAGE_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$SAGE_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo -e "${BLUE}SAGE Examples 测试工具${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示此帮助信息"
    echo "  -a, --analyze           只分析示例，不运行测试"
    echo "  -q, --quick             只运行快速测试"
    echo "  -c, --category CAT      指定测试类别 (tutorials,rag,memory,service,video)"
    echo "  -k, --keyword PATTERN   pytest关键字过滤（仅pytest模式）"
    echo "  -t, --timeout SEC       设置测试超时时间（秒）"
    echo "  -o, --output FILE       保存测试结果到文件"
    echo "  -v, --verbose           详细输出"
    echo "  --pytest               使用 pytest 运行（推荐）"
    echo "  --standalone            使用独立脚本运行"
    echo ""
    echo "示例:"
    echo "  $0 --quick                    # 运行所有快速测试"
    echo "  $0 --category tutorials       # 只测试教程示例"
    echo "  $0 --pytest --quick          # 用 pytest 运行快速测试"
    echo "  $0 -k test_examples_discovery # 运行特定测试"
    echo "  $0 --analyze                  # 只分析示例结构"
}

# 默认参数
ANALYZE_ONLY=false
QUICK_ONLY=false
CATEGORY=""
KEYWORD=""
# 根据环境设置默认超时：CI环境有超时，本地无超时
if [[ "$CI" == "true" ]]; then
    TIMEOUT=300  # CI环境默认5分钟超时
else
    TIMEOUT=0    # 本地环境默认无超时
fi
OUTPUT_FILE=""
VERBOSE=false
USE_PYTEST=true
STANDALONE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -a|--analyze)
            ANALYZE_ONLY=true
            shift
            ;;
        -q|--quick)
            QUICK_ONLY=true
            shift
            ;;
        -c|--category)
            CATEGORY="$2"
            shift 2
            ;;
        -k|--keyword)
            KEYWORD="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --pytest)
            USE_PYTEST=true
            STANDALONE=false
            shift
            ;;
        --standalone)
            USE_PYTEST=false
            STANDALONE=true
            shift
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 检查环境
check_environment() {
    echo -e "${BLUE}🔧 检查环境...${NC}"
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 未找到${NC}"
        exit 1
    fi
    
    # 检查必要的包
    echo "检查依赖包..."
    python3 -c "import typer, rich" 2>/dev/null || {
        echo -e "${RED}❌ typer 或 rich 未安装。请运行: pip install -e packages/sage-tools[cli]${NC}"
        exit 1
    }
    
    if $USE_PYTEST; then
        python3 -c "import pytest" 2>/dev/null || {
            echo -e "${RED}❌ pytest 未安装。请运行: pip install -e packages/sage-tools[dev]${NC}"
            exit 1
        }
        python3 -c "import pytest_timeout" 2>/dev/null || {
            echo -e "${RED}❌ pytest-timeout 未安装。请运行: pip install -e packages/sage-tools[dev]${NC}"
            exit 1
        }
    fi
    
    echo -e "${GREEN}✅ 环境检查完成${NC}"
}

# 运行分析
run_analysis() {
    echo -e "${BLUE}📊 分析 Examples 目录...${NC}"
    python3 tools/tests/test_examples.py analyze
}

# 使用 pytest 运行测试
run_pytest_tests() {
    echo -e "${BLUE}🚀 使用 pytest 运行测试...${NC}"
    
    local pytest_args=("-v")
    
    # 根据配置添加标记
    if $QUICK_ONLY; then
        if [[ -n "$CATEGORY" ]]; then
            # 使用关键字过滤，结合quick_examples标记和类别
            pytest_args+=("-m" "quick_examples" "-k" "$CATEGORY")
        else
            # 只运行有quick_examples标记的测试
            pytest_args+=("-m" "quick_examples")
        fi
    elif [[ -n "$CATEGORY" ]]; then
        # 只按类别过滤，不限制是否为快速测试
        pytest_args+=("-k" "$CATEGORY")
    else
        # 运行所有examples测试（包括slow测试，这样才是真正的"全部"）
        pytest_args+=("-m" "examples")
    fi
    
    # 添加关键字过滤（如果指定了的话）
    if [[ -n "$KEYWORD" ]]; then
        if [[ "${pytest_args[@]}" =~ "-k" ]]; then
            # 如果已经有-k参数，需要组合条件
            for i in "${!pytest_args[@]}"; do
                if [[ "${pytest_args[$i]}" == "-k" ]]; then
                    pytest_args[$((i+1))]="${pytest_args[$((i+1))]} and $KEYWORD"
                    break
                fi
            done
        else
            # 添加新的-k参数
            pytest_args+=("-k" "$KEYWORD")
        fi
    fi
    
    # 添加详细输出和时间显示
    pytest_args+=("--tb=short")  # 简短的错误回溯
    pytest_args+=("--durations=10")  # 显示最慢的10个测试的时间
    pytest_args+=("--durations-min=1.0")  # 只显示超过1秒的测试时间
    
    if $VERBOSE; then
        pytest_args+=("-s")  # 显示print输出
        pytest_args+=("-vv")  # 非常详细的输出
        pytest_args+=("--capture=no")  # 不捕获输出
        pytest_args+=("--showlocals")  # 在错误时显示局部变量
    else
        # 默认显示详细的测试名称和状态，但仍然捕获输出以保持实时进度显示清晰
        pytest_args+=("-v")
        pytest_args+=("-s")  # 允许我们的hooks输出显示
        pytest_args+=("--tb=line")  # 简化错误输出
    fi
    
    # 添加实时进度显示
    pytest_args+=("--disable-warnings")  # 减少噪音
    
    # 如果CI环境，添加颜色输出
    if [[ "$CI" == "true" ]]; then
        pytest_args+=("--color=yes")
    fi
    
    # 添加超时设置 - 移除pytest整体超时，让测试套件可以无限制运行
    # 单个example的超时通过环境变量SAGE_EXAMPLE_TIMEOUT控制（统一60秒）
    
    # 运行测试
    cd tools/tests
    echo "开始运行测试，将显示每个example的详细信息和运行时间..."
    echo "📊 测试配置:"
    echo "  - 快速模式: $(if $QUICK_ONLY; then echo "是"; else echo "否"; fi)"
    echo "  - 类别过滤: ${CATEGORY:-"无"}"
    echo "  - 详细输出: $(if $VERBOSE; then echo "是"; else echo "否"; fi)"
    echo "  - 测试套件超时: 无限制"
    echo "  - 单个Example超时: 60秒"
    echo ""
    
    # 设置example运行的超时环境变量 - 统一设置为60秒
    export SAGE_EXAMPLE_TIMEOUT="60"
    echo "  - Example超时: 60秒 (统一配置)"
    
    # 运行pytest并处理输出
    if [[ -n "$OUTPUT_FILE" ]]; then
        # 如果指定了输出文件，同时输出到文件和控制台
        python3 -m pytest "${pytest_args[@]}" test_examples_pytest.py 2>&1 | tee "$OUTPUT_FILE"
        local exit_code=${PIPESTATUS[0]}
    else
        # 直接输出到控制台
        python3 -m pytest "${pytest_args[@]}" test_examples_pytest.py
        local exit_code=$?
    fi
    
    return $exit_code
}

# 使用独立脚本运行测试
run_standalone_tests() {
    echo -e "${BLUE}🚀 使用独立脚本运行测试...${NC}"
    
    local cmd_args=()
    
    if $QUICK_ONLY; then
        cmd_args+=("--quick")
    fi
    
    if [[ -n "$CATEGORY" ]]; then
        cmd_args+=("--category" "$CATEGORY")
    fi
    
    if [[ -n "$OUTPUT_FILE" ]]; then
        cmd_args+=("--output" "$OUTPUT_FILE")
    fi
    
    cmd_args+=("--timeout" "$TIMEOUT")
    
    if $VERBOSE; then
        cmd_args+=("--verbose")
    fi
    
    echo "开始运行独立测试脚本..."
    echo "📊 测试配置:"
    echo "  - 快速模式: $(if $QUICK_ONLY; then echo "是"; else echo "否"; fi)"
    echo "  - 类别过滤: ${CATEGORY:-"无"}"
    echo "  - 详细输出: $(if $VERBOSE; then echo "是"; else echo "否"; fi)"
    echo "  - 测试套件超时: 无限制"
    echo "  - 单个Example超时: 60秒"
    echo ""
    
    python3 tools/tests/test_examples.py test "${cmd_args[@]}"
    return $?
}

# 显示测试统计
show_statistics() {
    echo -e "${BLUE}📈 生成测试报告...${NC}"
    
    if [[ -f "$OUTPUT_FILE" ]]; then
        echo -e "${GREEN}测试结果已保存到: $OUTPUT_FILE${NC}"
        
        # 解析pytest输出获取统计信息
        echo ""
        echo -e "${BLUE}测试统计:${NC}"
        
        # 提取基本统计信息
        if grep -q "passed" "$OUTPUT_FILE"; then
            local passed=$(grep -o '[0-9]* passed' "$OUTPUT_FILE" | head -1 | cut -d' ' -f1)
            echo "  ✅ 通过: ${passed:-0}"
        fi
        
        if grep -q "failed" "$OUTPUT_FILE"; then
            local failed=$(grep -o '[0-9]* failed' "$OUTPUT_FILE" | head -1 | cut -d' ' -f1)
            echo "  ❌ 失败: ${failed:-0}"
        fi
        
        if grep -q "skipped" "$OUTPUT_FILE"; then
            local skipped=$(grep -o '[0-9]* skipped' "$OUTPUT_FILE" | head -1 | cut -d' ' -f1)
            echo "  ⏭️  跳过: ${skipped:-0}"
        fi
        
        if grep -q "deselected" "$OUTPUT_FILE"; then
            local deselected=$(grep -o '[0-9]* deselected' "$OUTPUT_FILE" | head -1 | cut -d' ' -f1)
            echo "  🚫 未选择: ${deselected:-0}"
        fi
        
        # 提取运行时间
        if grep -q "in [0-9]*\.[0-9]*s" "$OUTPUT_FILE"; then
            local duration=$(grep -o 'in [0-9]*\.[0-9]*s' "$OUTPUT_FILE" | tail -1 | sed 's/in //')
            echo "  ⏱️  总耗时: $duration"
        fi
        
        # 显示最慢的测试
        echo ""
        echo -e "${BLUE}最慢的测试:${NC}"
        grep "^[0-9]*\.[0-9]*s" "$OUTPUT_FILE" | head -5 || echo "  (无超过1秒的测试)"
        
    else
        echo -e "${YELLOW}⚠️ 没有找到输出文件${NC}"
    fi
}

# 主函数
main() {
    echo -e "${GREEN}🔥 SAGE Examples 测试工具${NC}"
    echo "==============================="
    
    check_environment
    
    if $ANALYZE_ONLY; then
        run_analysis
        exit 0
    fi
    
    echo ""
    echo -e "${BLUE}配置:${NC}"
    echo "  测试模式: $(if $USE_PYTEST; then echo "pytest"; else echo "独立脚本"; fi)"
    echo "  快速模式: $(if $QUICK_ONLY; then echo "是"; else echo "否"; fi)"
    echo "  类别: ${CATEGORY:-"全部"}"
    echo "  测试套件超时: 无限制"
    echo "  单个Example超时: 60秒"
    if [[ -n "$OUTPUT_FILE" ]]; then
        echo "  输出文件: $OUTPUT_FILE"
    fi
    echo ""
    
    # 运行测试
    local test_exit_code=0
    if $USE_PYTEST; then
        run_pytest_tests
        test_exit_code=$?
    else
        run_standalone_tests
        test_exit_code=$?
    fi
    
    # 显示统计（对所有模式都显示，如果有输出文件的话）
    if [[ -n "$OUTPUT_FILE" ]]; then
        show_statistics
    fi
    
    echo ""
    if [ $test_exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ 测试完成!${NC}"
    else
        echo -e "${RED}❌ 测试失败! 退出码: $test_exit_code${NC}"
        
        # 在CI环境中，提供额外的故障处理信息
        if [[ "$CI" == "true" ]]; then
            echo -e "${YELLOW}💡 CI环境故障提示:${NC}"
            echo "  - 某些examples可能因缺少API密钥而失败"
            echo "  - 网络相关的examples可能因连接问题而失败"
            echo "  - 查看详细日志以确定具体失败原因"
        fi
    fi
    
    exit $test_exit_code
}

# 错误处理
trap 'echo -e "${RED}❌ 测试被中断${NC}"; exit 1' INT TERM

# 运行主函数
main "$@"