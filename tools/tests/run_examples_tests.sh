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
        echo -e "${YELLOW}⚠️ typer 或 rich 未安装。Examples 测试需要这些依赖，跳过测试${NC}"
        echo "💡 要运行完整的 Examples 测试，请运行: pip install -e packages/sage-tools[cli]"
        return 1
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
    
    # 安装 examples 的可选依赖（如果需要）
    if [[ "$CI" == "true" || -z "$CATEGORY" || "$CATEGORY" == "video" ]]; then
        echo "检查 Examples 可选依赖..."
        # 在 CI 环境或运行 video 测试时，安装 examples 依赖
        if ! python3 -c "import cv2" 2>/dev/null && [[ "$CATEGORY" == "video" || -z "$CATEGORY" ]]; then
            echo -e "${YELLOW}📦 安装 Examples 依赖（通过 sage-libs[examples]）...${NC}"
            # 优先尝试通过 sage-libs 安装
            if [[ -f "packages/sage-libs/pyproject.toml" ]]; then
                pip install -q -e "packages/sage-libs[examples]" 2>/dev/null || {
                    echo -e "${YELLOW}⚠️ 通过 sage-libs 安装失败，尝试使用 requirements.txt...${NC}"
                    if [[ -f "examples/requirements.txt" ]]; then
                        pip install -q -r examples/requirements.txt || {
                            echo -e "${YELLOW}⚠️ 无法安装所有 examples 依赖，某些示例可能被跳过${NC}"
                        }
                    fi
                }
            elif [[ -f "examples/requirements.txt" ]]; then
                pip install -q -r examples/requirements.txt || {
                    echo -e "${YELLOW}⚠️ 无法安装所有 examples 依赖，某些示例可能被跳过${NC}"
                }
            fi
        fi
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
    
    if $VERBOSE; then
        pytest_args+=("-s")  # 显示print输出
        pytest_args+=("-vv")  # 非常详细的输出
        pytest_args+=("--capture=no")  # 不捕获输出
        pytest_args+=("--showlocals")  # 在错误时显示局部变量
        pytest_args+=("--durations=10")  # 显示最慢的10个测试的时间
        pytest_args+=("--durations-min=1.0")  # 只显示超过1秒的测试时间
    else
        # CI环境：显示详细错误信息，便于调试
        if [[ "$CI" == "true" ]]; then
            pytest_args+=("--tb=short")  # 简短但有用的错误输出
            pytest_args+=("-v")  # 显示详细的测试名称
            pytest_args+=("-s")  # 不捕获输出，显示print语句
            pytest_args+=("--capture=no")  # 确保所有输出都被显示
            pytest_args+=("--durations=10")  # 显示最慢的10个测试
            pytest_args+=("--durations-min=5.0")  # 只显示超过5秒的测试
        else
            # 本地环境：适中的输出
            pytest_args+=("-v")
            pytest_args+=("-s")  # 允许我们的hooks输出显示
            pytest_args+=("--tb=line")  # 简化错误输出
            pytest_args+=("--durations=10")  # 显示最慢的10个测试的时间
            pytest_args+=("--durations-min=1.0")  # 只显示超过1秒的测试时间
        fi
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
    
    # 设置example运行的环境变量 - 让策略决定超时时间
    # 不在CI环境中设置固定的SAGE_EXAMPLE_TIMEOUT，让每个类别使用自己的策略超时
    if [[ "$CI" != "true" ]]; then
        export SAGE_EXAMPLE_TIMEOUT="${TIMEOUT}"
    fi
    
    # 在CI环境中启用test mode，让示例只运行第一个例子以加快测试速度
    if [[ "$CI" == "true" ]]; then
        export SAGE_EXAMPLES_MODE="test"
        export SAGE_LOG_LEVEL="ERROR"  # 减少日志输出
    fi
    
    if [[ "$CI" == "true" ]]; then
        echo "🧪 运行Examples测试 (CI模式)"
        echo "  - 快速模式: $(if $QUICK_ONLY; then echo "是"; else echo "否"; fi)"
        echo "  - 类别过滤: ${CATEGORY:-"无"}"
        echo "  - Example超时: 60秒"
    else
        echo "开始运行测试，将显示每个example的详细信息和运行时间..."
        echo "📊 测试配置:"
        echo "  - 快速模式: $(if $QUICK_ONLY; then echo "是"; else echo "否"; fi)"
        echo "  - 类别过滤: ${CATEGORY:-"无"}"
        echo "  - 详细输出: $(if $VERBOSE; then echo "是"; else echo "否"; fi)"
        echo "  - 测试套件超时: 无限制"
        echo "  - 单个Example超时: 60秒"
    fi
    echo ""
    
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
    
    # 如果测试失败，在CI环境中打印详细的失败信息
    if [[ $exit_code -ne 0 && "$CI" == "true" ]]; then
        echo ""
        echo "❌ Examples测试失败，收集详细失败信息..."
        echo "=========================================="
        
        # 直接从pytest输出中提取失败信息（如果有的话）
        echo "📋 主要错误信息已在上面显示"
        echo ""
        echo "� 额外调试信息:"
        echo "  - 测试运行在CI环境: $CI"
        echo "  - 测试模式: $SAGE_EXAMPLES_MODE"
        echo "  - 日志级别: $SAGE_LOG_LEVEL"
        echo ""
        
        # 显示一些系统信息
        echo "🖥️ 系统信息:"
        echo "  - Python版本: $(python3 --version)"
        echo "  - 工作目录: $(pwd)"
        echo "  - 示例目录存在: $(if [ -d examples ]; then echo '是'; else echo '否'; fi)"
        echo ""
        
        echo "💡 可能的解决方案:"
        echo "  - 检查API密钥是否正确配置 (OPENAI_API_KEY, etc.)"
        echo "  - 确认外部服务（如数据库、API）是否可访问"
        echo "  - 查看详细日志了解具体的错误原因"
        echo "  - 某些examples可能需要特定的环境配置"
        echo "  - 检查网络连接和外部依赖"
        echo "=========================================="
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
    
    if [[ "$CI" == "true" ]]; then
        echo "🧪 运行独立测试脚本 (CI模式)"
        echo "  - 快速模式: $(if $QUICK_ONLY; then echo "是"; else echo "否"; fi)"
        echo "  - 类别过滤: ${CATEGORY:-"无"}"
        echo "  - Example超时: 60秒"
    else
        echo "开始运行独立测试脚本..."
        echo "📊 测试配置:"
        echo "  - 快速模式: $(if $QUICK_ONLY; then echo "是"; else echo "否"; fi)"
        echo "  - 类别过滤: ${CATEGORY:-"无"}"
        echo "  - 详细输出: $(if $VERBOSE; then echo "是"; else echo "否"; fi)"
        echo "  - 测试套件超时: 无限制"
        echo "  - 单个Example超时: 60秒"
    fi
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

# 检查中间结果放置
# 检查中间结果放置
check_intermediate_results_placement() {
    echo -e "${BLUE}🔍 检查中间结果放置...${NC}"
    
    # 调用 Python 检查工具
    python3 "$SAGE_ROOT/tools/tests/check_intermediate_results.py" "$SAGE_ROOT"
    local exit_code=$?
    
    # 根据退出码显示结果
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}  ✅ 中间结果放置检查通过 - 项目根目录整洁${NC}"
    else
        echo -e "${RED}  ❌ 发现中间结果放置问题${NC}"
        echo -e "${BLUE}  💡 所有中间结果应该放置在 .sage/ 目录下以保持项目根目录整洁${NC}"
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
    
    # 检查中间结果放置
    echo ""
    echo "=================================================="
    check_intermediate_results_placement
    echo "=================================================="
    
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