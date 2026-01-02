#!/bin/bash
# SAGE 安装进度监控脚本
# 使用方法: ./tools/install/monitor_installation.sh

echo "🔍 SAGE 安装进度监控"
echo "================================"
echo ""

# 1. 检查 pip 进程
pip_count=$(ps aux | grep -E "pip.*install" | grep -v grep | wc -l)
if [ "$pip_count" -gt 0 ]; then
    echo "✅ pip 进程运行中（$pip_count 个）"
    ps aux | grep -E "pip.*install" | grep -v grep | awk '{print "   进程 " $2 ": " $11 " " $12 " " $13}'
    echo ""
else
    echo "❌ 未检测到 pip 进程"
    echo ""
fi

# 2. 检查安装的包数量
if command -v pip &> /dev/null; then
    installed_count=$(pip list 2>/dev/null | wc -l)
    echo "📦 已安装包数量: $((installed_count - 2))"  # 减去标题行
    echo ""
fi

# 3. 检查要安装的总数
if [ -f ".sage/external-deps-dev.txt" ]; then
    total_count=$(cat .sage/external-deps-dev.txt | wc -l)
    echo "📋 需要安装的外部依赖: $total_count 个"
    echo ""

    # 计算进度
    if [ "$installed_count" -gt 0 ] && [ "$total_count" -gt 0 ]; then
        progress=$((installed_count * 100 / total_count))
        echo "📊 预估进度: $progress%"
        echo ""
    fi
fi

# 4. 检查最近安装的包
echo "🆕 最近安装的 5 个包:"
pip list --format=freeze 2>/dev/null | tail -5 | while read line; do
    echo "   - $line"
done
echo ""

# 5. 检查网络连接
echo "🌐 网络连接测试:"
if timeout 2 curl -s https://pypi.org > /dev/null 2>&1; then
    echo "   ✓ PyPI 官方源可访问"
else
    echo "   ✗ PyPI 官方源访问失败"
fi

if timeout 2 curl -s https://pypi.tuna.tsinghua.edu.cn > /dev/null 2>&1; then
    echo "   ✓ 清华镜像源可访问"
else
    echo "   ✗ 清华镜像源访问失败"
fi
echo ""

# 6. 检查磁盘空间
echo "💾 磁盘空间:"
df -h . | tail -1 | awk '{print "   可用: " $4 " / " $2 " (" $5 " 已使用)"}'
echo ""

# 7. 检查日志文件大小
if [ -f "$HOME/.sage/logs/install.log" ] || [ -f ".sage/logs/install.log" ]; then
    log_file=""
    [ -f "$HOME/.sage/logs/install.log" ] && log_file="$HOME/.sage/logs/install.log"
    [ -f ".sage/logs/install.log" ] && log_file=".sage/logs/install.log"

    if [ -n "$log_file" ]; then
        log_size=$(du -h "$log_file" | cut -f1)
        log_lines=$(wc -l < "$log_file")
        echo "📄 安装日志:"
        echo "   文件: $log_file"
        echo "   大小: $log_size"
        echo "   行数: $log_lines"
        echo ""

        # 显示最后 3 条有意义的日志
        echo "   最近日志:"
        grep -E "INFO|WARN|ERROR" "$log_file" | tail -3 | while read line; do
            echo "   $line"
        done
        echo ""
    fi
fi

# 8. 估算剩余时间（基于当前速度）
if [ -f ".sage/external-deps-dev.txt" ]; then
    # 检查安装开始时间
    if [ -f ".sage/logs/install.log" ]; then
        start_time=$(grep "开始安装外部依赖" .sage/logs/install.log 2>/dev/null | head -1 | cut -d'"' -f4 | cut -d' ' -f1-2)
        if [ -n "$start_time" ]; then
            start_timestamp=$(date -d "$start_time" +%s 2>/dev/null || echo "0")
            current_timestamp=$(date +%s)
            elapsed=$((current_timestamp - start_timestamp))

            if [ "$elapsed" -gt 60 ]; then
                installed_count=$((installed_count - 10))  # 减去基础包
                remaining=$((total_count - installed_count))

                if [ "$installed_count" -gt 0 ]; then
                    avg_time_per_pkg=$((elapsed / installed_count))
                    estimated_remaining=$((avg_time_per_pkg * remaining))

                    echo "⏱️  时间估算:"
                    echo "   已用时: $((elapsed / 60)) 分钟 $((elapsed % 60)) 秒"
                    echo "   平均速度: $avg_time_per_pkg 秒/包"
                    echo "   预计剩余: $((estimated_remaining / 60)) 分钟 $((estimated_remaining % 60)) 秒"
                    echo ""
                fi
            fi
        fi
    fi
fi

# 9. 建议
echo "💡 建议:"
if [ "$pip_count" -eq 0 ]; then
    echo "   安装可能已完成或失败，请检查终端输出"
elif [ "$elapsed" -gt 1800 ]; then  # 超过 30 分钟
    echo "   安装时间较长，建议下次使用镜像源加速"
    echo "   运行: source tools/install/fast_install.sh"
else
    echo "   安装正在进行中，请耐心等待"
fi

echo ""
echo "================================"
echo "刷新: 按 Ctrl+C 退出，或重新运行此脚本查看最新状态"
