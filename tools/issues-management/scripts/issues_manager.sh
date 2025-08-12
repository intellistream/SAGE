#!/bin/bash

# SAGE Issues管理工具集 - 主菜单界面
# 统一的issues管理入口，每个功能对应_scripts下的一个脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_menu() {
    echo -e "${CYAN}🎯 SAGE Issues 管理工具集${NC}"
    echo "================================"
    echo ""
    echo -e "${BLUE}📋 可用功能:${NC}"
    echo ""
    echo -e "  1. ✨ 创建新Issue"
    echo -e "  2. 📥 下载GitHub Issues"
    echo -e "  3. 📊 查看统计信息"
    echo -e "  4. 🤖 AI智能Issues管理 (包含GitHub操作)"
    echo -e "  5. 📖 查看帮助文档"
    echo -e "  6. 🚪 退出"
    echo ""
}

download_issues() {
    echo "📥 启动GitHub Issues下载..."
    cd "$SCRIPT_DIR/.."
    python3 scripts/_scripts/1_download_issues.py
    read -p "按Enter键继续..."
}

create_new_issue() {
    echo "✨ 启动新Issue创建工具..."
    cd "$SCRIPT_DIR/.."
    python3 scripts/_scripts/create_github_issue.py
    read -p "按Enter键继续..."
}

ai_management() {
    echo "🤖 启动AI智能Issues管理系统..."
    echo "整合重复分析、标签优化、优先级评估、错误修正等AI功能"
    echo "✨ AI分析完成后可直接执行GitHub操作"
    cd "$SCRIPT_DIR/.."
    python3 scripts/_scripts/2_ai_unified_manager.py
    read -p "按Enter键继续..."
}

show_statistics() {
    echo "📊 显示Issues统计信息..."
    cd "$SCRIPT_DIR/.."
    python3 scripts/_scripts/4_show_statistics.py
    read -p "按Enter键继续..."
}

show_help() {
    echo -e "${GREEN}📖 SAGE Issues管理工具集帮助${NC}"
    echo "=================================="
    echo ""
    echo -e "${YELLOW}🔧 功能说明:${NC}"
    echo ""
    echo -e "${BLUE}1. ✨ 创建新Issue${NC}"
    echo "   - 交互式创建GitHub Issues"
    echo "   - 支持命令行参数和JSON文件输入"
    echo "   - 自动获取可用标签和验证输入"
    echo "   - 支持分配用户和设置里程碑"
    echo ""
    echo -e "${BLUE}2. 📥 下载GitHub Issues${NC}"
    echo "   - 从GitHub API下载最新的issues数据"
    echo "   - 支持开放和关闭的issues"
    echo "   - 按标签分类存储"
    echo ""
    echo -e "${BLUE}3. 📊 查看统计信息${NC}"
    echo "   - 详细的issues数据统计"
    echo "   - 标签分布分析"
    echo "   - 分配情况统计"
    echo "   - 活跃度趋势分析"
    echo ""
    echo -e "${BLUE}4. 🤖 AI智能Issues管理 (包含GitHub操作)${NC}"
    echo -e "${BLUE}4. 🤖 AI智能Issues管理 (包含GitHub操作)${NC}"
    echo "   - 🔍 AI重复检测分析 (深度语义理解)"
    echo "   - 🏷️ AI标签优化分析 (智能分类推荐)"
    echo "   - 📊 AI优先级评估 (多因素评估)"
    echo "   - 🔧 AI错误修正 (智能识别和修复)"
    echo "   - 🧠 AI综合管理 (全面管理建议)"
    echo "   - 📈 AI分析报告 (专业报告生成)"
    echo "   - ⚙️ 智能GitHub操作执行 (基于AI分析结果)"
    echo "     • 合并重复issues"
    echo "     • 更新标签和分配"
    echo "     • 关闭/重新开放issues"
    echo "     • 其他优化操作"
    echo ""
    echo -e "${BLUE}5. � 查看帮助文档${NC}"
    echo "   - 详细的工具使用说明"
    echo "   - AI特性介绍"
    echo "   - 环境变量配置指南"
    echo "   - 工作流程说明"
    echo ""
    echo -e "${YELLOW}🤖 AI特性:${NC}"
    echo "   - 完全摒弃rule-based硬编码逻辑"
    echo "   - 基于OpenAI GPT-4或Claude深度分析"
    echo "   - 支持Claude助手直接分析模式 (无需复制粘贴)"
    echo "   - Claude直接读取本地issues数据进行智能分析"
    echo "   - 理解SAGE项目特点和技术背景"
    echo "   - 生成专业的分析报告"
    echo "   - AI分析后可直接执行GitHub操作"
    echo ""
    echo -e "${YELLOW}🔄 工作流程:${NC}"
    echo "   1. 下载最新issues数据"
    echo "   2. AI分析生成操作建议"
    echo "   3. 用户确认后执行GitHub操作"
    echo "   4. 查看更新结果和统计信息"
    echo ""
    echo -e "${YELLOW}📁 目录结构:${NC}"
    echo "   - issues/: 下载的issues数据"
    echo "   - output/: AI分析报告和输出"
    echo "   - scripts/_scripts/: 实现脚本"
    echo ""
    echo -e "${YELLOW}🔧 环境变量:${NC}"
    echo "   - GITHUB_TOKEN: GitHub API访问token"
    echo "   - OPENAI_API_KEY: OpenAI API密钥 (可选)"
    echo "   - ANTHROPIC_API_KEY: Claude API密钥 (可选)"
    echo ""
    read -p "按Enter键继续..."
}

# 主循环
while true; do
    show_menu
    read -p "请选择功能 (1-6): " choice
    echo ""
    
    # 清理输入，去除空格和特殊字符
    choice=$(echo "$choice" | tr -d ' \t\n\r')
    
    case $choice in
        1) create_new_issue ;;
        2) download_issues ;;
        3) show_statistics ;;
        4) ai_management ;;
        5) show_help ;;
        6) 
            echo -e "${GREEN}👋 感谢使用SAGE Issues管理工具集！${NC}"
            exit 0
            ;;
        "")
            echo -e "${YELLOW}⚠️ 请输入一个选项${NC}"
            ;;
        *)
            echo -e "${RED}❌ 无效选择 '${choice}'，请输入1-6${NC}"
            ;;
    esac
    
    echo ""
done
