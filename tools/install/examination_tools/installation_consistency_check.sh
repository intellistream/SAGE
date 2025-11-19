#!/bin/bash
# 安装一致性检查脚本
# 确保本地开发环境的安装方式与CI/CD保持一致，避免"CI通过但本地失败"的问题
#
# 用途：
# 1. 作为 pre-commit hook 运行，检查安装配置
# 2. 验证是否使用 quickstart.sh 进行安装
# 3. 检测可能导致环境不一致的问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
DIM='\033[2m'
BOLD='\033[1m'

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 检查标志
WARNINGS_FOUND=false
ERRORS_FOUND=false

# 打印标题
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}🔍 SAGE 安装一致性检查${NC}"
    echo -e "${DIM}确保本地安装与CI/CD环境保持一致${NC}"
    echo ""
}

# 打印检查项
print_check() {
    local status="$1"
    local message="$2"

    case "$status" in
        "pass")
            echo -e "  ${GREEN}✓${NC} $message"
            ;;
        "warn")
            echo -e "  ${YELLOW}⚠${NC} $message"
            WARNINGS_FOUND=true
            ;;
        "fail")
            echo -e "  ${RED}✗${NC} $message"
            ERRORS_FOUND=true
            ;;
        "info")
            echo -e "  ${BLUE}ℹ${NC} $message"
            ;;
    esac
}

# 检查是否在 SAGE 根目录
check_sage_root() {
    echo -e "${BOLD}1. 检查项目结构${NC}"

    if [ -f "$SAGE_ROOT/quickstart.sh" ] && [ -d "$SAGE_ROOT/packages/sage" ]; then
        print_check "pass" "SAGE 项目根目录已识别"
    else
        print_check "fail" "未在 SAGE 项目根目录运行"
        return 1
    fi
}

# 检查是否使用 quickstart.sh 安装
check_installation_method() {
    echo ""
    echo -e "${BOLD}2. 检查安装方法${NC}"

    # 检查是否存在 .sage 目录（quickstart.sh 创建的）
    if [ -d "$SAGE_ROOT/.sage" ]; then
        print_check "pass" "发现 .sage 目录（quickstart.sh 创建）"

        # 检查安装日志
        if [ -f "$SAGE_ROOT/.sage/logs/install.log" ]; then
            print_check "pass" "发现安装日志文件"

            # 检查日志中是否有 quickstart.sh 的特征
            if grep -q "quickstart" "$SAGE_ROOT/.sage/logs/install.log" 2>/dev/null; then
                print_check "pass" "确认使用 quickstart.sh 进行安装"
            else
                print_check "warn" "安装日志中未找到 quickstart.sh 标记"
            fi
        else
            print_check "warn" "未找到安装日志，可能未使用 quickstart.sh 安装"
        fi
    else
        print_check "warn" "未找到 .sage 目录，建议使用 quickstart.sh 安装"
        print_check "info" "CI/CD 使用 quickstart.sh 安装，本地也应使用相同方式"
    fi
}

# 检查是否有手动 pip install 的痕迹
check_manual_install() {
    echo ""
    echo -e "${BOLD}3. 检查手动安装痕迹${NC}"

    # 检查 pip list 中的包是否是可编辑安装
    if command -v pip >/dev/null 2>&1 || command -v pip3 >/dev/null 2>&1; then
        local pip_cmd="pip"
        command -v pip3 >/dev/null 2>&1 && pip_cmd="pip3"

        # 检查 SAGE 相关包
        local sage_packages=$($pip_cmd list --format=freeze 2>/dev/null | grep -E "^isage|^-e.*sage" || true)

        if [ -n "$sage_packages" ]; then
            # 检查是否是可编辑安装（-e）
            if echo "$sage_packages" | grep -q "^-e"; then
                print_check "pass" "检测到可编辑安装（开发模式）"
                print_check "info" "这与 quickstart.sh --dev 一致"
            else
                # 检查是否有非可编辑的安装
                local non_editable=$(echo "$sage_packages" | grep -v "^-e" || true)
                if [ -n "$non_editable" ]; then
                    print_check "warn" "检测到非可编辑安装的 SAGE 包"
                    echo -e "${DIM}     可能手动使用了 'pip install isage'${NC}"
                    echo -e "${DIM}     建议卸载后使用 quickstart.sh 重新安装${NC}"
                fi
            fi
        else
            print_check "info" "未检测到已安装的 SAGE 包"
        fi
    else
        print_check "warn" "pip 命令不可用，跳过包安装检查"
    fi
}

# 检查环境一致性
check_environment_consistency() {
    echo ""
    echo -e "${BOLD}4. 检查环境一致性${NC}"

    # 检查 Python 版本
    if command -v python3 >/dev/null 2>&1; then
        local python_version=$(python3 --version 2>&1 | awk '{print $2}')
        local python_major=$(echo "$python_version" | cut -d. -f1)
        local python_minor=$(echo "$python_version" | cut -d. -f2)

        if [ "$python_major" -eq 3 ] && [ "$python_minor" -ge 10 ] && [ "$python_minor" -le 12 ]; then
            print_check "pass" "Python 版本 $python_version （与 CI/CD 兼容: 3.10-3.12）"
        else
            print_check "warn" "Python 版本 $python_version 可能不兼容"
            echo -e "${DIM}     CI/CD 使用 Python 3.10-3.12${NC}"
        fi
    fi

    # 检查系统依赖（C++编译工具）
    if command -v gcc >/dev/null 2>&1 && command -v g++ >/dev/null 2>&1; then
        print_check "pass" "C++ 编译工具已安装"
    else
        print_check "warn" "C++ 编译工具未找到，C++扩展可能无法构建"
        echo -e "${DIM}     运行: sudo apt-get install build-essential${NC}"
    fi

    # 检查 cmake
    if command -v cmake >/dev/null 2>&1; then
        print_check "pass" "CMake 已安装"
    else
        print_check "warn" "CMake 未找到，C++扩展可能无法构建"
        echo -e "${DIM}     运行: sudo apt-get install cmake${NC}"
    fi
}

# 检查 Git hooks 安装
check_git_hooks() {
    echo ""
    echo -e "${BOLD}5. 检查 Git Hooks${NC}"

    if [ -d "$SAGE_ROOT/.git/hooks" ]; then
        # 检查 pre-commit
        if [ -f "$SAGE_ROOT/.git/hooks/pre-commit" ]; then
            print_check "pass" "Git pre-commit hook 已安装"

            # 检查是否是 pre-commit 框架的 hook
            if grep -q "pre-commit" "$SAGE_ROOT/.git/hooks/pre-commit" 2>/dev/null; then
                print_check "pass" "使用 pre-commit 框架（推荐）"
            fi
        else
            print_check "warn" "Git pre-commit hook 未安装"
            print_check "info" "运行: sage-dev maintain hooks install"
        fi

        # 检查 pre-commit 配置
        if [ -f "$SAGE_ROOT/.pre-commit-config.yaml" ]; then
            print_check "pass" "pre-commit 配置文件存在"
        fi
    else
        print_check "info" "不在 Git 仓库中，跳过 hooks 检查"
    fi
}

# 检查子模块状态
check_submodules() {
    echo ""
    echo -e "${BOLD}6. 检查 Git 子模块${NC}"

    if [ -d "$SAGE_ROOT/.git" ]; then
        # 检查子模块配置
        if [ -f "$SAGE_ROOT/.gitmodules" ]; then
            print_check "pass" "项目包含 Git 子模块"

            # 检查子模块是否已初始化
            local uninit_submodules=$(git submodule status 2>/dev/null | grep "^-" | wc -l || echo "0")

            if [ "$uninit_submodules" -eq 0 ]; then
                print_check "pass" "所有子模块已初始化"
            else
                print_check "warn" "有 $uninit_submodules 个子模块未初始化"
                print_check "info" "quickstart.sh 会自动初始化子模块"
                echo -e "${DIM}     或手动运行: git submodule update --init --recursive${NC}"
            fi
        fi
    else
        print_check "info" "不在 Git 仓库中，跳过子模块检查"
    fi
}

# 提供修复建议
print_recommendations() {
    echo ""
    echo -e "${BOLD}${BLUE}📋 建议和最佳实践${NC}"
    echo ""

    if [ "$ERRORS_FOUND" = true ] || [ "$WARNINGS_FOUND" = true ]; then
        echo -e "${YELLOW}发现了一些问题，建议采取以下措施：${NC}"
        echo ""

        if [ ! -d "$SAGE_ROOT/.sage" ]; then
            echo -e "${BOLD}推荐安装方法：${NC}"
            echo -e "  ${GREEN}./quickstart.sh --dev --yes${NC}"
            echo -e "  ${DIM}(这与 CI/CD 使用的方法相同)${NC}"
            echo ""
        fi

        echo -e "${BOLD}确保环境一致性：${NC}"
        echo -e "  1. 始终使用 ${GREEN}quickstart.sh${NC} 进行安装"
        echo -e "  2. 不要手动运行 ${YELLOW}pip install isage${NC}"
        echo -e "  3. 开发时使用 ${GREEN}--dev${NC} 模式进行可编辑安装"
        echo -e "  4. 安装 Git hooks: ${GREEN}sage-dev maintain hooks install${NC}"
        echo ""

        echo -e "${BOLD}如果遇到问题：${NC}"
        echo -e "  1. 清理环境: ${GREEN}./quickstart.sh --clean${NC}"
        echo -e "  2. 重新安装: ${GREEN}./quickstart.sh --dev --yes${NC}"
        echo -e "  3. 查看日志: ${GREEN}.sage/logs/install.log${NC}"
        echo ""
    else
        echo -e "${GREEN}✓ 您的安装配置与 CI/CD 保持一致！${NC}"
        echo ""
        echo -e "${BOLD}持续保持一致性：${NC}"
        echo -e "  • 使用 quickstart.sh 更新依赖"
        echo -e "  • 定期运行此检查"
        echo -e "  • 遵循项目的安装指南"
        echo ""
    fi
}

# 主函数
main() {
    print_header

    check_sage_root || exit 1
    check_installation_method
    check_manual_install
    check_environment_consistency
    check_git_hooks
    check_submodules

    print_recommendations

    # 如果只有警告，返回成功（不阻止提交）
    # 如果有错误，返回失败
    if [ "$ERRORS_FOUND" = true ]; then
        echo -e "${RED}检查发现严重问题，建议修复后再继续${NC}"
        exit 1
    elif [ "$WARNINGS_FOUND" = true ]; then
        echo -e "${YELLOW}检查发现一些警告，但不会阻止您的操作${NC}"
        exit 0
    else
        echo -e "${GREEN}所有检查通过！${NC}"
        exit 0
    fi
}

# 运行主函数
main "$@"
