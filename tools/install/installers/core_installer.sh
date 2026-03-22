#!/bin/bash
# SAGE 安装脚本 - 核心包安装器 (重构版本)
# 负责通过主sage包统一安装所有依赖

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/logging.sh"

# 导入友好错误处理

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
CONDA_ENV_NAME="${CONDA_ENV_NAME:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
# ============================================================================

if [ -f "$(dirname "${BASH_SOURCE[0]}")/../fixes/friendly_error_handler.sh" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/../fixes/friendly_error_handler.sh"
fi

# CI环境检测
if [ "${CI:-}" = "true" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${GITLAB_CI:-}" ] || [ -n "${JENKINS_URL:-}" ]; then
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    # 确保在CI环境中禁用可能导致问题的进度条设置
    unset PIP_PROGRESS_BAR
elif [ "${SAGE_REMOTE_DEPLOY:-}" = "true" ]; then
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    # 远程部署环境也禁用可能导致问题的进度条设置
    unset PIP_PROGRESS_BAR
else
    export PYTHONNOUSERSITE=1
    # 非CI环境清除可能存在的全局进度条配置
    unset PIP_PROGRESS_BAR
fi

# 设置pip命令
PYTHON_CMD="${PYTHON_CMD:-python3}"
PIP_CMD="${PIP_CMD:-$PYTHON_CMD -m pip}"

parse_mirror_fallback_chain() {
    local current_index="${PIP_INDEX_URL:-https://pypi.org/simple/}"
    local chain="${SAGE_PIP_MIRROR_FALLBACKS:-}"

    local -a mirrors=()
    if [ -n "$chain" ]; then
        IFS='|' read -r -a mirrors <<< "$chain"
    fi

    local has_current=false
    local item
    for item in "${mirrors[@]}"; do
        if [ "$item" = "$current_index" ]; then
            has_current=true
            break
        fi
    done
    if [ "$has_current" = "false" ]; then
        mirrors=("$current_index" "${mirrors[@]}")
    fi

    local has_official=false
    for item in "${mirrors[@]}"; do
        if [ "$item" = "https://pypi.org/simple/" ]; then
            has_official=true
            break
        fi
    done
    if [ "$has_official" = "false" ]; then
        mirrors+=("https://pypi.org/simple/")
    fi

    local result=""
    for item in "${mirrors[@]}"; do
        [ -n "$item" ] || continue
        if [ -z "$result" ]; then
            result="$item"
        else
            result="$result|$item"
        fi
    done
    echo "$result"
}

pip_output_has_403_error() {
    local output_file="$1"
    grep -Eqi "(HTTP.*403|403[[:space:]]+Forbidden|status code[[:space:]]*403|response.*403)" "$output_file"
}

pip_install_with_mirror_403_retry() {
    local pip_args="$1"
    local log_file="$2"
    shift 2
    local -a pip_install_args=("$@")

    local mirrors
    mirrors="$(parse_mirror_fallback_chain)"
    local -a mirror_candidates=()
    IFS='|' read -r -a mirror_candidates <<< "$mirrors"

    local total_attempts=${#mirror_candidates[@]}
    if [ "$total_attempts" -le 0 ]; then
        mirror_candidates=("https://pypi.org/simple/")
        total_attempts=1
    fi

    local attempt=0
    local mirror_url
    local last_rc=1
    for mirror_url in "${mirror_candidates[@]}"; do
        [ -n "$mirror_url" ] || continue
        attempt=$((attempt + 1))
        echo -e "${DIM}[pip ${attempt}/${total_attempts}] 使用镜像: ${mirror_url}${NC}"

        local attempt_log
        attempt_log="$(mktemp)"

        set -o pipefail
        if PIP_INDEX_URL="$mirror_url" PIP_EXTRA_INDEX_URL="" $PIP_CMD install "${pip_install_args[@]}" $pip_args 2>&1 | tee -a "$log_file" "$attempt_log"; then
            set +o pipefail
            rm -f "$attempt_log"
            export PIP_INDEX_URL="$mirror_url"
            export PIP_EXTRA_INDEX_URL=""
            return 0
        fi
        last_rc=${PIPESTATUS[0]}
        set +o pipefail

        if pip_output_has_403_error "$attempt_log"; then
            echo -e "${WARNING} 检测到镜像返回 HTTP 403，自动切换下一个镜像重试"
            rm -f "$attempt_log"
            continue
        fi

        rm -f "$attempt_log"
        return "$last_rc"
    done

    return "$last_rc"
}

extract_meta_package_dependencies() {
    local install_mode="${1:-standard}"

    local mode_json="[]"
    if [ "$install_mode" = "full" ]; then
        mode_json='["full"]'
    elif [ "$install_mode" = "dev" ]; then
        mode_json='["full","dev"]'
    fi

    $PYTHON_CMD - <<PY
from __future__ import annotations

import json
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

pyproject_path = Path("pyproject.toml")
data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

project = data.get("project", {})
deps = list(project.get("dependencies", []) or [])
optional = project.get("optional-dependencies", {}) or {}

selected_extras = json.loads('''$mode_json''')
for extra in selected_extras:
    deps.extend(optional.get(extra, []) or [])

seen: set[str] = set()
for dep in deps:
    normalized = dep.strip()
    if not normalized or normalized in seen:
        continue
    seen.add(normalized)
    print(normalized)
PY
}

install_meta_dependencies_sequentially() {
    local install_mode="${1:-standard}"
    local pip_args="$2"
    local log_file="$3"

    local dep_specs=()
    while IFS= read -r dep; do
        [ -n "$dep" ] && dep_specs+=("$dep")
    done < <(extract_meta_package_dependencies "$install_mode")

    if [ ${#dep_specs[@]} -eq 0 ]; then
        log_warn "未提取到 meta-package 依赖，跳过预安装步骤" "INSTALL"
        echo -e "${WARNING} 未提取到依赖，跳过依赖预安装"
        return 0
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  🧩 预安装 meta-package 依赖（顺序安装，降低解析复杂度）${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    local idx=1
    local total=${#dep_specs[@]}
    local dep_spec
    for dep_spec in "${dep_specs[@]}"; do
        echo -e "${DIM}[${idx}/${total}] 安装依赖: ${dep_spec}${NC}"
        log_debug "PIP命令: $PIP_CMD install --upgrade \"$dep_spec\" [镜像403自动回退] $pip_args" "INSTALL"

        if ! pip_install_with_mirror_403_retry "$pip_args" "$log_file" --upgrade "$dep_spec"; then
            log_error "依赖预安装失败: $dep_spec" "INSTALL"
            echo -e "${CROSS} 依赖预安装失败: $dep_spec"
            return 1
        fi

        idx=$((idx + 1))
    done

    echo ""
    echo -e "${CHECK} meta-package 依赖预安装完成"
    return 0
}

install_resolver_guard_packages() {
    local pip_args="$1"
    local log_file="$2"

    local guard_specs=(
        "setuptools>=68"
        "wheel>=0.42"
        "wrapt>=1.15.0,<2.0.0"
    )

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  🛡️  预安装解析护栏依赖（避免回溯到不兼容旧版本）${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    local spec
    for spec in "${guard_specs[@]}"; do
        echo -e "${DIM}安装护栏依赖: ${spec}${NC}"
        if ! pip_install_with_mirror_403_retry "$pip_args" "$log_file" --upgrade "$spec"; then
            log_warn "护栏依赖安装失败，继续后续安装: $spec" "INSTALL"
            echo -e "${WARNING} 护栏依赖安装失败，继续: $spec"
        fi
    done

    echo ""
    echo -e "${CHECK} 解析护栏依赖处理完成"
    return 0
}

create_quickstart_constraints_file() {
    local project_root="$1"

    local constraints_file="$project_root/.sage/tmp/quickstart-pip-constraints.txt"
    cat > "$constraints_file" <<'EOF'
wrapt>=1.14.2,<2.0.0
setuptools>=68
wheel>=0.42
uvicorn>=0.34.0,<1.0.0
EOF

    echo "$constraints_file"
}

collect_workspace_repo_candidates() {
    local project_root="$1"
    local workspace_root
    workspace_root="$(dirname "$project_root")"
    local workspace_file="$project_root/SAGE.code-workspace"

    if [ ! -f "$workspace_file" ]; then
        return 0
    fi

    # SAGE.code-workspace 可能包含注释（JSONC）：按 name/path 成对提取，再用 path 定位仓库
    grep -oP '"name"\s*:\s*"\K[^"]+|"path"\s*:\s*"\K[^"]+' "$workspace_file" 2>/dev/null | \
        awk 'NR % 2 == 1 {name=$0; next} {print name "|" $0}' | \
        while IFS='|' read -r name rel_path; do
            [ -z "$rel_path" ] && continue
            [ "$rel_path" = "." ] && continue

            local repo_dir
            repo_dir="$(cd "$project_root" && cd "$rel_path" 2>/dev/null && pwd)"
            [ -n "$repo_dir" ] || continue
            [ -d "$repo_dir/.git" ] || continue

            local repo_name
            repo_name="$(basename "$repo_dir")"
            case "$repo_name" in
                sage*|sagellm*|neuromem)
                    echo "$repo_name"
                    ;;
                *)
                    ;;
            esac
        done
}

is_dev_editable_repo_allowed() {
    local repo_name="$1"

    case "$repo_name" in
        sage-benchmark|sage-docs|sage-examples|sage-tutorials)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# dev 模式下优先尝试安装本地 polyrepo 子仓库（editable）
install_local_editable_polyrepo_packages() {
    local project_root="$1"
    local log_file="$2"

    local workspace_root
    workspace_root="$(dirname "$project_root")"

    local repo_candidates=()
    while IFS= read -r repo_name; do
        [ -n "$repo_name" ] || continue
        if is_dev_editable_repo_allowed "$repo_name"; then
            repo_candidates+=("$repo_name")
        fi
    done < <(collect_workspace_repo_candidates "$project_root")

    if [ ${#repo_candidates[@]} -eq 0 ]; then
        local fallback_candidates=(
            "sage-benchmark"
            "sage-docs"
            "sage-tutorials"
            "sage-examples"
        )
        repo_candidates=("${fallback_candidates[@]}")
    fi

    local installed_count=0
    local skipped_count=0
    local failed_count=0

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  🧩 dev 模式：安装仍保持独立发布的本地仓库（editable，尽量）${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${DIM}工作区根目录: $workspace_root${NC}"
    echo -e "${DIM}说明: 已回收进主仓的核心 surface 不再自动按历史 split-repo 方式 editable 安装${NC}"
    echo ""

    for repo_name in "${repo_candidates[@]}"; do
        local repo_dir="$workspace_root/$repo_name"

        if [ ! -d "$repo_dir" ]; then
            echo -e "${DIM}  ⏭️  跳过 $repo_name（未检测到本地仓库）${NC}"
            skipped_count=$((skipped_count + 1))
            continue
        fi

        if [ ! -f "$repo_dir/pyproject.toml" ]; then
            echo -e "${DIM}  ⏭️  跳过 $repo_name（工作区内容仓库，无需 editable 安装）${NC}"
            skipped_count=$((skipped_count + 1))
            continue
        fi

        echo -e "${BOLD}  📦 安装本地 editable: $repo_name${NC}"
        if (cd "$repo_dir" && $PIP_CMD install -e "." --no-deps --upgrade --no-cache-dir >> "$log_file" 2>&1); then
            echo -e "${CHECK} $repo_name editable 安装成功"
            installed_count=$((installed_count + 1))
        else
            echo -e "${WARNING} $repo_name editable 安装失败，继续后续流程"
            echo -e "${DIM}      详情见日志: $log_file${NC}"
            failed_count=$((failed_count + 1))
        fi
    done

    echo ""
    echo -e "${INFO} 本地 editable 安装汇总: 成功 ${installed_count} / 跳过 ${skipped_count} / 失败 ${failed_count}"
    echo -e "${DIM}说明: dev 模式仅尝试安装仍保持独立发布的工作区仓库为 editable${NC}"
    echo ""
}

# ============================================================================
# 版本比较辅助函数
# ============================================================================

# 版本比较函数（语义版本）
version_gte() {
    # 比较 $1 >= $2（语义版本）
    # 返回 0（true）如果 $1 >= $2，否则返回 1（false）
    local ver1="$1"
    local ver2="$2"

    # 移除版本号中的非数字前缀（如 v2.7.0 -> 2.7.0）
    ver1="${ver1#v}"
    ver2="${ver2#v}"

    # 使用 Python 进行语义版本比较（更可靠）
    python3 -c "
from packaging import version
import sys
try:
    result = version.parse('$ver1') >= version.parse('$ver2')
    sys.exit(0 if result else 1)
except Exception:
    # 如果 packaging 不可用，使用简单字符串比较
    sys.exit(0 if '$ver1' >= '$ver2' else 1)
" 2>/dev/null
    return $?
}

# ============================================================================
# 核心安装函数
# ============================================================================

# 安装核心包
# SAGE 已重构为单一主仓 meta-package：
# - 根目录 `isage` 由本仓库直接维护并支持 editable 安装
# - 可选能力适配器通过 PyPI 版本号拉取
# - 适配器更新后需先发布到 PyPI，然后在 pyproject.toml 中更新版本号
install_core_packages() {
    local install_mode="${1:-dev}"  # default: dev

    # 根据 install_mode 选择安装目标（extras）
    # standard: pip install -e "."          (轻量，无 torch/CUDA)
    # full:     pip install -e ".[full]"    (扩展能力集)
    # dev:      pip install -e ".[full,dev]" (full + 开发工具 + local editable)
    local install_target
    case "$install_mode" in
        "dev")
            install_target='.[full,dev]'
            ;;
        "full")
            install_target='.[full]'
            ;;
        "standard"|*)
            install_mode="standard"
            install_target='.'
            ;;
    esac

    # 准备 pip 参数
    local pip_args="--disable-pip-version-check --no-input --prefer-binary --upgrade-strategy only-if-needed"

    # CI 环境额外处理
    if [ "${CI:-}" = "true" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${GITLAB_CI:-}" ] || [ -n "${JENKINS_URL:-}" ]; then
        pip_args="$pip_args --user"
        if $PYTHON_CMD -c "import sys; print(1 if '/usr' in sys.prefix else 0)" 2>/dev/null | grep -q "1"; then
            pip_args="$pip_args --break-system-packages"
            echo -e "${DIM}CI环境: 添加 --break-system-packages${NC}"
        fi
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "${DIM}CI环境: 使用 --user 安装，PATH+=~/.local/bin${NC}"
    fi

    # 获取项目根目录并初始化日志
    local project_root
    project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/.sage/logs/install.log"
    export SAGE_INSTALL_LOG="$log_file"
    mkdir -p "$project_root/.sage/logs" "$project_root/.sage/tmp" "$project_root/.sage/cache"

    local constraints_file
    constraints_file="$(create_quickstart_constraints_file "$project_root")"
    export SAGE_PIP_CONSTRAINT_FILE="$constraints_file"
    pip_args="$pip_args -c $constraints_file"

    log_info "SAGE 安装日志" "INSTALL"
    log_info "开始时间: $(date '+%Y-%m-%d %H:%M:%S')" "INSTALL"
    log_info "安装模式: $install_mode" "INSTALL"
    log_info "项目路径: $project_root" "INSTALL"

    echo -e "${INFO} 安装 SAGE ($install_mode 模式)..."
    echo -e "${DIM}安装日志: $log_file${NC}"
    echo -e "${DIM}pip constraints: $constraints_file${NC}"
    echo ""

    if [ "${CLEAN_BEFORE_INSTALL:-true}" != "true" ]; then
        echo -e "${WARNING} 检测到 --no-clean/--skip-clean：旧环境残留约束可能导致 pip 回溯过深（resolution-too-deep）"
        echo -e "${DIM}建议: 去掉 --no-clean，或先执行一次完整安装前清理${NC}"
        echo ""
    fi

    # 配置 pip 镜像源（遵循 quickstart 参数）
    # - USE_PIP_MIRROR=false (e.g. --no-mirror) 时：强制官方 PyPI + 禁用缓存
    # - 其他情况：按 MIRROR_SOURCE（默认 auto）配置
    echo -e "${BLUE}🌐 配置 pip 镜像源...${NC}"
    if [ "${USE_PIP_MIRROR:-true}" = "false" ]; then
        configure_pip_mirror "disable"
        pip_args="$pip_args --no-cache-dir"
        echo -e "${DIM}--no-mirror 生效：强制官方 PyPI + 禁用 pip 缓存${NC}"
    else
        configure_pip_mirror "${MIRROR_SOURCE:-auto}"
    fi
    echo ""

    # 记录环境信息
    log_phase_start_enhanced "环境信息收集" "INSTALL" 5
    log_environment "INSTALL"
    log_phase_end_enhanced "环境信息收集" "true" "INSTALL"

    case "$install_mode" in
        "standard")
            echo -e "${YELLOW}standard 安装：核心子包，无 torch/CUDA GPU 依赖${NC}"
            echo -e "${DIM}包含: 本地 isage (meta-package)，子包依赖从 PyPI 拉取：无 torch/peft/accelerate${NC}"
            ;;
        "full")
            echo -e "${CYAN}full 安装：standard + 扩展能力集${NC}"
            echo -e "${DIM}包含: .[full]（不强制 torch/CUDA）${NC}"
            ;;
        "dev")
            echo -e "${GREEN}dev 安装：full + 开发工具 + 本地子仓库 editable${NC}"
            echo -e "${DIM}包含: .[full,dev]，pytest/ruff/mypy/pre-commit + 优先本地 editable 覆盖${NC}"
            ;;
    esac
    echo ""

    # 检查 meta-package 目录
    if [ ! -f "pyproject.toml" ]; then
        log_error "找不到 meta-package (pyproject.toml)" "INSTALL"
        log_error "当前工作目录: $(pwd)" "INSTALL"
        echo -e "${CROSS} 错误：找不到 meta-package (pyproject.toml)"
        return 1
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  📦 安装 SAGE ($install_mode 模式：$install_target + PyPI 子包)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${DIM}安装策略: editable install 本地 isage (meta-package)，子包依赖默认从 PyPI 版本拉取${NC}"
    echo -e "${DIM}子包更新需先发布到 PyPI，再在 pyproject.toml 中更新版本号${NC}"
    echo ""

    log_info "安装目标: $install_target" "INSTALL"

    log_phase_start_enhanced "解析护栏依赖安装" "INSTALL" 60
    install_resolver_guard_packages "$pip_args" "$log_file"
    log_phase_end_enhanced "解析护栏依赖安装" "success" "INSTALL"

    log_phase_start_enhanced "meta-package 依赖预安装" "INSTALL" 180
    if ! install_meta_dependencies_sequentially "$install_mode" "$pip_args" "$log_file"; then
        log_phase_end_enhanced "meta-package 依赖预安装" "failure" "INSTALL"
        return 1
    fi
    log_phase_end_enhanced "meta-package 依赖预安装" "success" "INSTALL"

    log_phase_start_enhanced "SAGE meta-package 安装" "INSTALL" 120
    log_debug "PIP命令: $PIP_CMD install -e \"$install_target\" --no-deps $pip_args" "INSTALL"

    echo -e "${DIM}[INFO] 安装目标: $install_target${NC}"
    echo -e "${DIM}[INFO] 安装日志同步写入: $log_file${NC}"
    echo ""

    # 直接流式输出 pip 进度到终端，同时 tee 到日志文件
    # 针对镜像 403 进行自动回退重试
    if ! pip_install_with_mirror_403_retry "$pip_args" "$log_file" -e "$install_target" --no-deps; then
        log_error "安装失败: $install_target" "INSTALL"
        echo -e "${CROSS} SAGE meta-package 安装失败！"
        log_phase_end_enhanced "SAGE meta-package 安装" "failure" "INSTALL"
        return 1
    fi

    log_info "安装成功: $install_target" "INSTALL"
    log_pip_package_info "isage" "INSTALL"
    log_phase_end_enhanced "SAGE meta-package 安装" "success" "INSTALL"

    echo ""
    echo -e "${CHECK} SAGE ($install_mode 模式) 安装成功"
    echo -e "${DIM}      子包依赖已从 PyPI 解析并安装${NC}"
    echo ""

    # dev 模式：尽量将可用的本地 polyrepo 子仓库覆盖为 editable
    if [ "$install_mode" = "dev" ]; then
        log_phase_start_enhanced "dev 本地 editable 覆盖安装" "INSTALL" 60
        install_local_editable_polyrepo_packages "$project_root" "$log_file"
        log_phase_end_enhanced "dev 本地 editable 覆盖安装" "success" "INSTALL"
    fi

    log_info "SAGE ($install_mode 模式) 安装完成" "INSTALL"
    return 0
}

# 安装科学计算包（保持向后兼容）
install_scientific_packages() {
    echo -e "${DIM}科学计算包已包含在标准/开发模式中，跳过单独安装${NC}"
    return 0
}

# 安装开发工具（保持向后兼容）
install_dev_tools() {
    echo -e "${DIM}开发工具已包含在开发模式中，跳过单独安装${NC}"
    return 0
}

# 导出函数
export -f install_core_packages
export -f install_scientific_packages
export -f install_dev_tools
