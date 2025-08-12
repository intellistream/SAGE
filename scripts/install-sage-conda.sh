#!/bin/bash

# 安装 sage-conda.sh 到用户的 bin 目录
# 这个脚本会创建一个符号链接，使 sage-conda.sh 可以作为 sage-conda 命令使用

# 获取当前脚本的路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
SOURCE_SCRIPT="$SCRIPT_DIR/sage-conda.sh"
TARGET_DIR="$HOME/.local/bin"
TARGET_LINK="$TARGET_DIR/sage-conda"

# 检查源脚本是否存在
if [[ ! -f "$SOURCE_SCRIPT" ]]; then
    echo "Error: Source script not found at $SOURCE_SCRIPT"
    exit 1
fi

# 确保目标目录存在
mkdir -p "$TARGET_DIR"

# 创建符号链接
ln -sf "$SOURCE_SCRIPT" "$TARGET_LINK"

# 检查目标目录是否在 PATH 中
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
    echo "Warning: $TARGET_DIR is not in your PATH."
    echo "Add the following line to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$PATH:$TARGET_DIR\""
    echo "Then restart your terminal or run: source ~/.bashrc"
fi

# 设置执行权限
chmod +x "$SOURCE_SCRIPT"
chmod +x "$TARGET_LINK"

echo "✅ sage-conda command installed successfully at $TARGET_LINK"
echo "Usage: sage-conda [command] [options]"
echo "Example: sage-conda jobmanager start"
