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
echo ""
echo -e "${BLUE}🐛 DEBUG - 检查环境信息：${NC}"
echo "   工作目录: $PWD"
echo "   SAGE 根目录: $SAGE_ROOT"
echo "   当前用户: $(whoami)"
echo "   Python 版本: $(python3 --version 2>&1 || echo 'N/A')"
echo "   Pip 版本: $(pip3 --version 2>&1 || echo 'N/A')"
echo "   CI 环境: ${CI:-false}"
echo "   GitHub Actions: ${GITHUB_ACTIONS:-false}"
echo "   Git 分支: $(git branch --show-current 2>/dev/null || echo 'N/A')"
echo "   Git 提交: $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
echo ""

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
        echo ""
        echo -e "${BLUE}🐛 DEBUG - 日志目录内容：${NC}"
        ls -lah "$SAGE_ROOT/.sage/logs/" 2>&1 || echo "   目录不存在"
        exit 1
    fi
fi

echo -e "${BLUE}📋 日志文件信息：${NC}"
echo "   路径: $LOG_FILE"
echo "   大小: $(du -h "$LOG_FILE" 2>/dev/null | cut -f1 || echo 'N/A')"
echo "   行数: $(wc -l < "$LOG_FILE" 2>/dev/null || echo 'N/A')"
echo "   最后修改: $(stat -c '%y' "$LOG_FILE" 2>/dev/null || stat -f '%Sm' "$LOG_FILE" 2>/dev/null || echo 'N/A')"
echo ""

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
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ 依赖完整性检查失败${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}⚠️ 依赖完整性检查失败！${NC}"
    echo "检测到从 PyPI 下载了本地包，这是一个严重的配置错误！"
    echo ""
    echo -e "${BLUE}🐛 调试建议：${NC}"
    echo "1. 查看上方的详细 DEBUG 输出，了解具体哪些包违规"
    echo "2. 检查日志文件: $LOG_FILE"
    echo "3. 确认安装顺序是否正确（L1→L2→L3→L4→L5→L6）"
    echo "4. 验证 pyproject.toml 中的依赖声明"
    echo "5. 如果是 CI/CD 环境，对比本地安装日志"
    echo ""
    echo -e "${BLUE}🔍 快速诊断命令：${NC}"
    echo "   # 查看所有下载记录"
    echo "   grep 'Downloading' $LOG_FILE"
    echo ""
    echo "   # 查看 editable 安装记录"
    echo "   grep 'editable' $LOG_FILE"
    echo ""
    echo "   # 手动运行监控脚本"
    echo "   bash $MONITOR_SCRIPT analyze $LOG_FILE"
    echo ""

    if declare -f log_phase_end_enhanced &>/dev/null; then
        log_phase_end_enhanced "依赖完整性检查" "false" "DepsCheck"
    fi
    exit 1
fi
