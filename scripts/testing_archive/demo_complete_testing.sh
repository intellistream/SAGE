#!/bin/bash
# SAGE 测试系统综合演示脚本
# 展示一键自动化测试系统的所有功能

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}============================================${NC}"
    echo -e "${CYAN}🎯 $1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_section() {
    echo -e "\n${YELLOW}📋 $1${NC}"
    echo -e "${YELLOW}$(printf '%.40s' "----------------------------------------")${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_step() {
    echo -e "\n${PURPLE}🔧 步骤 $1: $2${NC}"
}

demo_pause() {
    echo -e "\n${YELLOW}⏸️  按 Enter 键继续演示...${NC}"
    read
}

main() {
    print_header "SAGE 一键自动化测试系统 - 综合演示"
    
    echo "这个演示将展示 SAGE 测试系统的所有主要功能："
    echo "• 🔍 环境检查和状态显示"
    echo "• ⚡ 快速测试模式"
    echo "• 🧪 智能差异测试"
    echo "• 📊 测试报告生成"
    echo "• 🎭 GitHub Actions 本地模拟"
    echo "• 🖥️  交互式菜单展示"
    
    demo_pause
    
    # 步骤1: 展示系统信息
    print_step "1" "系统环境信息"
    echo "当前工作目录: $(pwd)"
    echo "Python版本: $(python --version 2>&1 || echo '未安装')"
    echo "操作系统: $(uname -s)"
    echo "CPU核心数: $(nproc)"
    echo "内存信息: $(free -h | grep '^Mem:' | awk '{print $2 " 总内存, " $3 " 已使用"}')"
    
    demo_pause
    
    # 步骤2: 环境检查
    print_step "2" "环境检查"
    print_info "运行环境检查..."
    ./quick_test.sh --check
    
    demo_pause
    
    # 步骤3: 展示项目结构
    print_step "3" "项目测试结构分析"
    print_info "分析 SAGE 项目的测试文件结构..."
    
    echo "📂 主要测试目录:"
    find sage -type d -name 'test*' | head -10 | sed 's/^/  • /'
    
    echo -e "\n📄 测试文件统计:"
    echo "  • 总测试文件数: $(find . -name 'test_*.py' -o -name '*_test.py' | wc -l)"
    echo "  • CLI测试: $(find sage/cli -name 'test_*.py' | wc -l) 个"
    echo "  • 核心测试: $(find sage/core -name 'test_*.py' -o -name '*_test.py' | wc -l) 个"  
    echo "  • 工具测试: $(find sage/utils -name 'test_*.py' | wc -l) 个"
    
    demo_pause
    
    # 步骤4: 快速测试模式演示
    print_step "4" "快速测试模式演示"
    print_info "运行快速测试模式..."
    ./quick_test.sh --quick
    
    demo_pause
    
    # 步骤5: 智能差异测试
    print_step "5" "智能差异测试"
    print_info "演示基于git diff的智能测试..."
    ./quick_test.sh --diff
    
    demo_pause
    
    # 步骤6: 测试日志分析
    print_step "6" "测试日志分析"
    print_info "分析现有的测试日志..."
    
    if [ -d "test_logs" ]; then
        local log_count=$(find test_logs -name "*.log" | wc -l)
        echo "📊 测试日志统计:"
        echo "  • 总日志文件数: $log_count"
        echo "  • 日志目录大小: $(du -sh test_logs | cut -f1)"
        
        echo -e "\n📋 最新的5个日志文件:"
        ls -lt test_logs/*.log 2>/dev/null | head -5 | while read line; do
            local filename=$(echo "$line" | awk '{print $9}')
            local size=$(echo "$line" | awk '{print $5}')
            local date=$(echo "$line" | awk '{print $6 " " $7 " " $8}')
            echo "  • $(basename "$filename") (${size}字节, $date)"
        done
        
        # 显示一个日志文件的内容示例
        local sample_log=$(find test_logs -name "*.log" | head -1)
        if [ -f "$sample_log" ]; then
            echo -e "\n📝 日志内容示例 ($(basename "$sample_log")):"
            echo "$(head -10 "$sample_log" | sed 's/^/    /')"
            if [ $(wc -l < "$sample_log") -gt 10 ]; then
                echo "    ..."
                echo "    (共 $(wc -l < "$sample_log") 行)"
            fi
        fi
    else
        echo "⚠️  测试日志目录不存在"
    fi
    
    demo_pause
    
    # 步骤7: GitHub Actions 模拟
    print_step "7" "GitHub Actions 本地模拟"
    print_info "展示 GitHub Actions 工作流..."
    
    if [ -d ".github/workflows" ]; then
        echo "📋 发现的工作流文件:"
        find .github/workflows -name "*.yml" -exec basename {} \; | sed 's/^/  • /'
        
        echo -e "\n🎭 运行 act 工具列出工作流..."
        ./quick_test.sh --github
    else
        echo "⚠️  未发现 GitHub Actions 工作流目录"
    fi
    
    demo_pause
    
    # 步骤8: 报告生成演示
    print_step "8" "测试报告生成"
    print_info "生成测试报告..."
    
    # 手动生成一个简单报告
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local report_file="test_reports/demo_report_$timestamp.md"
    mkdir -p test_reports
    
    cat > "$report_file" << EOF
# SAGE 测试系统演示报告

## 📊 演示概览
- **生成时间**: $(date "+%Y-%m-%d %H:%M:%S")
- **系统信息**: $(uname -a)
- **Python版本**: $(python --version 2>&1)

## 🏗️ 项目结构
- **测试目录数**: $(find sage -type d -name 'test*' | wc -l)
- **测试文件数**: $(find . -name 'test_*.py' -o -name '*_test.py' | wc -l)
- **日志文件数**: $(find test_logs -name "*.log" 2>/dev/null | wc -l)

## 🚀 可用的测试模式
- ✅ 环境检查: \`./quick_test.sh --check\`
- ✅ 快速测试: \`./quick_test.sh --quick\`
- ✅ 完整测试: \`./quick_test.sh --full\`
- ✅ 差异测试: \`./quick_test.sh --diff\`
- ✅ GitHub Actions: \`./quick_test.sh --github\`

## 📈 系统性能
- **CPU核心数**: $(nproc)
- **内存信息**: $(free -h | grep '^Mem:' | awk '{print $2 " 总计, " $3 " 使用中"}')
- **磁盘空间**: $(df -h . | tail -1 | awk '{print $4}') 可用

## 🛠️ 推荐使用方式
1. 日常开发: \`./quick_test.sh --diff\`
2. 提交前检查: \`./quick_test.sh --full\`
3. 环境诊断: \`./quick_test.sh --check\`
4. 交互式操作: \`./quick_test.sh --interactive\`

---
*由 SAGE 测试系统演示脚本生成*
EOF
    
    print_success "演示报告已生成: $report_file"
    echo -e "\n📄 报告内容预览:"
    head -20 "$report_file" | sed 's/^/    /'
    echo "    ..."
    
    demo_pause
    
    # 步骤9: 功能总结
    print_step "9" "功能总结"
    
    echo "🎉 SAGE 一键自动化测试系统提供以下核心功能:"
    echo ""
    echo "📋 测试执行:"
    echo "  ✅ 快速测试模式 - 适合日常开发"
    echo "  ✅ 完整测试套件 - 适合提交前验证"
    echo "  ✅ 智能差异测试 - 基于代码变更"
    echo "  ✅ 并行执行 - 支持多核加速"
    echo ""
    echo "🔧 环境管理:"
    echo "  ✅ 自动环境检查和诊断"
    echo "  ✅ 虚拟环境管理"
    echo "  ✅ 依赖检查和安装"
    echo ""
    echo "📊 报告和日志:"
    echo "  ✅ 详细的测试日志记录"
    echo "  ✅ Markdown格式报告"
    echo "  ✅ 性能统计和分析"
    echo ""
    echo "🎭 CI/CD集成:"
    echo "  ✅ GitHub Actions本地模拟"
    echo "  ✅ 工作流验证"
    echo "  ✅ Docker容器支持"
    echo ""
    echo "🖥️  用户界面:"
    echo "  ✅ 交互式菜单"
    echo "  ✅ 命令行参数支持"
    echo "  ✅ 彩色输出和进度显示"
    
    demo_pause
    
    # 步骤10: 交互式菜单演示
    print_step "10" "交互式菜单演示"
    print_info "即将启动交互式菜单，你可以在其中体验所有功能..."
    
    echo -e "\n💡 菜单中可用的选项:"
    echo "  1. 🔍 环境检查"
    echo "  2. ⚡ 快速测试"  
    echo "  3. 🚀 完整测试"
    echo "  4. 🎯 智能差异测试"
    echo "  5. 🎭 GitHub Actions 模拟"
    echo "  6. 📊 生成测试报告"
    echo "  7. 🛠️ 设置环境"
    echo "  8. 📋 查看测试日志"
    echo "  0. 🚪 退出"
    
    echo -e "\n${YELLOW}准备启动交互式菜单...${NC}"
    demo_pause
    
    # 启动交互式菜单
    ./quick_test.sh --interactive
    
    # 演示结束
    print_header "演示完成"
    
    echo "🎊 SAGE 一键自动化测试系统演示已完成！"
    echo ""
    echo "🚀 现在你可以开始使用这个强大的测试系统："
    echo ""
    echo "📚 快速参考:"
    echo "  • 查看帮助: ./quick_test.sh --help"
    echo "  • 环境检查: ./quick_test.sh --check"
    echo "  • 快速测试: ./quick_test.sh --quick"
    echo "  • 完整测试: ./quick_test.sh --full"
    echo "  • 交互模式: ./quick_test.sh --interactive"
    echo ""
    echo "📖 详细文档: 查看 TEST_AUTOMATION_README.md"
    echo "🎯 演示报告: $report_file"
    echo ""
    print_success "感谢使用 SAGE 测试自动化系统！"
}

# 检查是否在正确的目录
if [ ! -f "quick_test.sh" ] || [ ! -f "run_all_tests.py" ]; then
    echo -e "${RED}❌ 错误: 请在 SAGE 项目根目录下运行此演示script${NC}"
    echo "当前目录: $(pwd)"
    echo "需要的文件: quick_test.sh, run_all_tests.py"
    exit 1
fi

# 启动演示
main "$@"
