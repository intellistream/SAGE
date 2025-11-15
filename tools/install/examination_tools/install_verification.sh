#!/bin/bash
# SAGE 安装验证模块
# 实现全面的安装验证：hello_world 测试、CLI 检查、依赖验证、报告生成

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 验证常量
VERIFICATION_LOG=".sage/install_verification.log"
HELLO_WORLD_SCRIPT="docs-public/hello_world.py"

# 验证结果状态
VERIFICATION_PASSED=true
VERIFICATION_RESULTS=()

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
Python 版本: $(python3 --version 2>&1 || echo "未安装")
Sage 版本: $(python3 -c "import sage; print(sage.__version__)" 2>/dev/null || echo "未安装")

================================================================================
EOF

    echo -e "${BLUE}📋 初始化验证日志: $VERIFICATION_LOG${NC}"
}

# 验证 hello_world 示例
verify_hello_world() {
    echo -e "${BLUE}🧪 运行 hello_world 测试...${NC}"

    if [ ! -f "$HELLO_WORLD_SCRIPT" ]; then
        log_verification_result "hello_world" "FAIL" "hello_world.py 文件不存在"
        echo -e "${RED}   ❌ hello_world.py 文件不存在${NC}"
        return 1
    fi

    # 运行 hello_world 脚本
    local output
    output=$(python3 "$HELLO_WORLD_SCRIPT" 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_verification_result "hello_world" "PASS" "hello_world.py 执行成功"
        echo -e "${GREEN}   ✅ hello_world.py 执行成功${NC}"
        echo -e "${DIM}   输出: $(echo "$output" | head -3 | tr '\n' ' ')${NC}"
        return 0
    else
        log_verification_result "hello_world" "FAIL" "hello_world.py 执行失败: $output"
        echo -e "${RED}   ❌ hello_world.py 执行失败${NC}"
        echo -e "${DIM}   错误: $output${NC}"
        return 1
    fi
}

# 验证 sage doctor 命令
verify_sage_doctor() {
    echo -e "${BLUE}🩺 验证 sage doctor 命令...${NC}"

    # 检查 sage-dev 命令是否存在
    if ! command -v sage-dev &> /dev/null; then
        log_verification_result "sage_doctor" "FAIL" "sage-dev 命令不可用"
        echo -e "${RED}   ❌ sage-dev 命令不可用${NC}"
        return 1
    fi

    # 运行 sage doctor
    local output
    output=$(sage-dev doctor 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_verification_result "sage_doctor" "PASS" "sage-dev doctor 执行成功"
        echo -e "${GREEN}   ✅ sage-dev doctor 执行成功${NC}"
        return 0
    else
        log_verification_result "sage_doctor" "WARN" "sage-dev doctor 执行失败: $output"
        echo -e "${YELLOW}   ⚠️  sage-dev doctor 执行失败${NC}"
        echo -e "${DIM}   错误: $output${NC}"
        return 1
    fi
}

# 验证 CLI 命令
verify_cli_commands() {
    echo -e "${BLUE}🔧 验证 CLI 命令...${NC}"

    local cli_commands=("sage-dev" "python3")
    local failed_commands=()

    for cmd in "${cli_commands[@]}"; do
        if command -v "$cmd" &> /dev/null; then
            echo -e "${GREEN}   ✅ $cmd 命令可用${NC}"
        else
            echo -e "${RED}   ❌ $cmd 命令不可用${NC}"
            failed_commands+=("$cmd")
        fi
    done

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
        if python3 -c "import $dep; print($dep.__version__)" &> /dev/null; then
            local version=$(python3 -c "import $dep; print($dep.__version__)" 2>/dev/null)
            echo -e "${GREEN}   ✅ $dep $version 已安装${NC}"
        else
            echo -e "${RED}   ❌ $dep 未安装或导入失败${NC}"
            version_issues+=("$dep")
        fi
    done

    # 检查版本兼容性
    if python3 -c "
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

    local sage_packages=("sage" "sage.common" "sage.kernel" "sage.libs" "sage.middleware")
    local failed_imports=()

    for pkg in "${sage_packages[@]}"; do
        if python3 -c "import $pkg; print(f'{pkg} version: {$pkg.__version__}')" &> /dev/null; then
            local version=$(python3 -c "import $pkg; print($pkg.__version__)" 2>/dev/null)
            echo -e "${GREEN}   ✅ $pkg $version 导入成功${NC}"
        else
            echo -e "${RED}   ❌ $pkg 导入失败${NC}"
            failed_imports+=("$pkg")
        fi
    done

    if [ ${#failed_imports[@]} -eq 0 ]; then
        log_verification_result "sage_imports" "PASS" "所有 SAGE 包导入成功"
        return 0
    else
        log_verification_result "sage_imports" "FAIL" "SAGE 包导入失败: ${failed_imports[*]}"
        return 1
    fi
}

# 验证 VLLM 安装（如果已安装）
verify_vllm_installation() {
    echo -e "${BLUE}🚀 验证 VLLM 安装...${NC}"

    if ! python3 -c "import vllm" &> /dev/null; then
        log_verification_result "vllm_install" "SKIP" "VLLM 未安装，跳过验证"
        echo -e "${DIM}   ℹ️  VLLM 未安装，跳过验证${NC}"
        return 0
    fi

    local vllm_version=$(python3 -c "import vllm; print(vllm.__version__)" 2>/dev/null)
    echo -e "${GREEN}   ✅ VLLM $vllm_version 已安装${NC}"

    # 尝试基本功能测试
    if python3 -c "
import vllm
print(f'VLLM 版本: {vllm.__version__}')

# 检查 CUDA 可用性
try:
    from vllm import LLM
    print('VLLM LLM 类导入成功')
except Exception as e:
    print(f'VLLM 功能测试失败: {e}')
    exit(1)
" 2>/dev/null; then
        log_verification_result "vllm_install" "PASS" "VLLM 安装和基本功能正常"
        return 0
    else
        log_verification_result "vllm_install" "WARN" "VLLM 安装但功能测试失败"
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

    verify_vllm_installation
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
