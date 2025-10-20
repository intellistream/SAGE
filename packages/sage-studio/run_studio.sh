#!/bin/bash
"""
SAGE Studio v2.0 启动脚本

这个脚本提供便捷的方式来启动 SAGE Studio 的不同模式
"""

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo -e "${BLUE}🚀 SAGE Studio v2.0 Launcher${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
    echo "Usage: $0 [MODE] [OPTIONS]"
    echo ""
    echo "MODES:"
    echo "  standalone    Run SAGE Studio independently (no SAGE required)"
    echo "  integrated    Run SAGE Studio with full SAGE integration"
    echo "  test          Run Phase 1 tests"
    echo "  help          Show this help message"
    echo ""
    echo "OPTIONS:"
    echo "  --interactive   Start in interactive CLI mode (default)"
    echo "  --server        Start as web server (not implemented yet)"
    echo "  --host HOST     Server host (default: localhost)"
    echo "  --port PORT     Server port (default: 8080)"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 standalone                    # Run in standalone mode"
    echo "  $0 integrated --interactive      # Run with SAGE integration"
    echo "  $0 test                         # Run tests"
    echo "  $0 standalone --server --port 3000  # Future: web server"
}

# 检查 Python 环境
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 is required but not installed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Python 3 detected${NC}"
}

# 检查依赖
check_dependencies() {
    echo -e "${BLUE}🔍 Checking dependencies...${NC}"
    
    # 检查 Python 包
    python3 -c "import pydantic, typing_extensions" 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Installing required Python packages...${NC}"
        pip install pydantic typing_extensions
    }
    
    echo -e "${GREEN}✅ Dependencies OK${NC}"
}

# 检查 SAGE 是否可用
check_sage() {
    if python3 -c "import sage" 2>/dev/null; then
        echo -e "${GREEN}✅ SAGE Kernel available${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  SAGE Kernel not available${NC}"
        return 1
    fi
}

# 运行独立模式
run_standalone() {
    echo -e "${BLUE}🚀 Starting SAGE Studio - Standalone Mode${NC}"
    echo -e "${BLUE}=========================================${NC}"
    
    check_python
    check_dependencies
    
    echo ""
    echo -e "${GREEN}Starting standalone SAGE Studio...${NC}"
    python3 run_standalone.py "$@"
}

# 运行集成模式
run_integrated() {
    echo -e "${BLUE}🚀 Starting SAGE Studio - Integrated Mode${NC}"
    echo -e "${BLUE}=========================================${NC}"
    
    check_python
    check_dependencies
    
    if check_sage; then
        echo -e "${GREEN}🔗 SAGE integration enabled${NC}"
    else
        echo -e "${YELLOW}⚠️  SAGE not found - running in limited mode${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}Starting integrated SAGE Studio...${NC}"
    python3 run_integrated.py "$@"
}

# 运行测试
run_tests() {
    echo -e "${BLUE}🧪 Running SAGE Studio v2.0 Tests${NC}"
    echo -e "${BLUE}==================================${NC}"
    
    check_python
    check_dependencies
    
    echo ""
    echo -e "${GREEN}Running Phase 1 tests...${NC}"
    python3 test_phase1.py
}

# 主逻辑
main() {
    # 如果没有参数，显示帮助
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    # 解析第一个参数（模式）
    MODE="$1"
    shift
    
    case "$MODE" in
        "standalone")
            run_standalone "$@"
            ;;
        "integrated")
            run_integrated "$@"
            ;;
        "test")
            run_tests
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            echo -e "${RED}❌ Unknown mode: $MODE${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"