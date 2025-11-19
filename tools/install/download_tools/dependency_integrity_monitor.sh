#!/bin/bash
# 🔍 依赖完整性监控 - CICD 入口脚本
# 检测 pip 安装过程中是否从 PyPI 下载了本地包

set -euo pipefail

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 导入颜色定义
if [ -f "$SCRIPT_DIR/../display_tools/colors.sh" ]; then
    source "$SCRIPT_DIR/../display_tools/colors.sh"
else
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    NC='\033[0m'
fi

# 导入日志工具
if [ -f "$SCRIPT_DIR/../display_tools/logging.sh" ]; then
    source "$SCRIPT_DIR/../display_tools/logging.sh"
fi

echo -e "${BLUE}🔍 CI/CD 安全检查：验证依赖完整性...${NC}"

# 确定要检查的日志文件
LOG_FILE="$SAGE_ROOT/.sage/logs/install.log"

if [ ! -f "$LOG_FILE" ]; then
    # 尝试使用 CI 安装日志
    if [ -f "$SAGE_ROOT/.sage/logs/ci_install.log" ]; then
        LOG_FILE="$SAGE_ROOT/.sage/logs/ci_install.log"
        echo -e "${YELLOW}⚠️  使用 CI 安装日志：$LOG_FILE${NC}"
    else
        echo -e "${RED}❌ 找不到安装日志文件${NC}"
        echo "   预期位置: $SAGE_ROOT/.sage/logs/install.log"
        echo "   备用位置: $SAGE_ROOT/.sage/logs/ci_install.log"
        exit 1
    fi
fi

# 调用 pip 安装监控器
MONITOR_SCRIPT="$SAGE_ROOT/tools/install/installation_table/pip_install_monitor.sh"

if [ ! -f "$MONITOR_SCRIPT" ]; then
    echo -e "${RED}❌ 监控脚本不存在：$MONITOR_SCRIPT${NC}"
    exit 1
fi

# 记录到日志（如果日志工具可用）
if declare -f log_phase_start_enhanced &>/dev/null; then
    log_phase_start_enhanced "依赖完整性检查" "DepsCheck" 10
fi

# 执行检查
if bash "$MONITOR_SCRIPT" analyze "$LOG_FILE"; then
    echo -e "${GREEN}✅ 依赖完整性检查通过${NC}"
    if declare -f log_phase_end_enhanced &>/dev/null; then
        log_phase_end_enhanced "依赖完整性检查" "true" "DepsCheck"
    fi
    exit 0
else
    echo -e "${RED}❌ 依赖完整性检查失败${NC}"
    echo ""
    echo -e "${YELLOW}⚠️ 依赖完整性检查失败！${NC}"
    echo "检测到从 PyPI 下载了本地包，这是一个严重的配置错误！"
    echo "请检查 pyproject.toml 中的依赖声明"
    echo ""
    if declare -f log_phase_end_enhanced &>/dev/null; then
        log_phase_end_enhanced "依赖完整性检查" "false" "DepsCheck"
    fi
    exit 1
fi
