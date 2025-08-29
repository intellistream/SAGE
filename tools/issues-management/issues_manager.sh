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
        return 0
    fi
    
    # 检查token文件
    if [ -f "$token_file" ]; then
        return 0
    fi
    
    return 1
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
    echo ""
    echo -e "${BLUE}📥 数据操作:${NC}"
    echo "  1. 📥 下载远端Issues"
    echo "  2. 📤 上传Issues到远端"
    echo ""
    echo -e "${BLUE}🔧 Issues管理:${NC}"
    echo "  3. � 查看Issues统计"
    echo "  4. 🏷️ 标签管理"
    echo "  5. ✨ 创建新Issue"
    echo ""
    echo -e "${BLUE}🚀 项目移动:${NC}"
    echo "  6. 🏷️ 暂存移动计划"
    echo "  7. 👀 预览移动计划"
    echo "  8. ✅ 执行移动计划"
    echo ""
    echo -e "${BLUE}👥 团队管理:${NC}"
    echo "  9. 👥 团队成员分析"
    echo "  10. 🔍 检查用户团队归属"
    echo ""
    echo -e "${BLUE}🔄 内容同步:${NC}"
    echo "  11. � 预览内容差异"
    echo "  12. ✅ 同步Issues内容"
    echo ""
    echo -e "${BLUE}🤖 AI功能:${NC}"
    echo "  13. 🤖 AI智能整理Issues"
    echo ""
    echo -e "${BLUE}⚙️ 系统:${NC}"
    echo "  14. ⚙️ 系统设置"
    echo "  15. 🚪 退出"
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
    echo "🏷️ 标签管理..."
    
    # 显示标签统计 - 使用Python脚本获取准确统计
    echo ""
    echo "📊 当前标签分布:"
    echo "=================="
    
    # 调用Python脚本获取最新的标签统计
    cd "$SCRIPT_DIR"
    python3 -c "
import sys
sys.path.insert(0, '.')
from issues_manager import SageIssuesManager

manager = SageIssuesManager()
manager._load_issues()
stats = manager._generate_statistics()

print('从Issues内容统计的标签分布:')
if stats['labels']:
    # 排序并显示所有标签
    sorted_labels = sorted(stats['labels'].items(), key=lambda x: x[1], reverse=True)
    for label, count in sorted_labels:
        if label != '未分配':  # 跳过未分配
            print(f'  {label:<25}: {count:>3d} issues')
    
    total_labeled = sum(count for label, count in stats['labels'].items() if label != '未分配')
    unlabeled = stats['labels'].get('未分配', 0)
    print(f'')
    print(f'  📊 总计: {total_labeled} 个已标记, {unlabeled} 个未标记')
else:
    print('  ❌ 没有找到标签信息')
" 2>/dev/null || {
        echo "❌ 无法加载标签统计，请确保Issues数据已下载"
    }
    
    echo ""
    echo "🛠️ 标签管理选项:"
    echo "=================="
    echo "  1. 📁 打开标签目录 (文件浏览器)"
    echo "  2. 🔍 查看特定标签的Issues"
    echo "  3. 📝 编辑Issue标签"
    echo "  4. 📊 导出标签报告"
    echo "  5. 🔄 刷新标签分类"
    echo "  6. 返回"
    echo ""
    
    read -p "请选择操作 (1-6): " label_choice
    
    case $label_choice in
        1)
            if command -v xdg-open >/dev/null 2>&1; then
                echo "📁 正在打开标签目录..."
                xdg-open "$label_dir" 2>/dev/null &
            elif command -v open >/dev/null 2>&1; then
                echo "📁 正在打开标签目录..."
                open "$label_dir" 2>/dev/null &
            else
                echo "📁 标签目录路径: $label_dir"
                echo "请手动在文件浏览器中打开此目录"
            fi
            ;;
        2)
            echo ""
            echo "可用标签:"
            select label_name in $(ls "$label_dir" 2>/dev/null); do
                if [ -n "$label_name" ]; then
                    echo ""
                    echo "🏷️ 标签 '$label_name' 下的Issues:"
                    echo "====================================="
                    find "$label_dir/$label_name" -name "*.md" 2>/dev/null | head -10 | while read issue_file; do
                        issue_name=$(basename "$issue_file" .md)
                        echo "  - $issue_name"
                    done
                    echo ""
                    break
                else
                    echo "❌ 无效选择"
                fi
            done
            ;;
        3)
            echo "📝 Issue标签编辑功能"
            echo "💡 提示: 可以直接编辑 issues_workspace/issues/ 目录下的.md文件"
            echo "      修改文件开头的标签字段，然后运行刷新命令"
            ;;
        4)
            echo "📊 正在生成标签报告..."
            report_file="$SCRIPT_DIR/output/label_report_$(date +%Y%m%d_%H%M%S).md"
            mkdir -p "$SCRIPT_DIR/output"
            
            echo "# 标签分布报告" > "$report_file"
            echo "" >> "$report_file"
            echo "生成时间: $(date)" >> "$report_file"
            echo "" >> "$report_file"
            echo "## 标签统计" >> "$report_file"
            echo "" >> "$report_file"
            
            for label_folder in "$label_dir"/*; do
                if [ -d "$label_folder" ]; then
                    label_name=$(basename "$label_folder")
                    count=$(find "$label_folder" -name "*.md" 2>/dev/null | wc -l)
                    echo "- **$label_name**: $count issues" >> "$report_file"
                fi
            done
            
            echo ""
            echo "✅ 报告已生成: $report_file"
            ;;
        5)
            echo "🔄 正在刷新标签分类..."
            cd "$SCRIPT_DIR"
            if [ -f "_scripts/download_issues.py" ]; then
                python3 _scripts/download_issues.py --refresh-labels-only 2>/dev/null || \
                echo "⚠️ 标签刷新需要实现 --refresh-labels-only 选项"
            else
                echo "⚠️ 需要重新运行下载脚本来刷新标签分类"
            fi
            ;;
        6|*)
            echo "返回上级菜单..."
            ;;
    esac
    
    if [ "$label_choice" != "6" ] && [ -n "$label_choice" ]; then
        echo ""
        read -p "按Enter键继续..."
    fi
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
    echo ""
    echo "🎯 项目移动选项:"
    echo "=================="
    echo "  1. 🔍 扫描所有仓库Issues (生成并可选执行移动计划)"
    echo "  2. 📦 扫描组织项目#6 (清理项目中的Issues分配)"
    echo "  3. 返回"
    echo ""
    
    read -p "请选择操作 (1-2): " project_choice
    
    case $project_choice in
        1)
            echo ""
            echo "🔍 扫描所有仓库Issues模式"
            echo "=========================="
            echo "此模式会扫描 https://github.com/intellistream/SAGE/issues 中的所有Issues"
            echo "根据作者的团队归属来建议项目分配"
            echo ""
            
            read -p "🔢 请输入要处理的Issues数量 (0表示全部处理): " limit_count
            
            # 验证输入
            if ! [[ "$limit_count" =~ ^[0-9]+$ ]]; then
                echo "❌ 请输入有效的数字"
                return 1
            fi
            
            echo ""
            echo "🚀 开始扫描所有仓库Issues..."
            echo "============================"
            
            cd "$SCRIPT_DIR/_scripts/helpers"
            
            # 构建命令 - 只扫描，不执行
            if [ "$limit_count" = "0" ]; then
                echo "📋 处理模式: 扫描全部Issues"
                plan_output=$(python3 project_manage.py --scan-all)
            else
                echo "📋 处理模式: 扫描前 $limit_count 个Issues"
                plan_output=$(python3 project_manage.py --scan-all --limit $limit_count)
            fi
            
            scan_result=$?
            echo "$plan_output"
            
            if [ $scan_result -eq 0 ]; then
                # 提取计划文件路径
                plan_file=$(echo "$plan_output" | grep "计划已写入:" | sed 's/.*计划已写入: \([^ ]*\).*/\1/')
                
                if [ -n "$plan_file" ] && [ -f "$plan_file" ]; then
                    echo ""
                    echo "✅ 仓库Issues扫描完成！移动计划已生成。"
                    echo ""
                    echo "🤔 是否要立即执行移动计划？"
                    echo "   ⚠️  警告: 这将实际修改GitHub上的项目分配"
                    echo ""
                    read -p "确认执行？ (y/N): " confirm_apply
                    
                    if [[ "$confirm_apply" =~ ^[Yy]$ ]]; then
                        echo ""
                        echo "⚡ 执行移动计划..."
                        echo "=================="
                        
                        # 使用保存的计划文件执行，避免重新扫描
                        python3 project_manage.py --load-plan "$plan_file"
                        
                        apply_result=$?
                        if [ $apply_result -eq 0 ]; then
                            echo ""
                            echo "🎉 移动计划执行完成！"
                        else
                            echo ""
                            echo "❌ 移动计划执行失败，请检查错误信息"
                        fi
                    else
                        echo ""
                        echo "📋 移动计划已保存: $plan_file"
                        echo "💡 稍后可运行: python3 project_manage.py --load-plan \"$plan_file\""
                    fi
                else
                    echo "❌ 无法找到生成的计划文件"
                fi
            else
                echo "❌ 扫描失败，请检查错误信息"
            fi
            ;;
        2)
            echo ""
            echo "📦 扫描组织项目#6模式"
            echo "===================="
            echo "此模式只扫描已在组织项目#6中的Issues"
            echo "主要用于清理 https://github.com/orgs/intellistream/projects/6"
            echo ""
            
            read -p "🔢 请输入要处理的Issues数量 (0表示全部处理): " limit_count
            
            # 验证输入
            if ! [[ "$limit_count" =~ ^[0-9]+$ ]]; then
                echo "❌ 请输入有效的数字"
                return 1
            fi
            
            echo ""
            echo "🚀 开始扫描组织项目#6..."
            echo "======================"
            
            cd "$SCRIPT_DIR/_scripts/helpers"
            
            # 使用项目模式（默认）- 只扫描，不执行
            if [ "$limit_count" = "0" ]; then
                echo "📋 处理模式: 扫描项目中全部Issues"
                plan_output=$(python3 project_manage.py --scan-project)
            else
                echo "📋 处理模式: 扫描项目中前 $limit_count 个Issues"
                plan_output=$(python3 project_manage.py --scan-project --limit $limit_count)
            fi
            
            scan_result=$?
            echo "$plan_output"
            
            if [ $scan_result -eq 0 ]; then
                # 提取计划文件路径
                plan_file=$(echo "$plan_output" | grep "计划已写入:" | sed 's/.*计划已写入: \([^ ]*\).*/\1/')
                
                if [ -n "$plan_file" ] && [ -f "$plan_file" ]; then
                    echo ""
                    echo "✅ 项目Issues扫描完成！移动计划已生成。"
                    echo ""
                    echo "🤔 是否要立即执行移动计划？"
                    echo "   ⚠️  警告: 这将实际修改GitHub上的项目分配"
                    echo ""
                    read -p "确认执行？ (y/N): " confirm_apply
                    
                    if [[ "$confirm_apply" =~ ^[Yy]$ ]]; then
                        echo ""
                        echo "⚡ 执行移动计划..."
                        echo "=================="
                        
                        # 使用保存的计划文件执行，避免重新扫描
                        python3 project_manage.py --load-plan "$plan_file"
                        
                        apply_result=$?
                        if [ $apply_result -eq 0 ]; then
                            echo ""
                            echo "🎉 移动计划执行完成！"
                        else
                            echo ""
                            echo "❌ 移动计划执行失败，请检查错误信息"
                        fi
                    else
                        echo ""
                        echo "📋 移动计划已保存: $plan_file"
                        echo "💡 稍后可运行: python3 project_manage.py --load-plan \"$plan_file\""
                    fi
                else
                    echo "❌ 无法找到生成的计划文件"
                fi
            else
                echo "❌ 扫描失败，请检查错误信息"
            fi
            ;;
        3)
            return
            ;;
        *)
            echo "❌ 无效选择，请输入1-2"
            ;;
    esac
    
    echo ""
    read -p "按Enter键继续..."
}

apply_project_moves() {
    echo "✅ 执行移动计划..."
    echo ""
    echo -e "${YELLOW}⚠️ 警告: 这将对GitHub进行实际修改${NC}"
    echo ""
    read -p "确认执行移动计划? (y/N): " confirm
    
    if [[ $confirm =~ ^[Yy]$ ]]; then
        cd "$SCRIPT_DIR"
        python3 _scripts/sync_issues.py --apply-plan --confirm
    else
        echo "取消操作"
    fi
    read -p "按Enter键继续..."
}

check_user_team() {
    echo "🔍 检查特定用户的团队归属..."
    echo ""
    read -p "输入GitHub用户名: " username
    
    if [ -n "$username" ]; then
        cd "$SCRIPT_DIR"
        python3 - <<EOF
import sys
from pathlib import Path
sys.path.insert(0, '_scripts/helpers')

from project_manage import IssueProjectMover

mover = IssueProjectMover()
print(f"\n=== 用户 '$username' 的团队检查 ===")

for team_slug in mover.target_teams.keys():
    try:
        is_member = mover.is_user_in_team('$username', team_slug)
        project_num = mover.target_teams[team_slug]
        status = "✅" if is_member else "❌"
        print(f"{status} 团队 '{team_slug}' (项目{project_num}): {is_member}")
    except Exception as e:
        print(f"❌ 团队 '{team_slug}' 检查出错: {e}")
EOF
    else
        echo "用户名不能为空"
    fi
    read -p "按Enter键继续..."
}

show_move_statistics() {
    echo "📊 查看移动统计..."
    cd "$SCRIPT_DIR"
    if [ -d "output" ]; then
        echo -e "${GREEN}=== 移动计划文件 ===${NC}"
        ls -lah output/project_move_plan_*.json 2>/dev/null | tail -5 || echo "无移动计划文件"
        
        latest_plan=$(ls -t output/project_move_plan_*.json 2>/dev/null | head -1)
        if [ -n "$latest_plan" ]; then
            echo ""
            echo -e "${GREEN}=== 最新计划统计 ===${NC}"
            python3 -c "
import json
with open('$latest_plan', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f'计划项目数: {len(data)}')
teams = {}
for item in data:
    team = item.get('to_team', 'unknown')
    teams[team] = teams.get(team, 0) + 1
print('按团队分布:')
for team, count in teams.items():
    print(f'  {team}: {count}')
"
        fi
    else
        echo "无输出目录"
    fi
    read -p "按Enter键继续..."
}

# 内容同步功能实现
preview_content_diff() {
    echo "🔍 预览内容差异..."
    echo ""
    read -p "输入检查数量限制 (默认5): " limit
    
    if [ -z "$limit" ]; then
        limit=5
    fi
    
    cd "$SCRIPT_DIR"
    python3 _scripts/sync_issues.py --content-preview --content-limit "$limit"
    read -p "按Enter键继续..."
}

sync_content_changes() {
    echo "📝 同步标题和正文..."
    echo ""
    echo -e "${YELLOW}⚠️ 警告: 这将修改GitHub上的Issues内容${NC}"
    echo ""
    read -p "确认同步内容更改? (y/N): " confirm
    
    if [[ $confirm =~ ^[Yy]$ ]]; then
        cd "$SCRIPT_DIR"
        python3 _scripts/sync_issues.py --apply-content --confirm
    else
        echo "取消操作"
    fi
    read -p "按Enter键继续..."
}

sync_label_updates() {
    echo "🏷️ 同步标签..."
    echo "此功能包含在内容同步中"
    preview_content_diff
}

view_sync_plans() {
    echo "📋 查看同步计划..."
    cd "$SCRIPT_DIR"
    if [ -d "output" ]; then
        echo -e "${GREEN}=== 同步计划文件 ===${NC}"
        ls -lah output/content_sync_plan_*.json 2>/dev/null | tail -5 || echo "无同步计划文件"
        
        latest_plan=$(ls -t output/content_sync_plan_*.json 2>/dev/null | head -1)
        if [ -n "$latest_plan" ]; then
            echo ""
            echo -e "${GREEN}=== 最新同步计划统计 ===${NC}"
            python3 -c "
import json
with open('$latest_plan', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f'待同步Issue数: {len(data)}')
changes = {}
for item in data:
    for change in item.get('changes', []):
        field = change.get('field', 'unknown')
        changes[field] = changes.get(field, 0) + 1
print('变更类型分布:')
for field, count in changes.items():
    print(f'  {field}: {count}')
"
        fi
    else
        echo "无输出目录"
    fi
    read -p "按Enter键继续..."
}

apply_sync_plan() {
    echo "✅ 执行同步计划..."
    echo ""
    echo -e "${YELLOW}⚠️ 警告: 这将对GitHub进行实际修改${NC}"
    echo ""
    read -p "确认执行同步计划? (y/N): " confirm
    
    if [[ $confirm =~ ^[Yy]$ ]]; then
        cd "$SCRIPT_DIR"
        python3 _scripts/sync_issues.py --apply-content --confirm
    else
        echo "取消操作"
    fi
    read -p "按Enter键继续..."
}

# 项目统计功能
project_statistics() {
    echo "📈 项目统计分析..."
    cd "$SCRIPT_DIR"
    python3 _scripts/issues_manager.py --action=project
    read -p "按Enter键继续..."
}

# 获取团队成员
get_team_members() {
    echo "👥 获取团队成员信息..."
    cd "$SCRIPT_DIR"
    python3 _scripts/helpers/get_team_members.py
    read -p "按Enter键继续..."
}

# 查看项目计划
view_project_plans() {
    echo "📋 查看项目移动计划..."
    cd "$SCRIPT_DIR"
    if [ -d "output" ]; then
        echo -e "${GREEN}=== 项目移动计划文件 ===${NC}"
        ls -lah output/project_move_plan_*.json 2>/dev/null || echo "无项目移动计划文件"
        
        echo ""
        echo -e "${GREEN}=== 内容同步计划文件 ===${NC}"
        ls -lah output/content_sync_plan_*.json 2>/dev/null || echo "无内容同步计划文件"
    else
        echo "无输出目录"
    fi
    read -p "按Enter键继续..."
}

# 主循环
while true; do
    show_main_menu
    read -p "请选择功能 (1-15): " choice
    echo ""
    
    case $choice in
        1) 
            download_menu
            ;;
        2) 
            upload_menu
            ;;
        3) 
            show_issues_statistics
            ;;
        4) 
            label_management
            ;;
        5) 
            create_new_issue
            ;;
        6) 
            stage_project_moves
            ;;
        7) 
            preview_project_moves
            ;;
        8) 
            apply_project_moves
            ;;
        9) 
            team_analysis
            ;;
        10) 
            check_user_team
            ;;
        11) 
            preview_content_diff
            ;;
        12) 
            sync_content_changes
            ;;
        13) 
            ai_menu
            ;;
        14) 
            system_settings
            ;;
        15) 
            echo -e "${GREEN}👋 感谢使用SAGE Issues管理工具！${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ 无效选择，请输入1-15${NC}"
            sleep 1
            ;;
    esac
done

# 系统设置菜单
system_settings() {
    echo -e "${BLUE}⚙️ 系统设置${NC}"
    echo "============"
    echo ""
    echo "  1. 🔄 刷新团队成员缓存"
    echo "  2. 📋 查看boards映射配置"
    echo "  3. 👥 查看团队成员列表"
    echo "  4. 🧹 清理缓存文件"
    echo "  5. 📊 显示元数据统计"
    echo "  6. 📋 查看项目移动计划"
    echo "  7. 📊 查看移动统计"
    echo "  8. 返回主菜单"
    echo ""
    read -p "请选择 (1-8): " choice
    
    case $choice in
        1) refresh_team_cache ;;
        2) view_boards_config ;;
        3) view_team_members ;;
        4) clean_cache_files ;;
        5) show_metadata_stats ;;
        6) view_project_plans ;;
        7) show_move_statistics ;;
        8) return ;;
        *) echo -e "${RED}❌ 无效选择${NC}"; sleep 1 ;;
    esac
}
