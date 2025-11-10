#!/bin/bash
# 自动配置 VS Code 以使用指定的 Conda 环境
# 用法: bash tools/install/fixes/setup_vscode_conda.sh <环境名>

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 导入颜色定义
source "$SCRIPT_DIR/../display_tools/colors.sh"

# 获取环境名（从参数或默认值）
ENV_NAME="${1:-sage}"

# 检测 conda 安装路径
if [ -n "$CONDA_PREFIX" ]; then
    # 如果在 conda 环境中，使用当前 conda 的根路径
    CONDA_PATH="$(dirname "$(dirname "$CONDA_PREFIX")")"
elif [ -d "$HOME/miniconda3" ]; then
    CONDA_PATH="$HOME/miniconda3"
elif [ -d "$HOME/anaconda3" ]; then
    CONDA_PATH="$HOME/anaconda3"
elif [ -d "$HOME/opt/miniconda3" ]; then
    CONDA_PATH="$HOME/opt/miniconda3"
elif [ -d "$HOME/opt/anaconda3" ]; then
    CONDA_PATH="$HOME/opt/anaconda3"
else
    echo -e "${YELLOW}⚠️  无法自动检测 Conda 安装路径${NC}"
    echo -e "${INFO} 请手动指定路径或使用默认值 ~/miniconda3"
    read -p "Conda 路径 [~/miniconda3]: " user_conda_path
    CONDA_PATH="${user_conda_path:-$HOME/miniconda3}"
fi

# 验证环境是否存在
ENV_PATH="$CONDA_PATH/envs/$ENV_NAME"
if [ ! -d "$ENV_PATH" ]; then
    echo -e "${RED}❌ Conda 环境不存在: $ENV_PATH${NC}"
    echo -e "${INFO} 可用的环境:"
    conda env list 2>/dev/null | grep -v "^#" | sed 's/^/  /'
    exit 1
fi

echo -e "${BLUE}🔧 配置 VS Code 以使用 Conda 环境${NC}"
echo ""
echo -e "${INFO} 环境名称: ${GREEN}$ENV_NAME${NC}"
echo -e "${INFO} Conda 路径: ${GREEN}$CONDA_PATH${NC}"
echo -e "${INFO} 工作区路径: ${GREEN}$WORKSPACE_ROOT${NC}"
echo ""

# 创建 .vscode 目录
mkdir -p "$WORKSPACE_ROOT/.vscode"

SETTINGS_FILE="$WORKSPACE_ROOT/.vscode/settings.json"

# 检查是否已存在配置文件
if [ -f "$SETTINGS_FILE" ]; then
    echo -e "${WARNING} VS Code 配置文件已存在: $SETTINGS_FILE"
    echo ""
    read -p "是否备份并覆盖? [y/N]: " overwrite
    
    if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
        echo -e "${INFO} 取消操作"
        echo ""
        echo -e "${YELLOW}请手动添加以下配置到 $SETTINGS_FILE:${NC}"
        echo ""
        echo -e "  \"python.defaultInterpreterPath\": \"$CONDA_PATH/envs/$ENV_NAME/bin/python\","
        echo -e "  \"terminal.integrated.env.linux\": {"
        echo -e "    \"CONDA_DEFAULT_ENV\": \"$ENV_NAME\""
        echo -e "  },"
        echo -e "  \"terminal.integrated.shellArgs.linux\": ["
        echo -e "    \"-c\","
        echo -e "    \"conda activate $ENV_NAME && exec bash\""
        echo -e "  ]"
        echo ""
        exit 0
    fi
    
    # 备份现有文件
    BACKUP_FILE="$SETTINGS_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$SETTINGS_FILE" "$BACKUP_FILE"
    echo -e "${CHECK} 已备份到: $BACKUP_FILE"
fi

# 创建配置文件
cat > "$SETTINGS_FILE" << EOF
{
  "python.defaultInterpreterPath": "$CONDA_PATH/envs/$ENV_NAME/bin/python",
  "terminal.integrated.env.linux": {
    "CONDA_DEFAULT_ENV": "$ENV_NAME"
  },
  "terminal.integrated.shellArgs.linux": [
    "-c",
    "conda activate $ENV_NAME && exec bash"
  ],
  "python.terminal.activateEnvironment": true,
  "python.analysis.extraPaths": [
    "\${workspaceFolder}/packages/sage/src",
    "\${workspaceFolder}/packages/sage-common/src",
    "\${workspaceFolder}/packages/sage-kernel/src",
    "\${workspaceFolder}/packages/sage-libs/src",
    "\${workspaceFolder}/packages/sage-middleware/src",
    "\${workspaceFolder}/packages/sage-platform/src",
    "\${workspaceFolder}/packages/sage-apps/src",
    "\${workspaceFolder}/packages/sage-studio/src",
    "\${workspaceFolder}/packages/sage-tools/src",
    "\${workspaceFolder}/packages/sage-cli/src",
    "\${workspaceFolder}/packages/sage-benchmark/src"
  ],
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "files.watcherExclude": {
    "**/.git/objects/**": true,
    "**/.git/subtree-cache/**": true,
    "**/node_modules/**": true,
    "**/.sage/**": true,
    "**/__pycache__/**": true,
    "**/.pytest_cache/**": true
  }
}
EOF

echo ""
echo -e "${CHECK} ✅ VS Code 配置已创建: $SETTINGS_FILE"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}配置已完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${INFO} VS Code 现在会:"
echo -e "  ✓ 自动使用 Python 解释器: $ENV_NAME"
echo -e "  ✓ 在新终端中自动激活环境"
echo -e "  ✓ 配置正确的导入路径"
echo ""
echo -e "${YELLOW}注意: 请重新加载 VS Code 窗口以应用配置${NC}"
echo -e "  快捷键: ${CYAN}Ctrl+Shift+P${NC} -> ${CYAN}Reload Window${NC}"
echo ""
