#!/usr/bin/env bash
# 使用示例：如何在其他脚本中使用改进后的 pip 安装进度显示

set -euo pipefail

# ============================================================================
# 示例 1: 基本用法
# ============================================================================

basic_usage() {
    echo "=== 示例 1: 基本用法 ==="

    # 1. 加载 logging.sh
    source "$(dirname "${BASH_SOURCE[0]}")/display_tools/logging.sh"

    # 2. 调用函数
    log_pip_install_with_verbose_progress "INSTALL" "SETUP" \
        "pip install --no-cache-dir numpy pandas"
}

# ============================================================================
# 示例 2: 在安装脚本中使用
# ============================================================================

install_script_usage() {
    echo "=== 示例 2: 在安装脚本中使用 ==="

    source "$(dirname "${BASH_SOURCE[0]}")/display_tools/logging.sh"

    # 安装核心依赖
    echo "安装核心依赖..."
    log_pip_install_with_verbose_progress "CORE" "DEPS" \
        "pip install torch torchvision torchaudio"

    # 安装可选依赖
    echo "安装可选依赖..."
    log_pip_install_with_verbose_progress "OPTIONAL" "ML" \
        "pip install transformers accelerate"
}

# ============================================================================
# 示例 3: 带错误处理
# ============================================================================

error_handling_usage() {
    echo "=== 示例 3: 带错误处理 ==="

    source "$(dirname "${BASH_SOURCE[0]}")/display_tools/logging.sh"

    # 尝试安装，捕获错误
    if log_pip_install_with_verbose_progress "TEST" "INSTALL" \
        "pip install some-nonexistent-package"; then
        echo "安装成功"
    else
        echo "安装失败，但我们可以继续..."
    fi
}

# ============================================================================
# 示例 4: 在 quickstart.sh 风格的脚本中使用
# ============================================================================

quickstart_style_usage() {
    echo "=== 示例 4: Quickstart 风格 ==="

    TOOLS_DIR="$(dirname "${BASH_SOURCE[0]}")"
    source "$TOOLS_DIR/display_tools/logging.sh"

    # 初始化日志
    init_logging "$SAGE_ROOT/.sage/logs"

    # 阶段 1: 系统依赖
    log_phase_start "SYSTEM_DEPS" "安装系统依赖"
    sudo apt-get update
    sudo apt-get install -y build-essential
    log_phase_end "SYSTEM_DEPS"

    # 阶段 2: Python 包（使用改进的进度显示）
    log_phase_start "PYTHON_PACKAGES" "安装 Python 包"
    log_pip_install_with_verbose_progress "PYTHON" "CORE" \
        "pip install -r requirements.txt"
    log_phase_end "PYTHON_PACKAGES"
}

# ============================================================================
# 示例 5: 自定义进度显示格式
# ============================================================================

custom_format_usage() {
    echo "=== 示例 5: 自定义格式 ==="

    source "$(dirname "${BASH_SOURCE[0]}")/display_tools/logging.sh"

    # 可以在调用前设置环境变量来影响行为
    export SAGE_DEBUG=true  # 启用调试模式

    log_pip_install_with_verbose_progress "CUSTOM" "TEST" \
        "pip install scikit-learn"
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    echo "=========================================="
    echo "改进后的 pip 进度显示 - 使用示例"
    echo "=========================================="
    echo ""

    # 运行示例（取消注释你想测试的）
    # basic_usage
    # install_script_usage
    # error_handling_usage
    # quickstart_style_usage
    # custom_format_usage

    echo ""
    echo "✓ 查看 PROGRESS_DISPLAY_IMPROVEMENT.md 获取详细文档"
}

# 如果直接运行此脚本
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
