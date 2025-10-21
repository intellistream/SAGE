#!/bin/bash

# SAGE Studio 启动脚本
# 自动启动后端和前端服务

set -e

echo "========================================="
echo "  🚀 启动 SAGE Studio"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 获取脚本所在目录 (sage-studio)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 清理函数
cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止服务...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓${NC} 后端已停止"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓${NC} 前端已停止"
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

# 1. 启动后端
echo -e "${BLUE}[1/2]${NC} 启动后端服务..."
echo ""

# 检查 8080 端口是否被占用
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠${NC}  端口 8080 已被占用，尝试清理..."
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo "   启动 FastAPI 服务器..."
python -m sage.studio.config.backend.api > /tmp/sage-studio-backend.log 2>&1 &
BACKEND_PID=$!

# 等待后端启动
echo -n "   等待后端就绪"
for i in {1..30}; do
    if curl -s http://localhost:8080/ > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✓${NC} 后端已启动: ${GREEN}http://localhost:8080${NC}"
        echo ""
        break
    fi
    echo -n "."
    sleep 1
    if [ $i -eq 30 ]; then
        echo ""
        echo -e "${RED}✗${NC} 后端启动超时"
        echo "   查看日志: tail -f /tmp/sage-studio-backend.log"
        exit 1
    fi
done

# 2. 启动前端
echo -e "${BLUE}[2/2]${NC} 启动前端服务..."
echo ""

cd frontend

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "   安装前端依赖..."
    npm install
fi

# 检查 5173 端口是否被占用
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠${NC}  端口 5173 已被占用，尝试清理..."
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo "   启动 Vite 开发服务器..."
npm run dev > /tmp/sage-studio-frontend.log 2>&1 &
FRONTEND_PID=$!

# 等待前端启动
echo -n "   等待前端就绪"
for i in {1..30}; do
    if curl -s http://localhost:5173/ > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✓${NC} 前端已启动: ${GREEN}http://localhost:5173${NC}"
        echo ""
        break
    fi
    echo -n "."
    sleep 1
    if [ $i -eq 30 ]; then
        echo ""
        echo -e "${YELLOW}⚠${NC}  前端启动超时（可能仍在启动中）"
        echo "   查看日志: tail -f /tmp/sage-studio-frontend.log"
    fi
done

echo "========================================="
echo -e "  ${GREEN}✓${NC} SAGE Studio 已启动！"
echo "========================================="
echo ""
echo -e "${BLUE}访问地址:${NC}"
echo -e "  🌐 前端: ${GREEN}http://localhost:5173${NC}"
echo -e "  🔌 后端: ${GREEN}http://localhost:8080${NC}"
echo ""
echo -e "${BLUE}服务状态:${NC}"
echo -e "  📊 后端 PID: ${BACKEND_PID}"
echo -e "  🎨 前端 PID: ${FRONTEND_PID}"
echo ""
echo -e "${BLUE}日志位置:${NC}"
echo -e "  📝 后端: /tmp/sage-studio-backend.log"
echo -e "  📝 前端: /tmp/sage-studio-frontend.log"
echo ""
echo -e "${BLUE}查看日志:${NC}"
echo -e "  ${YELLOW}tail -f /tmp/sage-studio-backend.log${NC}  # 后端日志"
echo -e "  ${YELLOW}tail -f /tmp/sage-studio-frontend.log${NC}  # 前端日志"
echo ""
echo "========================================="
echo -e "${YELLOW}💡 使用 Playground:${NC}"
echo "========================================="
echo ""
echo "1️⃣  打开浏览器访问: http://localhost:5173"
echo ""
echo "2️⃣  在画布中创建 Flow:"
echo "   - 从左侧拖拽节点到画布"
echo "   - 连接节点创建 Pipeline"
echo "   - 点击 '保存' 按钮保存 Flow"
echo ""
echo "3️⃣  打开 Playground:"
echo "   - 点击工具栏的 '💬 Playground' 按钮"
echo "   - Playground 对话框将打开"
echo ""
echo "4️⃣  与 AI 对话:"
echo "   - 在输入框输入消息"
echo "   - 按 Enter 发送 (Shift+Enter 换行)"
echo "   - 查看 AI 响应和 Agent 步骤"
echo ""
echo "5️⃣  查看代码:"
echo "   - 切换到 '代码' 标签"
echo "   - 选择 Python 或 cURL"
echo "   - 点击 '复制代码' 按钮"
echo ""
echo "========================================="
echo -e "${GREEN}按 Ctrl+C 停止所有服务${NC}"
echo "========================================="
echo ""

# 保持脚本运行
wait
