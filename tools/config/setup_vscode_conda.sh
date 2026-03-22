#!/bin/bash
# 自动配置 VS Code 以使用指定的 Conda 环境
# 用法: bash tools/config/setup_vscode_conda.sh <环境名>

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 导入颜色定义
source "$SCRIPT_DIR/../install/display_tools/colors.sh"

# 获取环境名（从参数或默认值）
ENV_INPUT="${1:-sage}"

# 检查是否是自动模式
AUTO_MODE=false
if [ "$2" = "--auto" ] || [ "$2" = "-y" ]; then
    AUTO_MODE=true
fi

# 检测 conda 安装路径
if [ -n "$CONDA_PREFIX" ]; then
    # 如果在 conda 环境中，使用当前 conda 的根路径
    if [[ "$CONDA_PREFIX" == */envs/* ]]; then
        # 在非 base 环境中，需要去掉两层目录
        CONDA_PATH="$(dirname "$(dirname "$CONDA_PREFIX")")"
    else
        # 在 base 环境中，CONDA_PREFIX 就是 conda 根路径
        CONDA_PATH="$CONDA_PREFIX"
    fi
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

# 判断输入是环境名还是完整路径
if [[ "$ENV_INPUT" == /* ]]; then
    # 输入是绝对路径
    ENV_PATH="$ENV_INPUT"
    ENV_NAME="$(basename "$ENV_PATH")"
else
    # 输入是环境名
    ENV_NAME="$ENV_INPUT"
    ENV_PATH="$CONDA_PATH/envs/$ENV_NAME"

    # 检查是否是 base 环境
    if [ "$ENV_NAME" = "base" ]; then
        ENV_PATH="$CONDA_PATH"
    fi
fi

# 验证环境是否存在
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
if [ -f "$SETTINGS_FILE" ] && [ "$AUTO_MODE" = false ]; then
    echo -e "${WARNING} VS Code 配置文件已存在: $SETTINGS_FILE"
    echo ""
    read -p "是否备份并覆盖? [y/N]: " overwrite

    if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
        echo -e "${INFO} 取消操作"
        echo ""
        echo -e "${YELLOW}请手动添加以下配置到 $SETTINGS_FILE:${NC}"
        echo ""
        echo -e "  \"python.defaultInterpreterPath\": \"$ENV_PATH/bin/python\","
        echo -e "  \"terminal.integrated.profiles.linux\": {"
        echo -e "    \"bash ($ENV_NAME)\": {"
        echo -e "      \"path\": \"bash\","
        echo -e "      \"args\": [\"--init-file\", \"\${workspaceFolder}/.vscode/conda_init.sh\"]"
        echo -e "    }"
        echo -e "  },"
        echo -e "  \"terminal.integrated.defaultProfile.linux\": \"bash ($ENV_NAME)\""
        echo ""
        exit 0
    fi
fi

# 备份现有文件（如果存在）
if [ -f "$SETTINGS_FILE" ]; then
    BACKUP_FILE="$SETTINGS_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$SETTINGS_FILE" "$BACKUP_FILE"
    echo -e "${CHECK} 已备份到: $BACKUP_FILE"
fi

# 创建 conda 初始化脚本
CONDA_INIT_SCRIPT="$WORKSPACE_ROOT/.vscode/conda_init.sh"
cat > "$CONDA_INIT_SCRIPT" << 'INIT_EOF'
#!/bin/bash
# VS Code 终端自动激活 conda 环境的初始化脚本

# 首先加载用户的 bashrc（保留用户自定义配置）
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# 确保 conda 已初始化
if [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
    source ~/miniconda3/etc/profile.d/conda.sh
elif [ -f ~/anaconda3/etc/profile.d/conda.sh ]; then
    source ~/anaconda3/etc/profile.d/conda.sh
fi

# 激活 SAGE_ENV 环境（将被替换）
if command -v conda &> /dev/null; then
    conda activate SAGE_ENV 2>/dev/null || echo "⚠️  无法激活 SAGE_ENV 环境，请检查环境是否存在"
else
    echo "⚠️  Conda 未找到，请确保已安装 Miniconda/Anaconda"
fi
INIT_EOF

# 替换环境名
sed -i "s/SAGE_ENV/$ENV_NAME/g" "$CONDA_INIT_SCRIPT"
chmod +x "$CONDA_INIT_SCRIPT"

# 创建配置文件
cat > "$SETTINGS_FILE" << EOF
{
  "python.defaultInterpreterPath": "$ENV_PATH/bin/python",
  "python.terminal.activateEnvironment": true,
  "terminal.integrated.env.linux": {
    "CONDA_DEFAULT_ENV": "$ENV_NAME",
        "PYTHONPATH": "\${workspaceFolder}/src"
  },
  "terminal.integrated.profiles.linux": {
    "bash ($ENV_NAME)": {
      "path": "bash",
      "args": [
        "--init-file",
        "\${workspaceFolder}/.vscode/conda_init.sh"
      ]
    }
  },
  "terminal.integrated.defaultProfile.linux": "bash ($ENV_NAME)",
  "python.analysis.extraPaths": [
        "\${workspaceFolder}/src"
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
echo -e "${CHECK} ✅ Conda 初始化脚本已创建: $CONDA_INIT_SCRIPT"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}配置已完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${INFO} VS Code 现在会:"
echo -e "  ✓ 自动使用 Python 解释器: $ENV_NAME"
echo -e "  ✓ 在新终端中自动激活 conda 环境"
echo -e "  ✓ 配置正确的导入路径"
echo -e "  ✓ 确保 sage-dev 等命令可用"
echo ""
echo -e "${YELLOW}注意: 请重新加载 VS Code 窗口以应用配置${NC}"
echo -e "  快捷键: ${CYAN}Ctrl+Shift+P${NC} -> ${CYAN}Reload Window${NC}"
echo ""
