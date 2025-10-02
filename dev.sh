#!/bin/bash
# 🚀 SAGE 开发工具快捷脚本
# 为不熟悉 Make 的用户提供的简单包装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo -e "${CYAN}🚀 SAGE 开发工具快捷命令${NC}"
    echo ""
    echo -e "${GREEN}用法:${NC} ./dev.sh <command> [options]"
    echo ""
    echo -e "${YELLOW}📦 安装与设置:${NC}"
    echo "  install         - 快速安装 SAGE（开发模式）"
    echo ""
    echo -e "${YELLOW}✨ 代码质量:${NC}"
    echo "  lint           - 运行代码检查（flake8）"
    echo "  format         - 格式化代码（black + isort）"
    echo "  quality        - 运行完整质量检查"
    echo ""
    echo -e "${YELLOW}🧪 测试:${NC}"
    echo "  test           - 运行所有测试"
    echo "  test:quick     - 运行快速测试"
    echo "  test:all       - 运行完整测试套件"
    echo ""
    echo -e "${YELLOW}📦 构建与发布:${NC}"
    echo "  build          - 构建所有包"
    echo "  clean          - 清理构建产物"
    echo "  check          - 检查包配置"
    echo "  publish        - 发布到 TestPyPI"
    echo "  publish:prod   - 发布到生产 PyPI"
    echo ""
    echo -e "${YELLOW}🔧 版本管理:${NC}"
    echo "  version        - 显示当前版本"
    echo "  version:bump   - 升级版本号"
    echo "  version:set    - 设置指定版本"
    echo ""
    echo -e "${YELLOW}📚 文档:${NC}"
    echo "  docs           - 构建文档"
    echo "  docs:serve     - 本地预览文档"
    echo ""
    echo -e "${PURPLE}💡 提示:${NC} 这些命令调用 'sage dev' 工具，需要源码安装模式"
    echo -e "${PURPLE}💡 提示:${NC} 也可以使用 'make <command>' 如果你熟悉 Make"
}

# 主逻辑
case "$1" in
    # 安装
    install)
        echo -e "${BLUE}🚀 运行快速安装...${NC}"
        ./quickstart.sh
        ;;
    
    # 代码质量
    lint)
        echo -e "${BLUE}🔍 运行代码检查...${NC}"
        sage dev quality --check-only
        ;;
    
    format)
        echo -e "${BLUE}✨ 格式化代码...${NC}"
        sage dev quality
        ;;
    
    quality)
        echo -e "${BLUE}🎨 运行完整质量检查...${NC}"
        sage dev quality
        ;;
    
    # 测试
    test)
        echo -e "${BLUE}🧪 运行测试...${NC}"
        pytest "${@:2}"
        ;;
    
    test:quick)
        echo -e "${BLUE}⚡ 运行快速测试...${NC}"
        pytest -m "not slow" -v "${@:2}"
        ;;
    
    test:all)
        echo -e "${BLUE}🧪 运行完整测试套件...${NC}"
        pytest -v --cov=packages --cov-report=html "${@:2}"
        ;;
    
    # 构建与发布
    build)
        echo -e "${BLUE}🔨 构建所有包...${NC}"
        sage dev pypi build "${@:2}"
        ;;
    
    clean)
        echo -e "${BLUE}🧹 清理构建产物...${NC}"
        sage dev pypi clean "${@:2}"
        ;;
    
    check)
        echo -e "${BLUE}🔍 检查包配置...${NC}"
        sage dev pypi check "${@:2}"
        ;;
    
    publish)
        echo -e "${BLUE}📦 发布到 TestPyPI...${NC}"
        sage dev pypi publish --dry-run "${@:2}"
        ;;
    
    publish:prod)
        echo -e "${YELLOW}⚠️  发布到生产 PyPI...${NC}"
        read -p "确认发布到生产环境? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sage dev pypi publish "${@:2}"
        else
            echo -e "${RED}已取消${NC}"
        fi
        ;;
    
    # 版本管理
    version)
        sage dev version list "${@:2}"
        ;;
    
    version:bump)
        sage dev version bump "${@:2}"
        ;;
    
    version:set)
        if [ -z "$2" ]; then
            echo -e "${RED}错误: 请指定版本号${NC}"
            echo "用法: ./dev.sh version:set <version>"
            exit 1
        fi
        sage dev version set "$2" "${@:3}"
        ;;
    
    # 文档
    docs)
        echo -e "${BLUE}📚 构建文档...${NC}"
        cd docs-public && ./build.sh
        ;;
    
    docs:serve)
        echo -e "${BLUE}🌐 启动文档服务器...${NC}"
        cd docs-public && mkdocs serve
        ;;
    
    # 帮助
    help|--help|-h|"")
        show_help
        ;;
    
    *)
        echo -e "${RED}错误: 未知命令 '$1'${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
