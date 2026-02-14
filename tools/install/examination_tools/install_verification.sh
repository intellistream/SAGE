#!/bin/bash
# SAGE 安装验证模块
# 实现全面的安装验证：hello_world 测试、CLI 检查、依赖验证、报告生成

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 设置 Python 命令（使用安装过程中设置的环境变量）

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

PYTHON_CMD="${PYTHON_CMD:-python3}"
SAGE_ENV_NAME="${SAGE_ENV_NAME:-}"  # 可能由安装流程设置

# 验证常量
VERIFICATION_LOG=".sage/install_verification.log"
HELLO_WORLD_SCRIPT="tools/verify_hello_world.py"

# 验证结果状态
VERIFICATION_PASSED=true
VERIFICATION_RESULTS=()

# 从 PYTHON_CMD 中推断 conda 环境名称（例如 "conda run -n sage python"）
detect_conda_env_from_python_cmd() {
    if [[ "$PYTHON_CMD" =~ conda[[:space:]]+run[[:space:]]+-n[[:space:]]+([^[:space:]]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    fi
}

# 检查 conda 环境是否存在
conda_env_exists() {
    local env_name="$1"
    if [ -z "$env_name" ]; then
        return 1
    fi
    if ! command -v conda >/dev/null 2>&1; then
        return 1
    fi
    conda env list 2>/dev/null | grep -q "^${env_name} " || \
    conda env list 2>/dev/null | grep -q "^${env_name}$"
}

get_sage_cli_env() {
    if [ -n "${SAGE_ENV_NAME:-}" ]; then
        # 验证环境是否存在
        if conda_env_exists "${SAGE_ENV_NAME:-}"; then
            echo "${SAGE_ENV_NAME:-}"
            return
        fi
    fi

    local detected
    detected=$(detect_conda_env_from_python_cmd)
    if [ -n "$detected" ] && conda_env_exists "$detected"; then
        echo "$detected"
    fi
}

run_sage_dev() {
    local env_name
    env_name=$(get_sage_cli_env)

    if [ -n "$env_name" ] && command -v conda >/dev/null 2>&1; then
        conda run -n "$env_name" sage-dev "$@"
    else
        # 对于 pip 安装，CLI 工具可能在 ~/.local/bin 中
        if command -v sage-dev >/dev/null 2>&1; then
            sage-dev "$@"
        elif [ -x "$HOME/.local/bin/sage-dev" ]; then
            "$HOME/.local/bin/sage-dev" "$@"
        else
            echo "sage-dev 命令不可用" >&2
            return 1
        fi
    fi
}

sage_dev_available() {
    local env_name
    env_name=$(get_sage_cli_env)

    if [ -n "$env_name" ] && command -v conda >/dev/null 2>&1; then
        conda run -n "$env_name" which sage-dev >/dev/null 2>&1
    else
        # 检查 sage-dev 命令是否可用
        # 对于 pip 安装，CLI 工具可能在 ~/.local/bin 中
        if command -v sage-dev >/dev/null 2>&1; then
            return 0
        elif [ -x "$HOME/.local/bin/sage-dev" ]; then
            return 0
        else
            return 1
        fi
    fi
}

# 记录验证结果
log_verification_result() {
    local test_name="$1"
    local status="$2"
    local details="$3"

    VERIFICATION_RESULTS+=("$test_name|$status|$details")

    if [ "$status" = "FAIL" ]; then
        VERIFICATION_PASSED=false
    fi

    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [$status] $test_name: $details" >> "$VERIFICATION_LOG"
}

# 初始化验证日志
init_verification_log() {
    mkdir -p "$(dirname "$VERIFICATION_LOG")"

    cat > "$VERIFICATION_LOG" << EOF
# SAGE 安装验证报告
生成时间: $(date)
安装环境: $(uname -s) $(uname -r)
Python 命令: $PYTHON_CMD
Python 版本: $($PYTHON_CMD --version 2>&1 || echo "未安装")
SAGE 包版本: $($PYTHON_CMD -c "import sage.common; print(sage.common.__version__)" 2>/dev/null || echo "未安装")
注意: SAGE 使用 PEP 420 namespace，各包版本独立（sage.common, sage.kernel 等）

================================================================================
EOF

    echo -e "${BLUE}📋 初始化验证日志: $VERIFICATION_LOG${NC}"
}

# 验证 hello_world 示例
# Uses tools/verify_hello_world.py - a minimal verification script in SAGE core repo
verify_hello_world() {
    echo -e "${BLUE}🧪 运行 hello_world 测试...${NC}"

    if [ ! -f "$HELLO_WORLD_SCRIPT" ]; then
        log_verification_result "hello_world" "FAIL" "verify_hello_world.py 文件不存在"
        echo -e "${RED}   ❌ verify_hello_world.py 文件不存在${NC}"
        return 1
    fi

    # 运行验证脚本
    local output
    output=$($PYTHON_CMD "$HELLO_WORLD_SCRIPT" 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_verification_result "hello_world" "PASS" "verify_hello_world.py 执行成功"
        echo -e "${GREEN}   ✅ verify_hello_world.py 执行成功${NC}"
        echo -e "${DIM}   输出: $(echo "$output" | grep -E "^✅" | head -3 | tr '\n' ' ')${NC}"
        return 0
    else
        log_verification_result "hello_world" "FAIL" "verify_hello_world.py 执行失败"
        echo -e "${RED}   ❌ verify_hello_world.py 执行失败${NC}"
        echo -e "${DIM}   错误: $(echo "$output" | grep -E "^❌" | head -3 | tr '\n' ' ')${NC}"
        return 1
    fi
}

# 验证 sage doctor 命令
verify_sage_doctor() {
    echo -e "${BLUE}🩺 验证 sage doctor 命令...${NC}"

    # 检查 sage-dev 命令是否存在
    if ! sage_dev_available; then
        log_verification_result "sage_doctor" "FAIL" "sage-dev 命令不可用"
        echo -e "${RED}   ❌ sage-dev 命令不可用${NC}"
        return 1
    fi

    # 运行 sage maintain doctor（新命令结构）
    local output
    output=$(run_sage_dev maintain doctor 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_verification_result "sage_doctor" "PASS" "sage-dev maintain doctor 执行成功"
        echo -e "${GREEN}   ✅ sage-dev maintain doctor 执行成功${NC}"
        return 0
    else
        log_verification_result "sage_doctor" "WARN" "sage-dev maintain doctor 执行失败: $output"
        echo -e "${YELLOW}   ⚠️  sage-dev maintain doctor 执行失败${NC}"
        echo -e "${DIM}   错误: $output${NC}"
        return 1
    fi
}

# 验证 CLI 命令
verify_cli_commands() {
    echo -e "${BLUE}🔧 验证 CLI 命令...${NC}"

    local failed_commands=()

    # 验证 sage-dev 命令
    if sage_dev_available; then
        echo -e "${GREEN}   ✅ sage-dev 命令可用${NC}"
    else
        echo -e "${RED}   ❌ sage-dev 命令不可用${NC}"
        failed_commands+=("sage-dev")
    fi

    # 验证 Python 命令（使用 PYTHON_CMD）
    if $PYTHON_CMD --version &> /dev/null; then
        local py_version=$($PYTHON_CMD --version 2>&1)
        echo -e "${GREEN}   ✅ Python 命令可用 ($py_version)${NC}"
    else
        echo -e "${RED}   ❌ Python 命令不可用 ($PYTHON_CMD)${NC}"
        failed_commands+=("python")
    fi

    if [ ${#failed_commands[@]} -eq 0 ]; then
        log_verification_result "cli_commands" "PASS" "所有 CLI 命令可用"
        return 0
    else
        log_verification_result "cli_commands" "FAIL" "CLI 命令不可用: ${failed_commands[*]}"
        return 1
    fi
}

# 验证依赖版本兼容性
verify_dependency_versions() {
    echo -e "${BLUE}📦 验证依赖版本兼容性...${NC}"

    local critical_deps=("torch" "numpy" "transformers")
    local version_issues=()

    for dep in "${critical_deps[@]}"; do
        if $PYTHON_CMD -c "import $dep; print($dep.__version__)" &> /dev/null; then
            local version=$($PYTHON_CMD -c "import $dep; print($dep.__version__)" 2>/dev/null)
            echo -e "${GREEN}   ✅ $dep $version 已安装${NC}"
        else
            echo -e "${RED}   ❌ $dep 未安装或导入失败${NC}"
            version_issues+=("$dep")
        fi
    done

    # 检查版本兼容性
    if $PYTHON_CMD -c "
import sys
try:
    import torch
    import numpy as np
    import transformers

    # 检查 PyTorch CUDA 版本
    if torch.cuda.is_available():
        cuda_version = torch.version.cuda
        print(f'PyTorch CUDA 版本: {cuda_version}')

    # 检查 NumPy 版本
    numpy_version = np.__version__
    if numpy_version.startswith('2.'):
        print(f'NumPy 2.x 版本: {numpy_version}')
    else:
        print(f'警告: NumPy 版本 {numpy_version} 可能不兼容')
        sys.exit(1)

    print('依赖版本检查通过')

except Exception as e:
    print(f'版本兼容性检查失败: {e}')
    sys.exit(1)
" 2>/dev/null; then
        log_verification_result "dependency_versions" "PASS" "依赖版本兼容"
        return 0
    else
        log_verification_result "dependency_versions" "WARN" "依赖版本可能存在兼容性问题"
        return 1
    fi
}

# 验证 SAGE 包导入
verify_sage_imports() {
    echo -e "${BLUE}📚 验证 SAGE 包导入...${NC}"

    # PEP 420 Namespace Package Note:
    # SAGE uses PEP 420 native namespace packages (no src/sage/__init__.py)
    # This allows multiple independent packages to share the 'sage.*' namespace
    # NOTE: External packages (e.g., sage-benchmark from PyPI) may still use
    #       old-style pkgutil namespace, which can hijack the namespace

    # Check if sage namespace is hijacked by external packages (should not have __file__ in PEP 420)
    if $PYTHON_CMD -c "import sage; hasattr(sage, '__file__')" 2>/dev/null | grep -q "True"; then
        local hijacker=$($PYTHON_CMD -c "import sage; print(getattr(sage, '__file__', 'unknown'))" 2>/dev/null)
        echo -e "${YELLOW}   ⚠️  sage namespace has __file__ (PEP 420 violation): $hijacker${NC}"
        echo -e "${DIM}      This indicates an external package is hijacking the namespace${NC}"
        echo -e "${DIM}      Consider updating or uninstalling the conflicting package${NC}"
        echo ""
    fi

    # 核心包列表：按层级顺序验证
    # L1: sage-common
    # L2: sage-platform
    # L3: sage-kernel, sage-libs
    # L4: sage-middleware
    # L5: sage-cli, sage-tools
    # NOTE: PEP 420 namespace packages - 'sage' namespace is implicit, cannot be imported directly
    # We only verify actual packages under the namespace
    #
    # 已独立的包（不再验证）:
    # - sageLLM: 独立 PyPI 包 isagellm (pip install isagellm)
    # - sage-examples (原 sage.apps): 已迁移到 sage-examples 仓库
    # - sage.benchmark: 独立 PyPI 包 isage-benchmark (pip install isage-benchmark)
    # - sage.studio: 独立仓库 https://github.com/intellistream/sage-studio
    # - sage.edge: 独立 PyPI 包 isage-edge (pip install isage-edge)
    local sage_packages=(
        "sage.common"             # L1: Foundation
        "sage.platform"           # L2: Platform
        "sage.kernel"             # L3: Kernel
        "sage.libs"               # L3: Libraries
        "sage.middleware"         # L4: Middleware (C++ extensions)
        "sage.cli"                # L5: CLI (optional)
        "sage.tools"              # L5: Dev Tools (optional)
    )
    local failed_imports=()
    local optional_failed=()

    for pkg in "${sage_packages[@]}"; do
        # 判断是否为可选包（L5 层 CLI/Tools）
        local is_optional=false
        if [[ "$pkg" =~ ^sage\.(cli|tools)$ ]]; then
            is_optional=true
        fi

        # 使用转义避免 shell 变量展开问题
        if $PYTHON_CMD -c "import ${pkg}; print('${pkg}', ${pkg}.__version__)" &> /dev/null; then
            local version=$($PYTHON_CMD -c "import ${pkg}; print(${pkg}.__version__)" 2>/dev/null)
            echo -e "${GREEN}   ✅ $pkg $version 导入成功${NC}"
        else
            # 获取详细的导入错误信息
            local import_error=$($PYTHON_CMD -c "import ${pkg}" 2>&1 | head -n 10)

            if [ "$is_optional" = true ]; then
                echo -e "${YELLOW}   ⚠️  $pkg 导入失败（可选包）${NC}"
                optional_failed+=("$pkg")
            else
                echo -e "${RED}   ❌ $pkg 导入失败${NC}"

                # 显示详细错误信息（缩进）
                if [ -n "$import_error" ]; then
                    echo -e "${DIM}      错误详情:${NC}"
                    echo "$import_error" | sed 's/^/      /' | head -n 5
                fi

                # 针对特定包提供诊断提示
                case "$pkg" in
                    "sage.middleware")
                        echo -e "${DIM}      💡 诊断提示:${NC}"
                        echo -e "${DIM}         • 检查 packages/sage-middleware 是否存在${NC}"
                        echo -e "${DIM}         • 运行: pip show isage-middleware${NC}"
                        echo -e "${DIM}         • 如未安装，运行: pip install -e packages/sage-middleware${NC}"
                        ;;
                    "sage.kernel")
                        echo -e "${DIM}      💡 诊断提示:${NC}"
                        echo -e "${DIM}         • 运行: pip show isage-kernel${NC}"
                        echo -e "${DIM}         • 如未安装，运行: pip install -e packages/sage-kernel${NC}"
                        ;;
                    "sage.libs")
                        echo -e "${DIM}      💡 诊断提示:${NC}"
                        echo -e "${DIM}         • 运行: pip show isage-libs${NC}"
                        echo -e "${DIM}         • 如未安装，运行: pip install -e packages/sage-libs${NC}"
                        ;;
                esac

                failed_imports+=("$pkg")
            fi
        fi
    done

    echo ""
    echo -e "${DIM}   说明：${NC}"
    echo -e "${DIM}   • L1-L4 为核心层，必须能够导入${NC}"
    echo -e "${DIM}   • L5 为接口层（CLI/Tools），根据安装模式可能不存在${NC}"
    echo -e "${DIM}   • sage-benchmark/examples/studio/edge 已独立为单独仓库/包，不在此验证${NC}"
    echo ""

    if [ ${#failed_imports[@]} -eq 0 ]; then
        if [ ${#optional_failed[@]} -eq 0 ]; then
            log_verification_result "sage_imports" "PASS" "所有 SAGE 包导入成功"
        else
            log_verification_result "sage_imports" "PASS" "核心包导入成功（${#optional_failed[@]} 个可选包未安装）"
        fi
        return 0
    else
        log_verification_result "sage_imports" "FAIL" "核心包导入失败: ${failed_imports[*]}"

        # 输出详细的故障排查建议
        echo ""
        echo -e "${RED}${BOLD}❌ 导入失败诊断${NC}"
        echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}失败的包: ${failed_imports[*]}${NC}"
        echo ""
        echo -e "${BOLD}建议的修复步骤:${NC}"
        echo -e "1. 检查包是否已安装:"
        for pkg in "${failed_imports[@]}"; do
            local pypi_name=$(echo "$pkg" | sed 's/sage\./isage-/')
            echo -e "   ${DIM}pip show $pypi_name${NC}"
        done
        echo ""
        echo -e "2. 检查 Python 环境:"
        echo -e "   ${DIM}which python3${NC}"
        echo -e "   ${DIM}python3 -m site${NC}"
        echo ""
        echo -e "3. 尝试重新安装失败的包:"
        echo -e "   ${DIM}cd /path/to/SAGE${NC}"
        for pkg in "${failed_imports[@]}"; do
            local pkg_dir=$(echo "$pkg" | sed 's/sage\./sage-/')
            echo -e "   ${DIM}pip install -e packages/$pkg_dir${NC}"
        done
        echo ""
        echo -e "4. 查看安装日志:"
        echo -e "   ${DIM}cat .sage/logs/install.log${NC}"
        echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        return 1
    fi
}

# 生成验证报告
generate_verification_report() {
    echo -e "\n${BLUE}${BOLD}📊 安装验证报告${NC}" >> "$VERIFICATION_LOG"
    echo -e "================================================================================\n" >> "$VERIFICATION_LOG"

    local total_tests=${#VERIFICATION_RESULTS[@]}
    local passed_tests=0
    local failed_tests=0
    local warned_tests=0

    for result in "${VERIFICATION_RESULTS[@]}"; do
        IFS='|' read -r test_name status details <<< "$result"
        echo -e "[$status] $test_name: $details" >> "$VERIFICATION_LOG"

        case "$status" in
            "PASS") ((passed_tests++)) ;;
            "FAIL") ((failed_tests++)) ;;
            "WARN") ((warned_tests++)) ;;
        esac
    done

    echo -e "\n总结:" >> "$VERIFICATION_LOG"
    echo -e "- 总测试数: $total_tests" >> "$VERIFICATION_LOG"
    echo -e "- 通过: $passed_tests" >> "$VERIFICATION_LOG"
    echo -e "- 失败: $failed_tests" >> "$VERIFICATION_LOG"
    echo -e "- 警告: $warned_tests" >> "$VERIFICATION_LOG"
    echo -e "- 整体状态: $([ "$VERIFICATION_PASSED" = true ] && echo "PASS" || echo "FAIL")" >> "$VERIFICATION_LOG"

    echo -e "\n${BLUE}${BOLD}📊 安装验证报告${NC}"
    echo -e "${DIM}详细报告已保存到: $VERIFICATION_LOG${NC}"
    echo -e "${DIM}测试结果: $passed_tests 通过, $failed_tests 失败, $warned_tests 警告${NC}"

    if [ "$VERIFICATION_PASSED" = true ]; then
        echo -e "${GREEN}${BOLD}✅ 安装验证通过！${NC}"
    else
        echo -e "${YELLOW}${BOLD}⚠️  安装验证发现问题，请检查报告${NC}"
    fi
}

# 运行完整的安装验证
run_comprehensive_verification() {
    echo -e "${BLUE}${BOLD}🔍 开始全面安装验证...${NC}"
    echo ""

    init_verification_log

    # 运行各项验证
    verify_cli_commands
    echo ""

    verify_sage_imports
    echo ""

    verify_dependency_versions
    echo ""

    verify_hello_world
    echo ""

    verify_sage_doctor
    echo ""

    generate_verification_report

    return $([ "$VERIFICATION_PASSED" = true ] && echo 0 || echo 1)
}

# 快速验证（仅关键项目）
run_quick_verification() {
    echo -e "${BLUE}🔍 快速安装验证...${NC}"

    init_verification_log

    # 只运行最关键的验证
    verify_sage_imports
    verify_cli_commands

    generate_verification_report

    return $([ "$VERIFICATION_PASSED" = true ] && echo 0 || echo 1)
}
