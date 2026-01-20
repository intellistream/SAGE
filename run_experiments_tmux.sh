#!/bin/bash
# 使用 tmux 运行 SAGE 实验套件
# 使用方法: ./run_experiments_tmux.sh

SESSION_NAME="sage_experiments"

# 检查 tmux session 是否已存在
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "错误: tmux session '$SESSION_NAME' 已存在"
    echo "请使用以下命令之一："
    echo "  tmux attach -t $SESSION_NAME  # 重新连接到现有 session"
    echo "  tmux kill-session -t $SESSION_NAME  # 删除现有 session"
    exit 1
fi

# 创建新的 tmux session 并运行实验
echo "========================================"
echo "启动 SAGE 实验 (tmux session: $SESSION_NAME)"
echo "========================================"
echo ""
echo "实验将在后台运行，你可以安全地断开连接。"
echo ""
echo "常用命令："
echo "  tmux attach -t $SESSION_NAME     # 重新连接"
echo "  Ctrl+B 然后按 D                 # 断开连接（实验继续运行）"
echo "  tmux kill-session -t $SESSION_NAME  # 强制停止"
echo ""
echo "正在启动..."
sleep 2

# 创建 tmux session，运行实验脚本
tmux new-session -d -s $SESSION_NAME "cd $(pwd) && ./sage_experiment.sh; echo ''; echo '实验已完成！按任意键退出...'; read"

# 自动连接到 session
tmux attach -t $SESSION_NAME
