#!/bin/bash
# SAGE 安装脚本 - 核心包安装器 (重构版本)
# 负责通过主sage包统一安装所有依赖

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 导入友好错误处理
if [ -f "$(dirname "${BASH_SOURCE[0]}")/../fixes/friendly_error_handler.sh" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/../fixes/friendly_error_handler.sh"
fi

# CI环境检测
if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
elif [ "$SAGE_REMOTE_DEPLOY" = "true" ]; then
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
else
    export PYTHONNOUSERSITE=1
fi

# 设置pip命令
PIP_CMD="${PIP_CMD:-pip3}"

# 安装核心包 - 新的简化版本
install_core_packages() {
    local install_mode="${1:-dev}"  # 默认为开发模式

    # 获取项目根目录并初始化日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/.sage/logs/install.log"

    # 确保.sage目录结构存在
    mkdir -p "$project_root/.sage/logs"
    mkdir -p "$project_root/.sage/tmp"
    mkdir -p "$project_root/.sage/cache"

    # 初始化日志文件
    echo "SAGE 安装日志 - $(date)" > "$log_file"
    echo "安装模式: $install_mode" >> "$log_file"
    echo "========================================" >> "$log_file"

    echo -e "${INFO} 安装 SAGE ($install_mode 模式)..."
    echo -e "${DIM}安装日志: $log_file${NC}"
    echo ""

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
            echo -e "${PURPLE}完整功能：Standard + Apps + Studio${NC}"
            echo -e "${DIM}包含: 标准 + sage-apps, sage-benchmark, sage-studio (~300MB)${NC}"
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
    fi

    # full 和 dev 模式需要 studio
    if [ "$install_mode" = "full" ] || [ "$install_mode" = "dev" ]; then
        [ -d "packages/sage-studio" ] && required_packages+=("packages/sage-studio")
        # full/dev 模式添加 L5 包（如果存在）
        [ -d "packages/sage-apps" ] && required_packages+=("packages/sage-apps")
        [ -d "packages/sage-benchmark" ] && required_packages+=("packages/sage-benchmark")
    fi

    # dev 模式需要 sage-tools
    if [ "$install_mode" = "dev" ]; then
        [ -d "packages/sage-tools" ] && required_packages+=("packages/sage-tools")
    fi

    required_packages+=("packages/sage")

    # 切换到项目根目录进行检查和安装
    cd "$project_root" || {
        echo -e "${CROSS} 错误：无法切换到项目根目录 $project_root"
        return 1
    }

    for package_dir in "${required_packages[@]}"; do
        if [ ! -d "$package_dir" ]; then
            echo -e "${CROSS} 错误：找不到包目录 ($package_dir)"
            echo "$(date): 错误：包目录 $package_dir 不存在" >> "$log_file"
            return 1
        fi
    done

    # 执行安装
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  📦 安装 SAGE ($install_mode 模式)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # 准备pip安装参数
    local pip_args="--disable-pip-version-check --no-input"

    # CI环境额外处理
    if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
        # 在CI中将包安装到用户site（~/.local），便于跨job缓存与导入
        pip_args="$pip_args --user"
        # 某些系统前缀可能仍需此选项
        if python3 -c "import sys; exit(0 if '/usr' in sys.prefix else 1)" 2>/dev/null; then
            pip_args="$pip_args --break-system-packages"
            echo -e "${DIM}CI环境: 添加 --break-system-packages${NC}"
        fi
        # 确保用户脚本目录在PATH中（供 'sage' 可执行脚本使用）
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "${DIM}CI环境: 使用 --user 安装，PATH+=~/.local/bin${NC}"
    fi

    echo "$(date): 开始安装本地依赖包" >> "$log_file"

    # 本地开发安装策略：
    # 使用 -e (editable) 模式安装，但添加 --no-deps 避免从PyPI下载依赖
    # 因为我们会按正确的依赖顺序手动安装所有包
    local install_flags="-e"

    # 第一步：安装基础包（L1-L2）
    echo -e "${DIM}步骤 1/3: 安装基础包 (L1-L2)...${NC}"
    local base_packages=("packages/sage-common" "packages/sage-platform")

    for package_dir in "${base_packages[@]}"; do
        echo -e "${DIM}  正在安装: $package_dir${NC}"
        echo "$(date): 安装 $package_dir" >> "$log_file"

        if ! $PIP_CMD install $install_flags "$package_dir" $pip_args --no-deps >> "$log_file" 2>&1; then
            echo -e "${CROSS} 安装 $package_dir 失败！"
            echo "$(date): 安装 $package_dir 失败" >> "$log_file"
            return 1
        fi
    done

    # 第二步：安装核心引擎 (L3)
    echo -e "${DIM}步骤 2/3: 安装核心引擎 (L3)...${NC}"
    local core_packages=("packages/sage-kernel")

    if [ "$install_mode" != "core" ]; then
        core_packages+=("packages/sage-libs")
    fi

    for package_dir in "${core_packages[@]}"; do
        echo -e "${DIM}  正在安装: $package_dir${NC}"
        echo "$(date): 安装 $package_dir" >> "$log_file"

        if ! $PIP_CMD install $install_flags "$package_dir" $pip_args --no-deps >> "$log_file" 2>&1; then
            echo -e "${CROSS} 安装 $package_dir 失败！"
            echo "$(date): 安装 $package_dir 失败" >> "$log_file"
            return 1
        fi
    done

    # 第三步：安装上层包（L4-L6，根据模式）
    if [ "$install_mode" != "core" ]; then
        echo -e "${DIM}步骤 3/3: 安装上层包 (L4-L6)...${NC}"

        # L4: middleware (包含C++扩展构建)
        # 注意：必须使用 --no-deps 防止 pip 重新安装已有的 sage 子包依赖
        # C++ 构建依赖（pybind11等）在 build-system.requires 中声明，通过环境已安装
        # 运行时依赖（isage-common/platform/kernel/libs）在 step 1-2 已安装
        echo -e "${DIM}  正在安装: packages/sage-middleware${NC}"
        echo -e "${DIM}    (包含 C++ 扩展构建，可能需要几分钟...)${NC}"
        if ! $PIP_CMD install $install_flags "packages/sage-middleware" $pip_args --no-deps >> "$log_file" 2>&1; then
            echo -e "${CROSS} 安装 sage-middleware 失败！"
            echo -e "${DIM}提示: 检查日志文件获取详细错误信息: $log_file${NC}"
            return 1
        fi
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

        # L5: apps & benchmark (仅 full 和 dev 模式)
        if [ "$install_mode" = "full" ] || [ "$install_mode" = "dev" ]; then
            # 配置 pyproject.toml（确保所有子包都被包含）
            echo -e "${DIM}  检查并配置 pyproject.toml...${NC}"

            # 配置 sage-benchmark: 确保 sage.data 及其子包被包含
            if [ -f "packages/sage-benchmark/pyproject.toml" ]; then
                if ! grep -q '"sage\.data"' "packages/sage-benchmark/pyproject.toml"; then
                    # 在 sage.benchmark.benchmark_rag.evaluation 之后添加 sage.data 相关包
                    sed -i '/sage\.benchmark\.benchmark_rag\.evaluation",/a\    "sage.data",\n    "sage.data.qa",\n    "sage.data.locomo",\n    "sage.data.bbh",\n    "sage.data.mmlu",\n    "sage.data.gpqa",' packages/sage-benchmark/pyproject.toml
                fi
            fi

            # 配置 sage-apps: 确保所有子应用包被包含
            if [ -f "packages/sage-apps/pyproject.toml" ]; then
                if ! grep -q '"sage\.apps\.video"' "packages/sage-apps/pyproject.toml"; then
                    # 在 sage.apps 之后添加子应用包
                    sed -i '/"sage\.apps",/a\    "sage.apps.video",\n    "sage.apps.medical_diagnosis",\n    "sage.apps.smart_home",\n    "sage.apps.article_monitoring",\n    "sage.apps.auto_scaling_chat",' packages/sage-apps/pyproject.toml
                fi
            fi

            # 配置 sage.data 子模块导入（确保使用相对导入）
            if [ -d "packages/sage-benchmark/src/sage/data" ]; then
                # 配置 sage/data/__init__.py
                [ -f "packages/sage-benchmark/src/sage/data/__init__.py" ] && \
                    sed -i 's/^from qa import/from .qa import/g; s/^from locomo import/from .locomo import/g; s/^from bbh import/from .bbh import/g; s/^from mmlu import/from .mmlu import/g; s/^from gpqa import/from .gpqa import/g' \
                    packages/sage-benchmark/src/sage/data/__init__.py

                # 配置各个子模块的 __init__.py
                for submodule in qa locomo gpqa; do
                    [ -f "packages/sage-benchmark/src/sage/data/$submodule/__init__.py" ] && \
                        sed -i "s|^from $submodule\.|from .|g; s|^from $submodule import|from .dataloader import|g" \
                        packages/sage-benchmark/src/sage/data/$submodule/__init__.py
                done
            fi

            if [ -d "packages/sage-apps" ]; then
                echo -e "${DIM}  正在安装: packages/sage-apps${NC}"
                $PIP_CMD install $install_flags "packages/sage-apps" $pip_args --no-deps >> "$log_file" 2>&1
            fi

            if [ -d "packages/sage-benchmark" ]; then
                echo -e "${DIM}  正在安装: packages/sage-benchmark${NC}"
                $PIP_CMD install $install_flags "packages/sage-benchmark" $pip_args --no-deps >> "$log_file" 2>&1
            fi
        fi

        # L6: CLI (standard/full/dev 模式)
        if [ -d "packages/sage-cli" ]; then
            echo -e "${DIM}  正在安装: packages/sage-cli${NC}"
            if ! $PIP_CMD install $install_flags "packages/sage-cli" $pip_args --no-deps >> "$log_file" 2>&1; then
                echo -e "${CROSS} 安装 sage-cli 失败！"
                return 1
            fi
        fi
    fi

    # L6: studio (full/dev 模式)
    if [ "$install_mode" = "full" ] || [ "$install_mode" = "dev" ]; then
        if [ -d "packages/sage-studio" ]; then
            echo -e "${DIM}  正在安装: packages/sage-studio${NC}"
            if ! $PIP_CMD install $install_flags "packages/sage-studio" $pip_args --no-deps >> "$log_file" 2>&1; then
                echo -e "${CROSS} 安装 sage-studio 失败！"
                return 1
            fi
        fi
    fi

    # L6: tools (仅 dev 模式)
    if [ "$install_mode" = "dev" ]; then
        if [ -d "packages/sage-tools" ]; then
            echo -e "${DIM}  正在安装: packages/sage-tools${NC}"
            if ! $PIP_CMD install $install_flags "packages/sage-tools" $pip_args --no-deps >> "$log_file" 2>&1; then
                echo -e "${CROSS} 安装 sage-tools 失败！"
                return 1
            fi
        fi
    fi

    if [ "$install_mode" = "core" ]; then
        echo -e "${DIM}步骤 3/3: 跳过上层包（core 模式）${NC}"
    fi

    echo -e "${CHECK} 本地依赖包安装完成"
    echo ""

    # 第四步：安装主SAGE包和外部依赖
    echo -e "${DIM}步骤 4/4: 安装外部依赖...${NC}"
    echo "$(date): 安装外部依赖" >> "$log_file"

    # 3a. 先用 --no-deps 安装 sage meta-package（避免重复安装本地包）
    local install_target="packages/sage[$install_mode]"
    echo -e "${DIM}  3a. 安装 sage meta-package (--no-deps)...${NC}"

    if ! $PIP_CMD install $install_flags "$install_target" $pip_args --no-deps >> "$log_file" 2>&1; then
        echo -e "${CROSS} 安装 sage meta-package 失败！"
        echo "$(date): 安装 sage meta-package 失败" >> "$log_file"
        return 1
    fi

    # 3b. 安装外部依赖（不重装本地 editable 包）
    echo -e "${DIM}  3b. 安装外部依赖（numpy, typer, rich 等）...${NC}"
    echo "$(date): 安装外部依赖" >> "$log_file"

    # 关键修复：使用 --upgrade-strategy only-if-needed 防止重装已安装的 editable 包
    # 这确保只安装缺失的外部依赖，不会从 PyPI 重装本地包
    if $PIP_CMD install --upgrade-strategy only-if-needed "$install_target" $pip_args 2>&1 | tee -a "$log_file"; then
        echo ""
        echo -e "${CHECK} SAGE ($install_mode 模式) 和外部依赖安装成功！"
        echo ""

        # 验证sage命令
        echo -e "${DIM}验证 sage 命令...${NC}"
        if command -v sage >/dev/null 2>&1; then
            echo -e "${CHECK} sage 命令已可用"
            echo "$(date): sage 命令验证成功" >> "$log_file"
        else
            echo -e "${WARN} sage 命令不可用，可能需要重启终端"
            echo "$(date): sage 命令验证失败" >> "$log_file"
        fi

        echo "$(date): SAGE ($install_mode 模式) 安装成功" >> "$log_file"
        return 0

    else
        echo ""
        echo -e "${CROSS} SAGE ($install_mode 模式) 安装失败！"
        echo -e "${DIM}检查日志: $log_file${NC}"
        echo ""
        echo "$(date): SAGE ($install_mode 模式) 安装失败" >> "$log_file"
        return 1
    fi
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
