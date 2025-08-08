#!/bin/bash

# SAGE Frontend Server 启动脚本
# 使用方法: ./start_frontend.sh [选项]

# 默认配置
DEFAULT_HOST="127.0.0.1"
DEFAULT_PORT="8080"
RELOAD=false

# 帮助信息
show_help() {
    echo "SAGE Frontend Server 启动脚本"
    echo ""
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示此帮助信息"
    echo "  --host HOST             设置服务器地址 (默认: $DEFAULT_HOST)"
    echo "  --port PORT             设置服务器端口 (默认: $DEFAULT_PORT)"
    echo "  --reload                启用开发模式自动重载"
    echo "  --version               显示版本信息"
    echo ""
    echo "示例:"
    echo "  $0                      # 使用默认设置启动"
    echo "  $0 --host 0.0.0.0       # 监听所有接口"
    echo "  $0 --port 8888          # 使用端口 8888"
    echo "  $0 --reload             # 开发模式启动"
}

# 解析命令行参数
HOST=$DEFAULT_HOST
PORT=$DEFAULT_PORT

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --reload)
            RELOAD=true
            shift
            ;;
        --version)
            python -c "import sys; sys.path.insert(0, './src'); import sage_frontend.sage_server.main as main; main.main()" version
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# 构建启动命令
CMD_ARGS="start --host $HOST --port $PORT"
if [ "$RELOAD" = true ]; then
    CMD_ARGS="$CMD_ARGS --reload"
fi

# 显示启动信息
echo "🚀 启动 SAGE Frontend Server"
echo "📍 地址: http://$HOST:$PORT"
echo "📚 API文档: http://$HOST:$PORT/docs"
echo "🔍 健康检查: http://$HOST:$PORT/health"
echo ""

# 启动服务器
python -c "import sys; sys.path.insert(0, './src'); import sage_frontend.sage_server.main as main; main.main()" $CMD_ARGS
