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
PIP_CMD="${PIP_CMD:-pip3}"

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

# 安装核心包 - 新的简化版本
install_core_packages() {
    local install_mode="${1:-dev}"  # 默认为开发模式

    # 准备pip安装参数
    local pip_args="--disable-pip-version-check --no-input"

    # CI环境额外处理
    if [ "${CI:-}" = "true" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${GITLAB_CI:-}" ] || [ -n "${JENKINS_URL:-}" ]; then
        # 在CI中将包安装到用户site（~/.local），便于跨job缓存与导入
        pip_args="$pip_args --user"
        # 某些系统前缀可能仍需此选项
        if python3 -c "import sys; print(1 if '/usr' in sys.prefix else 0)" 2>/dev/null | grep -q "1"; then
            pip_args="$pip_args --break-system-packages"
            echo -e "${DIM}CI环境: 添加 --break-system-packages${NC}"
        fi
        # 确保用户脚本目录在PATH中（供 'sage' 可执行脚本使用）
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "${DIM}CI环境: 使用 --user 安装，PATH+=~/.local/bin${NC}"
        # CI环境也使用 off，避免版本兼容性问题
        pip_args="$pip_args --progress-bar=off"
    else
        # 非CI环境，使用简洁进度条（off 在所有 pip 版本中都支持）
        pip_args="$pip_args --progress-bar=off"
    fi

    # 获取项目根目录并初始化日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/.sage/logs/install.log"

    # 设置全局日志文件路径
    export SAGE_INSTALL_LOG="$log_file"

    # 确保.sage目录结构存在
    mkdir -p "$project_root/.sage/logs"
    mkdir -p "$project_root/.sage/tmp"
    mkdir -p "$project_root/.sage/cache"

    # 初始化日志文件
    log_info "SAGE 安装日志" "INSTALL"
    log_info "开始时间: $(date '+%Y-%m-%d %H:%M:%S')" "INSTALL"
    log_info "安装模式: $install_mode" "INSTALL"
    log_info "项目路径: $project_root" "INSTALL"

    echo -e "${INFO} 安装 SAGE ($install_mode 模式)..."
    echo -e "${DIM}安装日志: $log_file${NC}"
    echo ""

    # 配置 pip 镜像源（自动检测网络）
    echo -e "${BLUE}🌐 配置 pip 镜像源...${NC}"
    configure_pip_mirror "auto"
    echo ""

    # 记录环境信息
    log_phase_start_enhanced "环境信息收集" "INSTALL" 5
    log_environment "INSTALL"
    log_phase_end_enhanced "环境信息收集" "true" "INSTALL"

    case "$install_mode" in
        "core")
            echo -e "${GRAY}核心运行时：L1-L4 (仅运行时)${NC}"
            echo -e "${DIM}包含: common, platform, kernel, libs, middleware (~100MB)${NC}"
            ;;
        "standard")
            echo -e "${GREEN}标准模式：Core + CLI + 科学计算${NC}"
            echo -e "${DIM}包含: L1-L4 + sage-cli + numpy, pandas, matplotlib (~200MB)${NC}"
            ;;
        "full")
            echo -e "${PURPLE}完整功能：Standard + 开发工具${NC}"
            echo -e "${DIM}包含: 标准 + sage-tools (~250MB)${NC}"
            ;;
        "dev")
            echo -e "${YELLOW}开发模式：Full + 开发工具${NC}"
            echo -e "${DIM}包含: 完整 + sage-tools, pytest, black, mypy, pre-commit (~350MB)${NC}"
            ;;
        *)
            echo -e "${YELLOW}未知模式，使用开发者模式${NC}"
            install_mode="dev"
            ;;
    esac

    echo ""

    # 检查所有必要的包目录是否存在
    local required_packages=("packages/sage-common" "packages/sage-platform" "packages/sage-kernel")

    # 根据模式添加更多包
    if [ "$install_mode" != "core" ]; then
        required_packages+=("packages/sage-middleware" "packages/sage-libs")
        # standard/full/dev 模式需要 CLI
        required_packages+=("packages/sage-cli")
        # Note: sage-benchmark moved to independent repo (pip install isage-benchmark)
    fi

    # dev 模式需要 sage-tools
    if [ "$install_mode" = "full" ] || [ "$install_mode" = "dev" ]; then
        [ -d "packages/sage-tools" ] && required_packages+=("packages/sage-tools")
    fi

    required_packages+=("packages/sage")

    for package_dir in "${required_packages[@]}"; do
        if [ ! -d "$package_dir" ]; then
            log_error "找不到包目录: $package_dir" "INSTALL"
            log_error "当前工作目录: $(pwd)" "INSTALL"
            log_error "项目根目录: $project_root" "INSTALL"
            echo -e "${CROSS} 错误：找不到包目录 ($package_dir)"
            return 1
        fi
    done

    # 执行安装
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  📦 安装 SAGE ($install_mode 模式)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # 准备pip安装参数
    local pip_args="--disable-pip-version-check --no-input"

    # 添加缓存支持（非CI环境）
    if [ "${CI:-}" != "true" ] && [ -z "${GITHUB_ACTIONS:-}" ] && [ -z "$GITLAB_CI" ] && [ -z "$JENKINS_URL" ]; then
        # 非CI环境启用缓存以加速重复安装
        pip_args="$pip_args --cache-dir ~/.cache/pip"
        echo -e "${DIM}启用 pip 缓存: ~/.cache/pip${NC}"
    else
        # CI环境禁用缓存以确保新鲜安装
        pip_args="$pip_args --no-cache-dir"
        echo -e "${DIM}CI环境: 禁用 pip 缓存${NC}"
    fi

    # CI环境额外处理
    if [ "${CI:-}" = "true" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${GITLAB_CI:-}" ] || [ -n "${JENKINS_URL:-}" ]; then
        # 在CI中将包安装到用户site（~/.local），便于跨job缓存与导入
        pip_args="$pip_args --user"
        # 某些系统前缀可能仍需此选项
        if python3 -c "import sys; print(1 if '/usr' in sys.prefix else 0)" 2>/dev/null; then
            pip_args="$pip_args --break-system-packages"
            echo -e "${DIM}CI环境: 添加 --break-system-packages${NC}"
        fi
        # 确保用户脚本目录在PATH中（供 'sage' 可执行脚本使用）
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "${DIM}CI环境: 使用 --user 安装，PATH+=~/.local/bin${NC}"
        # CI环境也使用 off，避免版本兼容性问题
        pip_args="$pip_args --progress-bar=off"
    else
        # 非CI环境，使用简洁进度条（off 在所有 pip 版本中都支持）
        pip_args="$pip_args --progress-bar=off"
    fi

    log_phase_start_enhanced "本地依赖包安装" "INSTALL" 180

    # 本地开发安装策略：
    # 1. 使用 -e (editable) 模式安装
    # 2. 使用 --no-deps 完全禁用依赖解析，避免从 PyPI 安装 isage-* 包
    # 3. 按正确的依赖顺序手动安装所有包
    # 4. 最后单独安装外部依赖
    local install_flags="-e"

    log_info "安装策略: editable + --no-deps (禁用 PyPI 依赖解析)" "INSTALL"
    log_info "手动控制安装顺序，确保使用本地源码" "INSTALL"
    echo -e "${DIM}安装策略: 先安装外部依赖，再 editable install 本地包${NC}"
    echo -e "${DIM}           确保所有传递依赖可用后再安装本地源码${NC}"
    echo ""

    # 配置 pip 镜像源（自动检测网络）
    echo -e "${BLUE}🌐 配置 pip 镜像源...${NC}"
    configure_pip_mirror "auto"
    echo ""

    # 步骤 0: 检测 GPU 并预安装 CUDA 版本的 PyTorch（如果有 GPU）
    echo -e "${DIM}步骤 0/5: 检测 GPU 环境...${NC}"
    log_info "步骤 0/5: 检测 GPU 并安装 CUDA 版本 PyTorch" "INSTALL"

    local pytorch_installer="$(dirname "${BASH_SOURCE[0]}")/../fixes/pytorch_cuda_installer.sh"
    if [ -f "$pytorch_installer" ]; then
        source "$pytorch_installer"
        if preinstall_pytorch_cuda; then
            log_info "PyTorch 环境设置完成" "INSTALL"
        else
            log_warn "PyTorch CUDA 安装失败，将使用 CPU 版本" "INSTALL"
        fi
    else
        log_warn "pytorch_cuda_installer.sh 不存在，跳过 GPU 检测" "INSTALL"
        echo -e "${DIM}跳过 GPU 检测（安装脚本不存在）${NC}"
    fi
    echo ""

    # 第一步：安装外部依赖（必须在本地包之前）
    echo -e "${DIM}步骤 1/5: 安装外部依赖...${NC}"
    log_info "步骤 1/5: 提取并安装外部依赖" "INSTALL"

    # 使用 Python 脚本提取已声明的外部依赖
    local external_deps_file=".sage/external-deps-${install_mode}.txt"
    local external_deps_marker=".sage/external-deps-${install_mode}.installed"
    mkdir -p .sage

    # 检查是否已经安装过外部依赖（基于 pyproject.toml 的 hash）
    local current_hash=""
    local cached_hash=""

    # 计算当前所有 pyproject.toml 的 hash
    if command -v sha256sum &> /dev/null; then
        current_hash=$(find packages/sage-*/pyproject.toml -type f 2>/dev/null | sort | xargs cat | sha256sum | cut -d' ' -f1)
    elif command -v shasum &> /dev/null; then
        current_hash=$(find packages/sage-*/pyproject.toml -type f 2>/dev/null | sort | xargs cat | shasum -a 256 | cut -d' ' -f1)
    fi

    # 读取缓存的 hash
    if [ -f "$external_deps_marker" ]; then
        cached_hash=$(cat "$external_deps_marker" 2>/dev/null || echo "")
    fi

    # 如果 hash 相同且依赖文件存在，跳过安装
    if [ -n "$current_hash" ] && [ "$current_hash" = "$cached_hash" ] && [ -f "$external_deps_file" ]; then
        log_info "检测到外部依赖已安装（pyproject.toml 未变化），跳过" "INSTALL"
        echo -e "${CHECK} 外部依赖已是最新（跳过安装）"
        echo ""
    else
        if [ -n "$cached_hash" ] && [ "$current_hash" != "$cached_hash" ]; then
            log_info "检测到 pyproject.toml 变化，重新安装外部依赖" "INSTALL"
            echo -e "${DIM}     检测到依赖变化，重新安装...${NC}"
        fi

    log_debug "外部依赖将保存到: $external_deps_file" "INSTALL"
    echo -e "${DIM}     从 pyproject.toml 中提取外部依赖...${NC}"

    # 执行 Python 脚本提取依赖（优化版：去重+合并版本）
    log_debug "执行 Python 依赖提取脚本（去重优化）..." "INSTALL"
    if $PYTHON_CMD -c "
import sys, re
from pathlib import Path
from collections import defaultdict

# 存储包名到版本约束的映射
dep_versions = defaultdict(list)

package_dirs = ['packages/sage-common', 'packages/sage-platform', 'packages/sage-kernel', 'packages/sage-libs', 'packages/sage-middleware']
install_mode = '$install_mode'
if install_mode != 'core':
    package_dirs.extend(['packages/sage-cli'])
if install_mode in ['full', 'dev']:
    package_dirs.extend(['packages/sage-tools'])

for pkg_dir in package_dirs:
    pyproject = Path(pkg_dir) / 'pyproject.toml'
    if not pyproject.exists(): continue
    content = pyproject.read_text()
    in_deps = False
    for line in content.splitlines():
        line = line.strip()
        if 'dependencies' in line and '=' in line: in_deps = True; continue
        if in_deps:
            if line == ']': in_deps = False; continue
            match = re.search(r'\"([^\"]+)\"', line)
            if match:
                dep = match.group(1)
                if not dep.startswith('isage-'):
                    # 提取包名和版本约束
                    pkg_match = re.match(r'^([a-zA-Z0-9_-]+[a-zA-Z0-9_\[\]-]*)', dep)
                    if pkg_match:
                        pkg_name = pkg_match.group(1)
                        dep_versions[pkg_name].append(dep)

# 合并多个包的相同依赖声明（版本已统一，无需去重）
external_deps = []
conflict_count = 0
for pkg_name, versions in sorted(dep_versions.items()):
    unique_versions = list(set(versions))
    if len(unique_versions) == 1:
        external_deps.append(unique_versions[0])
    else:
        # 理论上不应该有冲突（版本已通过 unify_dependencies.py 统一）
        # 如果仍有冲突，选择最严格的版本
        best_dep = max(unique_versions, key=lambda v: ('>=' in v, '<' in v, v))
        external_deps.append(best_dep)
        conflict_count += 1

with open('$external_deps_file', 'w') as f:
    for dep in external_deps:
        f.write(f'{dep}\n')

# 根据情况显示不同的消息
if conflict_count > 0:
    print(f'⚠️  提取了 {len(external_deps)} 个外部依赖（发现 {conflict_count} 个版本冲突）', file=sys.stderr)
    print(f'   建议运行: python3 tools/install/helpers/unify_dependencies.py --apply', file=sys.stderr)
else:
    # 不显示 duplicate_count，因为多包共享依赖是正常的
    print(f'✓ 提取了 {len(external_deps)} 个外部依赖', file=sys.stderr)
" 2>&1; then
        log_info "依赖提取脚本执行成功" "INSTALL"

        if [ -f "$external_deps_file" ] && [ -s "$external_deps_file" ]; then
            local dep_count=$(wc -l < "$external_deps_file")
            log_info "共提取 $dep_count 个外部依赖" "INSTALL"

            echo -e "${DIM}     安装 $dep_count 个外部依赖包...${NC}"
            log_info "开始安装外部依赖包..." "INSTALL"

            # 智能代理检测和自动规避
            local pip_utils="${SAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}/tools/lib/pip_install_utils.sh"
            if [ -f "$pip_utils" ]; then
                source "$pip_utils"
                check_and_fix_pip_proxy || true
            fi

            # 移除 --no-deps，让 pip 正常解析传递依赖
            local deps_pip_args=$(echo "$pip_args" | sed 's/--no-deps//g')
            log_debug "PIP命令: $PIP_CMD install -r $external_deps_file $deps_pip_args" "INSTALL"

            # 使用详细输出模式，让用户看到编译进度（避免看起来卡住）
            if log_pip_install_with_verbose_progress "INSTALL" "Deps" "$PIP_CMD install -r \"$external_deps_file\" $deps_pip_args"; then
                log_info "外部依赖安装成功" "INSTALL"
                echo -e "${CHECK} 外部依赖安装完成"

                # 保存 hash 标记，避免下次重复安装（提前保存，即使后续步骤失败也能复用缓存）
                if [ -n "$current_hash" ]; then
                    echo "$current_hash" > "$external_deps_marker"
                    log_info "已保存外部依赖安装标记" "INSTALL"
                fi

                # 强制升级关键包到正确版本（解决依赖解析问题）
                echo -e "${DIM}     验证并升级关键包版本...${NC}"
                log_info "强制安装 transformers 和 peft 到兼容版本" "INSTALL"

                # transformers 4.52.0 与 peft 0.18.0 兼容
                # 同时需要 tokenizers<0.22 来匹配 transformers 4.52.0
                if log_command "INSTALL" "Deps" "$PIP_CMD install 'transformers==4.52.0' 'tokenizers>=0.21,<0.22' 'peft>=0.18.0,<1.0.0' $deps_pip_args"; then
                    log_info "关键包版本升级成功" "INSTALL"
                    echo -e "${CHECK} 关键包版本验证完成"
                else
                    log_warn "关键包升级失败，继续安装..." "INSTALL"
                    echo -e "${YELLOW}⚠️  关键包升级失败，可能导致运行时错误${NC}"
                fi
            else
                log_error "外部依赖安装失败" "INSTALL"
                echo -e "${RED}❌ 外部依赖安装失败${NC}"
                return 1
            fi
        else
            log_warn "未能提取外部依赖或依赖文件为空" "INSTALL"
            echo -e "${YELLOW}⚠️  未能提取外部依赖，跳过...${NC}"
        fi
    else
        log_error "依赖提取脚本失败" "INSTALL"
        echo -e "${YELLOW}⚠️  依赖提取脚本失败，跳过...${NC}"
    fi
    fi  # 闭合 hash 检查的 if

    echo ""

    # 第二步：安装基础包（L1-L2）
    echo -e "${DIM}步骤 2/5: 安装基础包 (L1-L2)...${NC}"
    log_info "步骤 2/5: 安装基础包 (L1-L2)" "INSTALL"

    # L1: Foundation, L2: Platform
    # Note: sage-llm-core moved to independent repo (pip install isagellm)
    local base_packages=("packages/sage-common" "packages/sage-platform")

    for package_dir in "${base_packages[@]}"; do
        echo -e "${DIM}  正在安装: $package_dir${NC}"
        log_info "开始安装: $package_dir" "INSTALL"
        log_debug "PIP命令: $PIP_CMD install $install_flags $package_dir $pip_args --no-deps" "INSTALL"

        if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"$package_dir\" $pip_args --no-deps"; then
            log_error "安装失败: $package_dir" "INSTALL"
            log_error "请检查日志文件: ${SAGE_INSTALL_LOG:-}" "INSTALL"
            echo -e "${CROSS} 安装 $package_dir 失败！"
            return 1
        fi

        log_info "安装成功: $package_dir" "INSTALL"
        # 验证安装
        local pkg_name=$(basename "$package_dir" | sed 's/sage-/isage-/')
        log_pip_package_info "$pkg_name" "INSTALL"
    done

    # 第三步：安装核心引擎 (L3)
    echo -e "${DIM}步骤 3/5: 安装核心引擎 (L3)...${NC}"
    log_info "步骤 3/5: 安装核心引擎 (L3)" "INSTALL"
    local core_packages=("packages/sage-kernel")

    if [ "$install_mode" != "core" ]; then
        core_packages+=("packages/sage-libs")
    fi

    for package_dir in "${core_packages[@]}"; do
        echo -e "${DIM}  正在安装: $package_dir${NC}"
        log_info "开始安装: $package_dir" "INSTALL"

        log_debug "PIP命令: $PIP_CMD install $install_flags $package_dir $pip_args --no-deps" "INSTALL"

        if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"$package_dir\" $pip_args --no-deps"; then
            log_error "安装失败: $package_dir" "INSTALL"
            log_error "请检查日志文件: ${SAGE_INSTALL_LOG:-}" "INSTALL"
            echo -e "${CROSS} 安装 $package_dir 失败！"
            return 1
        fi

        log_info "安装成功: $package_dir" "INSTALL"
        local pkg_name=$(basename "$package_dir" | sed 's/sage-/isage-/')
        log_pip_package_info "$pkg_name" "INSTALL"
    done

    # 第四步：安装上层包（L4-L6，根据模式）
    if [ "$install_mode" != "core" ]; then
        echo -e "${DIM}步骤 4/5: 安装上层包 (L4-L6)...${NC}"

        # 显式安装独立 PyPI 包依赖 (因为下面使用了 --no-deps)
        # 这些包是 sage-middleware 的依赖，但因为 --no-deps 选项会被跳过
        echo -e "${DIM}  正在安装独立 PyPI 包依赖 (isage-vdb, isage-flow, etc.)...${NC}"
        log_info "开始安装独立 PyPI 包依赖" "INSTALL"

        # 使用与 pyproject.toml 一致的版本约束
        # 使用单引号包裹每个包名，防止 shell 将 > 解析为重定向
        local independent_packages="'isage-vdb>=0.1.5' 'isage-tsdb>=0.1.5' 'isage-flow>=0.1.1' 'isage-refiner>=0.1.0' 'isage-neuromem>=0.2.1.1'"

        # 注意：独立包是 PyPI 包，不能使用 -e (install_flags)
        log_debug "PIP命令: $PIP_CMD install $independent_packages $pip_args" "INSTALL"

        if ! log_command "INSTALL" "Deps" "$PIP_CMD install $independent_packages $pip_args"; then
            log_warn "独立 PyPI 包安装失败，可能导致部分功能不可用" "INSTALL"
            echo -e "${WARNING} 独立 PyPI 包安装失败，可能导致部分功能不可用"
            # 不中断安装，因为这些可能是可选的或者网络问题
        else
            log_info "独立 PyPI 包安装成功" "INSTALL"
            echo -e "${CHECK} 独立 PyPI 包安装成功"
        fi

        # L4: middleware (Python 兼容层)
        # 注意：必须使用 --no-deps 防止 pip 重新安装已有的 sage 子包依赖
        # 运行时依赖（isage-common/platform/kernel/libs）在 step 1-2 已安装
        # C++ 扩展（isage-vdb/isage-flow/isage-tsdb/isage-neuromem/isage-refiner）通过外部依赖安装
        echo -e "${DIM}  正在安装: packages/sage-middleware${NC}"
        log_info "开始安装: packages/sage-middleware" "INSTALL"
        log_debug "PIP命令: $PIP_CMD install $install_flags packages/sage-middleware $pip_args --no-deps" "INSTALL"

        if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"packages/sage-middleware\" $pip_args --no-deps"; then
            log_error "安装 sage-middleware 失败" "INSTALL"
            echo -e "${CROSS} 安装 sage-middleware 失败！"
            return 1
        fi

        log_info "安装成功: packages/sage-middleware" "INSTALL"
        log_pip_package_info "isage-middleware" "INSTALL"
        echo -e "${CHECK} sage-middleware 安装完成"

        # L5: apps & benchmark (standard/full/dev 模式)
        if [ "$install_mode" != "core" ]; then
            # 清理已独立为 PyPI 包的组件残留目录
            local residual_paths=(
                "packages/sage-benchmark"
                "packages/sage-gateway"
                "packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB"
                "packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow"
                "packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB"
                "packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem"
                "packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner"
                "packages/sage-common/src/sage/common/components/sage_llm"
            )

            for path in "${residual_paths[@]}"; do
                if [ -d "$path" ]; then
                    echo -e "${DIM}  清理本地残留目录: $path...${NC}"
                    rm -rf "$path"
                fi
            done

            # Note: sage-benchmark 已独立为 PyPI 包 (pip install isage-benchmark)
            # 如需使用 benchmark，请单独安装: pip install isage-benchmark
        fi

        # L6: CLI (standard/full/dev 模式)
        if [ -d "packages/sage-cli" ]; then
            echo -e "${DIM}  正在安装: packages/sage-cli${NC}"
            log_info "开始安装: packages/sage-cli" "INSTALL"
            log_debug "PIP命令: $PIP_CMD install $install_flags packages/sage-cli $pip_args --no-deps" "INSTALL"

            if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"packages/sage-cli\" $pip_args --no-deps"; then
                log_error "安装 sage-cli 失败" "INSTALL"
                echo -e "${CROSS} 安装 sage-cli 失败！"
                return 1
            fi

            log_info "安装成功: packages/sage-cli" "INSTALL"
            log_pip_package_info "isage-cli" "INSTALL"
            echo -e "${CHECK} sage-cli 安装完成"
        fi
    fi

    # L6: tools (full/dev 模式)
    # Note: sage-studio 已独立为独立仓库: https://github.com/intellistream/sage-studio
    if [ "$install_mode" = "full" ] || [ "$install_mode" = "dev" ]; then
        if [ -d "packages/sage-tools" ]; then
            echo -e "${DIM}  正在安装: packages/sage-tools${NC}"
            log_info "开始安装: packages/sage-tools" "INSTALL"
            log_debug "PIP命令: $PIP_CMD install $install_flags packages/sage-tools $pip_args --no-deps" "INSTALL"

            if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"packages/sage-tools\" $pip_args --no-deps"; then
                log_error "安装 sage-tools 失败" "INSTALL"
                echo -e "${CROSS} 安装 sage-tools 失败！"
                return 1
            fi

            log_info "安装成功: packages/sage-tools" "INSTALL"
            log_pip_package_info "isage-tools" "INSTALL"
            echo -e "${CHECK} sage-tools 安装完成"
        fi
    fi

    # Note: L6 tools (sage-tools) 已在上面的代码块中安装

    if [ "$install_mode" = "core" ]; then
        echo -e "${DIM}步骤 4/5: 跳过上层包（core 模式）${NC}"
    fi

    echo -e "${CHECK} 本地依赖包安装完成"
    echo ""

    # 预安装构建依赖（防止 pip build isolation 从镜像下载失败）
    echo -e "${DIM}预安装构建依赖（setuptools, wheel, packaging）...${NC}"
    log_info "开始预安装构建依赖" "INSTALL"
    log_debug "PIP命令: $PIP_CMD install 'setuptools>=64' 'wheel' 'packaging>=24.2' $pip_args" "INSTALL"

    if ! log_command "INSTALL" "BuildDeps" "$PIP_CMD install 'setuptools>=64' 'wheel' 'packaging>=24.2' $pip_args"; then
        log_warn "构建依赖预安装失败，但继续尝试安装（可能已有足够版本）" "INSTALL"
        echo -e "${WARNING} 构建依赖预安装失败（可能已有足够版本，继续...）"
    else
        log_info "构建依赖预安装成功" "INSTALL"
        echo -e "${CHECK} 构建依赖预安装完成"
    fi
    echo ""

    # 第五步：安装主 SAGE meta-package
    echo -e "${DIM}步骤 5/5: 安装 SAGE meta-package...${NC}"
    log_phase_start_enhanced "SAGE meta-package 安装" "INSTALL" 60

    # 安装 sage meta-package (--no-deps)
    local install_target="packages/sage"
    echo -e "${DIM}  安装 sage meta-package (--no-deps)...${NC}"
    log_info "开始安装: sage meta-package" "INSTALL"
    log_debug "PIP命令: $PIP_CMD install $install_flags $install_target $pip_args --no-deps" "INSTALL"

    if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"$install_target\" $pip_args --no-deps"; then
        log_error "安装 sage meta-package 失败" "INSTALL"
        echo -e "${CROSS} 安装 sage meta-package 失败！"
        log_phase_end "SAGE meta-package 安装" "failure" "INSTALL"
        return 1
    fi

    log_info "安装成功: sage meta-package" "INSTALL"
    log_pip_package_info "isage" "INSTALL"

    # 4b. 手动安装外部依赖（不经过 sage[mode] 依赖解析）
    echo -e "${DIM}  4b. 安装外部依赖（提取自各子包声明）...${NC}"

    # 开始外部依赖安装阶段（记录开始时间）
    log_phase_start_enhanced "外部依赖安装" "INSTALL" 300

    log_info "开始提取外部依赖（从 pyproject.toml 文件）" "INSTALL"

    # 使用 Python 脚本提取已安装 editable 包的外部依赖
    local external_deps_file=".sage/external-deps-${install_mode}.txt"
    mkdir -p .sage

    log_debug "外部依赖将保存到: $external_deps_file" "INSTALL"
    echo -e "${DIM}     从已安装包中提取外部依赖...${NC}"

    # 执行 Python 脚本提取依赖（优化版：去重+合并版本）
    log_debug "执行 Python 依赖提取脚本（去重优化）..." "INSTALL"
    if $PYTHON_CMD -c "
import sys, re
from pathlib import Path
from collections import defaultdict

# 存储包名到版本约束的映射
dep_versions = defaultdict(list)

# 独立发布但仍需安装的 isage-* 扩展包（已从源码仓库移除）
allowed_isage_packages = {
    'isage-tsdb',      # 时间序列数据库
    'isage-flow',      # 流式语义状态引擎
    'isage-refiner',   # 长上下文压缩
    'isage-neuromem',  # 记忆系统
}

package_dirs = ['packages/sage-common', 'packages/sage-platform', 'packages/sage-kernel', 'packages/sage-libs', 'packages/sage-middleware']
install_mode = '$install_mode'
if install_mode != 'core':
    # Note: sage-benchmark, sage-llm-gateway, sage-llm-core moved to independent repos
    package_dirs.extend(['packages/sage-cli'])
if install_mode == 'dev':
    package_dirs.extend(['packages/sage-tools'])

# 提取常规依赖
for pkg_dir in package_dirs:
    pyproject = Path(pkg_dir) / 'pyproject.toml'
    if not pyproject.exists(): continue
    content = pyproject.read_text()
    in_deps = False
    for line in content.splitlines():
        line = line.strip()
        if 'dependencies' in line and '=' in line: in_deps = True; continue
        if in_deps:
            if line == ']': in_deps = False; continue
            match = re.search(r'\"([^\"]+)\"', line)
            if match:
                dep = match.group(1)
                # 提取包名（移除版本约束和extras）
                pkg_match = re.match(r'^([a-zA-Z0-9_-]+)', dep)
                if not pkg_match:
                    continue
                pkg_base = pkg_match.group(1)

                # 允许外部 isage-* 独立包，否则跳过内部 isage- 依赖
                if pkg_base.startswith('isage-') and pkg_base not in allowed_isage_packages:
                    continue

                # 提取包名和版本约束（包含 extras）
                full_pkg_match = re.match(r'^([a-zA-Z0-9_-]+[a-zA-Z0-9_\[\]-]*)', dep)
                if full_pkg_match:
                    pkg_name = full_pkg_match.group(1)
                    dep_versions[pkg_name].append(dep)

# 去重并选择最严格的版本约束
external_deps = []
for pkg_name, versions in sorted(dep_versions.items()):
    if len(versions) == 1:
        external_deps.append(versions[0])
    else:
        # 多个版本约束时，选择最新的（通常是最严格的）
        best_dep = max(versions, key=lambda v: ('>=' in v, v))
        external_deps.append(best_dep)
        if len(versions) > 1:
            print(f'[DEDUP] {pkg_name}: {len(versions)} 个版本 -> {best_dep}', file=sys.stderr)

with open('$external_deps_file', 'w') as f:
    for dep in external_deps:
        f.write(f'{dep}\n')

print(f'✓ 提取了 {len(external_deps)} 个外部依赖（已去重）', file=sys.stderr)
" 2>&1; then
        log_info "依赖提取脚本执行成功" "INSTALL"

        if [ -f "$external_deps_file" ] && [ -s "$external_deps_file" ]; then
            local dep_count=$(wc -l < "$external_deps_file")
            log_info "共提取 $dep_count 个外部依赖" "INSTALL"
            log_debug "依赖列表文件: $external_deps_file" "INSTALL"

            # 记录依赖列表（前10个）
            if [ "$dep_count" -le 10 ]; then
                log_debug "依赖列表:\n$(cat "$external_deps_file")" "INSTALL"
            else
                log_debug "依赖列表（前10个）:\n$(head -10 "$external_deps_file")" "INSTALL"
                log_debug "...还有 $((dep_count - 10)) 个依赖（查看完整列表: $external_deps_file）" "INSTALL"
            fi

            echo -e "${DIM}     安装 $dep_count 个外部依赖包...${NC}"
            log_info "开始安装外部依赖包..." "INSTALL"

            # 智能代理检测和自动规避
            local pip_utils="${SAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}/tools/lib/pip_install_utils.sh"
            if [ -f "$pip_utils" ]; then
                source "$pip_utils"
                check_and_fix_pip_proxy || true
            fi
            log_debug "PIP命令: $PIP_CMD install -r $external_deps_file $pip_args" "INSTALL"

            # 从文件读取并安装
            if log_command "INSTALL" "Deps" "$PIP_CMD install -r \"$external_deps_file\" $pip_args"; then
                log_info "外部依赖安装成功" "INSTALL"
                echo -e "${CHECK} 外部依赖安装完成"

                # 验证关键依赖是否安装成功（采样几个）
                local sample_deps=$(head -3 "$external_deps_file" | tr '\n' ' ')
                log_debug "验证采样依赖是否安装: $sample_deps" "INSTALL"
                for dep in $sample_deps; do
                    local pkg_name=$(echo "$dep" | sed 's/[<>=].*//' | tr '-' '_')
                    log_pip_package_info "$pkg_name" "INSTALL" || true
                done
            else
                log_warn "部分外部依赖安装失败，但继续..." "INSTALL"
                echo -e "${YELLOW}⚠️  部分外部依赖安装失败，但继续...${NC}"

                # 尝试提取安装失败的包
                local failed_packages=$(grep -i "error\|failed" "${SAGE_INSTALL_LOG:-}" | tail -5 || echo "无法确定失败包")
                log_warn "失败详情:\n$failed_packages" "INSTALL"
            fi
        else
            log_warn "未能提取外部依赖或依赖文件为空" "INSTALL"
            log_debug "文件状态: $(ls -lh "$external_deps_file" 2>&1 || echo '文件不存在')" "INSTALL"
            echo -e "${YELLOW}⚠️  未能提取外部依赖，跳过...${NC}"
        fi
    else
        log_error "依赖提取脚本执行失败" "INSTALL"
        log_error "Python脚本返回非零退出码" "INSTALL"
        echo -e "${YELLOW}⚠️  依赖提取脚本失败，跳过外部依赖安装${NC}"
    fi

    log_phase_end_enhanced "外部依赖安装" "success" "INSTALL"

    echo ""
    echo -e "${CHECK} SAGE ($install_mode 模式) 和外部依赖安装成功."
    echo ""

    # 验证sage命令
    echo -e "${DIM}验证 sage 命令...${NC}"
    log_info "验证 sage 命令可用性" "INSTALL"

    # 在 conda 环境中验证命令（因为安装在 conda 环境中）
    if $PIP_CMD --version >/dev/null 2>&1 && conda run -n "$CONDA_ENV_NAME" sage --version >/dev/null 2>&1; then
        log_info "sage 命令验证成功（在 conda 环境中）" "INSTALL"

        # 尝试获取版本信息
        local sage_version=$(conda run -n "$CONDA_ENV_NAME" sage --version 2>&1 || echo "无法获取版本")
        log_debug "sage 版本: $sage_version" "INSTALL"

        echo -e "${CHECK} sage 命令已安装到 conda 环境"
        echo -e "${DIM}      运行 ${BOLD}conda activate $CONDA_ENV_NAME${NC}${DIM} 或重启终端后可直接使用 sage 命令${NC}"
    elif command -v sage >/dev/null 2>&1; then
        # 如果在当前 PATH 中可用（比如用户已经激活了环境）
        log_info "sage 命令验证成功（当前 shell）" "INSTALL"
        local sage_version=$(sage --version 2>&1 || echo "无法获取版本")
        log_debug "sage 版本: $sage_version" "INSTALL"
        echo -e "${CHECK} sage 命令已可用"
    else
        log_warn "sage 命令需要激活 conda 环境后使用" "INSTALL"
        log_debug "PATH: $PATH" "INSTALL"
        log_debug "CONDA_ENV: $CONDA_ENV_NAME" "INSTALL"
        echo -e "${INFO} sage 命令已安装，激活环境后可用: ${BOLD}conda activate $CONDA_ENV_NAME${NC}"
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
