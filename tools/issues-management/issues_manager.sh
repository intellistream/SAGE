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

# 从config.py获取路径的helper函数
get_config_path() {
    local path_type="$1"
    # 只允许已知的安全类型
    case "$path_type" in
        workspace|output|metadata|issues)
            # 使用tail获取最后一行，过滤掉token加载信息
            python3 _scripts/helpers/get_paths.py "$path_type" 2>/dev/null | tail -1
            ;;
        *)
            echo -e "${RED}Error: Invalid path_type '$path_type'.${NC}" >&2
            return 1
            ;;
    esac
}

# 从config获取实际路径
ISSUES_WORKSPACE_PATH="$(get_config_path "workspace")"
ISSUES_OUTPUT_PATH="$(get_config_path "output")"
ISSUES_METADATA_PATH="$(get_config_path "metadata")"
ISSUES_DIR="$(get_config_path "issues")"

# 如果无法从config获取路径，使用备用路径
if [ -z "$ISSUES_WORKSPACE_PATH" ]; then
    ISSUES_WORKSPACE_PATH="$PROJECT_ROOT/output/issues-workspace"
fi
if [ -z "$ISSUES_OUTPUT_PATH" ]; then
    ISSUES_OUTPUT_PATH="$PROJECT_ROOT/output/issues-output"
fi
if [ -z "$ISSUES_METADATA_PATH" ]; then
    ISSUES_METADATA_PATH="$PROJECT_ROOT/output/issues-metadata"
fi
if [ -z "$ISSUES_DIR" ]; then
    ISSUES_DIR="$PROJECT_ROOT/output/issues-workspace/issues"
fi

# 检查GitHub Token
check_github_token() {
    local token_file="$PROJECT_ROOT/.github_token"
    
    # 检查环境变量
    if [ -n "$GITHUB_TOKEN" ]; then
        return 0
    fi
    
    # 检查token文件
    if [ -f "$token_file" ]; then
        return 0
    fi
    
    return 1
}

# 初始化metadata文件
# 检查metadata文件是否存在
check_metadata_files() {
    local boards_file="$ISSUES_METADATA_PATH/boards_metadata.json"
    local team_file="$ISSUES_METADATA_PATH/team_config.py"
    
    if [ ! -f "$boards_file" ] || [ ! -f "$team_file" ]; then
        return 1  # metadata文件不完整
    fi
    return 0  # metadata文件存在
}

# 自动初始化metadata文件
auto_initialize_metadata() {
    echo -e "${CYAN}🔍 检查metadata文件状态...${NC}"
    
    if ! check_metadata_files; then
        echo -e "${YELLOW}📋 检测到metadata文件缺失，正在自动初始化...${NC}"
        echo ""
        initialize_metadata_files
        echo ""
        
        # 再次检查是否成功
        if check_metadata_files; then
            echo -e "${GREEN}🎉 metadata文件自动初始化成功！${NC}"
        else
            echo -e "${YELLOW}⚠️ metadata文件初始化可能不完整，请检查${NC}"
        fi
    else
        echo -e "${GREEN}✅ metadata文件检查完成，所有文件正常${NC}"
    fi
}

initialize_metadata_files() {
    echo "  📋 初始化boards metadata..."
    cd "$SCRIPT_DIR"
    if python3 _scripts/helpers/get_boards.py > /dev/null 2>&1; then
        echo -e "    ${GREEN}✅ boards metadata初始化完成${NC}"
    else
        echo -e "    ${YELLOW}⚠️ boards metadata初始化失败，请稍后手动运行${NC}"
    fi
    
    echo "  👥 初始化team members metadata..."
    if python3 _scripts/helpers/get_team_members.py > /dev/null 2>&1; then
        echo -e "    ${GREEN}✅ team members metadata初始化完成${NC}"
    else
        echo -e "    ${YELLOW}⚠️ team members metadata初始化失败，请稍后手动运行${NC}"
    fi
    
    echo -e "${GREEN}✅ 所有metadata文件初始化完成${NC}"
}

# 首次使用向导
first_time_setup() {
    local token_file="$PROJECT_ROOT/.github_token"
    
    echo -e "${YELLOW}🌟 欢迎首次使用SAGE Issues管理工具！${NC}"
    echo "================================================"
    echo ""
    echo "为了正常使用所有功能，您需要配置GitHub Personal Access Token。"
    echo ""
    echo -e "${CYAN}📋 设置步骤：${NC}"
    echo ""
    echo "1. 访问GitHub生成Personal Access Token:"
    echo -e "   ${BLUE}https://github.com/settings/tokens${NC}"
    echo ""
    echo "2. 点击 'Generate new token' > 'Generate new token (classic)'"
    echo ""
    echo "3. 设置权限 (Scopes):"
    echo "   ✅ repo (完整仓库访问权限)"
    echo "   ✅ read:org (读取组织信息)"
    echo "   ✅ project (项目访问权限)"
    echo ""
    echo "4. 点击 'Generate token' 并复制生成的token"
    echo ""
    echo -e "${RED}⚠️ 重要提醒：${NC}"
    echo "   - Token只会显示一次，请立即复制保存"
    echo "   - 不要将token分享给他人或提交到版本控制系统"
    echo ""
    
    read -p "您已经获得GitHub Token了吗？(y/N): " has_token
    case "$has_token" in
        [yY]|[yY][eE][sS])
            echo ""
            echo "请粘贴您的GitHub Token:"
            read -s token  # -s 隐藏输入
            echo ""
            
            if [ -n "$token" ]; then
                # 验证token是否有效
                echo "🔍 验证Token有效性..."
                if curl -s -H "Authorization: token $token" \
                   -H "Accept: application/vnd.github.v3+json" \
                   https://api.github.com/user > /dev/null 2>&1; then
                    
                    echo "$token" > "$token_file"
                    chmod 600 "$token_file"
                    echo -e "${GREEN}✅ Token验证成功并已保存到: $token_file${NC}"
                    echo ""
                    
                    # 初始化metadata文件
                    echo "🔄 正在初始化metadata文件..."
                    initialize_metadata_files
                    
                    echo -e "${GREEN}🎉 设置完成！现在您可以使用所有功能了。${NC}"
                    echo ""
                    read -p "按回车键继续..." dummy
                    return 0
                else
                    echo -e "${RED}❌ Token验证失败，请检查Token是否正确${NC}"
                    echo ""
                    read -p "按回车键继续..." dummy
                    return 1
                fi
            else
                echo -e "${RED}❌ 未输入token${NC}"
                return 1
            fi
            ;;
        *)
            echo ""
            echo -e "${YELLOW}📝 您也可以稍后手动创建token文件：${NC}"
            echo "   echo 'your_token_here' > $token_file"
            echo "   chmod 600 $token_file"
            echo ""
            echo -e "${CYAN}💡 提示：没有token时可以使用匿名模式，但功能会受到限制。${NC}"
            echo ""
            read -p "按回车键继续..." dummy
            return 1
            ;;
    esac
}

show_main_menu() {
    clear
    echo -e "${CYAN}🎯 SAGE Issues 管理工具${NC}"
    echo "=============================="
    
    # 显示GitHub Token状态
    if check_github_token; then
        echo -e "${GREEN}✅ GitHub Token: 已配置${NC}"
    else
        echo -e "${YELLOW}⚠️ GitHub Token: 未配置 (功能受限)${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}核心功能:${NC}"
    echo ""
    echo -e "  1. 📝 手动管理Issues"
    echo -e "  2. 📥 下载远端Issues"
    echo -e "  3. 🤖 AI智能管理" 
    echo -e "  4. 📤 上传Issues到远端"
    echo ""
    echo -e "${CYAN}设置选项:${NC}"
    echo ""
    echo -e "  6. ⚙️ 配置管理"
    if ! check_github_token; then
        echo -e "  9. 🔑 配置GitHub Token"
    fi
    echo ""
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
        echo "  4. 🗑️ 清空本地Issues数据"
        echo "  5. 返回主菜单"
        echo ""
        echo -e "${CYAN}💡 提示: 选项1-3会在下载前自动询问是否清空本地数据${NC}"
        echo ""
        read -p "请选择 (1-5): " choice
        
        case $choice in
            1) download_all_issues ;;
            2) download_open_issues ;;
            3) download_closed_issues ;;
            4) clear_local_issues; read -p "按Enter键继续..." ;;
            5) break ;;
            *) echo -e "${RED}❌ 无效选择${NC}"; sleep 1 ;;
        esac
    done
}

ai_menu() {
    # 首先检查是否有本地数据
    local has_local_data=false
    if [ -d "$ISSUES_DIR" ] && [ "$(ls -A "$ISSUES_DIR" 2>/dev/null)" ]; then
        has_local_data=true
    fi
    
    while true; do
        clear
        echo -e "${BLUE}🤖 AI智能管理${NC}"
        echo "================"
        echo ""
        
        if [ "$has_local_data" = true ]; then
            echo -e "${GREEN}✅ 检测到本地Issues数据${NC}"
        else
            echo -e "${YELLOW}⚠️ 未检测到本地Issues数据，请先下载Issues${NC}"
        fi
        
        echo ""
        echo -e "${CYAN}📊 Copilot分析助手:${NC}"
        echo "  1. 📈 全部open issues分析"
        echo "  2. 📅 近一周的open issues分析"  
        echo "  3. 📆 近一个月的open issues分析"
        echo ""
        echo -e "${CYAN}🎯 AI智能操作:${NC}"
        echo "  4. 🤖 基于Project智能分配Issues"
        echo ""
        echo "  5. 📖 查看使用指南"
        
        if [ "$has_local_data" = false ]; then
            echo ""
            echo -e "${CYAN}  d. 📥 前往下载Issues数据${NC}"
        fi
        
        echo "  9. 返回主菜单"
        echo ""
        
        if [ "$has_local_data" = true ]; then
            read -p "请选择 (1-3, 9): " choice
        else
            read -p "请选择 (1-3, d, 9): " choice
        fi
        
        case $choice in
            1) 
                if [ "$has_local_data" = true ]; then
                    copilot_time_range_menu "all"
                else
                    echo -e "${RED}❌ 需要先下载Issues数据${NC}"
                    sleep 1
                fi
                ;;
            2) 
                if [ "$has_local_data" = true ]; then
                    copilot_time_range_menu "week"
                else
                    echo -e "${RED}❌ 需要先下载Issues数据${NC}"
                    sleep 1
                fi
                ;;
            3) 
                if [ "$has_local_data" = true ]; then
                    copilot_time_range_menu "month"
                else
                    echo -e "${RED}❌ 需要先下载Issues数据${NC}"
                    sleep 1
                fi
                ;;
            4)
                if [ "$has_local_data" = true ]; then
                    project_based_assign_menu
                else
                    echo -e "${RED}❌ 需要先下载Issues数据${NC}"
                    sleep 1
                fi
                ;;
            5)
                copilot_show_usage_guide
                ;;
            d|D)
                if [ "$has_local_data" = false ]; then
                    echo ""
                    echo "🔄 跳转到下载菜单..."
                    sleep 1
                    download_menu
                    # 重新检查数据状态
                    if [ -d "$ISSUES_DIR" ] && [ "$(ls -A "$ISSUES_DIR" 2>/dev/null)" ]; then
                        has_local_data=true
                    fi
                else
                    echo -e "${RED}❌ 无效选择${NC}"
                    sleep 1
                fi
                ;;
            9) 
                break 
                ;;
            *) 
                echo -e "${RED}❌ 无效选择${NC}"
                sleep 1 
                ;;
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
        echo "  1. 📊 查看Issues统计和分析"
        echo "  2. 🗂️ 自动归档已完成Issues"
        echo "  3. 📋 查看Issues更新记录"
        echo "  4. 返回主菜单"
        echo ""
        read -p "请选择 (1-4): " choice
        
        case $choice in
            1) show_issues_statistics ;;
            2) archive_completed_issues ;;
            3) show_update_history_menu ;;
            4) break ;;
            *) echo -e "${RED}❌ 无效选择${NC}"; sleep 1 ;;
        esac
    done
}

# 下载功能实现
clear_local_issues() {
    local issues_dir="$ISSUES_DIR"
    
    if [ -d "$issues_dir" ] && [ "$(ls -A "$issues_dir" 2>/dev/null)" ]; then
        echo -e "${YELLOW}🗑️ 发现本地Issues数据${NC}"
        echo "目录: $issues_dir"
        echo ""
        ls -la "$issues_dir" | head -10
        if [ $(ls -1 "$issues_dir" | wc -l) -gt 10 ]; then
            echo "... 以及更多文件"
        fi
        echo ""
        echo -e "${RED}⚠️ 警告: 此操作将删除所有本地Issues数据${NC}"
        echo ""
        read -p "确认清空本地Issues目录？ (y/N): " confirm_clear
        
        if [[ "$confirm_clear" =~ ^[Yy]$ ]]; then
            echo ""
            echo "🗑️ 正在清空本地Issues目录..."
            rm -rf "$issues_dir"/*
            echo -e "${GREEN}✅ 本地Issues目录已清空${NC}"
            echo ""
        else
            echo ""
            echo "❌ 取消清空操作"
            echo ""
        fi
    else
        echo -e "${CYAN}ℹ️ 本地Issues目录为空或不存在，无需清空${NC}"
        echo ""
    fi
}

download_all_issues() {
    clear_local_issues
    echo "📥 正在下载所有Issues..."
    cd "$SCRIPT_DIR"
    python3 _scripts/download_issues.py --state=all
    read -p "按Enter键继续..."
}

download_open_issues() {
    clear_local_issues
    echo "📥 正在下载开放的Issues..."
    cd "$SCRIPT_DIR"
    python3 _scripts/download_issues.py --state=open
    read -p "按Enter键继续..."
}

download_closed_issues() {
    clear_local_issues
    echo "📥 正在下载已关闭的Issues..."
    cd "$SCRIPT_DIR"
    python3 _scripts/download_issues.py --state=closed
    read -p "按Enter键继续..."
}

project_based_assign_menu() {
    # 首先检查是否有本地数据
    local has_local_data=false
    if [ -d "$ISSUES_DIR" ] && [ "$(ls -A "$ISSUES_DIR" 2>/dev/null)" ]; then
        has_local_data=true
    fi
    
    while true; do
        clear
        echo -e "${BLUE}🎯 基于Project智能分配Issues${NC}"
        echo "==============================="
        echo ""
        
        if [ "$has_local_data" = true ]; then
            echo -e "${GREEN}✅ 检测到本地Issues数据${NC}"
            
            # 统计当前分配情况 (使用正确的统计逻辑)
            local total_issues=0
            local assigned_issues=0
            local unassigned_issues=0
            
            for file in "$ISSUES_DIR"/open_*.md; do
                if [ -f "$file" ]; then
                    ((total_issues++))
                    
                    # 检查是否已分配 (与analyze_assignment_status使用相同逻辑)
                    if grep -A 1 "## 分配给" "$file" | grep -v "## 分配给" | grep -v "^--$" | grep -q "^未分配$\|^$"; then
                        ((unassigned_issues++))
                    else
                        ((assigned_issues++))
                    fi
                fi
            done
            
            echo "📊 当前状态:"
            echo "  - 总Issues数: $total_issues"
            echo "  - 已分配: $assigned_issues"
            echo "  - 未分配: $unassigned_issues"
        else
            echo -e "${YELLOW}⚠️ 未检测到本地Issues数据，请先下载Issues${NC}"
        fi
        
        echo ""
        echo -e "${CYAN}🛠️ 分配选项:${NC}"
        echo "  1. 🚀 执行完整智能分配 (包含错误检测与修复)"
        echo "  2. 📋 预览分配计划 (不实际修改文件)"
        echo "  3. 📊 分析当前分配状态"
        echo ""
        
        if [ "$has_local_data" = false ]; then
            echo -e "${CYAN}  d. 📥 前往下载Issues数据${NC}"
        fi
        
        echo "  9. 返回上级菜单"
        echo ""
        
        if [ "$has_local_data" = true ]; then
            read -p "请选择 (1-4, 9): " choice
        else
            read -p "请选择 (1-4, d, 9): " choice
        fi
        
        case $choice in
            1) 
                if [ "$has_local_data" = true ]; then
                    execute_project_based_assign
                else
                    echo -e "${RED}❌ 需要先下载Issues数据${NC}"
                    sleep 2
                fi
                ;;
            2) 
                if [ "$has_local_data" = true ]; then
                    preview_project_based_assign
                else
                    echo -e "${RED}❌ 需要先下载Issues数据${NC}"
                    sleep 2
                fi
                ;;
            3) 
                if [ "$has_local_data" = true ]; then
                    analyze_assignment_status
                else
                    echo -e "${RED}❌ 需要先下载Issues数据${NC}"
                    sleep 2
                fi
                ;;
            d|D)
                if [ "$has_local_data" = false ]; then
                    download_menu
                else
                    echo -e "${RED}❌ 无效选择${NC}"
                    sleep 1
                fi
                ;;
            9) break ;;
            *) echo -e "${RED}❌ 无效选择${NC}"; sleep 1 ;;
        esac
    done
}

execute_project_based_assign() {
    clear
    echo -e "${CYAN}🚀 执行完整智能分配 (包含错误检测与修复)${NC}"
    echo "================================================="
    echo ""
    echo -e "${CYAN}此功能将自动执行以下操作：${NC}"
    echo "  🔍 1. 检测错误分配的Issues (team与project不匹配)"
    echo "  🔧 2. 自动修复检测到的分配问题"
    echo "  🎯 3. 执行智能分配 (基于Project归属)"
    echo "  📊 4. 显示分配结果统计"
    echo ""
    echo -e "${YELLOW}⚠️ 此操作将修改Issues文件中的分配信息${NC}"
    echo ""
    read -p "确认执行完整智能分配？ (y/N): " confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${CYAN}🔍 步骤1: 检测错误分配的Issues...${NC}"
        cd "$SCRIPT_DIR"
        
        # 首先运行错误检测
        if python3 _scripts/helpers/fix_misplaced_issues.py --dry-run; then
            echo -e "${GREEN}✅ 错误检测完成${NC}"
            
            # 检查是否有生成的修复计划文件
            local fix_plan_files=($(ls -t "$ISSUES_OUTPUT_PATH"/issues_fix_plan_*.json 2>/dev/null))
            
            if [ ${#fix_plan_files[@]} -gt 0 ]; then
                local latest_plan="${fix_plan_files[0]}"
                echo -e "${YELLOW}⚠️ 发现需要修复的错误分配，自动执行修复...${NC}"
                echo ""
                echo -e "${CYAN}🔧 步骤2: 自动修复错误分配...${NC}"
                if python3 _scripts/helpers/execute_fix_plan.py "$latest_plan" --live; then
                    echo -e "${GREEN}✅ 错误分配修复完成${NC}"
                else
                    echo -e "${RED}❌ 错误分配修复失败${NC}"
                fi
            else
                echo -e "${GREEN}✅ 未发现错误分配的Issues${NC}"
                echo -e "${CYAN}📝 跳过步骤2: 无需修复${NC}"
            fi
        else
            echo -e "${RED}❌ 错误检测失败，继续执行智能分配...${NC}"
        fi
        
        echo ""
        echo -e "${CYAN}🎯 步骤3: 执行智能分配...${NC}"
        
        # 执行智能分配
        if python3 _scripts/project_based_assign.py --assign; then
            echo ""
            echo -e "${GREEN}✅ 智能分配完成！${NC}"
            echo ""
            echo -e "${CYAN}📊 步骤4: 显示分配结果统计...${NC}"
            
            # 自动显示分配统计
            local total=0
            local assigned=0
            local unassigned=0
            local by_team_kernel=0
            local by_team_middleware=0
            local by_team_apps=0
            local by_team_intellistream=0
            
            for file in "$ISSUES_DIR"/open_*.md; do
                if [ -f "$file" ]; then
                    ((total++))
                    
                    # 检查是否已分配
                    if grep -A 1 "## 分配给" "$file" | grep -v "## 分配给" | grep -v "^--$" | grep -q "^未分配$\|^$"; then
                        ((unassigned++))
                    else
                        ((assigned++))
                    fi
                    
                    # 统计按项目归属
                    if grep -q "sage-kernel" "$file"; then
                        ((by_team_kernel++))
                    elif grep -q "sage-middleware" "$file"; then
                        ((by_team_middleware++))
                    elif grep -q "sage-apps" "$file"; then
                        ((by_team_apps++))
                    elif grep -q "intellistream" "$file"; then
                        ((by_team_intellistream++))
                    fi
                fi
            done
            
            echo "📈 分配结果统计:"
            echo "  - 总Issues数: $total"
            echo "  - 已分配: $assigned"
            echo "  - 未分配: $unassigned"
            if [ $total -gt 0 ]; then
                echo "  - 分配率: $(( assigned * 100 / total ))%"
            fi
            echo ""
            echo "📊 按项目归属分布:"
            echo "  - intellistream: $by_team_intellistream issues"
            echo "  - sage-kernel: $by_team_kernel issues"
            echo "  - sage-middleware: $by_team_middleware issues"
            echo "  - sage-apps: $by_team_apps issues"
            echo ""
            
            if [ $unassigned -eq 0 ]; then
                echo -e "${GREEN}🎉 所有Issues都已成功分配！${NC}"
            else
                echo -e "${YELLOW}💡 还有 $unassigned 个Issues未分配，可能需要手动处理${NC}"
            fi
            
            echo ""
            echo -e "${CYAN}📤 自动同步分配结果到GitHub远端...${NC}"
            echo ""
            
            # 直接执行快速同步，避免多次确认
            echo "🚀 正在智能同步分配结果..."
            if python3 _scripts/sync_issues.py --apply-projects --auto-confirm; then
                echo -e "${GREEN}✅ 分配结果已成功同步到GitHub！${NC}"
            else
                echo -e "${YELLOW}⚠️ 同步过程中遇到问题，但本地分配已完成${NC}"
                echo "💡 您可以稍后通过上传菜单手动同步"
            fi
        else
            echo ""
            echo -e "${RED}❌ 智能分配失败${NC}"
        fi
        
        echo ""
        read -p "按Enter键继续..."
    else
        echo ""
        echo "❌ 已取消智能分配操作"
        sleep 1
    fi
}

preview_project_based_assign() {
    clear
    echo -e "${CYAN}📋 预览基于Project的分配计划${NC}"
    echo "==============================="
    echo ""
    echo "🔍 分析Issues并生成分配计划(不修改文件)..."
    cd "$SCRIPT_DIR"
    
    # 创建临时预览脚本
    cat > /tmp/preview_assign.py << 'EOF'
import sys
sys.path.insert(0, '_scripts')
from project_based_assign import *

def preview_assignment():
    print("🚀 开始分析Issues...")
    team_config = load_team_config()
    config = Config()
    issues_dir = config.workspace_path / "issues"
    
    if not issues_dir.exists():
        print("❌ Issues目录不存在")
        return
    
    files = sorted(list(issues_dir.glob("open_*.md")))
    print(f"📋 分析 {len(files)} 个issues...")
    
    assignments = []
    project_stats = {}
    workload = {}
    unassigned_issues = []
    
    for file_path in files[:10]:  # 只预览前10个
        issue_info = parse_issue_file(file_path)
        if not issue_info['number']:
            continue
        
        project_team = issue_info['project_team']
        if project_team:
            project_stats[project_team] = project_stats.get(project_team, 0) + 1
            assignee = select_assignee_by_expertise_and_workload(
                team_config, project_team, issue_info, workload
            )
            
            if assignee:
                workload[assignee] = workload.get(assignee, 0) + 1
                print(f"  Issue #{issue_info['number']}: {project_team} -> {assignee}")
                if issue_info['current_assignee'] != assignee:
                    print(f"    (从 {issue_info['current_assignee'] or '未分配'} 更改)")
            else:
                unassigned_issues.append(issue_info)
        else:
            unassigned_issues.append(issue_info)
    
    print(f"\n📊 项目分布预览:")
    for team, count in sorted(project_stats.items()):
        print(f"  {team}: {count} issues")
    
    if unassigned_issues:
        print(f"\n⚠️ {len(unassigned_issues)} 个issues无法分配")

if __name__ == "__main__":
    preview_assignment()
EOF
    
    python3 /tmp/preview_assign.py
    rm -f /tmp/preview_assign.py
    echo ""
    read -p "按Enter键继续..."
}

analyze_assignment_status() {
    clear
    echo -e "${CYAN}📊 分析当前分配状态${NC}"
    echo "======================"
    echo ""
    echo "🔍 正在分析当前Issues分配情况..."
    
    local total=0
    local assigned=0
    local unassigned=0
    local by_team_kernel=0
    local by_team_middleware=0
    local by_team_apps=0
    
    for file in "$ISSUES_DIR"/open_*.md; do
        if [ -f "$file" ]; then
            ((total++))
            
            # 检查是否已分配
            if grep -A 1 "## 分配给" "$file" | grep -v "## 分配给" | grep -v "^--$" | grep -q "^未分配$\|^$"; then
                ((unassigned++))
            else
                ((assigned++))
            fi
            
            # 统计按项目归属
            if grep -q "sage-kernel" "$file"; then
                ((by_team_kernel++))
            elif grep -q "sage-middleware" "$file"; then
                ((by_team_middleware++))
            elif grep -q "sage-apps" "$file"; then
                ((by_team_apps++))
            fi
        fi
    done
    
    echo "📈 总体统计:"
    echo "  - 总Issues数: $total"
    echo "  - 已分配: $assigned"
    echo "  - 未分配: $unassigned"
    echo "  - 分配率: $(( assigned * 100 / total ))%"
    echo ""
    echo "📊 按项目归属统计:"
    echo "  - sage-kernel: $by_team_kernel issues"
    echo "  - sage-middleware: $by_team_middleware issues"
    echo "  - sage-apps: $by_team_apps issues"
    echo ""
    
    if [ $unassigned -gt 0 ]; then
        echo -e "${YELLOW}💡 建议: 有 $unassigned 个未分配的Issues，可以使用智能分配功能${NC}"
    else
        echo -e "${GREEN}✅ 所有Issues都已分配！${NC}"
    fi
    
    echo ""
    read -p "按Enter键继续..."
}

# Copilot Issues分析功能实现
copilot_time_range_menu() {
    local time_filter="$1"
    local time_desc=""
    
    case "$time_filter" in
        "all") time_desc="全部" ;;
        "week") time_desc="近一周" ;;
        "month") time_desc="近一个月" ;;
        *) time_desc="未知" ;;
    esac
    
    while true; do
        clear
        echo -e "${BLUE}🤖 Copilot分析 - $time_desc 的Open Issues${NC}"
        echo "==========================================="
        echo ""
        echo -e "${CYAN}📊 按团队分组生成分析文档:${NC}"
        echo "  1. 🎯 生成综合分析文档 (所有团队概况)"
        echo "  2. 👥 生成所有团队详细文档"
        echo "  3. 📋 生成未分配Issues文档"
        echo "  4. 🔄 生成完整分析包 (推荐)"
        echo ""
        echo -e "${CYAN}🏷️ 按单个团队生成:${NC}"
        echo "  5. 📱 SAGE Apps团队文档"
        echo "  6. ⚙️ SAGE Kernel团队文档"
        echo "  7. 🔧 SAGE Middleware团队文档"
        echo ""
        echo "  8. 返回时间选择"
        echo ""
        read -p "请选择 (1-8): " choice
        
        case $choice in
            1) copilot_generate_comprehensive "$time_filter" ;;
            2) copilot_generate_teams "$time_filter" ;;
            3) copilot_generate_unassigned "$time_filter" ;;
            4) copilot_generate_all "$time_filter" ;;
            5) copilot_generate_single_team "sage-apps" "$time_filter" ;;
            6) copilot_generate_single_team "sage-kernel" "$time_filter" ;;
            7) copilot_generate_single_team "sage-middleware" "$time_filter" ;;
            8) break ;;
            *) echo -e "${RED}❌ 无效选择${NC}"; sleep 1 ;;
        esac
    done
}

copilot_generate_comprehensive() {
    local time_filter="${1:-all}"
    local time_desc=""
    
    case "$time_filter" in
        "all") time_desc="全部" ;;
        "week") time_desc="近一周" ;;
        "month") time_desc="近一个月" ;;
    esac
    
    echo "🎯 生成综合分析文档 ($time_desc)..."
    cd "$SCRIPT_DIR"
    python3 _scripts/copilot_issue_formatter.py --format=comprehensive --time="$time_filter"
    echo ""
    echo "✅ 综合分析文档已生成 (时间范围: $time_desc)"
    echo "💡 请将生成的文档内容复制到Copilot聊天窗口进行分析"
    read -p "按Enter键继续..."
}

copilot_generate_teams() {
    local time_filter="${1:-all}"
    local time_desc=""
    
    case "$time_filter" in
        "all") time_desc="全部" ;;
        "week") time_desc="近一周" ;;
        "month") time_desc="近一个月" ;;
    esac
    
    echo "👥 生成所有团队详细文档 ($time_desc)..."
    cd "$SCRIPT_DIR"
    python3 _scripts/copilot_issue_formatter.py --format=teams --time="$time_filter"
    echo ""
    echo "✅ 团队详细文档已生成 (时间范围: $time_desc)"
    echo "💡 可分别将各团队文档复制到Copilot进行针对性分析"
    read -p "按Enter键继续..."
}

copilot_generate_unassigned() {
    local time_filter="${1:-all}"
    local time_desc=""
    
    case "$time_filter" in
        "all") time_desc="全部" ;;
        "week") time_desc="近一周" ;;
        "month") time_desc="近一个月" ;;
    esac
    
    echo "📋 生成未分配Issues文档 ($time_desc)..."
    cd "$SCRIPT_DIR"
    python3 _scripts/copilot_issue_formatter.py --format=unassigned --time="$time_filter"
    echo ""
    echo "✅ 未分配Issues文档已生成 (时间范围: $time_desc)"
    echo "💡 将文档内容给Copilot分析如何分配这些Issues"
    read -p "按Enter键继续..."
}

copilot_generate_all() {
    local time_filter="${1:-all}"
    local time_desc=""
    
    case "$time_filter" in
        "all") time_desc="全部" ;;
        "week") time_desc="近一周" ;;
        "month") time_desc="近一个月" ;;
    esac
    
    echo "🔄 生成完整分析包 ($time_desc)..."
    cd "$SCRIPT_DIR"
    python3 _scripts/copilot_issue_formatter.py --format=all --time="$time_filter"
    echo ""
    echo "✅ 完整分析包已生成，包括："
    echo "   - 综合分析文档 (时间范围: $time_desc)"
    echo "   - 各团队详细文档"
    echo "   - 未分配Issues文档"
    echo "   - 使用指南"
    echo ""
    echo "💡 建议先从综合分析文档开始，再深入到具体团队"
    read -p "按Enter键继续..."
}

copilot_generate_single_team() {
    local team_name="$1"
    local time_filter="${2:-all}"
    local team_display_name=""
    local time_desc=""
    
    case "$team_name" in
        "sage-apps") team_display_name="SAGE Apps" ;;
        "sage-kernel") team_display_name="SAGE Kernel" ;;
        "sage-middleware") team_display_name="SAGE Middleware" ;;
        *) team_display_name="$team_name" ;;
    esac
    
    case "$time_filter" in
        "all") time_desc="全部" ;;
        "week") time_desc="近一周" ;;
        "month") time_desc="近一个月" ;;
    esac
    
    echo "📱 生成 $team_display_name 团队文档 ($time_desc)..."
    cd "$SCRIPT_DIR"
    python3 _scripts/copilot_issue_formatter.py --team="$team_name" --time="$time_filter"
    echo ""
    echo "✅ $team_display_name 团队文档已生成 (时间范围: $time_desc)"
    echo "💡 将文档内容给Copilot分析该团队的具体情况和建议"
    read -p "按Enter键继续..."
}

copilot_show_usage_guide() {
    echo "📖 Copilot使用指南"
    echo "=================="
    echo ""
    echo "🎯 使用流程："
    echo "1. 选择时间范围（全部/近一周/近一个月）"
    echo "2. 生成分析文档（选择分析类型）"
    echo "3. 打开VS Code Copilot聊天窗口"
    echo "4. 复制生成的文档内容到聊天窗口"
    echo "5. 向Copilot提出具体的分析问题"
    echo ""
    echo "⏰ 时间范围选项："
    echo "   - 全部: 所有open状态的issues"
    echo "   - 近一周: 最近7天创建的open issues"
    echo "   - 近一个月: 最近30天创建的open issues"
    echo ""
    echo "🤖 推荐的Copilot分析问题："
    echo ""
    echo "优先级分析："
    echo "   '请分析这些open issues，识别需要立即处理的高优先级问题'"
    echo ""
    echo "工作负载分析："
    echo "   '分析各团队的工作负载分布，是否存在不均衡？'"
    echo ""
    echo "问题分类："
    echo "   '将这些issues按类型分类并建议标签优化方案'"
    echo ""
    echo "重复性分析："
    echo "   '识别是否存在重复或相似的issues，哪些可以合并？'"
    echo ""
    echo "依赖关系："
    echo "   '分析issues之间的依赖关系，建议处理顺序'"
    echo ""
    echo "流程改进："
    echo "   '基于这些issues状态，建议项目管理改进方案'"
    echo ""
    echo "时间趋势分析："
    echo "   '分析近期issues的创建趋势和类型变化'"
    echo ""
    echo "📁 文档位置: $ISSUES_OUTPUT_PATH/"
    echo "   查看最新生成的以 'copilot_' 开头的文档"
    echo "   文档名包含时间范围标识: _week 或 _month"
    echo ""
    echo "💡 提示："
    echo "   - 可以同时分析多个团队的文档"
    echo "   - 根据Copilot建议制定具体行动计划"
    echo "   - 定期重新生成文档跟踪进度"
    echo "   - 使用时间过滤关注最新的问题"
    echo ""
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

# 自动归档已完成Issues
archive_completed_issues() {
    echo -e "${BLUE}🗂️ 自动归档已完成Issues${NC}"
    echo "=============================="
    echo ""
    echo "此功能将根据Issues完成时间自动归档："
    echo "  📋 一周内的已完成Issues → Done列"
    echo "  📦 超过一周但不到一个月 → Archive列"
    echo "  📚 超过一个月 → History列（如不存在将创建）"
    echo ""
    
    read -p "🤔 是否要先预览归档计划？ (Y/n): " preview_choice
    
    case $preview_choice in
        [nN]|[nN][oO])
            preview_flag=""
            ;;
        *)
            preview_flag="--preview"
            ;;
    esac
    
    echo ""
    echo "🚀 开始处理已完成Issues归档..."
    echo "============================"
    
    cd "$SCRIPT_DIR/_scripts/helpers"
    
    if [ -n "$preview_flag" ]; then
        echo "🔍 预览归档计划："
        python3 archive_completed_issues.py $preview_flag
        
        echo ""
        read -p "是否执行归档操作？ (y/N): " confirm_execute
        
        case $confirm_execute in
            [yY]|[yY][eE][sS])
                echo ""
                echo "⚡ 执行归档操作..."
                python3 archive_completed_issues.py
                ;;
            *)
                echo "📋 归档操作已取消"
                ;;
        esac
    else
        echo "⚡ 直接执行归档操作..."
        python3 archive_completed_issues.py
    fi
    
    echo ""
    read -p "按Enter键继续..."
}

# 查看Issues更新记录
show_update_history_menu() {
    while true; do
        clear
        echo -e "${BLUE}📋 Issues更新记录查看${NC}"
        echo "========================"
        echo ""
        echo "  1. 📋 列出所有有更新记录的Issues"
        echo "  2. 🔍 查看特定Issue的更新记录"
        echo "  3. ℹ️ 关于更新记录的说明"
        echo "  4. 返回上级菜单"
        echo ""
        read -p "请选择 (1-4): " choice
        
        case $choice in
            1) 
                echo -e "${CYAN}📋 正在扫描Issues更新记录...${NC}"
                echo ""
                cd "$SCRIPT_DIR"
                python3 _scripts/show_update_history.py
                echo ""
                read -p "按Enter键继续..."
                ;;
            2)
                echo ""
                read -p "🔍 请输入要查看的Issue编号: " issue_id
                if [[ "$issue_id" =~ ^[0-9]+$ ]]; then
                    echo ""
                    echo -e "${CYAN}📋 显示Issue #${issue_id}的更新记录...${NC}"
                    echo ""
                    cd "$SCRIPT_DIR"
                    python3 _scripts/show_update_history.py --issue-id "$issue_id"
                    echo ""
                    read -p "按Enter键继续..."
                else
                    echo -e "${RED}❌ 请输入有效的Issue编号${NC}"
                    sleep 1
                fi
                ;;
            3)
                clear
                echo -e "${BLUE}ℹ️ 关于更新记录的说明${NC}"
                echo "========================"
                echo ""
                echo -e "${CYAN}📝 更新记录的作用：${NC}"
                echo "  • 记录我们对每个Issue的本地管理操作"
                echo "  • 追踪Issue的下载、同步、修改历史"
                echo "  • 提供本地管理的审计轨迹"
                echo ""
                echo -e "${CYAN}🔧 设计原则：${NC}"
                echo "  • 更新记录是本地管理信息，不会同步到GitHub"
                echo "  • GitHub本身有完整的活动历史记录"
                echo "  • 这样避免污染GitHub上的原始Issue内容"
                echo ""
                echo -e "${CYAN}📊 查看GitHub活动历史：${NC}"
                echo "  • 在GitHub网页上查看Issue可以看到完整的活动历史"
                echo "  • 包括评论、标签变更、状态变更等所有操作"
                echo ""
                echo -e "${YELLOW}💡 如果需要在GitHub上记录管理操作，建议通过Issue评论的方式${NC}"
                echo ""
                read -p "按Enter键继续..."
                ;;
            4) 
                break 
                ;;
            *) 
                echo -e "${RED}❌ 无效选择${NC}"
                sleep 1 
                ;;
        esac
    done
}

# 配置管理菜单
config_management_menu() {
    while true; do
        clear
        echo -e "${BLUE}⚙️ 配置管理${NC}"
        echo "==============="
        echo ""
        echo "  1. 📋 查看当前配置"
        echo "  2. 🔄 交互式配置向导"
        echo "  3. 📤 更新记录同步设置"
        echo "  4. 💾 自动备份设置"
        echo "  5. 返回主菜单"
        echo ""
        read -p "请选择 (1-5): " choice
        
        case $choice in
            1)
                echo -e "${CYAN}📋 当前配置状态${NC}"
                echo ""
                cd "$SCRIPT_DIR"
                python3 _scripts/config_manager.py --show
                echo ""
                read -p "按Enter键继续..."
                ;;
            2)
                echo -e "${CYAN}🔄 交互式配置向导${NC}"
                echo ""
                cd "$SCRIPT_DIR"
                python3 _scripts/config_manager.py --interactive
                echo ""
                read -p "按Enter键继续..."
                ;;
            3)
                echo -e "${CYAN}📤 更新记录同步设置${NC}"
                echo "========================"
                echo ""
                echo "选择更新记录同步模式："
                echo "  on  - 将更新记录同步到GitHub (推荐)"
                echo "  off - 更新记录仅保存在本地"
                echo ""
                read -p "请选择 (on/off): " sync_choice
                
                case $sync_choice in
                    on|ON|On)
                        cd "$SCRIPT_DIR"
                        python3 _scripts/config_manager.py --sync-history on
                        ;;
                    off|OFF|Off)
                        cd "$SCRIPT_DIR"
                        python3 _scripts/config_manager.py --sync-history off
                        ;;
                    *)
                        echo -e "${RED}❌ 无效选择${NC}"
                        ;;
                esac
                echo ""
                read -p "按Enter键继续..."
                ;;
            4)
                echo -e "${CYAN}💾 自动备份设置${NC}"
                echo "=================="
                echo ""
                read -p "启用自动备份？ (on/off): " backup_choice
                
                case $backup_choice in
                    on|ON|On)
                        cd "$SCRIPT_DIR"
                        python3 _scripts/config_manager.py --auto-backup on
                        ;;
                    off|OFF|Off)
                        cd "$SCRIPT_DIR"
                        python3 _scripts/config_manager.py --auto-backup off
                        ;;
                    *)
                        echo -e "${RED}❌ 无效选择${NC}"
                        ;;
                esac
                echo ""
                read -p "按Enter键继续..."
                ;;
            5)
                break
                ;;
            *)
                echo -e "${RED}❌ 无效选择${NC}"
                sleep 1
                ;;
        esac
    done
}

# 启动时检查GitHub Token
# 检查是否首次使用
echo -e "${CYAN}正在初始化SAGE Issues管理工具...${NC}"

# 自动检查并初始化metadata文件
auto_initialize_metadata

if ! check_github_token; then
    echo ""
    echo -e "${YELLOW}⚠️ 检测到您是首次使用或未配置GitHub Token${NC}"
    echo ""
    read -p "是否要现在进行初始设置？(Y/n): " setup_now
    case "$setup_now" in
        [nN]|[nN][oO])
            echo -e "${CYAN}💡 您可以稍后通过主菜单的选项9来配置Token${NC}"
            ;;
        *)
            if first_time_setup; then
                echo ""
                echo -e "${GREEN}🎉 设置完成！正在重新检查Token状态...${NC}"
            fi
            ;;
    esac
fi

echo ""

# 主循环
while true; do
    show_main_menu
    
    # 根据是否有token调整提示
    if check_github_token; then
        read -p "请选择功能 (1-5): " choice
    else
        read -p "请选择功能 (1-5, 9): " choice
    fi
    echo ""
    
    case $choice in
        1) 
            issues_management_menu
            ;;
        2) 
            download_menu
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
        6)
            config_management_menu
            ;;
        9)
            if ! check_github_token; then
                echo -e "${CYAN}🔑 配置GitHub Token${NC}"
                echo "===================="
                echo ""
                first_time_setup
                echo ""
                read -p "按回车键返回主菜单..." dummy
            else
                echo -e "${YELLOW}❌ Token已配置，无需重复设置${NC}"
                sleep 1
            fi
            ;;
        "")
            # 空输入，重新显示菜单
            continue
            ;;
        *)
            if check_github_token; then
                echo -e "${RED}❌ 无效选择，请输入1-5${NC}"
            else
                echo -e "${RED}❌ 无效选择，请输入1-5或9${NC}"
            fi
            sleep 1
            ;;
    esac
done
