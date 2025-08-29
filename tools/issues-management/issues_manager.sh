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
    
    # 显示GitHub Token状态
    if check_github_token; then
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
    echo ""
    if ! check_github_token; then
        echo -e "${YELLOW}设置选项:${NC}"
        echo ""
        echo -e "  9. 🔑 配置GitHub Token"
        echo ""
    fi
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
        echo "  1. 📊 查看Issues统计和分析"
        echo "  2. 📋 项目管理"
        echo "  3. 返回主菜单"
        echo ""
        read -p "请选择 (1-3): " choice
        
        case $choice in
            1) show_issues_statistics ;;
            2) project_management ;;
            3) break ;;
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
    echo "🎯 项目管理选项:"
    echo "=================="
    echo "  1. � 生成移动计划 (仅扫描，不执行)"
    echo "  2. � 查看已有的移动计划"
    echo "  3. ✅ 执行移动计划"
    echo "  4. 返回"
    echo ""
    
    read -p "请选择操作 (1-3): " project_choice
    
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
            
            # 构建命令
            if [ "$limit_count" = "0" ]; then
                echo "📋 处理模式: 扫描全部Issues"
                python3 project_manage.py --scan-all
            else
                echo "📋 处理模式: 扫描前 $limit_count 个Issues"
                python3 project_manage.py --scan-all --limit $limit_count
            fi
            
            scan_result=$?
            echo ""
            
            if [ $scan_result -eq 0 ]; then
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
                    
                    if [ "$limit_count" = "0" ]; then
                        python3 project_manage.py --scan-all --apply
                    else
                        python3 project_manage.py --scan-all --apply --limit $limit_count
                    fi
                    
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
                    echo "📋 移动计划已保存，以供后续查看"
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
            
            # 使用项目模式（默认）
            if [ "$limit_count" = "0" ]; then
                echo "📋 处理模式: 扫描项目中全部Issues"
                python3 project_manage.py --scan-project
            else
                echo "📋 处理模式: 扫描项目中前 $limit_count 个Issues"
                python3 project_manage.py --scan-project --limit $limit_count
            fi
            
            scan_result=$?
            echo ""
            
            if [ $scan_result -eq 0 ]; then
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
                    
                    if [ "$limit_count" = "0" ]; then
                        python3 project_manage.py --scan-project --apply
                    else
                        python3 project_manage.py --scan-project --apply --limit $limit_count
                    fi
                    
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
                    echo "📋 移动计划已保存，以供后续查看"
                fi
            else
                echo "❌ 扫描失败，请检查错误信息"
            fi
            ;;
        3)
            return
            ;;
        *)
            echo "❌ 无效选择"
            ;;
    esac
    
    echo ""
    read -p "按Enter键继续..."
}

search_and_filter() {
    echo "🔍 搜索和过滤Issues..."
    echo ""
    echo "📁 Issues目录结构:"
    echo "=================="
    echo "  - issues_workspace/issues/     (所有issue文件)"
    echo "  - issues_workspace/metadata/   (元数据信息)"
    echo ""
    echo "🛠️ 搜索选项:"
    echo "============"
    echo "  1. 🔤 按关键词搜索标题"
    echo "  2. 🏷️ 按标签筛选"
    echo "  3. 👤 按作者筛选"
    echo "  4. 📅 按状态筛选"
    echo "  5. 📊 显示搜索统计"
    echo "  6. 💻 打开VS Code搜索"
    echo "  7. 返回"
    echo ""
    
    read -p "请选择搜索方式 (1-7): " search_choice
    
    case $search_choice in
        1)
            echo ""
            read -p "🔤 请输入搜索关键词: " keyword
            if [ -n "$keyword" ]; then
                echo ""
                echo "🔍 搜索结果 (标题包含 '$keyword'):"
                echo "=================================="
                grep -l -i "$keyword" "$SCRIPT_DIR/issues_workspace/issues/"*.md 2>/dev/null | head -20 | while read file; do
                    filename=$(basename "$file" .md)
                    echo "  - $filename"
                done | head -20
                echo ""
                echo "💡 提示: 显示前20个结果，完整搜索请使用VS Code"
            fi
            ;;
        2)
            echo ""
            echo "🏷️ 输入要查看的标签名称："
            read -p "标签名: " label
            if [ -n "$label" ]; then
                echo ""
                echo "🏷️ 包含标签 '$label' 的Issues:"
                echo "=========================="
                cd "$SCRIPT_DIR"
                python3 -c "
import sys
sys.path.insert(0, '.')
from issues_manager import SageIssuesManager

manager = SageIssuesManager()
manager._load_issues()

label_query = '$label'.lower()
found_issues = []

for issue in manager.issues:
    labels = issue.get('labels', [])
    if any(label_query in label.lower() for label in labels):
        found_issues.append(issue)

if found_issues:
    print(f'找到 {len(found_issues)} 个包含标签 \"$label\" 的Issues:')
    for issue in found_issues[:10]:  # 限制显示前10个
        print(f'  Issue #{issue.get(\"number\", \"N/A\")}: {issue.get(\"title\", \"无标题\")}')
    if len(found_issues) > 10:
        print(f'  ... 还有 {len(found_issues) - 10} 个Issues未显示')
else:
    print(f'未找到包含标签 \"$label\" 的Issues')
" 2>/dev/null || echo "❌ 查询失败"
            else
                echo "❌ 请输入标签名称"
            fi
            ;;
        3)
            echo ""
            read -p "👤 请输入作者用户名: " author
            if [ -n "$author" ]; then
                echo ""
                echo "👤 作者 '$author' 的Issues:"
                echo "========================"
                grep -l "author.*$author" "$SCRIPT_DIR/issues_workspace/issues/"*.md 2>/dev/null | head -20 | while read file; do
                    filename=$(basename "$file" .md)
                    echo "  - $filename"
                done
            fi
            ;;
        4)
            echo ""
            echo "📅 按状态筛选:"
            echo "  1. 开放状态 (open)"
            echo "  2. 已关闭 (closed)"
            echo ""
            read -p "请选择状态 (1-2): " status_choice
            
            case $status_choice in
                1) status="open" ;;
                2) status="closed" ;;
                *) echo "❌ 无效选择"; return ;;
            esac
            
            echo ""
            echo "📅 状态为 '$status' 的Issues:"
            echo "=========================="
            if [ "$status" = "open" ]; then
                find "$SCRIPT_DIR/issues_workspace/issues/" -name "open_*.md" 2>/dev/null | head -20 | while read file; do
                    filename=$(basename "$file" .md)
                    echo "  - $filename"
                done
            else
                find "$SCRIPT_DIR/issues_workspace/issues/" -name "closed_*.md" 2>/dev/null | head -20 | while read file; do
                    filename=$(basename "$file" .md)
                    echo "  - $filename"
                done
            fi
            ;;
        5)
            echo ""
            echo "📊 Issues统计信息:"
            echo "=================="
            total_issues=$(find "$SCRIPT_DIR/issues_workspace/issues/" -name "*.md" 2>/dev/null | wc -l)
            open_issues=$(find "$SCRIPT_DIR/issues_workspace/issues/" -name "open_*.md" 2>/dev/null | wc -l)
            closed_issues=$(find "$SCRIPT_DIR/issues_workspace/issues/" -name "closed_*.md" 2>/dev/null | wc -l)
            
            echo "  总Issues数量: $total_issues"
            echo "  开放Issues: $open_issues"
            echo "  已关闭Issues: $closed_issues"
            echo ""
            echo "📁 目录大小:"
            if command -v du >/dev/null 2>&1; then
                du -sh "$SCRIPT_DIR/issues_workspace" 2>/dev/null || echo "  无法计算目录大小"
            fi
            ;;
        6)
            echo ""
            echo "💻 正在尝试打开VS Code..."
            if command -v code >/dev/null 2>&1; then
                echo "🚀 在VS Code中打开Issues工作区..."
                code "$SCRIPT_DIR/issues_workspace" 2>/dev/null &
                echo "✅ VS Code已启动，您可以使用 Ctrl+Shift+F 进行全局搜索"
            else
                echo "❌ VS Code未安装或不在PATH中"
                echo "💡 建议安装VS Code进行高级搜索和编辑"
                echo "📁 工作区目录: $SCRIPT_DIR/issues_workspace"
            fi
            ;;
        7|*)
            echo "返回上级菜单..."
            return
            ;;
    esac
    
    if [ "$search_choice" != "7" ] && [ -n "$search_choice" ]; then
        echo ""
        read -p "按Enter键继续..."
    fi
}

# 启动时检查GitHub Token
# 检查是否首次使用
echo -e "${CYAN}正在初始化SAGE Issues管理工具...${NC}"

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
