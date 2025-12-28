#!/bin/bash
# SAGE Cluster SSH 免密登录配置脚本
# 自动为 sage2, sage3, sage4 配置 SSH 免密登录

set -e

echo "=========================================="
echo "SAGE Cluster SSH 免密登录配置"
echo "=========================================="

# 默认配置
DEFAULT_USER="sage"
DEFAULT_PASSWORD="123"
DEFAULT_HOSTS=("sage2" "sage3" "sage4")

# 检查是否安装了 sshpass
if ! command -v sshpass &> /dev/null; then
    echo "❌ 未找到 sshpass 工具，正在安装..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y sshpass
    elif command -v yum &> /dev/null; then
        sudo yum install -y sshpass
    else
        echo "❌ 无法自动安装 sshpass，请手动安装"
        echo "   Ubuntu/Debian: sudo apt-get install sshpass"
        echo "   CentOS/RHEL: sudo yum install sshpass"
        exit 1
    fi
fi

# 检查是否已有 SSH 密钥
SSH_KEY="$HOME/.ssh/id_rsa"
if [ ! -f "$SSH_KEY" ]; then
    echo "🔑 生成 SSH 密钥对..."
    ssh-keygen -t rsa -b 4096 -f "$SSH_KEY" -N "" -C "sage-cluster-$(whoami)@$(hostname)"
    echo "✅ SSH 密钥生成完成: $SSH_KEY"
else
    echo "✅ SSH 密钥已存在: $SSH_KEY"
fi

# 读取用户配置
read -p "SSH 用户名 [默认: $DEFAULT_USER]: " USER
USER=${USER:-$DEFAULT_USER}

read -s -p "SSH 密码 [默认: $DEFAULT_PASSWORD]: " PASSWORD
echo
PASSWORD=${PASSWORD:-$DEFAULT_PASSWORD}

read -p "目标主机 (空格分隔) [默认: ${DEFAULT_HOSTS[*]}]: " HOSTS_INPUT
if [ -z "$HOSTS_INPUT" ]; then
    HOSTS=("${DEFAULT_HOSTS[@]}")
else
    read -ra HOSTS <<< "$HOSTS_INPUT"
fi

echo ""
echo "📋 配置信息："
echo "   用户: $USER"
echo "   主机: ${HOSTS[*]}"
echo ""

# 为每个主机配置免密登录
SUCCESS_COUNT=0
TOTAL_COUNT=${#HOSTS[@]}

for HOST in "${HOSTS[@]}"; do
    echo "----------------------------------------"
    echo "🔧 配置主机: $HOST"
    echo "----------------------------------------"

    # 测试连接
    echo "1. 测试 SSH 连接..."
    if ! sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$USER@$HOST" "echo 'Connection OK'" 2>/dev/null; then
        echo "❌ 无法连接到 $HOST，跳过"
        continue
    fi
    echo "✅ 连接成功"

    # 复制公钥
    echo "2. 复制 SSH 公钥..."
    if sshpass -p "$PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no -i "$SSH_KEY.pub" "$USER@$HOST" 2>/dev/null; then
        echo "✅ 公钥复制成功"
    else
        echo "❌ 公钥复制失败"
        continue
    fi

    # 验证免密登录
    echo "3. 验证免密登录..."
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$USER@$HOST" "echo 'Passwordless login works.'" 2>/dev/null; then
        echo "✅ 免密登录配置成功: $USER@$HOST"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "❌ 免密登录验证失败"
    fi

    echo ""
done

echo "=========================================="
echo "配置完成: $SUCCESS_COUNT/$TOTAL_COUNT 成功"
echo "=========================================="

if [ $SUCCESS_COUNT -eq $TOTAL_COUNT ]; then
    echo "🎉 所有主机配置成功！"
    echo ""
    echo "💡 测试命令："
    for HOST in "${HOSTS[@]}"; do
        echo "   ssh $USER@$HOST 'hostname'"
    done
    exit 0
else
    echo "⚠️  部分主机配置失败，请检查网络和密码"
    exit 1
fi
