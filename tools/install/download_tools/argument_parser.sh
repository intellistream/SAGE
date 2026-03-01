#!/bin/bash
# SAGE 安装脚本 - 参数解析模块
# 处理命令行参数的解析和验证

# 获取脚本目录

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
AUTO_YES="${AUTO_YES:-false}"
AUTO_CONFIRM="${AUTO_CONFIRM:-false}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set_hooks_mode_value() {
    local value="${1,,}"
    case "$value" in
        "auto"|"background"|"sync")
            HOOKS_MODE="$value"
            ;;
        *)
            echo -e "${CROSS} 无效的 --hooks-mode 参数: $1 (可选: auto, background, sync)"
            exit 1
            ;;
    esac
}

set_hooks_profile_value() {
    local value="${1,,}"
    case "$value" in
        "lightweight"|"full")
            HOOKS_PROFILE="$value"
            ;;
        *)
            echo -e "${CROSS} 无效的 --hooks-profile 参数: $1 (可选: lightweight, full)"
            exit 1
            ;;
    esac
}

set_install_mode_value() {
    local value="${1,,}"
    case "$value" in
        "dev"|"standard")
            INSTALL_MODE="$value"
            ;;
        "non-dev"|"nondev")
            INSTALL_MODE="standard"
            ;;
        *)
            echo -e "${CROSS} 无效的安装模式: $1 (可选: dev, standard)"
            exit 1
            ;;
    esac
}

set_mirror_source_value() {
    local raw_value="$1"
    local value="${raw_value,,}"

    if [[ "$raw_value" == http*://* ]]; then
        MIRROR_SOURCE="custom:${raw_value}"
        return
    fi

    case "$value" in
        "auto"|"tsinghua"|"aliyun"|"tencent"|"pypi")
            MIRROR_SOURCE="$value"
            ;;
        custom:*)
            MIRROR_SOURCE="$raw_value"
            ;;
        *)
            echo -e "${CROSS} 无效的 --use-mirror 取值: $raw_value"
            echo -e "${DIM}支持: auto, tsinghua, aliyun, tencent, pypi, custom:<url>${NC}"
            exit 1
            ;;
    esac
}

SAGE_TOOLS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 导入颜色定义
source "$SCRIPT_DIR/../display_tools/colors.sh"

# 导入 conda 工具函数
source "$SAGE_TOOLS_ROOT/conda/conda_utils.sh"

# 全局变量
INSTALL_MODE=""
INSTALL_ENVIRONMENT=""
# AUTO_CONFIRM 已在上面的环境变量安全默认值部分初始化
SHOW_HELP=false
CLEAN_PIP_CACHE=true
RUN_DOCTOR=true
DOCTOR_ONLY=false
FIX_ENVIRONMENT=false
VERIFY_DEPS=false
VERIFY_DEPS_STRICT=false
SKIP_HOOKS=false
HOOKS_MODE="auto"
SETUP_WORKSPACE=false  # 新增：设置 workspace 依赖
CLONE_SATELLITE_REPOS=false  # 新增：克隆附属仓库
HOOKS_PROFILE="lightweight"
USE_PIP_MIRROR=true  # 默认启用pip镜像自动检测（中国用户自动使用清华源）
MIRROR_SOURCE="auto"
RESUME_INSTALL=true  # 默认启用断点续传（安装失败时自动恢复）
RESET_CHECKPOINT=false  # 新增：重置检查点
CLEAN_BEFORE_INSTALL=true  # 新增：安装前清理（默认启用）
FORCE_REBUILD=false        # 强制重新编译 C++ 扩展（跳过智能缓存检查）

# 检测当前Python环境
detect_current_environment() {
    local env_type="system"
    local env_name=""
    local in_conda=false
    local in_venv=false
    local in_conda_base=false

    # 检测conda环境
    if [ -n "${CONDA_DEFAULT_ENV:-}" ]; then
        if [ "${CONDA_DEFAULT_ENV:-}" = "base" ]; then
            env_type="conda_base"
            env_name="base"
            in_conda_base=true
        else
            env_type="conda"
            env_name="${CONDA_DEFAULT_ENV:-}"
            in_conda=true
        fi
    elif [ -n "${CONDA_PREFIX:-}" ]; then
        if [[ "${CONDA_PREFIX:-}" == *"/base" ]]; then
            env_type="conda_base"
            env_name="base"
            in_conda_base=true
        else
            env_type="conda"
            env_name=$(basename "${CONDA_PREFIX:-}")
            in_conda=true
        fi
    fi

    # 检测 Python venv（策略：不作为推荐环境，仅用于识别并后续 fail-fast）
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        if [ "$in_conda" = false ] && [ "$in_conda_base" = false ]; then
            env_type="system"
            env_name=""
        fi
    fi

    echo "$env_type|$env_name|$in_conda|$in_venv|$in_conda_base"
}

# 根据当前环境智能推荐安装方式
get_smart_environment_recommendation() {
    local env_info=$(detect_current_environment)
    local env_type=$(echo "$env_info" | cut -d'|' -f1)
    local env_name=$(echo "$env_info" | cut -d'|' -f2)
    local in_conda=$(echo "$env_info" | cut -d'|' -f3)
    local in_venv=$(echo "$env_info" | cut -d'|' -f4)
    local in_conda_base=$(echo "$env_info" | cut -d'|' -f5)

    if [ "$in_conda" = true ]; then
        # 用户已经在 conda 环境中（非 base），推荐直接使用
        echo "pip|$env_type|$env_name"
    elif [ "$in_conda_base" = true ]; then
        # 用户在 conda base 环境中，不推荐使用，推荐创建新环境
        echo "conda|conda_base|base"
    else
        # 用户在系统环境中，推荐创建conda环境（如果conda可用）
        if command -v conda &> /dev/null; then
            echo "conda|system|"
        else
            echo "pip|system|"
        fi
    fi
}

# 显示 Conda 安装后的重启提示
show_conda_install_restart_message() {
    echo ""
    echo -e "${GREEN}✅ Conda 安装成功！${NC}"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}⚠️  重要：必须重新加载 shell 环境${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${INFO} Conda 已成功安装到: ${GREEN}$HOME/miniconda3${NC}"
    echo -e "${INFO} 已自动配置到 ${GREEN}~/.bashrc${NC}"
    echo ""
    echo -e "${RED}${BOLD}注意: 当前终端还无法使用 conda 命令！${NC}"
    echo ""
    echo -e "${BOLD}请选择以下任一方式重新加载环境：${NC}"
    echo ""
    echo -e "  ${YELLOW}方式 1 (推荐):${NC} 在当前终端运行"
    echo -e "    ${CYAN}source ~/.bashrc && ./quickstart.sh${NC}"
    echo ""
    echo -e "  ${YELLOW}方式 2:${NC} 关闭此终端，打开新终端后运行"
    echo -e "    ${CYAN}./quickstart.sh${NC}"
    echo ""
    echo -e "${DIM}小提示: 方式 1 更快，无需关闭终端${NC}"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# 提示用户输入 Conda 环境名称
prompt_conda_env_name() {
    echo ""
    echo -e "${BLUE}请输入 Conda 环境名称 ${DIM}(默认: sage)${NC}"
    read -p "环境名称: " conda_env_input
    if [ -z "$conda_env_input" ]; then
        SAGE_ENV_NAME="sage"
    else
        SAGE_ENV_NAME="$conda_env_input"
    fi
    export SAGE_ENV_NAME
    echo -e "${INFO} 将创建 Conda 环境: ${GREEN}${SAGE_ENV_NAME:-}${NC}"
}

# 交互式安装菜单
show_installation_menu() {
    echo ""
    echo -e "${BLUE}🔧 请选择安装配置${NC}"
    echo ""

    # 选择安装模式
    while true; do
        echo -e "${BOLD}1. 选择安装模式：${NC}"
        echo -e "  ${YELLOW}1)${NC} standard 安装 - 依赖优先从 PyPI 拉取 ${DIM}(~200+包, 推荐稳定使用)${NC}"
        echo -e "  ${GREEN}2)${NC} dev 安装      - standard+开发工具+本地 editable(尽量) ${DIM}(~220+包, 日常开发)${NC}"
        echo ""
        read -p "请选择安装模式 [1-2，默认1]: " mode_choice

        case "${mode_choice:-1}" in
            1)
                INSTALL_MODE="standard"
                break
                ;;
            2)
                INSTALL_MODE="dev"
                break
                ;;
            *)
                echo -e "${RED}无效选择，请输入 1 或 2${NC}"
                echo ""
                ;;
        esac
    done

    echo ""

    # 检测当前环境并智能推荐
    local recommendation=$(get_smart_environment_recommendation)
    local recommended_env=$(echo "$recommendation" | cut -d'|' -f1)
    local current_env_type=$(echo "$recommendation" | cut -d'|' -f2)
    local current_env_name=$(echo "$recommendation" | cut -d'|' -f3)

    # 显示当前环境信息
    if [ "$current_env_type" = "conda" ] && [ -n "$current_env_name" ]; then
        echo -e "${INFO} 检测到您当前在 conda 环境中: ${GREEN}$current_env_name${NC}"
    elif [ "$current_env_type" = "conda_base" ]; then
        echo -e "${INFO} 检测到您当前在 conda ${YELLOW}base${NC} 环境中 ${DIM}(不推荐用于开发)${NC}"
    elif [ "$current_env_type" = "system" ]; then
        echo -e "${INFO} 检测到您当前在系统 Python 环境中"
    fi

    echo ""

    # 选择安装环境
    while true; do
        echo -e "${BOLD}2. 选择安装环境：${NC}"

        # 检查 conda 是否可用
        local conda_available=false
        if command -v conda &> /dev/null; then
            conda_available=true
        fi

        if [ "$recommended_env" = "pip" ]; then
            # 推荐使用当前环境（仅当在当前 conda 环境中，非 base）
            if [ "$current_env_type" = "system" ]; then
                # 在系统环境中，不推荐使用，建议创建 conda 环境
                echo -e "  ${PURPLE}1)${NC} 使用当前系统环境 ${DIM}(不推荐，建议使用 conda 环境)${NC}"
                if [ "$conda_available" = true ]; then
                    echo -e "  ${GREEN}2)${NC} 创建新的 Conda 环境 ${DIM}(推荐)${NC}"
                    local default_choice=2
                else
                    echo -e "  ${GRAY}2)${NC} 创建新的 Conda 环境 ${DIM}(conda 未安装)${NC}"
                    local default_choice=1
                fi
            elif [ "$current_env_type" = "conda_base" ]; then
                # 在 conda base 环境中，不推荐使用
                echo -e "  ${PURPLE}1)${NC} 使用当前 base 环境 ${DIM}(不推荐，建议创建新环境)${NC}"
                if [ "$conda_available" = true ]; then
                    echo -e "  ${GREEN}2)${NC} 创建新的 Conda 环境 ${DIM}(推荐)${NC}"
                    local default_choice=2
                else
                    echo -e "  ${GRAY}2)${NC} 创建新的 Conda 环境 ${DIM}(conda 未安装)${NC}"
                    local default_choice=1
                fi
            else
                # 在 conda 环境中，推荐使用当前环境
                echo -e "  ${GREEN}1)${NC} 使用当前环境 ${DIM}(推荐，已在 Conda 环境中)${NC}"
                if [ "$conda_available" = true ]; then
                    echo -e "  ${PURPLE}2)${NC} 创建新的 Conda 环境"
                else
                    echo -e "  ${GRAY}2)${NC} 创建新的 Conda 环境 ${DIM}(conda 未安装)${NC}"
                fi
                local default_choice=1
            fi
        else
            # 推荐创建conda环境
            if [ "$conda_available" = true ]; then
                echo -e "  ${GREEN}1)${NC} 创建新的 Conda 环境 ${DIM}(推荐)${NC}"
                echo -e "  ${PURPLE}2)${NC} 使用当前系统环境 ${DIM}(不推荐)${NC}"
                local default_choice=1
            else
                echo -e "  ${GRAY}1)${NC} 创建新的 Conda 环境 ${DIM}(conda 未安装)${NC}"
                echo -e "  ${GREEN}2)${NC} 使用当前系统环境 ${DIM}(推荐，因为 conda 不可用)${NC}"
                local default_choice=2
            fi
        fi

        echo ""
        read -p "请选择安装环境 [1-2，默认$default_choice]: " env_choice

        case "${env_choice:-$default_choice}" in
            1)
                if [ "$recommended_env" = "pip" ]; then
                    INSTALL_ENVIRONMENT="pip"
                else
                    if [ "$conda_available" = true ]; then
                        INSTALL_ENVIRONMENT="conda"
                        prompt_conda_env_name
                    else
                        echo -e "${RED}❌ Conda 未安装！${NC}"
                        echo ""
                        read -p "是否自动安装 Miniconda？[Y/n]: " install_conda_choice
                        if [[ "${install_conda_choice:-Y}" =~ ^[Yy]$ ]]; then
                            echo ""
                            if install_miniconda; then
                                show_conda_install_restart_message
                                exit 0
                            else
                                echo -e "${RED}❌ Conda 安装失败${NC}"
                                echo -e "${YELLOW}请手动安装或选择使用当前环境${NC}"
                                echo -e "${YELLOW}访问 https://docs.conda.io/en/latest/miniconda.html${NC}"
                                echo ""
                                continue
                            fi
                        else
                            echo -e "${YELLOW}已取消，请选择使用当前环境或稍后手动安装 Conda${NC}"
                            echo ""
                            continue
                        fi
                    fi
                fi
                break
                ;;
            2)
                if [ "$recommended_env" = "pip" ]; then
                    if [ "$conda_available" = true ]; then
                        INSTALL_ENVIRONMENT="conda"
                        prompt_conda_env_name
                    else
                        echo -e "${RED}❌ Conda 未安装！${NC}"
                        echo ""
                        read -p "是否自动安装 Miniconda？[Y/n]: " install_conda_choice
                        if [[ "${install_conda_choice:-Y}" =~ ^[Yy]$ ]]; then
                            echo ""
                            if install_miniconda; then
                                show_conda_install_restart_message
                                exit 0
                            else
                                echo -e "${RED}❌ Conda 安装失败${NC}"
                                echo -e "${YELLOW}请手动安装或选择使用当前环境 (选项 1)${NC}"
                                echo -e "${YELLOW}访问 https://docs.conda.io/en/latest/miniconda.html${NC}"
                                echo ""
                                continue
                            fi
                        else
                            echo -e "${YELLOW}已取消，请选择使用当前环境 (选项 1)${NC}"
                            echo ""
                            continue
                        fi
                    fi
                else
                    INSTALL_ENVIRONMENT="pip"
                fi
                break
                ;;
            *)
                echo -e "${RED}无效选择，请输入 1 或 2${NC}"
                echo ""
                ;;
        esac
    done

    echo ""

    # 询问是否克隆附属仓库
    echo -e "${BOLD}3. 克隆附属仓库？${NC}"
    echo -e "  ${DIM}包括: sage-examples, sage-tutorials, sagellm, sage-benchmark 等${NC}"
    echo ""
    read -p "是否克隆 SAGE 附属仓库？[y/N]: " -n 1 -r clone_choice
    echo ""
    if [[ "$clone_choice" =~ ^[Yy]$ ]]; then
        CLONE_SATELLITE_REPOS=true
        echo -e "${GREEN}✅ 将克隆附属仓库${NC}"
    else
        CLONE_SATELLITE_REPOS=false
        echo -e "${DIM}跳过克隆（可稍后手动克隆）${NC}"
    fi

    echo ""
}

# 显示参数帮助信息
show_parameter_help() {
    echo ""
    echo -e "${BOLD}SAGE 快速安装脚本${NC}"
    echo ""
    echo -e "${BLUE}用法：${NC}"
    echo -e "  ./quickstart.sh                                  ${DIM}# 交互式安装（推荐新用户）${NC}"
    echo -e "  ./quickstart.sh [安装模式] [安装环境] [AI模型支持] [选项]"
    echo ""
    echo -e "${PURPLE}💡 无参数运行时将显示交互式菜单，引导您完成安装配置${NC}"
    echo ""

    echo -e "${BLUE}📦 安装模式：${NC}"
    echo ""
    echo -e "  ${BOLD}--install-mode <dev|standard>, --mode <dev|standard>${NC} ${GREEN}显式指定安装模式${NC}"
    echo -e "    ${DIM}推荐写法，语义清晰，便于脚本自动化${NC}"
    echo ""
    echo -e "  ${BOLD}--standard, -s${NC}                              ${YELLOW}standard 安装 (默认)${NC}"
    echo -e "    ${DIM}包含: 完整功能依赖 (ML, VDB, streaming, etc.)，子包依赖默认从 PyPI 解析${NC}"
    echo -e "    ${DIM}大小: ~200+ 个包（约 1GB，含 PyTorch）${NC}"
    echo -e "    ${DIM}适合: 学习示例、完整功能体验、研究实验${NC}"
    echo ""
    echo -e "  ${BOLD}--dev, -d${NC}                                   ${GREEN}开发安装${NC}"
    echo -e "    ${DIM}包含: standard 安装 + 开发工具 (pytest, ruff, mypy, pre-commit)${NC}"
    echo -e "    ${DIM}并尽量将本地 polyrepo 子仓库安装为 editable（未命中仍回退到 PyPI）${NC}"
    echo -e "    ${DIM}大小: ~220+ 个包（约 1.2GB，含 PyTorch）${NC}"
    echo -e "    ${DIM}适合: 日常开发、贡献 SAGE 框架源码${NC}"
    echo -e "    ${DIM}兼容别名: --non-dev / --nondev 等同于 standard${NC}"
    echo ""

    echo -e "${BLUE}🔧 安装环境：${NC}"
    echo ""
    echo -e "  ${BOLD}--pip, -pip${NC}                                  ${PURPLE}使用当前环境${NC}"
    echo -e "  ${BOLD}--conda, -conda${NC}                              ${GREEN}创建conda环境${NC}"
    echo ""
    echo -e "  ${DIM}💡 不指定时自动智能选择: Conda环境→pip，系统环境→conda${NC}"
    echo ""

    echo -e "${BLUE}⚡ 其他选项：${NC}"
    echo ""
    echo -e "  ${BOLD}--yes, --y, -yes, -y${NC}                        ${CYAN}跳过确认提示${NC}"
    echo -e "    ${DIM}自动确认所有安装选项，适合自动化脚本${NC}"
    echo ""
    echo -e "  ${BOLD}--doctor, --diagnose, --check-env${NC}           ${GREEN}环境诊断${NC}"
    echo -e "    ${DIM}全面检查 Python 环境、包管理器、依赖等问题${NC}"
    echo -e "    ${DIM}识别并报告常见的环境配置问题${NC}"
    echo ""
    echo -e "  ${BOLD}--doctor-fix, --diagnose-fix, --fix-env${NC}     ${YELLOW}诊断并修复${NC}"
    echo -e "    ${DIM}在诊断的基础上自动修复检测到的问题${NC}"
    echo -e "    ${DIM}安全的自动修复常见环境冲突${NC}"
    echo ""
    echo -e "  ${BOLD}--pre-check, --env-check${NC}                    ${BLUE}安装前检查${NC}"
    echo -e "    ${DIM}在正常安装前进行环境预检查${NC}"
    echo -e "    ${DIM}与其他安装选项结合使用${NC}"
    echo ""
    echo -e "  ${BOLD}--skip-hooks${NC}                             ${YELLOW}跳过 Git hooks 安装${NC}"
    echo -e "    ${DIM}稍后可手动运行 'sage-dev maintain hooks install'${NC}"
    echo ""
    echo -e "  ${BOLD}--workspace${NC}                              ${GREEN}设置 workspace 依赖${NC}"
    echo -e "    ${DIM}克隆 SAGE-Pub 和 sage-team-info 仓库${NC}"
    echo -e "    ${DIM}用于 VS Code 多文件夹编辑（SAGE.code-workspace）${NC}"
    echo ""
    echo -e "  ${BOLD}--clone-satellites${NC}                       ${GREEN}克隆附属仓库${NC}"
    echo -e "    ${DIM}克隆所有 SAGE 附属仓库（examples, tutorials, benchmark 等）${NC}"
    echo -e "    ${DIM}支持别名: --clone-repos, --satellites${NC}"
    echo ""
    echo -e "  ${BOLD}--no-clone-satellites${NC}                    ${YELLOW}跳过克隆附属仓库${NC}"
    echo -e "    ${DIM}支持别名: --skip-satellites, --no-repos${NC}"
    echo ""
    echo -e "  ${BOLD}--hooks-mode <auto|background|sync>${NC}      ${GREEN}控制 hooks 安装方式${NC}"
    echo -e "    ${DIM}auto: 交互式安装后台运行，其余场景同步${NC}"
    echo -e "    ${DIM}background: 总是异步，安装更快${NC}"
    echo -e "    ${DIM}sync: 与主流程一起执行（旧行为）${NC}"
    echo ""
    echo -e "  ${BOLD}--hooks-profile <lightweight|full>${NC}        ${PURPLE}选择 hooks 工具链大小${NC}"
    echo -e "    ${DIM}lightweight: 仅安装 hook 脚本，首次提交再下载依赖${NC}"
    echo -e "    ${DIM}full: 立即下载完整工具链，适合离线/CI${NC}"
    echo ""
    echo -e "  ${BOLD}--use-mirror [源]${NC}                        ${GREEN}使用 pip 镜像（默认自动检测）${NC}"
    echo -e "    ${DIM}无参数=auto，根据网络位置自动选择最优镜像${NC}"
    echo -e "    ${DIM}支持: auto, aliyun, tencent, pypi, custom:<url>${NC}"
    echo -e "    ${DIM}注意: 默认已启用自动检测，中国用户自动使用清华源${NC}"
    echo -e "    ${DIM}✨ 新增: 自动启用并行下载(8线程)和预编译包优先${NC}"
    echo -e "    ${DIM}✨ 预期效果: 安装速度提升 3-5 倍（12-18 分钟 vs 35-45 分钟）${NC}"
    echo ""
    echo -e "  ${BOLD}--no-mirror${NC}                              ${YELLOW}禁用 pip 镜像和网络优化${NC}"
    echo -e "    ${DIM}强制使用官方 PyPI，禁用所有加速优化${NC}"
    echo -e "    ${DIM}适用于海外用户或需要验证官方源完整性的场景${NC}"
    echo ""
    echo -e "  ${BOLD}--resume${NC}                                ${BLUE}断点续传安装（默认启用）${NC}"
    echo -e "    ${DIM}从上次失败的地方继续安装${NC}"
    echo -e "    ${DIM}如果没有断点，等同于正常安装${NC}"
    echo ""
    echo -e "  ${BOLD}--no-resume${NC}                             ${YELLOW}禁用断点续传${NC}"
    echo -e "    ${DIM}强制从头开始安装，忽略之前的进度${NC}"
    echo ""
    echo -e "  ${BOLD}--reset-checkpoint${NC}                      ${YELLOW}重置安装进度${NC}"
    echo -e "    ${DIM}清除之前的安装记录，从头开始${NC}"
    echo -e "    ${DIM}可与其他选项组合使用${NC}"
    echo ""
    echo -e "  ${BOLD}--verify-deps${NC}                              ${GREEN}依赖深度验证${NC}"
    echo -e "    ${DIM}检查 checksum、扫描漏洞、验证兼容性${NC}"
    echo -e "    ${DIM}适合安全敏感环境或生产部署前的验证${NC}"
    echo ""
    echo -e "  ${BOLD}--no-cache-clean, --skip-cache-clean${NC}        ${YELLOW}跳过 pip 缓存清理${NC}"
    echo -e "    ${DIM}默认安装前会清理 pip 缓存，此选项可跳过${NC}"
    echo -e "    ${DIM}适用于网络受限或缓存清理可能出错的环境${NC}"
    echo ""
    echo -e "  ${BOLD}--clean, --clean-before-install${NC}            ${GREEN}明确启用安装前清理${NC}"
    echo -e "    ${DIM}默认已启用，此选项可显式指定清理行为${NC}"
    echo ""
    echo -e "  ${BOLD}--no-clean, --skip-clean${NC}                   ${YELLOW}跳过安装前清理${NC}"
    echo -e "    ${DIM}默认会清理 Python 缓存、旧构建文件、空目录${NC}"
    echo -e "    ${DIM}使用此选项可跳过清理（加快安装速度）${NC}"
    echo ""
    echo ""
    echo -e "${BLUE}🛡️ 环境隔离配置：${NC}"
    echo ""
    echo -e "  ${BOLD}环境变量:${NC}"
    echo -e "    ${DIM}SAGE_VENV_POLICY=warning${NC}   默认，系统环境时警告"
    echo -e "    ${DIM}SAGE_VENV_POLICY=error${NC}     系统环境时报错退出"
    echo -e "    ${DIM}SAGE_VENV_POLICY=ignore${NC}    跳过虚拟环境检查"
    echo ""
    echo -e "    ${DIM}使用 pip-audit 和 safety 工具${NC}"
    echo -e "    ${DIM}与安装选项结合使用: ./quickstart.sh --verify-deps --dev${NC}"
    echo ""
    echo -e "  ${BOLD}--verify-deps-strict${NC}                       ${YELLOW}严格依赖验证${NC}"
    echo -e "    ${DIM}在发现任何问题时失败（用于 CI/CD）${NC}"
    echo -e "    ${DIM}推荐用于自动化部署流程${NC}"
    echo ""
    echo -e "  ${BOLD}--no-cache-clean, --skip-cache-clean${NC}        ${YELLOW}跳过 pip 缓存清理${NC}"
    echo -e "    ${DIM}默认安装前会清理 pip 缓存，此选项可跳过${NC}"
    echo -e "    ${DIM}适用于网络受限或缓存清理可能出错的环境${NC}"
    echo ""

    echo -e "${BLUE}💡 使用示例：${NC}"
    echo -e "  ./quickstart.sh                                  ${DIM}# 交互式安装（推荐）${NC}"
    echo -e "  ./quickstart.sh --yes                            ${DIM}# standard 安装 + 跳过确认（默认）${NC}"
    echo -e "  ./quickstart.sh --install-mode dev --yes         ${DIM}# 显式 dev 模式 + 跳过确认${NC}"
    echo -e "  ./quickstart.sh --mode standard --pip            ${DIM}# 显式 standard 模式 + 当前环境${NC}"
    echo -e "  ./quickstart.sh --dev --yes                      ${DIM}# 开发安装 + 跳过确认${NC}"
    echo -e "  ./quickstart.sh --standard --conda               ${DIM}# standard 安装 + 创建conda环境${NC}"
    echo -e "  ./quickstart.sh --clone-satellites --yes         ${DIM}# standard 安装(默认) + 克隆附属仓库${NC}"
    echo ""
    echo -e "${PURPLE}📝 注意：${NC}"
    echo -e "  ${DIM}• quickstart.sh 默认使用 standard 模式（子包依赖优先 PyPI）${NC}"
    echo -e "  ${DIM}• dev 模式会在 standard 基础上额外安装开发工具，并尽量切换为本地 editable${NC}"
    echo -e "  ${DIM}• pip 安装: pip install isage (等同于默认 standard 模式)${NC}"
    echo -e "  ${DIM}• 克隆要求网络连接到 GitHub，多个仓库可能需要几十秒${NC}"
    echo ""
}




# 解析安装模式参数
# 两种显式模式：--standard 与 --dev
parse_install_mode() {
    local param="$1"
    case "$param" in
        "--standard"|"-s")
            INSTALL_MODE="standard"
            return 0
            ;;
        # 开发安装：核心 + 开发工具
        "--dev"|"-d")
            INSTALL_MODE="dev"
            return 0
            ;;
        "--non-dev"|"--nondev")
            INSTALL_MODE="standard"
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析安装环境参数
parse_install_environment() {
    local param="$1"
    case "$param" in
        "--conda"|"-conda")
            INSTALL_ENVIRONMENT="conda"
            return 0
            ;;
        "--pip"|"-pip")
            INSTALL_ENVIRONMENT="pip"
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析自动确认参数
parse_auto_confirm() {
    local param="$1"
    case "$param" in
        "--yes"|"--y"|"-yes"|"-y")
            AUTO_CONFIRM=true
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析 pip 缓存清理参数
parse_cache_option() {
    local param="$1"
    case "$param" in
        "--no-cache-clean"|"--skip-cache-clean"|"-no-cache"|"-skip-cache")
            CLEAN_PIP_CACHE=false
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析安装前清理参数
parse_clean_before_install_option() {
    local param="$1"
    case "$param" in
        "--clean"|"--clean-before-install"|"--cleanup")
            CLEAN_BEFORE_INSTALL=true
            return 0
            ;;
        "--no-clean"|"--skip-clean"|"--no-cleanup")
            CLEAN_BEFORE_INSTALL=false
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析帮助参数
parse_help_option() {
    local param="$1"
    case "$param" in
        "--help"|"--h"|"-help"|"-h")
            SHOW_HELP=true
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析环境医生参数
parse_doctor_option() {
    local param="$1"
    case "$param" in
        "--doctor"|"--diagnose"|"--check-env")
            RUN_DOCTOR=true
            DOCTOR_ONLY=true
            return 0
            ;;
        "--doctor-fix"|"--diagnose-fix"|"--fix-env")
            RUN_DOCTOR=true
            FIX_ENVIRONMENT=true
            DOCTOR_ONLY=true
            return 0
            ;;
        "--pre-check"|"--env-check")
            RUN_DOCTOR=true
            DOCTOR_ONLY=false
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析断点续传参数
parse_resume_option() {
    local param="$1"
    case "$param" in
        "--resume")
            RESUME_INSTALL=true
            return 0
            ;;
        "--no-resume")
            RESUME_INSTALL=false
            return 0
            ;;
        "--reset-checkpoint")
            RESET_CHECKPOINT=true
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析依赖验证参数
parse_verify_deps_option() {
    local param="$1"
    case "$param" in
        "--verify-deps")
            VERIFY_DEPS=true
            VERIFY_DEPS_STRICT=false
            return 0
            ;;
        "--verify-deps-strict")
            VERIFY_DEPS=true
            VERIFY_DEPS_STRICT=true
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析强制重新编译参数
parse_force_rebuild_option() {
    local param="$1"
    case "$param" in
        "--force-rebuild")
            FORCE_REBUILD=true
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析克隆附属仓库参数
parse_clone_satellites_option() {
    local param="$1"
    case "$param" in
        "--clone-satellites"|"--clone-repos"|"--satellites")
            CLONE_SATELLITE_REPOS=true
            return 0
            ;;
        "--no-clone-satellites"|"--skip-satellites"|"--no-repos")
            CLONE_SATELLITE_REPOS=false
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 主参数解析函数
parse_arguments() {
    local unknown_params=()

    # 首先检查是否有帮助参数
    for arg in "$@"; do
        if parse_help_option "$arg"; then
            show_parameter_help
            exit 0
        fi
    done

    # 解析其他参数
    while [[ $# -gt 0 ]]; do
        local param="$1"

        if [[ "$param" == "--skip-hooks" ]]; then
            SKIP_HOOKS=true
            shift
        elif [[ "$param" == --install-mode=* ]] || [[ "$param" == --mode=* ]]; then
            set_install_mode_value "${param#*=}"
            shift
        elif [[ "$param" == "--install-mode" ]] || [[ "$param" == "--mode" ]]; then
            if [[ $# -lt 2 ]]; then
                echo -e "${CROSS} $param 需要一个值 (dev|standard)"
                exit 1
            fi
            set_install_mode_value "$2"
            shift 2
        elif [[ "$param" == "--workspace" ]]; then
            SETUP_WORKSPACE=true
            shift
        elif [[ "$param" == --hooks-mode=* ]]; then
            set_hooks_mode_value "${param#*=}"
            shift
        elif [[ "$param" == "--hooks-mode" ]]; then
            if [[ $# -lt 2 ]]; then
                echo -e "${CROSS} --hooks-mode 需要一个值 (auto|background|sync)"
                exit 1
            fi
            set_hooks_mode_value "$2"
            shift 2
        elif [[ "$param" == --hooks-profile=* ]]; then
            set_hooks_profile_value "${param#*=}"
            shift
        elif [[ "$param" == "--hooks-profile" ]]; then
            if [[ $# -lt 2 ]]; then
                echo -e "${CROSS} --hooks-profile 需要一个值 (lightweight|full)"
                exit 1
            fi
            set_hooks_profile_value "$2"
            shift 2
        elif [[ "$param" == --use-mirror=* ]]; then
            USE_PIP_MIRROR=true
            set_mirror_source_value "${param#*=}"
            shift
        elif [[ "$param" == "--use-mirror" ]]; then
            USE_PIP_MIRROR=true
            if [[ $# -ge 2 && ! "$2" =~ ^- ]]; then
                set_mirror_source_value "$2"
                shift 2
            else
                MIRROR_SOURCE="auto"
                shift
            fi
        elif [[ "$param" == "--no-mirror" ]]; then
            USE_PIP_MIRROR=false
            MIRROR_SOURCE="disable"
            shift
        elif parse_install_mode "$param"; then
            # 安装模式参数
            shift
        elif parse_install_environment "$param"; then
            # 安装环境参数
            shift
        elif parse_auto_confirm "$param"; then
            # 自动确认参数
            shift
        elif parse_cache_option "$param"; then
            # pip 缓存清理参数
            shift
        elif parse_clean_before_install_option "$param"; then
            # 安装前清理参数
            shift
        elif parse_doctor_option "$param"; then
            # 环境医生参数
            shift
        elif parse_resume_option "$param"; then
            # 断点续传参数
            shift
        elif parse_verify_deps_option "$param"; then
            # 依赖验证参数
            shift
        elif parse_force_rebuild_option "$param"; then
            # 强制重新编译参数
            shift
        elif parse_clone_satellites_option "$param"; then
            # 克隆附属仓库参数
            shift
        else
            # 未知参数
            unknown_params+=("$param")
            shift
        fi
    done

    # 处理未知参数
    if [ ${#unknown_params[@]} -gt 0 ]; then
        echo -e "${CROSS} 发现未知参数: ${unknown_params[*]}"
        echo ""
        show_parameter_help
        exit 1
    fi

    # 设置默认值并显示提示
    set_defaults_and_show_tips
}

set_defaults_and_show_tips() {
    local has_defaults=false

    # 检测 CI 环境并自动设置为确认模式
    if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" || -n "${GITLAB_CI:-}" || -n "${JENKINS_URL:-}" || -n "${BUILDKITE:-}" ]]; then
        AUTO_CONFIRM=true
        echo -e "${INFO} 检测到 CI 环境，自动启用确认模式"
        has_defaults=true

        # CI 环境中的环境选择逻辑
        # 在 CI 中，如果没有明确指定环境，强制使用 pip（即使有 conda）
        # 因为 CI 环境是临时的，使用 pip 安装更简单、更快
        if [ -z "$INSTALL_ENVIRONMENT" ]; then
            INSTALL_ENVIRONMENT="pip"
            echo -e "${INFO} CI 环境中自动使用 pip 模式（依赖系统 Python）"
            has_defaults=true
        elif [ "$INSTALL_ENVIRONMENT" = "conda" ] && ! command -v conda &> /dev/null; then
            # 如果明确指定了 conda 但 conda 不可用，降级到 pip
            echo -e "${WARNING} CI环境中指定了conda但未找到conda，自动降级为pip模式"
            INSTALL_ENVIRONMENT="pip"
            has_defaults=true
        fi

        # 检查是否在受管理的Python环境中（如Ubuntu 24.04+）
        if [ "$INSTALL_ENVIRONMENT" = "pip" ] || [ -z "$INSTALL_ENVIRONMENT" ]; then
            if python3 -c "import sysconfig; print(sysconfig.get_path('purelib'))" 2>/dev/null | grep -q "/usr/lib/python"; then
                echo -e "${WARNING} 检测到受管理的Python环境，在CI中推荐使用--break-system-packages"
                echo -e "${INFO} 这在CI环境中是安全的，因为CI环境是临时的"
            fi
        fi
    fi

    # 设置安装模式默认值
    if [ -z "$INSTALL_MODE" ]; then
        INSTALL_MODE="standard"
        echo -e "${INFO} 未指定安装模式，使用默认: ${YELLOW}standard 安装${NC} ${DIM}(历史兼容)${NC}"
        has_defaults=true
    fi

    # 设置安装环境默认值（基于当前环境智能选择）
    if [ -z "$INSTALL_ENVIRONMENT" ]; then
        local recommendation=$(get_smart_environment_recommendation)
        local recommended_env=$(echo "$recommendation" | cut -d'|' -f1)
        local current_env_type=$(echo "$recommendation" | cut -d'|' -f2)
        local current_env_name=$(echo "$recommendation" | cut -d'|' -f3)

        INSTALL_ENVIRONMENT="$recommended_env"

        if [ "$recommended_env" = "pip" ] && [ "$current_env_type" != "system" ]; then
            echo -e "${INFO} 检测到虚拟环境，使用默认: ${PURPLE}当前环境 ($current_env_type: $current_env_name)${NC}"
        elif [ "$recommended_env" = "conda" ]; then
            echo -e "${INFO} 检测到系统环境，推荐默认: ${GREEN}创建conda环境${NC}"
        else
            echo -e "${INFO} 未指定安装环境，使用默认: ${PURPLE}系统Python环境${NC}"
        fi
        has_defaults=true
    fi

    # 如果使用了默认值，显示提示
    if [ "$has_defaults" = true ]; then
        echo -e "${DIM}提示: 可使用 --help 查看所有可用选项${NC}"
        echo ""
    fi
}

# 显示安装配置信息
show_install_configuration() {
    echo -e "${BLUE}📋 安装配置：${NC}"
    case "$INSTALL_MODE" in
        "standard")
            echo -e "  ${BLUE}安装模式:${NC} ${YELLOW}standard 安装${NC}"
            ;;
        "dev")
            echo -e "  ${BLUE}安装模式:${NC} ${YELLOW}开发者安装${NC}"
            ;;
        *)
            echo -e "  ${BLUE}安装模式:${NC} ${YELLOW}standard 安装${NC}"
            ;;
    esac

    case "$INSTALL_ENVIRONMENT" in
        "conda")
            if [ -n "${SAGE_ENV_NAME:-}" ]; then
                echo -e "  ${BLUE}安装环境:${NC} ${GREEN}conda环境 (${SAGE_ENV_NAME})${NC}"
            else
                echo -e "  ${BLUE}安装环境:${NC} ${GREEN}conda环境${NC}"
            fi
            ;;
        "pip")
            # 检查是否在虚拟环境中
            local current_env_info=$(detect_current_environment)
            local env_type=$(echo "$current_env_info" | cut -d'|' -f1)
            local env_name=$(echo "$current_env_info" | cut -d'|' -f2)

            if [ "$env_type" != "system" ]; then
                echo -e "  ${BLUE}安装环境:${NC} ${PURPLE}当前环境 ($env_type: $env_name)${NC}"
            else
                echo -e "  ${BLUE}安装环境:${NC} ${PURPLE}系统Python环境${NC}"
            fi
            ;;
    esac

    if [ "$SKIP_HOOKS" = true ]; then
        echo -e "  ${BLUE}Git Hooks:${NC} ${DIM}跳过自动安装${NC}"
    else
        local hooks_mode_label="$HOOKS_MODE"
        if [ "$HOOKS_MODE" = "auto" ]; then
            hooks_mode_label="auto (交互式后台)"
        fi
        echo -e "  ${BLUE}Git Hooks:${NC} 模式=${GREEN}$hooks_mode_label${NC}, 配置=${PURPLE}$HOOKS_PROFILE${NC}"
    fi

    if [ "$USE_PIP_MIRROR" = true ]; then
        if [ "$MIRROR_SOURCE" = "auto" ]; then
            echo -e "  ${BLUE}pip 镜像:${NC} ${GREEN}自动检测${NC} ${DIM}(中国网络自动使用清华源)${NC}"
        else
            echo -e "  ${BLUE}pip 镜像:${NC} ${GREEN}$MIRROR_SOURCE${NC}"
        fi
    else
        echo -e "  ${BLUE}pip 镜像:${NC} ${YELLOW}已禁用${NC} ${DIM}(使用官方 PyPI)${NC}"
    fi

    if [ "$CLEAN_PIP_CACHE" = false ]; then
        echo -e "  ${BLUE}特殊选项:${NC} ${YELLOW}跳过 pip 缓存清理${NC}"
    fi

    if [ "$CLONE_SATELLITE_REPOS" = true ]; then
        echo -e "  ${BLUE}附属仓库:${NC} ${GREEN}克隆所有仓库${NC}"
    else
        echo -e "  ${BLUE}附属仓库:${NC} ${YELLOW}跳过克隆${NC}"
    fi

    echo ""
}

# 获取解析后的安装模式
get_install_mode() {
    echo "$INSTALL_MODE"
}

# 获取解析后的安装环境
get_install_environment() {
    echo "$INSTALL_ENVIRONMENT"
}

# 获取是否执行依赖验证
get_verify_deps() {
    echo "$VERIFY_DEPS"
}

# 获取是否执行严格依赖验证
get_verify_deps_strict() {
    echo "$VERIFY_DEPS_STRICT"
}

# 获取是否自动确认
get_auto_confirm() {
    echo "$AUTO_CONFIRM"
}

# 获取是否清理 pip 缓存
get_clean_pip_cache() {
    echo "$CLEAN_PIP_CACHE"
}

# 获取是否安装前清理
get_clean_before_install() {
    echo "$CLEAN_BEFORE_INSTALL"
}

# 检查是否需要显示帮助
should_show_help() {
    [ "$SHOW_HELP" = true ]
}

# 获取是否运行环境医生
get_run_doctor() {
    echo "$RUN_DOCTOR"
}

# 获取是否仅运行医生模式
get_doctor_only() {
    echo "$DOCTOR_ONLY"
}

# 获取是否修复环境
get_fix_environment() {
    echo "$FIX_ENVIRONMENT"
}

# 获取是否断点续传
get_resume_install() {
    echo "$RESUME_INSTALL"
}

# 获取是否强制重新编译
get_force_rebuild() {
    echo "$FORCE_REBUILD"
}

# 获取是否重置检查点
get_reset_checkpoint() {
    echo "$RESET_CHECKPOINT"
}

should_skip_hooks() {
    echo "$SKIP_HOOKS"
}

get_hooks_mode_value() {
    echo "$HOOKS_MODE"
}

get_hooks_profile_value() {
    echo "$HOOKS_PROFILE"
}

should_use_pip_mirror() {
    echo "$USE_PIP_MIRROR"
}

get_setup_workspace() {
    echo "$SETUP_WORKSPACE"
}

should_clone_satellite_repos() {
    echo "$CLONE_SATELLITE_REPOS"
}

get_mirror_source_value() {
    echo "$MIRROR_SOURCE"
}
