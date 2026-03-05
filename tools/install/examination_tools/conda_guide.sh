#!/bin/bash
# SAGE: Conda Environment Guide
# 引导用户下载、安装 Conda 并创建专用环境
# 借鉴自 sagellm/scripts/installation/checks/conda_guide.sh

set -e

_CONDA_GUIDE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_CONDA_GUIDE_DIR/../display_tools/colors.sh"

# ============================================================
# Constants
# ============================================================

SAGE_CONDA_ENV_NAME="${SAGE_CONDA_ENV_NAME:-sage}"
SAGE_PYTHON_VERSION="${SAGE_PYTHON_VERSION:-3.11}"

# Miniforge installer URLs (open-source, conda-forge default, supports ARM/x86)
_MINIFORGE_BASE_URL="https://github.com/conda-forge/miniforge/releases/latest/download"
_MINIFORGE_BASE_URL_CN="https://mirrors.tuna.tsinghua.edu.cn/github-release/conda-forge/miniforge/LatestRelease"

_get_miniforge_installer_name() {
    local os arch
    os="$(uname -s)"
    arch="$(uname -m)"

    case "$os" in
        Linux)
            case "$arch" in
                x86_64)  echo "Miniforge3-Linux-x86_64.sh" ;;
                aarch64) echo "Miniforge3-Linux-aarch64.sh" ;;
                *)       echo "Miniforge3-Linux-x86_64.sh" ;;
            esac
            ;;
        Darwin)
            case "$arch" in
                arm64)   echo "Miniforge3-MacOSX-arm64.sh" ;;
                x86_64)  echo "Miniforge3-MacOSX-x86_64.sh" ;;
                *)       echo "Miniforge3-MacOSX-x86_64.sh" ;;
            esac
            ;;
        *)
            echo "Miniforge3-Linux-x86_64.sh"
            ;;
    esac
}

# ============================================================
# Local print helpers (inline, no dependency on output_formatter)
# ============================================================

_cg_print_success() { echo -e "${GREEN}   ✅ $*${NC}"; }
_cg_print_error()   { echo -e "${RED}   ❌ $*${NC}"; }
_cg_print_warning() { echo -e "${YELLOW}   ⚠️  $*${NC}"; }
_cg_print_info()    { echo -e "${BLUE}   ℹ️  $*${NC}"; }

# ============================================================
# Utility helpers
# ============================================================

_conda_is_installed() {
    command -v conda >/dev/null 2>&1
}

_is_ci() {
    [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" || -n "${GITLAB_CI:-}" || -n "${JENKINS_URL:-}" || -n "${BUILDKITE:-}" ]]
}

_is_interactive() {
    [ -t 0 ] && [ -t 1 ]
}

_is_auto_confirm() {
    [[ "${AUTO_YES:-false}" = "true" || "${AUTO_CONFIRM:-false}" = "true" || "${SAGE_AUTO_CONFIRM:-false}" = "true" ]]
}

# ============================================================
# Case 1: Conda 未安装 → 引导安装 Miniforge3
# ============================================================

guide_install_conda() {
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}   ⚠️  未检测到 Conda${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}SAGE 强烈建议在 Conda 环境中运行，原因：${NC}"
    echo -e "  • 隔离依赖，避免污染系统 Python"
    echo -e "  • 支持精确 Python 版本控制（需 >= 3.10）"
    echo -e "  • 多项目并行开发时互不干扰"
    echo -e "  • 与 Ascend / CUDA 硬件驱动环境兼容性更好"
    echo ""
    echo -e "${BOLD}推荐安装方式：Miniforge3（轻量，默认 conda-forge 频道）${NC}"
    echo ""

    local installer_name
    installer_name="$(_get_miniforge_installer_name)"

    echo -e "${CYAN}方法 1：官方下载（国际网络）${NC}"
    echo -e "  wget ${_MINIFORGE_BASE_URL}/${installer_name}"
    echo -e "  bash ${installer_name} -b -p \$HOME/miniforge3"
    echo -e "  source \$HOME/miniforge3/etc/profile.d/conda.sh"
    echo -e "  conda init bash"
    echo ""
    echo -e "${CYAN}方法 2：清华镜像（国内推荐）${NC}"
    echo -e "  wget ${_MINIFORGE_BASE_URL_CN}/${installer_name}"
    echo -e "  bash ${installer_name} -b -p \$HOME/miniforge3"
    echo -e "  source \$HOME/miniforge3/etc/profile.d/conda.sh"
    echo -e "  conda init bash"
    echo ""
    echo -e "${CYAN}安装后，创建专用环境：${NC}"
    echo -e "  conda create -n ${SAGE_CONDA_ENV_NAME} python=${SAGE_PYTHON_VERSION} -y"
    echo -e "  conda activate ${SAGE_CONDA_ENV_NAME}"
    echo -e "  ./quickstart.sh"
    echo ""

    if _is_ci || _is_auto_confirm; then
        _cg_print_warning "CI/自动确认模式：未安装 Conda，继续在当前环境安装（可能存在依赖冲突）"
        return 0
    fi

    if ! _is_interactive; then
        _cg_print_warning "非交互模式：未安装 Conda，继续在当前环境安装"
        return 0
    fi

    echo -e "${YELLOW}是否现在自动下载并安装 Miniforge3？${NC}"
    echo -e "  [1] 是，使用官方源下载"
    echo -e "  [2] 是，使用清华镜像下载（国内网络推荐）"
    echo -e "  [3] 否，我稍后自行安装"
    echo -e "  [4] 否，跳过 Conda，继续在当前环境安装"
    echo ""
    read -r -p "请选择 [1/2/3/4]（默认 4）: " choice
    choice="${choice:-4}"

    case "$choice" in
        1|2)
            _auto_install_miniforge "$installer_name" "$choice"
            return $?
            ;;
        3)
            echo ""
            echo -e "${BLUE}请完成以下步骤后重新运行 ./quickstart.sh：${NC}"
            echo -e "  1. 安装 Miniforge3（见上方命令）"
            echo -e "  2. conda create -n ${SAGE_CONDA_ENV_NAME} python=${SAGE_PYTHON_VERSION} -y"
            echo -e "  3. conda activate ${SAGE_CONDA_ENV_NAME}"
            echo -e "  4. ./quickstart.sh"
            exit 0
            ;;
        4)
            _cg_print_warning "跳过 Conda 安装，继续在当前 Python 环境中安装（可能存在依赖冲突）"
            return 0
            ;;
        *)
            _cg_print_warning "无效选择，跳过 Conda 安装，继续当前环境"
            return 0
            ;;
    esac
}

_auto_install_miniforge() {
    local installer_name="$1"
    local mirror_choice="$2"

    local download_url
    if [ "$mirror_choice" = "1" ]; then
        download_url="${_MINIFORGE_BASE_URL}/${installer_name}"
    else
        download_url="${_MINIFORGE_BASE_URL_CN}/${installer_name}"
    fi

    local install_prefix="$HOME/miniforge3"
    local installer_path="/tmp/${installer_name}"

    if ! command -v wget >/dev/null 2>&1 && ! command -v curl >/dev/null 2>&1; then
        _cg_print_error "未找到 wget 或 curl，无法自动下载"
        _cg_print_info "请手动下载并安装 Miniforge3，然后重新运行 ./quickstart.sh"
        return 1
    fi

    # 若已有完整安装，跳过下载与安装步骤
    if [ -x "${install_prefix}/bin/conda" ]; then
        _cg_print_success "检测到已有 Miniforge3 安装：${install_prefix}，跳过下载与安装"
    else
        echo ""
        echo -e "${BLUE}📥 下载 Miniforge3...${NC}"
        echo -e "  URL: ${download_url}"
        echo -e "  目标: ${installer_path}"
        echo ""

        if command -v wget >/dev/null 2>&1; then
            wget -q --show-progress -O "$installer_path" "$download_url" || {
                _cg_print_error "下载失败，请检查网络连接"
                return 1
            }
        else
            curl -L --progress-bar -o "$installer_path" "$download_url" || {
                _cg_print_error "下载失败，请检查网络连接"
                return 1
            }
        fi

        echo ""
        echo -e "${BLUE}📦 安装 Miniforge3 到 ${install_prefix}...${NC}"

        if [ -d "$install_prefix" ]; then
            _cg_print_warning "目录已存在但 conda 不完整，使用 -u 模式更新..."
            bash "$installer_path" -b -u -p "$install_prefix" || {
                _cg_print_error "安装失败"
                rm -f "$installer_path"
                return 1
            }
        else
            bash "$installer_path" -b -p "$install_prefix" || {
                _cg_print_error "安装失败"
                rm -f "$installer_path"
                return 1
            }
        fi
        rm -f "$installer_path"
    fi

    # 初始化 conda 供当前 shell 使用
    # shellcheck disable=SC1091
    source "${install_prefix}/etc/profile.d/conda.sh" || true

    echo ""
    _cg_print_success "Miniforge3 安装完成：${install_prefix}"

    echo -e "${BLUE}🔧 初始化 Conda shell integration...${NC}"
    "${install_prefix}/bin/conda" init bash 2>/dev/null || true

    echo ""
    echo -e "${BLUE}🐍 创建专用 Conda 环境: ${SAGE_CONDA_ENV_NAME} (Python ${SAGE_PYTHON_VERSION})...${NC}"
    "${install_prefix}/bin/conda" create -n "${SAGE_CONDA_ENV_NAME}" "python=${SAGE_PYTHON_VERSION}" -y || {
        _cg_print_error "创建环境失败"
        return 1
    }

    _cg_print_success "环境 '${SAGE_CONDA_ENV_NAME}' 创建成功"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}   ✅ Conda 安装完成！${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    # 将 sage 环境写入 bashrc，设为默认
    setup_bashrc_conda_default "${SAGE_CONDA_ENV_NAME}"
    echo -e "${BLUE}请在新终端（或重新 source ~/.bashrc 后）执行：${NC}"
    echo ""
    echo -e "  ${CYAN}conda activate ${SAGE_CONDA_ENV_NAME}${NC}"
    echo -e "  ${CYAN}./quickstart.sh${NC}"
    echo ""
    echo -e "提示：如果 conda 命令不可用，请先执行："
    echo -e "  ${CYAN}source ${install_prefix}/etc/profile.d/conda.sh${NC}"
    echo ""
    exit 0
}

# ============================================================
# Case 2: Conda base 环境激活 → 警告并引导创建专用环境
# ============================================================

guide_conda_base_env() {
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}   ⚠️  检测到 Conda base 环境${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${RED}   ❌ 不建议在 base 环境中安装 SAGE${NC}"
    echo ""
    echo -e "${BLUE}   原因：${NC}"
    echo -e "   • 可能导致 conda base 环境污染，影响系统其他工具"
    echo -e "   • 依赖版本冲突风险高（numpy、torch、protobuf 等）"
    echo -e "   • 难以后续清理和卸载"
    echo ""
    echo -e "${GREEN}   建议：创建并激活专用 '${SAGE_CONDA_ENV_NAME}' 环境${NC}"
    echo ""
    echo -e "${CYAN}   手动操作命令：${NC}"
    echo -e "     conda create -n ${SAGE_CONDA_ENV_NAME} python=${SAGE_PYTHON_VERSION} -y"
    echo -e "     conda activate ${SAGE_CONDA_ENV_NAME}"
    echo -e "     ./quickstart.sh"
    echo ""

    if _is_ci; then
        _cg_print_warning "CI 环境：检测到 base 环境，继续安装（CI 流程允许）"
        return 0
    fi

    if _is_auto_confirm; then
        _cg_print_warning "自动确认模式：在 base 环境中继续安装"
        return 0
    fi

    if ! _is_interactive; then
        _cg_print_warning "非交互模式：在 base 环境中继续安装"
        return 0
    fi

    echo -e "${YELLOW}请选择操作：${NC}"
    echo -e "  [1] 自动创建 '${SAGE_CONDA_ENV_NAME}' 环境（推荐）"
    echo -e "  [2] 继续在 base 环境安装（不推荐）"
    echo -e "  [3] 取消，我手动操作"
    echo ""
    read -r -p "请选择 [1/2/3]（默认 1）: " choice
    choice="${choice:-1}"

    case "$choice" in
        1)
            _create_and_guide_activate_env
            return $?
            ;;
        2)
            echo ""
            _cg_print_warning "继续在 conda base 环境安装，风险自负"
            return 0
            ;;
        3|*)
            echo ""
            echo -e "${BLUE}手动操作步骤：${NC}"
            echo -e "  conda create -n ${SAGE_CONDA_ENV_NAME} python=${SAGE_PYTHON_VERSION} -y"
            echo -e "  conda activate ${SAGE_CONDA_ENV_NAME}"
            echo -e "  ./quickstart.sh"
            exit 0
            ;;
    esac
}

# ============================================================
# Case 3: Conda 已安装但无环境激活 → 引导创建专用环境
# ============================================================

guide_conda_no_env() {
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}   ℹ️  检测到 Conda 已安装，但未激活任何环境${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}建议为 SAGE 创建独立的 Conda 环境：${NC}"
    echo -e "  conda create -n ${SAGE_CONDA_ENV_NAME} python=${SAGE_PYTHON_VERSION} -y"
    echo -e "  conda activate ${SAGE_CONDA_ENV_NAME}"
    echo -e "  ./quickstart.sh"
    echo ""

    if _is_ci || _is_auto_confirm; then
        _cg_print_warning "自动确认模式：跳过 Conda 环境创建，继续当前 Python 环境"
        return 0
    fi

    if ! _is_interactive; then
        _cg_print_warning "非交互模式：跳过 Conda 环境创建"
        return 0
    fi

    echo -e "${YELLOW}请选择操作：${NC}"
    echo -e "  [1] 自动创建并提示激活 '${SAGE_CONDA_ENV_NAME}' 环境（推荐）"
    echo -e "  [2] 继续在当前系统 Python 环境安装"
    echo -e "  [3] 取消，我手动操作"
    echo ""
    read -r -p "请选择 [1/2/3]（默认 1）: " choice
    choice="${choice:-1}"

    case "$choice" in
        1)
            _create_and_guide_activate_env
            return $?
            ;;
        2)
            _cg_print_warning "继续在系统 Python 环境安装，建议后续迁移到 Conda 环境"
            return 0
            ;;
        3|*)
            echo ""
            echo -e "${BLUE}手动操作步骤：${NC}"
            echo -e "  conda create -n ${SAGE_CONDA_ENV_NAME} python=${SAGE_PYTHON_VERSION} -y"
            echo -e "  conda activate ${SAGE_CONDA_ENV_NAME}"
            echo -e "  ./quickstart.sh"
            exit 0
            ;;
    esac
}

# ============================================================
# RC 文件写入工具：将 conda activate <env> 写入 shell RC 文件
# ============================================================

# 将 conda activate 行写入 RC 文件（conda initialize 块之后，或末尾）
_write_conda_activate_to_rc() {
    local rc_file="$1"
    local env_name="$2"
    local marker="$3"
    local activate_line="$4"

    if grep -q "<<< conda initialize <<<" "$rc_file" 2>/dev/null; then
        local tmp
        tmp="$(mktemp)"
        awk -v marker="$marker" -v activate="$activate_line" '
            /<<< conda initialize <<</ {
                print
                print ""
                print marker
                print activate
                next
            }
            { print }
        ' "$rc_file" > "$tmp"
        mv "$tmp" "$rc_file"
    else
        printf '\n%s\n%s\n' "$marker" "$activate_line" >> "$rc_file"
    fi

    _cg_print_success "已写入 ${rc_file}"
    echo ""
    echo -e "提示：在当前终端立即生效请执行："
    echo -e "  ${CYAN}source ${rc_file}${NC}"
    echo ""
    echo -e "之后每次打开新终端都会自动激活 '${env_name}' 环境。"
}

# 安装完成后将 sage conda 环境写入 shell RC 文件，设为默认环境
# 参数：可选 env_name（默认 $SAGE_CONDA_ENV_NAME）
# 跳过条件：CI / SAGE_NO_SET_DEFAULT_ENV=true
setup_bashrc_conda_default() {
    local env_name="${1:-${SAGE_CONDA_ENV_NAME:-sage}}"

    if _is_ci; then
        _cg_print_warning "CI 环境：跳过默认 Conda 环境配置"
        return 0
    fi

    if [ "${SAGE_NO_SET_DEFAULT_ENV:-false}" = "true" ]; then
        _cg_print_info "已跳过默认 Conda 环境配置（--no-set-default-env）"
        return 0
    fi

    # ── 禁用 auto_activate_base，防止新终端自动进入 base 覆盖后续 activate ──
    if _conda_is_installed; then
        local _conda_bin
        _conda_bin="$(command -v conda 2>/dev/null || echo conda)"
        if ! grep -q "^auto_activate_base: false" "$HOME/.condarc" 2>/dev/null; then
            "$_conda_bin" config --set auto_activate_base false 2>/dev/null && \
                _cg_print_success "已设置 auto_activate_base=false（禁止新终端默认进入 base）" || true
        fi
    fi

    local shell_type
    shell_type="$(basename "${SHELL:-bash}")"
    local primary_rc=""
    local rc_files=()

    case "$shell_type" in
        zsh) primary_rc="$HOME/.zshrc" ;;
        bash|*)
            primary_rc="$HOME/.bashrc"
            [ -f "$HOME/.bashrc" ] || primary_rc="$HOME/.bash_profile"
            ;;
    esac

    for _f in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.bash_profile"; do
        [ -f "$_f" ] && rc_files+=("$_f")
    done

    if [ ${#rc_files[@]} -eq 0 ]; then
        _cg_print_warning "未找到 shell 配置文件（~/.bashrc / ~/.zshrc），跳过默认环境配置"
        return 0
    fi

    [ -f "$primary_rc" ] || touch "$primary_rc"

    local activate_line="conda activate ${env_name}"
    local marker="# sage: auto-activate conda env"

    # 检查是否已在任意 RC 文件中配置
    local already_in=""
    for _f in "${rc_files[@]}"; do
        if grep -qF "$activate_line" "$_f" 2>/dev/null; then
            already_in="$_f"
            break
        fi
    done

    if [ -n "$already_in" ]; then
        _cg_print_success "默认 Conda 环境 '${env_name}' 已配置于 ${already_in}，无需重复添加"
        return 0
    fi

    if ! grep -q "conda initialize" "$primary_rc" 2>/dev/null; then
        echo ""
        _cg_print_warning "${primary_rc} 中未检测到 'conda initialize' 块"
        echo -e "  conda 可能尚未初始化 shell。如新终端中 conda 命令不可用，请运行："
        echo -e "  ${CYAN}conda init bash && source ${primary_rc}${NC}"
        echo ""
    fi

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   🐍 设置默认 Conda 环境${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "正在将以下内容写入 ${CYAN}${primary_rc}${NC}"
    echo -e "  ${CYAN}${marker}${NC}"
    echo -e "  ${CYAN}${activate_line}${NC}"
    echo ""

    _write_conda_activate_to_rc "$primary_rc" "$env_name" "$marker" "$activate_line"

    echo -e "如需撤销，删除 ${primary_rc} 中以下两行即可："
    echo -e "  ${marker}"
    echo -e "  ${activate_line}"
    echo -e "或使用 --no-set-default-env 跳过（重新运行 ./quickstart.sh --no-set-default-env）。"
    echo ""
}

# ============================================================
# Internal: 创建环境并打印激活引导
# ============================================================

_create_and_guide_activate_env() {
    if conda env list 2>/dev/null | grep -qE "^${SAGE_CONDA_ENV_NAME}[[:space:]]"; then
        _cg_print_success "环境 '${SAGE_CONDA_ENV_NAME}' 已存在"
    else
        echo ""
        echo -e "${BLUE}🐍 创建 Conda 环境: ${SAGE_CONDA_ENV_NAME} (Python ${SAGE_PYTHON_VERSION})...${NC}"
        conda create -n "${SAGE_CONDA_ENV_NAME}" "python=${SAGE_PYTHON_VERSION}" -y || {
            _cg_print_error "创建环境失败，请检查 Conda 安装是否完整"
            return 1
        }
        _cg_print_success "环境 '${SAGE_CONDA_ENV_NAME}' 创建成功"
    fi

    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}   ✅ 请激活环境后重新运行安装脚本${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    # 写入 bashrc，下次打开终端自动激活 sage 环境
    setup_bashrc_conda_default "${SAGE_CONDA_ENV_NAME}"
    echo -e "  ${CYAN}conda activate ${SAGE_CONDA_ENV_NAME}${NC}"
    echo -e "  ${CYAN}./quickstart.sh${NC}"
    echo ""
    echo -e "提示：Conda 环境切换需要在同一 shell 中执行，脚本无法替您激活。"
    echo ""
    exit 0
}

# ============================================================
# Main entry: check_conda_environment
# 统一处理所有 conda 场景，由 environment_prechecks.sh 调用
# ============================================================

check_conda_environment() {
    local _rc=0

    # Case 1: conda 已安装，已激活非 base 环境 → OK
    if _conda_is_installed && [ -n "${CONDA_DEFAULT_ENV:-}" ] && [ "${CONDA_DEFAULT_ENV:-}" != "base" ]; then
        echo -e "${GREEN}   ✅ 已检测到 Conda 环境: ${CONDA_DEFAULT_ENV}${NC}"
        _rc=0
    # Case 2: conda 已安装，base 环境激活 → 警告并引导
    elif _conda_is_installed && [ "${CONDA_DEFAULT_ENV:-}" = "base" ]; then
        guide_conda_base_env
        _rc=$?
    # Case 3: conda 已安装但未激活任何环境
    elif _conda_is_installed && [ -z "${CONDA_DEFAULT_ENV:-}" ]; then
        guide_conda_no_env
        _rc=$?
    # Case 4: conda 未安装
    elif ! _conda_is_installed; then
        guide_install_conda
        _rc=$?
    fi

    # 标记已完成检查，避免 run_environment_prechecks 重复调用
    _SAGE_CONDA_ENV_CHECKED=true
    return $_rc
}

# Run if executed directly
if [ "${BASH_SOURCE[0]}" -ef "$0" ]; then
    check_conda_environment
    exit $?
fi
