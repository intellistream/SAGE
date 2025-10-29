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
            echo -e "${GRAY}核心运行时：L1-L4 (基础框架)${NC}"
            echo -e "${DIM}包含: common, platform, kernel, libs, middleware${NC}"
            ;;
        "standard")
            echo -e "${GREEN}标准版本：Core + L5 (应用包)${NC}"
            echo -e "${DIM}包含: 核心框架 + apps, benchmark, studio${NC}"
            ;;
        "full")
            echo -e "${PURPLE}完整功能：Standard + CLI${NC}"
            echo -e "${DIM}包含: 标准版本 + sage CLI 命令${NC}"
            ;;
        "dev")
            echo -e "${YELLOW}开发模式：Full + 开发工具${NC}"
            echo -e "${DIM}包含: 完整功能 + sage-dev, pytest, pre-commit 等${NC}"
            ;;
        *)
            echo -e "${YELLOW}未知模式，使用开发者模式${NC}"
            install_mode="dev"
            ;;
    esac

    echo ""

    # 检查所有必要的包目录是否存在
    local required_packages=("packages/sage-common" "packages/sage-platform" "packages/sage-kernel")

    # 所有模式都需要 L4 (libs, middleware)
    required_packages+=("packages/sage-libs" "packages/sage-middleware")

    # standard/full/dev 模式需要 sage-cli
    if [ "$install_mode" != "core" ]; then
        [ -d "packages/sage-cli" ] && required_packages+=("packages/sage-cli")
    fi

    # standard/full/dev 模式需要 L5 应用包 (apps, benchmark)
    if [ "$install_mode" != "core" ]; then
        [ -d "packages/sage-apps" ] && required_packages+=("packages/sage-apps")
        [ -d "packages/sage-benchmark" ] && required_packages+=("packages/sage-benchmark")
    fi

    # full 和 dev 模式需要 studio
    if [ "$install_mode" = "full" ] || [ "$install_mode" = "dev" ]; then
        [ -d "packages/sage-studio" ] && required_packages+=("packages/sage-studio")
    fi

    # dev 模式需要 sage-tools
    if [ "$install_mode" = "dev" ]; then
        [ -d "packages/sage-tools" ] && required_packages+=("packages/sage-tools")
    fi

    required_packages+=("packages/sage")

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

    # 第二步：安装核心引擎和库 (L3-L4)
    echo -e "${DIM}步骤 2/3: 安装核心引擎和库 (L3-L4)...${NC}"
    local core_packages=("packages/sage-kernel" "packages/sage-libs")

    for package_dir in "${core_packages[@]}"; do
        echo -e "${DIM}  正在安装: $package_dir${NC}"
        echo "$(date): 安装 $package_dir" >> "$log_file"

        if ! $PIP_CMD install $install_flags "$package_dir" $pip_args --no-deps >> "$log_file" 2>&1; then
            echo -e "${CROSS} 安装 $package_dir 失败！"
            echo "$(date): 安装 $package_dir 失败" >> "$log_file"
            return 1
        fi
    done

    # 第三步：安装middleware和上层包（L4-L6，根据模式）
    echo -e "${DIM}步骤 3/3: 安装上层包 (L4-L6)...${NC}"

    # L4: middleware (特殊处理：不使用 --no-deps，需要构建C++扩展)
    echo -e "${DIM}  正在安装: packages/sage-middleware${NC}"
    echo -e "${DIM}    (包含 C++ 扩展构建，可能需要几分钟...)${NC}"
    if ! $PIP_CMD install $install_flags "packages/sage-middleware" $pip_args >> "$log_file" 2>&1; then
        echo -e "${CROSS} 安装 sage-middleware 失败！"
        echo -e "${DIM}提示: 检查日志文件获取详细错误信息: $log_file${NC}"
        return 1
    fi
    echo -e "${CHECK} sage-middleware 安装完成（包括 C++ 扩展）"

    # L5: apps, benchmark (standard/full/dev 模式)
    if [ "$install_mode" != "core" ]; then
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
    if [ "$install_mode" != "core" ]; then
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
        echo -e "${DIM}  正在安装: packages/sage-tools${NC}"
        if ! $PIP_CMD install $install_flags "packages/sage-tools" $pip_args --no-deps >> "$log_file" 2>&1; then
            echo -e "${CROSS} 安装 sage-tools 失败！"
            return 1
        fi
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

    # 3b. 重新安装 sage[mode] 来获取所有外部依赖（本地包已经是 editable，不会被重装）
    echo -e "${DIM}  3b. 安装外部依赖（numpy, typer, rich 等）...${NC}"
    echo "$(date): 安装外部依赖（允许重复以确保依赖安装）" >> "$log_file"

    # 使用 --force-reinstall --no-deps 只针对 sage 包，然后用普通安装获取依赖
    # 实际上，由于本地包是 -e 安装，pip 会识别它们已安装，只会安装缺失的外部依赖
    if $PIP_CMD install "$install_target" $pip_args 2>&1 | tee -a "$log_file"; then
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
