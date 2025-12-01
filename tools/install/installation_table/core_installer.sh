#!/bin/bash
# SAGE 安装脚本 - 核心包安装器 (重构版本)
# 负责通过主sage包统一安装所有依赖

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/logging.sh"

# 导入友好错误处理
if [ -f "$(dirname "${BASH_SOURCE[0]}")/../fixes/friendly_error_handler.sh" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/../fixes/friendly_error_handler.sh"
fi

# CI环境检测
if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    # 确保在CI环境中禁用可能导致问题的进度条设置
    unset PIP_PROGRESS_BAR
elif [ "$SAGE_REMOTE_DEPLOY" = "true" ]; then
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

# 从本地源码安装 vLLM
# vLLM 源码位于 packages/sage-common/src/sage/common/components/sage_llm/sageLLM/engines/vllm
install_vllm_from_source() {
    local pip_args="$1"
    local project_root="${2:-$(pwd)}"
    local vllm_source_dir="$project_root/packages/sage-common/src/sage/common/components/sage_llm/sageLLM/engines/vllm"

    if [ ! -d "$vllm_source_dir" ]; then
        log_error "vLLM 源码目录不存在: $vllm_source_dir" "INSTALL"
        echo -e "${CROSS} vLLM 源码目录不存在，请先同步 submodules: ./manage.sh"
        return 1
    fi

    if [ ! -f "$vllm_source_dir/pyproject.toml" ]; then
        log_error "vLLM pyproject.toml 不存在: $vllm_source_dir/pyproject.toml" "INSTALL"
        echo -e "${CROSS} vLLM 源码不完整，缺少 pyproject.toml"
        return 1
    fi

    echo -e "${BLUE}🔧 从本地源码编译安装 vLLM...${NC}"
    echo -e "${DIM}   源码目录: $vllm_source_dir${NC}"
    echo -e "${DIM}   注意：编译可能需要 10-30 分钟，取决于硬件配置${NC}"
    log_info "开始从源码编译安装 vLLM: $vllm_source_dir" "INSTALL"

    # 首先安装编译依赖（torch 等）
    echo -e "${DIM}   安装编译依赖 (torch>=2.4.0)...${NC}"
    local torch_install_cmd="$PIP_CMD install 'torch>=2.4.0' 'torchaudio>=2.4.0' 'torchvision>=0.17.0'"
    for arg in $pip_args; do
        torch_install_cmd+=" $arg"
    done

    if ! eval "$torch_install_cmd" >> "$project_root/.sage/logs/install.log" 2>&1; then
        log_warn "torch 安装失败，但继续尝试编译 vLLM" "INSTALL"
    fi

    # 编译并安装 vLLM（使用 editable 模式便于开发调试）
    echo -e "${DIM}   编译 vLLM（这可能需要较长时间）...${NC}"
    local pip_install_cmd="$PIP_CMD install -e '$vllm_source_dir'"
    for arg in $pip_args; do
        pip_install_cmd+=" $arg"
    done

    # 记录开始时间
    local start_time=$(date +%s)

    if log_pip_install_with_progress "INSTALL" "vLLM (源码编译)" "$pip_install_cmd"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "vLLM 源码编译安装完成，耗时 ${duration} 秒" "INSTALL"
        echo -e "${CHECK} vLLM 源码编译安装完成（耗时 ${duration} 秒）"
        return 0
    else
        log_error "vLLM 源码编译安装失败" "INSTALL"
        echo -e "${CROSS} vLLM 源码编译安装失败${NC}"
        echo -e "${DIM}   可能原因:${NC}"
        echo -e "${DIM}   - CUDA toolkit 未安装或版本不兼容${NC}"
        echo -e "${DIM}   - cmake 或 ninja 未安装${NC}"
        echo -e "${DIM}   - 内存不足（建议 16GB+）${NC}"
        echo -e "${DIM}   查看日志: $project_root/.sage/logs/install.log${NC}"
        echo -e "${DIM}   或尝试 pip 安装: ./quickstart.sh --vllm-pip${NC}"
        return 1
    fi
}

# 安装 vLLM 运行时依赖（基于 optional-dependencies[vllm]）
install_vllm_optional_dependencies() {
    local pip_args="$1"
    local pyproject="packages/sage-common/pyproject.toml"
    local extra_name="vllm"
    local python_cmd="${PYTHON_CMD:-python3}"

    if [ ! -f "$pyproject" ]; then
        log_warn "跳过 vLLM 依赖安装：找不到 $pyproject" "INSTALL"
        return 0
    fi

    local deps_output
    if ! deps_output=$(
        PYPROJECT_PATH="$pyproject" \
        EXTRA_NAME="$extra_name" \
        "$python_cmd" - <<'PY' 2>/dev/null
import os
import re
from pathlib import Path

pyproject = Path(os.environ['PYPROJECT_PATH'])
extra_name = os.environ['EXTRA_NAME']
if not pyproject.exists():
    raise SystemExit(0)

text = pyproject.read_text(encoding='utf-8')
pattern = re.compile(rf"\b{re.escape(extra_name)}\s*=\s*\[(.*?)\]", re.S)
match = pattern.search(text)
if not match:
    raise SystemExit(0)

deps_block = match.group(1)
deps = []
for raw_line in deps_block.splitlines():
    line = raw_line.strip()
    if not line or line.startswith('#'):
        continue
    if line.endswith(','):
        line = line[:-1].strip()
    if line.startswith(('"', "'")) and line.endswith(('"', "'")) and len(line) >= 2:
        line = line[1:-1]
    if line:
        deps.append(line)

print("\n".join(deps))
PY
    ); then
        log_warn "解析 vLLM 可选依赖失败" "INSTALL"
        return 1
    fi

    if [ -z "$deps_output" ]; then
        log_warn "未在 pyproject.toml 中找到 vLLM 可选依赖" "INSTALL"
        return 0
    fi

    # 转为数组（逐行）
    local IFS=$'\n'
    local vllm_deps=($deps_output)
    IFS=' '

    if [ ${#vllm_deps[@]} -eq 0 ]; then
        log_warn "vLLM 依赖列表为空" "INSTALL"
        return 0
    fi

    echo -e "${DIM}  安装 vLLM 运行时依赖 (${#vllm_deps[@]} 个)...${NC}"
    log_info "开始安装 vLLM 运行时依赖: ${vllm_deps[*]}" "INSTALL"

    # 构建 pip 安装命令（依赖包名需要用引号包裹，避免 >= 被解释为重定向）
    local pip_cmd="$PIP_CMD install"
    for dep in "${vllm_deps[@]}"; do
        pip_cmd+=" '${dep}'"
    done
    pip_cmd+=" $pip_args"

    if log_pip_install_with_progress "INSTALL" "vLLM" "$pip_cmd"; then
        log_success "vLLM 运行时依赖安装完成" "INSTALL"
        echo -e "${CHECK} vLLM 运行时依赖安装完成"
        return 0
    else
        log_warn "vLLM 运行时依赖安装失败，可稍后运行 pip install 'isage-common[vllm]'" "INSTALL"
        echo -e "${WARNING} vLLM 依赖安装失败，可稍后运行: pip install 'isage-common[vllm]'${NC}"
        return 1
    fi
}

# 安装核心包 - 新的简化版本
install_core_packages() {
    local install_mode="${1:-dev}"  # 默认为开发模式
    local install_vllm="${SAGE_INSTALL_VLLM:-true}"

    # 准备pip安装参数
    local pip_args="--disable-pip-version-check --no-input"

    # CI环境额外处理
    if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
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
            echo -e "${GREEN}标准模式：Core + CLI + Benchmark + 科学计算${NC}"
            echo -e "${DIM}包含: L1-L4 + sage-cli + sage-benchmark + numpy, pandas, matplotlib (~220MB)${NC}"
            ;;
        "full")
            echo -e "${PURPLE}完整功能：Standard + Apps + Studio${NC}"
            echo -e "${DIM}包含: 标准 + sage-apps, sage-studio (~300MB)${NC}"
            ;;
        "dev")
            echo -e "${YELLOW}开发模式：Full + 开发工具${NC}"
            echo -e "${DIM}包含: 完整 + sage-tools, pytest, black, mypy, pre-commit (~400MB)${NC}"
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
        # standard/full/dev 模式需要 benchmark
        [ -d "packages/sage-benchmark" ] && required_packages+=("packages/sage-benchmark")
    fi

    # full 和 dev 模式需要 studio
    if [ "$install_mode" = "full" ] || [ "$install_mode" = "dev" ]; then
        [ -d "packages/sage-studio" ] && required_packages+=("packages/sage-studio")
        # full/dev 模式添加 L5 apps（如果存在）
        [ -d "packages/sage-apps" ] && required_packages+=("packages/sage-apps")
        [ -d "packages/sage-gateway" ] && required_packages+=("packages/sage-gateway")
    fi

    # dev 模式需要 sage-tools 和 sage-gateway
    if [ "$install_mode" = "dev" ]; then
        [ -d "packages/sage-tools" ] && required_packages+=("packages/sage-tools")
        [ -d "packages/sage-gateway" ] && required_packages+=("packages/sage-gateway")
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
    if [ "$CI" != "true" ] && [ -z "$GITHUB_ACTIONS" ] && [ -z "$GITLAB_CI" ] && [ -z "$JENKINS_URL" ]; then
        # 非CI环境启用缓存以加速重复安装
        pip_args="$pip_args --cache-dir ~/.cache/pip"
        echo -e "${DIM}启用 pip 缓存: ~/.cache/pip${NC}"
    else
        # CI环境禁用缓存以确保新鲜安装
        pip_args="$pip_args --no-cache-dir"
        echo -e "${DIM}CI环境: 禁用 pip 缓存${NC}"
    fi

    # CI环境额外处理
    if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
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
    mkdir -p .sage

    log_debug "外部依赖将保存到: $external_deps_file" "INSTALL"
    echo -e "${DIM}     从 pyproject.toml 中提取外部依赖...${NC}"

    # 执行 Python 脚本提取依赖
    log_debug "执行 Python 依赖提取脚本..." "INSTALL"
    if $PYTHON_CMD -c "
import sys, re
from pathlib import Path
external_deps = set()
package_dirs = ['packages/sage-common', 'packages/sage-platform', 'packages/sage-kernel', 'packages/sage-libs', 'packages/sage-middleware']
install_mode = '$install_mode'
if install_mode != 'core':
    package_dirs.extend(['packages/sage-cli', 'packages/sage-benchmark'])
if install_mode in ['full', 'dev']:
    package_dirs.extend(['packages/sage-apps', 'packages/sage-studio'])
if install_mode == 'dev':
    package_dirs.extend(['packages/sage-tools', 'packages/sage-gateway'])
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
                if not dep.startswith('isage-'): external_deps.add(dep)
with open('$external_deps_file', 'w') as f:
    for dep in sorted(external_deps): f.write(f'{dep}\n')
print(f'✓ 提取了 {len(external_deps)} 个外部依赖', file=sys.stderr)
" 2>&1; then
        log_info "依赖提取脚本执行成功" "INSTALL"

        if [ -f "$external_deps_file" ] && [ -s "$external_deps_file" ]; then
            local dep_count=$(wc -l < "$external_deps_file")
            log_info "共提取 $dep_count 个外部依赖" "INSTALL"

            echo -e "${DIM}     安装 $dep_count 个外部依赖包...${NC}"
            log_info "开始安装外部依赖包..." "INSTALL"

            # 移除 --no-deps，让 pip 正常解析传递依赖
            local deps_pip_args=$(echo "$pip_args" | sed 's/--no-deps//g')
            log_debug "PIP命令: $PIP_CMD install -r $external_deps_file $deps_pip_args" "INSTALL"

            if log_pip_install_with_progress "INSTALL" "Deps" "$PIP_CMD install -r \"$external_deps_file\" $deps_pip_args"; then
                log_info "外部依赖安装成功" "INSTALL"
                echo -e "${CHECK} 外部依赖安装完成"

                # 强制升级关键包到正确版本（解决依赖解析问题）
                echo -e "${DIM}     验证并升级关键包版本...${NC}"
                log_info "强制安装 transformers 和 peft 到兼容版本" "INSTALL"

                # vllm 0.9.2 与 transformers 4.57+ 有兼容性问题 (aimv2 冲突)
                # 使用 transformers 4.52.0 可以同时兼容 vllm 0.9.2 和 peft 0.18.0
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

    echo ""

    # 第二步：安装基础包（L1-L2）
    echo -e "${DIM}步骤 2/5: 安装基础包 (L1-L2)...${NC}"
    log_info "步骤 2/5: 安装基础包 (L1-L2)" "INSTALL"
    local base_packages=("packages/sage-common" "packages/sage-platform")

    for package_dir in "${base_packages[@]}"; do
        echo -e "${DIM}  正在安装: $package_dir${NC}"
        log_info "开始安装: $package_dir" "INSTALL"
        log_debug "PIP命令: $PIP_CMD install $install_flags $package_dir $pip_args --no-deps" "INSTALL"

        if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"$package_dir\" $pip_args --no-deps"; then
            log_error "安装失败: $package_dir" "INSTALL"
            log_error "请检查日志文件: $SAGE_INSTALL_LOG" "INSTALL"
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

        # 特殊处理 sage-libs: LibAMM C++ 扩展默认跳过本地编译
        # LibAMM 编译需要大量内存（单文件 500MB+），不适合本地构建
        # 默认从 PyPI 获取预编译版本（由 CI/CD self-hosted server 构建）
        # 如需本地编译 LibAMM，设置环境变量: BUILD_LIBAMM=1
        if [[ "$package_dir" == *"sage-libs"* ]]; then
            if [ "${BUILD_LIBAMM:-0}" = "1" ]; then
                log_info "sage-libs: BUILD_LIBAMM=1，将编译 LibAMM C++ 扩展（需要大量内存）" "INSTALL"
                echo -e "${YELLOW}  ⚠️  sage-libs: 将本地编译 LibAMM（可能导致内存不足）${NC}"
            else
                log_info "sage-libs: LibAMM C++ 扩展已跳过（默认行为），将从 PyPI 安装预编译版本" "INSTALL"
                echo -e "${DIM}  sage-libs: 跳过 LibAMM 本地编译（从 PyPI 获取预编译版本）${NC}"
                # 确保 BUILD_LIBAMM 为 0（CMakeLists.txt 默认就是 OFF，这里显式设置）
                export BUILD_LIBAMM=0
            fi
        fi

        log_debug "PIP命令: $PIP_CMD install $install_flags $package_dir $pip_args --no-deps" "INSTALL"

        if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"$package_dir\" $pip_args --no-deps"; then
            log_error "安装失败: $package_dir" "INSTALL"
            log_error "请检查日志文件: $SAGE_INSTALL_LOG" "INSTALL"
            echo -e "${CROSS} 安装 $package_dir 失败！"

            # 清理环境变量
            if [[ "$package_dir" == *"sage-libs"* ]]; then
                unset BUILD_LIBAMM
            fi
            return 1
        fi

        # 清理环境变量
        if [[ "$package_dir" == *"sage-libs"* ]]; then
            unset BUILD_LIBAMM
        fi

        log_info "安装成功: $package_dir" "INSTALL"
        local pkg_name=$(basename "$package_dir" | sed 's/sage-/isage-/')
        log_pip_package_info "$pkg_name" "INSTALL"
    done

    # 第四步：安装上层包（L4-L6，根据模式）
    if [ "$install_mode" != "core" ]; then
        echo -e "${DIM}步骤 4/5: 安装上层包 (L4-L6)...${NC}"

        # L4: middleware (包含C++扩展构建)
        # 注意：必须使用 --no-deps 防止 pip 重新安装已有的 sage 子包依赖
        # C++ 构建依赖（pybind11等）在 build-system.requires 中声明，通过环境已安装
        # 运行时依赖（isage-common/platform/kernel/libs）在 step 1-2 已安装
        echo -e "${DIM}  正在安装: packages/sage-middleware${NC}"
        echo -e "${DIM}    (包含 C++ 扩展构建，可能需要几分钟...)${NC}"

        log_info "开始安装: packages/sage-middleware (包含 C++ 扩展)" "INSTALL"
        log_debug "这一步会编译 C++ 扩展，可能较慢" "INSTALL"
        log_debug "PIP命令: $PIP_CMD install $install_flags packages/sage-middleware $pip_args --no-deps" "INSTALL"

        if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"packages/sage-middleware\" $pip_args --no-deps"; then
            log_error "安装 sage-middleware 失败！" "INSTALL"
            log_error "这通常是由于 C++ 编译错误，请检查日志: $SAGE_INSTALL_LOG" "INSTALL"

            # 尝试提取编译错误的关键信息
            if [ -f "$SAGE_INSTALL_LOG" ]; then
                local error_context=$(grep -A 5 -i "error:" "$SAGE_INSTALL_LOG" | tail -20 || echo "未找到具体错误信息")
                log_error "编译错误摘要:\n$error_context" "INSTALL"
            fi

            echo -e "${CROSS} 安装 sage-middleware 失败！"
            echo -e "${DIM}提示: 检查日志文件获取详细错误信息: $SAGE_INSTALL_LOG${NC}"
            return 1
        fi

        log_info "安装成功: packages/sage-middleware" "INSTALL"
        log_pip_package_info "isage-middleware" "INSTALL"
        echo -e "${CHECK} sage-middleware 安装完成（包括 C++ 扩展）"

        # 调试：检查 .so 文件位置（仅在 CI 环境）
        if [[ -n "$CI" || -n "$GITHUB_ACTIONS" ]]; then
            echo -e "${DIM}    [CI调试] 检查 C++ 扩展文件位置...${NC}"
            for ext in sage_flow sage_db sage_tsdb; do
                ext_dir="packages/sage-middleware/src/sage/middleware/components/${ext}"
                if [ -d "$ext_dir" ]; then
                    so_count=$(find "$ext_dir" -name "lib*.so" -type f 2>/dev/null | wc -l)
                    echo -e "${DIM}      ${ext}: 找到 ${so_count} 个 .so 文件${NC}"
                fi
            done
        fi

        # L5: apps & benchmark (standard/full/dev 模式)
        if [ "$install_mode" != "core" ]; then
            if [ -d "packages/sage-benchmark" ]; then
                echo -e "${DIM}  正在安装: packages/sage-benchmark${NC}"
                log_info "开始安装: packages/sage-benchmark" "INSTALL"
                log_debug "PIP命令: $PIP_CMD install $install_flags packages/sage-benchmark $pip_args --no-deps" "INSTALL"

                if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"packages/sage-benchmark\" $pip_args --no-deps"; then
                    log_error "安装 sage-benchmark 失败" "INSTALL"
                    echo -e "${CROSS} 安装 sage-benchmark 失败！"
                    return 1
                fi

                log_info "安装成功: packages/sage-benchmark" "INSTALL"
                log_pip_package_info "isage-benchmark" "INSTALL"
                echo -e "${CHECK} sage-benchmark 安装完成"
            fi
        fi

        # L5: apps (仅 full 和 dev 模式)
        if [ "$install_mode" = "full" ] || [ "$install_mode" = "dev" ]; then
            if [ -d "packages/sage-apps" ]; then
                echo -e "${DIM}  正在安装: packages/sage-apps${NC}"
                log_info "开始安装: packages/sage-apps" "INSTALL"
                log_debug "PIP命令: $PIP_CMD install $install_flags packages/sage-apps $pip_args --no-deps" "INSTALL"

                if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"packages/sage-apps\" $pip_args --no-deps"; then
                    log_error "安装 sage-apps 失败" "INSTALL"
                    echo -e "${CROSS} 安装 sage-apps 失败！"
                    return 1
                fi

                log_info "安装成功: packages/sage-apps" "INSTALL"
                log_pip_package_info "isage-apps" "INSTALL"
                echo -e "${CHECK} sage-apps 安装完成"
            fi

            # L5: gateway (API server)
            if [ -d "packages/sage-gateway" ]; then
                echo -e "${DIM}  正在安装: packages/sage-gateway${NC}"
                log_info "开始安装: packages/sage-gateway" "INSTALL"
                log_debug "PIP命令: $PIP_CMD install $install_flags packages/sage-gateway $pip_args --no-deps" "INSTALL"

                if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"packages/sage-gateway\" $pip_args --no-deps"; then
                    log_error "安装 sage-gateway 失败" "INSTALL"
                    echo -e "${CROSS} 安装 sage-gateway 失败！"
                    return 1
                fi

                log_info "安装成功: packages/sage-gateway" "INSTALL"
                log_pip_package_info "isage-gateway" "INSTALL"
                echo -e "${CHECK} sage-gateway 安装完成"
            fi
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

    # L6: studio (full/dev 模式)
    if [ "$install_mode" = "full" ] || [ "$install_mode" = "dev" ]; then
        if [ -d "packages/sage-studio" ]; then
            echo -e "${DIM}  正在安装: packages/sage-studio${NC}"
            log_info "开始安装: packages/sage-studio" "INSTALL"
            log_debug "PIP命令: $PIP_CMD install $install_flags packages/sage-studio $pip_args --no-deps" "INSTALL"

            if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"packages/sage-studio\" $pip_args --no-deps"; then
                log_error "安装 sage-studio 失败" "INSTALL"
                echo -e "${CROSS} 安装 sage-studio 失败！"
                return 1
            fi

            log_info "安装成功: packages/sage-studio" "INSTALL"
            log_pip_package_info "isage-studio" "INSTALL"
            echo -e "${CHECK} sage-studio 安装完成"

            # 自动安装前端依赖 (npm install)
            # 用户期望 quickstart.sh 能一站式搞定所有依赖
            local frontend_dir="packages/sage-studio/src/sage/studio/frontend"
            if [ -d "$frontend_dir" ] && command -v npm &> /dev/null; then
                echo -e "${DIM}  正在安装前端依赖 (npm install)...${NC}"
                log_info "开始安装前端依赖: $frontend_dir" "INSTALL"

                # 使用子shell进入目录执行，避免影响当前目录
                # 使用 --no-audit --no-fund 加速安装
                if (cd "$frontend_dir" && npm install --no-audit --no-fund --loglevel=error &> /dev/null); then
                    log_info "前端依赖安装成功" "INSTALL"
                    echo -e "${CHECK} 前端依赖安装完成"
                else
                    log_warn "前端依赖安装失败，但这不影响 Python 包安装" "INSTALL"
                    echo -e "${WARNING} 前端依赖安装失败 (请稍后运行 'sage studio install' 修复)"
                fi
            fi
        fi
    fi

    # L6: tools (仅 dev 模式)
    if [ "$install_mode" = "dev" ]; then
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

    # L6: gateway (dev 模式)
    if [ "$install_mode" = "dev" ]; then
        if [ -d "packages/sage-gateway" ]; then
            echo -e "${DIM}  正在安装: packages/sage-gateway${NC}"
            log_info "开始安装: packages/sage-gateway" "INSTALL"
            log_debug "PIP命令: $PIP_CMD install $install_flags packages/sage-gateway $pip_args --no-deps" "INSTALL"

            if ! log_command "INSTALL" "Deps" "$PIP_CMD install $install_flags \"packages/sage-gateway\" $pip_args --no-deps"; then
                log_error "安装 sage-gateway 失败" "INSTALL"
                echo -e "${CROSS} 安装 sage-gateway 失败！"
                return 1
            fi

            log_info "安装成功: packages/sage-gateway" "INSTALL"
            log_pip_package_info "isage-gateway" "INSTALL"
            echo -e "${CHECK} sage-gateway 安装完成"
        fi
    fi

    if [ "$install_mode" = "core" ]; then
        echo -e "${DIM}步骤 4/5: 跳过上层包（core 模式）${NC}"
    fi

    echo -e "${CHECK} 本地依赖包安装完成"
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

    # 执行 Python 脚本提取依赖（内联脚本）
    log_debug "执行 Python 依赖提取脚本..." "INSTALL"
    if $PYTHON_CMD -c "
import sys, re
from pathlib import Path
external_deps = set()
package_dirs = ['packages/sage-common', 'packages/sage-platform', 'packages/sage-kernel', 'packages/sage-libs', 'packages/sage-middleware']
install_mode = '$install_mode'
if install_mode != 'core':
    package_dirs.extend(['packages/sage-cli', 'packages/sage-benchmark'])
if install_mode in ['full', 'dev']:
    package_dirs.extend(['packages/sage-apps', 'packages/sage-gateway', 'packages/sage-studio'])
if install_mode == 'dev':
    package_dirs.extend(['packages/sage-tools', 'packages/sage-gateway'])
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
                if not dep.startswith('isage-'): external_deps.add(dep)
with open('$external_deps_file', 'w') as f:
    for dep in sorted(external_deps): f.write(f'{dep}\n')
print(f'✓ 提取了 {len(external_deps)} 个外部依赖', file=sys.stderr)
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
                local failed_packages=$(grep -i "error\|failed" "$SAGE_INSTALL_LOG" | tail -5 || echo "无法确定失败包")
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
    if [ "$install_vllm" = "true" ]; then
        local vllm_from_source="${SAGE_VLLM_FROM_SOURCE:-false}"
        if [ "$vllm_from_source" = "true" ]; then
            echo -e "${BLUE}🔧 从本地源码编译安装 vLLM...${NC}"
            install_vllm_from_source "$pip_args" "$project_root"
        else
            echo -e "${BLUE}🤖 安装 vLLM 运行时依赖（从 PyPI）...${NC}"
            install_vllm_optional_dependencies "$pip_args"
        fi
    else
        echo -e "${DIM}跳过 vLLM 运行时依赖安装（使用 --no-vllm）${NC}"
        log_info "用户通过 --no-vllm 跳过 vLLM 依赖安装" "INSTALL"
    fi

    echo ""
    echo -e "${CHECK} SAGE ($install_mode 模式) 和外部依赖安装成功！"
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
