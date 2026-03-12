#!/bin/bash
# SAGE 安装验证测试脚本
# 验证安装是否成功，检查核心组件和依赖


# ============================================================================
# 环境变量安全默认值（防止 set -u 报错）
# ============================================================================
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"
GITLAB_CI="${GITLAB_CI:-}"
JENKINS_URL="${JENKINS_URL:-}"
BUILDKITE="${BUILDKITE:-}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
CONDA_DEFAULT_ENV="${CONDA_DEFAULT_ENV:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
# ============================================================================

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 导入颜色定义
source "${SAGE_ROOT:-}/tools/install/display_tools/colors.sh"

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 打印测试标题
print_test_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# 运行单个测试
run_test() {
    local test_name="$1"
    local test_command="$2"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${DIM}测试 $TOTAL_TESTS: $test_name${NC}"

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 通过${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ 失败${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}


# 运行测试并显示输出
run_test_with_output() {
    local test_name="$1"
    local test_command="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${DIM}测试 $TOTAL_TESTS: $test_name${NC}"

    local output
    if output=$(eval "$test_command" 2>&1); then
        echo -e "${GREEN}✅ 通过${NC}"
        echo -e "${DIM}   输出: $output${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ 失败${NC}"
        echo -e "${DIM}   错误: $output${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 运行警告级测试（失败不会使脚本退出）
run_warning_test() {
    local test_name="$1"
    local test_command="$2"

    echo ""
    echo -e "${DIM}⚠️ 非阻断测试: $test_name${NC}"

    local output
    if output=$(eval "$test_command" 2>&1); then
        echo -e "${GREEN}✅ 非阻断测试通过${NC}"
        echo -e "${DIM}   输出: $output${NC}"
    else
        echo -e "${YELLOW}⚠️  非阻断测试失败（不影响结果）${NC}"
        echo -e "${DIM}   错误: $output${NC}"
    fi
}

# 主函数
main() {
    echo -e "${BLUE}${BOLD}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║                                                ║"
    echo "║       🧪 SAGE 安装验证测试                     ║"
    echo "║                                                ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # 1. Python 环境检查
    print_test_header "📦 1. Python 环境检查"
    run_test_with_output "Python 版本检查" "python3 --version"
    run_test "pip 可用性" "python3 -m pip --version"

    # 2. SAGE 核心包导入测试（主仓 in-tree 表面）
    print_test_header "🔧 2. SAGE 核心包导入测试"
    run_test "导入 sage.foundation" "python3 -c 'import sage.foundation'"
    run_test "导入 sage.stream" "python3 -c 'import sage.stream'"
    run_test "导入 sage.runtime" "python3 -c 'import sage.runtime'"
    run_test "导入 sage.serving" "python3 -c 'import sage.serving'"
    run_test_with_output "导入 sage.cli" "python3 -c 'import sage.cli; print(sage.cli.__version__)'"

    echo ""
    echo -e "${DIM}以下为过渡兼容命名空间，失败不影响主仓核心功能：${NC}"
    run_warning_test "导入 sage.common" "python3 -c 'import sage.common'"
    run_warning_test "导入 sage.kernel" "python3 -c 'import sage.kernel'"
    run_warning_test "导入 sage.libs" "python3 -c 'import sage.libs'"
    run_warning_test "导入 sage.middleware" "python3 -c 'import sage.middleware'"
    # Note: sage.llm has been moved to independent package isagellm
    # run_test "导入 isagellm" "python3 -c 'import isagellm'"  # optional

    # 3. 关键依赖检查
    print_test_header "📚 3. 关键依赖检查"
    run_test "numpy 可用" "python3 -c 'import numpy; print(numpy.__version__)'"

    # 可选依赖（standard/dev 模式都安装）
    echo ""
    echo -e "${DIM}以下为可选依赖，失败不影响核心功能：${NC}"
    run_warning_test "pandas 可用" "python3 -c 'import pandas'"
    run_warning_test "torch 可用" "python3 -c 'import torch'"
    run_warning_test "transformers 可用" "python3 -c 'import transformers'"

    # 4. 主仓版本与核心表面检查
    print_test_header "🔍 4. 版本一致性检查"
    run_test_with_output "子包版本一致性" "python3 -c 'from sage._version import __version__; import sage.cli; packages=[(\"isage\", __version__), (\"sage.cli\", sage.cli.__version__)]; print(\"包版本信息:\"); [print(f\"  {pkg}: {version}\") for pkg, version in packages]; print(\"✅ 主仓版本与 CLI 表面已检测\")'"

    # 5. CLI 工具检查
    print_test_header "🛠️ 5. CLI 工具检查"
    run_test "sage CLI 可用" "command -v sage"
    run_test "sage-dev CLI 可用" "command -v sage-dev"
    run_test_with_output "sage version" "sage version"

    # 6. 可选组件检查（不影响总体结果）
    print_test_header "🎯 6. 可选组件检查（非必需）"
    echo -e "${DIM}以下测试失败不影响核心功能${NC}"

    # SageLLM（核心推理引擎）
    if python3 -c "import sagellm" 2>/dev/null; then
        echo -e "${GREEN}✅ SageLLM 已安装${NC}"
    else
        echo -e "${YELLOW}⚠️  SageLLM 未安装（可选组件，LLM 推理引擎）${NC}"
    fi

    # CUDA（可选）
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${GREEN}✅ CUDA/NVIDIA 驱动已安装${NC}"
    else
        echo -e "${YELLOW}⚠️  CUDA/NVIDIA 驱动未检测到（可选）${NC}"
    fi

    # 7. 配置文件检查
    print_test_header "⚙️ 7. 配置文件检查"
    if [ -f "${SAGE_ROOT:-}/.env" ]; then
        echo -e "${GREEN}✅ .env 配置文件存在${NC}"

        # 检查关键 API keys
        if grep -q "OPENAI_API_KEY=" "${SAGE_ROOT:-}/.env" 2>/dev/null; then
            echo -e "${DIM}   • OPENAI_API_KEY 已配置${NC}"
        else
            echo -e "${YELLOW}   ⚠️  OPENAI_API_KEY 未配置${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  .env 配置文件不存在${NC}"
        echo -e "${DIM}   提示: 复制 .env.template 为 .env 并配置 API keys${NC}"
    fi

    # 8. 示例测试（快速验证）
    print_test_header "🎓 8. 快速示例测试"
    if [ -f "${SAGE_ROOT:-}/tools/verify_hello_world.py" ]; then
        echo -e "${DIM}运行 verify_hello_world.py...${NC}"
        if python3 "${SAGE_ROOT:-}/tools/verify_hello_world.py" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ verify_hello_world.py 运行成功${NC}"
        else
            echo -e "${YELLOW}⚠️  verify_hello_world.py 运行失败${NC}"
            echo -e "${DIM}   请检查核心包是否正确安装${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  verify_hello_world.py 未找到${NC}"
    fi

    # 9. 环境健康与隔离检查
    print_test_header "🛡️ 9. 环境健康与隔离检查"
    run_warning_test "pip 依赖一致性（可选）" "python3 -m pip check"
    run_test_with_output "pip 缓存目录" "python3 -m pip cache dir"
    run_test_with_output "Python 安装前缀" "python3 -c 'import sys; print(sys.prefix)'"
    run_test_with_output "PYTHONNOUSERSITE 标志" "python3 -c 'import os; print(os.environ.get(\"PYTHONNOUSERSITE\", \"<未设置>\"))'"

    # 10. 打印测试总结
    print_test_header "📊 测试总结"
    echo -e "${BOLD}总测试数: $TOTAL_TESTS${NC}"
    echo -e "${GREEN}✅ 通过: $PASSED_TESTS${NC}"
    echo -e "${RED}❌ 失败: $FAILED_TESTS${NC}"

    local pass_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo ""
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}${BOLD}🎉 所有测试通过！SAGE 安装验证成功！${NC}"
        echo ""
        echo -e "${DIM}下一步:${NC}"
        echo -e "${DIM}  1. 配置 API keys: cp .env.template .env${NC}"
        echo -e "${DIM}  2. 运行验证: python tools/verify_hello_world.py${NC}"
        echo -e "${DIM}  3. 查看文档: https://intellistream.github.io/sage-docs/${NC}"
        return 0
    elif [ $pass_rate -ge 80 ]; then
        echo -e "${YELLOW}⚠️  大部分测试通过 (${pass_rate}%)，但有部分失败${NC}"
        echo -e "${DIM}SAGE 核心功能可能可用，请检查失败的测试项${NC}"
        return 1
    else
        echo -e "${RED}❌ 多项测试失败 (${pass_rate}% 通过率)${NC}"
        echo -e "${DIM}请重新安装或运行故障排查工具${NC}"
        echo -e "${DIM}  ./quickstart.sh --doctor --fix${NC}"
        return 1
    fi
}

# 运行主函数
main "$@"
