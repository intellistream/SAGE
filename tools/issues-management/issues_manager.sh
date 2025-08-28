#!/bin/bash

# SAGE Issues 管理工具 - 简化版主入口
# 专注于核心的三大功能：下载、AI整理、上传

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 检查GitHub Token
check_github_token() {
    local token_file="$PROJECT_ROOT/.github_token"
    
    # 检查环境变量
    if [ -n "$GITHUB_TOKEN" ]; then
        echo -e "${GREEN}✅ 检测到GitHub Token (环境变量)${NC}"
        return 0
    fi
    
    # 检查token文件
    if [ -f "$token_file" ]; then
        echo -e "${GREEN}✅ 检测到GitHub Token文件: $token_file${NC}"
        return 0
    fi
    
    # 没有找到token，显示创建指导
    echo -e "${RED}❌ 未找到GitHub Token！${NC}"
    echo "=================================="
    echo ""
    echo "为了使用GitHub API，您需要创建一个包含GitHub Personal Access Token的文件。"
    echo ""
    echo "📋 请按以下步骤操作："
    echo ""
    echo "1. 访问GitHub生成Personal Access Token:"
    echo "   https://github.com/settings/tokens"
    echo ""
    echo "2. 创建新的token，需要以下权限:"
    echo "   - repo (完整仓库访问权限)"
    echo "   - read:org (读取组织信息)"
    echo ""
    echo "3. 创建token文件:"
    echo '   echo "your_token_here" > '"$token_file"
    echo ""
    echo "4. 设置安全权限:"
    echo '   chmod 600 '"$token_file"
    echo ""
    echo "WARNING: Please keep your token safe and do not commit it to version control!"
    echo ""
    
    read -p "是否要现在创建token文件？(y/N): " response
    case "$response" in
        [yY]|[yY][eE][sS])
            echo ""
            read -p "请输入您的GitHub Token: " token
            if [ -n "$token" ]; then
                echo "$token" > "$token_file"
                chmod 600 "$token_file"
                echo -e "${GREEN}✅ Token文件已创建: $token_file${NC}"
                echo "Token设置完成，可以继续使用。"
                return 0
            else
                echo -e "${RED}❌ 未输入token，将使用匿名访问（功能受限）${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${YELLOW}⚠️ 将使用匿名访问GitHub API（功能受限）${NC}"
            return 1
            ;;
    esac
}

show_main_menu() {
    clear
    echo -e "${CYAN}🎯 SAGE Issues 管理工具${NC}"
    echo "=============================="
    
    # 显示GitHub Token状态
    if [ -n "$GITHUB_TOKEN" ] || [ -f "$PROJECT_ROOT/.github_token" ]; then
        echo -e "${GREEN}✅ GitHub Token: 已配置${NC}"
    else
        echo -e "${YELLOW}⚠️ GitHub Token: 未配置 (功能受限)${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}核心功能:${NC}"
    echo ""
    echo -e "  1. 📥 下载远端Issues"
    echo -e "  2. 📝 手动管理Issues"
    echo -e "  3. 🤖 AI智能整理Issues" 
    echo -e "  4. 📤 上传Issues到远端"
    echo -e "  5. 🚪 退出"
    echo ""
}

download_menu() {
    while true; do
        clear
        echo -e "${BLUE}📥 下载远端Issues${NC}"
        echo "===================="
        echo ""
        echo "  1. 下载所有Issues"
        echo "  2. 下载开放的Issues"
        echo "  3. 下载已关闭的Issues"
        echo "  4. 返回主菜单"
        echo ""
        read -p "请选择 (1-4): " choice
        
        case $choice in
            1) download_all_issues ;;
            2) download_open_issues ;;
            3) download_closed_issues ;;
            4) break ;;
            *) echo -e "${RED}❌ 无效选择${NC}"; sleep 1 ;;
        esac
    done
}

ai_menu() {
    while true; do
        clear
        echo -e "${BLUE}🤖 AI智能整理Issues${NC}"
        echo "======================"
        echo ""
        echo "  1. AI分析重复Issues"
        echo "  2. AI优化标签分类"
        echo "  3. AI评估优先级"
        echo "  4. AI综合分析报告"
        echo "  5. 返回主菜单"
        echo ""
        read -p "请选择 (1-5): " choice
        
        case $choice in
            1) ai_analyze_duplicates ;;
            2) ai_optimize_labels ;;
            3) ai_evaluate_priority ;;
            4) ai_comprehensive_analysis ;;
            5) break ;;
            *) echo -e "${RED}❌ 无效选择${NC}"; sleep 1 ;;
        esac
    done
}

upload_menu() {
    while true; do
        clear
        echo -e "${BLUE}📤 上传Issues到远端${NC}"
        echo "===================="
        echo ""
        echo "  1. 同步所有修改"
        echo "  2. 同步标签更新"
        echo "  3. 同步状态更新"
        echo "  4. 预览待同步更改"
        echo "  5. 返回主菜单"
        echo ""
        read -p "请选择 (1-5): " choice
        
        case $choice in
            1) sync_all_changes ;;
            2) sync_label_changes ;;
            3) sync_status_changes ;;
            4) preview_changes ;;
            5) break ;;
            *) echo -e "${RED}❌ 无效选择${NC}"; sleep 1 ;;
        esac
    done
}

issues_management_menu() {
    while true; do
        clear
        echo -e "${BLUE}📝 手动管理Issues${NC}"
        echo "=================="
        echo ""
        echo "  1. 📊 查看Issues统计"
        echo "  2. 🏷️ 标签管理"
        echo "  3. 👥 团队分析"
        echo "  4. ✨ 创建新Issue"
        echo "  5. 📋 项目管理"
        echo "  6. 🔍 搜索和过滤"
        echo "  7. 返回主菜单"
        echo ""
        read -p "请选择 (1-7): " choice
        
        case $choice in
            1) show_issues_statistics ;;
            2) label_management ;;
            3) team_analysis ;;
            4) create_new_issue ;;
            5) project_management ;;
            6) search_and_filter ;;
            7) break ;;
            *) echo -e "${RED}❌ 无效选择${NC}"; sleep 1 ;;
        esac
    done
}

# 下载功能实现
download_all_issues() {
    echo "📥 正在下载所有Issues..."
    cd "$SCRIPT_DIR"
    python3 _scripts/download_issues.py --state=all
    read -p "按Enter键继续..."
}

download_open_issues() {
    echo "📥 正在下载开放的Issues..."
    cd "$SCRIPT_DIR"
    python3 _scripts/download_issues.py --state=open
    read -p "按Enter键继续..."
}

download_closed_issues() {
    echo "📥 正在下载已关闭的Issues..."
    cd "$SCRIPT_DIR"
    python3 _scripts/download_issues.py --state=closed
    read -p "按Enter键继续..."
}

# AI功能实现
ai_analyze_duplicates() {
    echo "🤖 AI分析重复Issues..."
    cd "$SCRIPT_DIR"
    python3 _scripts/ai_analyzer.py --mode=duplicates
    read -p "按Enter键继续..."
}

ai_optimize_labels() {
    echo "🤖 AI优化标签分类..."
    cd "$SCRIPT_DIR"
    python3 _scripts/ai_analyzer.py --mode=labels
    read -p "按Enter键继续..."
}

ai_evaluate_priority() {
    echo "🤖 AI评估优先级..."
    cd "$SCRIPT_DIR"
    python3 _scripts/ai_analyzer.py --mode=priority
    read -p "按Enter键继续..."
}

ai_comprehensive_analysis() {
    echo "🤖 AI综合分析报告..."
    cd "$SCRIPT_DIR"
    python3 _scripts/ai_analyzer.py --mode=comprehensive
    read -p "按Enter键继续..."
}

# 上传功能实现
sync_all_changes() {
    echo "📤 同步所有修改到远端..."
    cd "$SCRIPT_DIR"
    python3 _scripts/sync_issues.py --all
    read -p "按Enter键继续..."
}

sync_label_changes() {
    echo "📤 同步标签更新..."
    cd "$SCRIPT_DIR"
    python3 _scripts/sync_issues.py --labels-only
    read -p "按Enter键继续..."
}

sync_status_changes() {
    echo "📤 同步状态更新..."
    cd "$SCRIPT_DIR"
    python3 _scripts/sync_issues.py --status-only
    read -p "按Enter键继续..."
}

preview_changes() {
    echo "🔍 预览待同步更改..."
    cd "$SCRIPT_DIR"
    python3 _scripts/sync_issues.py --preview
    read -p "按Enter键继续..."
}

# Issues管理功能实现
show_issues_statistics() {
    echo "📊 显示Issues统计信息..."
    cd "$SCRIPT_DIR"
    python3 _scripts/issues_manager.py --action=statistics
    read -p "按Enter键继续..."
}

label_management() {
    echo "🏷️ 手动标签管理..."
    echo "可手动编辑标签文件: issues_workspace/by_label/"
    echo "或直接修改单个issue的标签属性"
    read -p "按Enter键继续..."
}

team_analysis() {
    echo "👥 团队分析..."
    cd "$SCRIPT_DIR"
    python3 _scripts/issues_manager.py --action=team
    read -p "按Enter键继续..."
}

create_new_issue() {
    echo "✨ 创建新Issue..."
    cd "$SCRIPT_DIR"
    python3 _scripts/issues_manager.py --action=create
    read -p "按Enter键继续..."
}

project_management() {
    echo "📋 项目管理..."
    cd "$SCRIPT_DIR"
    python3 _scripts/issues_manager.py --action=project
    read -p "按Enter键继续..."
}

search_and_filter() {
    echo "🔍 手动搜索和过滤..."
    echo "可手动浏览以下目录结构："
    echo "- issues_workspace/issues/ (所有issue文件)"
    echo "- issues_workspace/by_label/ (按标签分类)"
    echo "建议使用VS Code的搜索功能进行精确搜索"
    read -p "按Enter键继续..."
}

# 启动时检查GitHub Token
echo -e "${CYAN}正在初始化SAGE Issues管理工具...${NC}"
check_github_token
echo ""

# 主循环
while true; do
    show_main_menu
    read -p "请选择功能 (1-5): " choice
    echo ""
    
    case $choice in
        1) 
            download_menu
            ;;
        2) 
            issues_management_menu
            ;;
        3) 
            ai_menu
            ;;
        4) 
            upload_menu
            ;;
        5) 
            echo -e "${GREEN}👋 感谢使用SAGE Issues管理工具！${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ 无效选择，请输入1-5${NC}"
            sleep 1
            ;;
    esac
done
