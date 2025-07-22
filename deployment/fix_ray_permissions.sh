#!/bin/bash

# 默认 session_latest 链接路径
SESSION_LINK="/var/lib/ray_shared/session_latest"

echo "🔍 检查 Ray 会话软链接：$SESSION_LINK"

# 检查软链接是否存在
if [ ! -L "$SESSION_LINK" ]; then
    echo "❌ $SESSION_LINK 不是软链接，无法解析目标目录。"
    exit 1
fi

# 获取实际指向的路径
REAL_SESSION_DIR=$(readlink -f "$SESSION_LINK")

echo "📍 软链接指向的实际路径是：$REAL_SESSION_DIR"

# 检查路径是否有效
if [ ! -d "$REAL_SESSION_DIR" ]; then
    echo "❌ 实际目录不存在：$REAL_SESSION_DIR"
    exit 2
fi

# 设置目标组
TARGET_GROUP="sudo"

echo "🛠️ 正在将目录赋权给组 '$TARGET_GROUP' 并设置组写权限..."

# 修改组归属
sudo chgrp -R "$TARGET_GROUP" "$REAL_SESSION_DIR"

# 添加组读写执行权限
sudo chmod -R g+rwX "$REAL_SESSION_DIR"

# 设置目录为 setgid：后续创建文件自动继承组
sudo find "$REAL_SESSION_DIR" -type d -exec chmod g+s {} \;

echo "✅ 权限修复完成！所有 sudo 用户都可以愉快使用 Ray 啦～🍰"
