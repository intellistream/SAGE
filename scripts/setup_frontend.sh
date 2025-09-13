#!/bin/bash
#
# SAGE Frontend Setup Script
# 自动安装前端依赖和配置环境

set -euo pipefail

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# 当前脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 前端相关路径
FRONTEND_DIR="$PROJECT_ROOT/packages/sage-tools/src/sage/tools/frontend"
STUDIO_DIR="$FRONTEND_DIR/studio"

echo -e "${BOLD}${BLUE}🌐 SAGE Frontend Setup${NC}"
echo -e "${BLUE}=========================${NC}"
echo ""

# 检查操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo -e "${BLUE}📱 检测到操作系统: $OS${NC}"

# 检查 Node.js
check_nodejs() {
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo -e "${GREEN}✅ Node.js 已安装: $NODE_VERSION${NC}"
        
        # 检查版本是否满足要求 (>=18)
        MAJOR_VERSION=$(echo "$NODE_VERSION" | sed 's/v//' | cut -d. -f1)
        if [ "$MAJOR_VERSION" -ge 18 ]; then
            echo -e "${GREEN}✅ Node.js 版本满足要求 (>=18)${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  Node.js 版本过低，需要 >=18，当前: $NODE_VERSION${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Node.js 未安装${NC}"
        return 1
    fi
}

# 安装 Node.js
install_nodejs() {
    echo -e "${YELLOW}📦 正在安装 Node.js...${NC}"
    
    case $OS in
        "linux")
            if command -v apt-get &> /dev/null; then
                # Ubuntu/Debian
                echo -e "${BLUE}🔧 使用 apt-get 安装 Node.js 18...${NC}"
                curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
                sudo apt-get install -y nodejs
            elif command -v yum &> /dev/null; then
                # RHEL/CentOS
                echo -e "${BLUE}🔧 使用 yum 安装 Node.js 18...${NC}"
                curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
                sudo yum install -y nodejs
            else
                echo -e "${RED}❌ 不支持的 Linux 发行版，请手动安装 Node.js 18+${NC}"
                echo -e "${BLUE}💡 访问: https://nodejs.org/en/download/${NC}"
                exit 1
            fi
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                echo -e "${BLUE}🔧 使用 Homebrew 安装 Node.js...${NC}"
                brew install node@18
            else
                echo -e "${YELLOW}⚠️  请安装 Homebrew 或手动安装 Node.js 18+${NC}"
                echo -e "${BLUE}💡 Homebrew: https://brew.sh/${NC}"
                echo -e "${BLUE}💡 Node.js: https://nodejs.org/en/download/${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}❌ 请手动安装 Node.js 18+${NC}"
            echo -e "${BLUE}💡 访问: https://nodejs.org/en/download/${NC}"
            exit 1
            ;;
    esac
}

# 检查 npm
check_npm() {
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        echo -e "${GREEN}✅ npm 已安装: $NPM_VERSION${NC}"
        return 0
    else
        echo -e "${RED}❌ npm 未安装${NC}"
        return 1
    fi
}

# 安装 Angular Studio 依赖
install_studio_deps() {
    echo -e "${BLUE}📦 安装 Angular Studio 依赖...${NC}"
    
    if [ ! -d "$STUDIO_DIR" ]; then
        echo -e "${RED}❌ Studio 目录不存在: $STUDIO_DIR${NC}"
        exit 1
    fi
    
    cd "$STUDIO_DIR"
    
    if [ ! -f "package.json" ]; then
        echo -e "${RED}❌ package.json 不存在${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}📍 当前目录: $(pwd)${NC}"
    echo -e "${BLUE}🔧 运行 npm install...${NC}"
    
    npm install
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Angular Studio 依赖安装成功${NC}"
    else
        echo -e "${RED}❌ Angular Studio 依赖安装失败${NC}"
        exit 1
    fi
}

# 创建启动脚本
create_startup_scripts() {
    echo -e "${BLUE}📝 创建启动脚本...${NC}"
    
    # 创建 web_ui 启动脚本
    cat > "$PROJECT_ROOT/start_web_ui.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/packages/sage-tools/src/sage/tools/frontend/web_ui"
python main.py start "$@"
EOF
    chmod +x "$PROJECT_ROOT/start_web_ui.sh"
    
    # 创建 studio 启动脚本
    cat > "$PROJECT_ROOT/start_studio.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/packages/sage-tools/src/sage/tools/frontend/studio"
npm start
EOF
    chmod +x "$PROJECT_ROOT/start_studio.sh"
    
    echo -e "${GREEN}✅ 启动脚本已创建:${NC}"
    echo -e "${GREEN}   - $PROJECT_ROOT/start_web_ui.sh${NC}"
    echo -e "${GREEN}   - $PROJECT_ROOT/start_studio.sh${NC}"
}

# 显示使用说明
show_usage() {
    echo ""
    echo -e "${BOLD}${GREEN}🎉 SAGE Frontend 安装完成！${NC}"
    echo ""
    echo -e "${BOLD}🚀 启动方式：${NC}"
    echo ""
    echo -e "${BLUE}1. 启动 Web UI (FastAPI Web 管理界面):${NC}"
    echo -e "   ${GREEN}./start_web_ui.sh${NC}"
    echo -e "   ${BLUE}或${NC}"
    echo -e "   ${GREEN}sage web-ui start${NC}"
    echo -e "   ${BLUE}或${NC}"
    echo -e "   ${GREEN}cd packages/sage-tools/src/sage/tools/frontend/web_ui${NC}"
    echo -e "   ${GREEN}python main.py start${NC}"
    echo -e "   ${YELLOW}访问: http://localhost:8080${NC}"
    echo ""
    echo -e "${BLUE}2. 启动 Studio (Angular 低代码界面):${NC}"
    echo -e "   ${GREEN}./start_studio.sh${NC}"
    echo -e "   ${BLUE}或${NC}"
    echo -e "   ${GREEN}cd packages/sage-tools/src/sage/tools/frontend/studio${NC}"
    echo -e "   ${GREEN}npm start${NC}"
    echo -e "   ${YELLOW}访问: http://localhost:4200${NC}"
    echo ""
    echo -e "${BOLD}📦 Python 依赖安装：${NC}"
    echo -e "   ${GREEN}pip install isage-tools    # 基础前端依赖${NC}"
    echo -e "   ${GREEN}pip install isage-tools      # Studio 依赖${NC}"
    echo -e "   ${GREEN}pip install isage-tools          # 完整 UI 套件${NC}"
    echo ""
}

# 主函数
main() {
    echo -e "${BLUE}🔍 检查前端环境...${NC}"
    
    # 检查 Node.js
    if ! check_nodejs; then
        echo -e "${YELLOW}📦 正在安装 Node.js...${NC}"
        install_nodejs
        
        # 重新检查
        if ! check_nodejs; then
            echo -e "${RED}❌ Node.js 安装失败${NC}"
            exit 1
        fi
    fi
    
    # 检查 npm
    if ! check_npm; then
        echo -e "${RED}❌ npm 未安装，请检查 Node.js 安装${NC}"
        exit 1
    fi
    
    # 安装 Studio 依赖
    install_studio_deps
    
    # 创建启动脚本
    create_startup_scripts
    
    # 显示使用说明
    show_usage
}

# 运行主函数
main "$@"
