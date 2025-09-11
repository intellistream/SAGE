# Converted from .sh for Python packaging
# SAGE Issues 管理工具 - 简化版主入口
# 专注于核心的三大功能：下载、AI整理、上传

import os
import sys
import subprocess
import requests
import json
from pathlib import Path

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

# 获取脚本目录
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

def print_colored(color, msg):
    print(f"{color}{msg}{NC}")

def get_config_path(path_type):
    """从config获取路径"""
    allowed_types = ['workspace', 'output', 'metadata', 'issues']
    if path_type not in allowed_types:
        print_colored(RED, f"Error: Invalid path_type '{path_type}'.")
        return None
    try:
        result = subprocess.run(['python3', '_scripts/helpers/get_paths.py', path_type], 
                                cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines:
                return lines[-1].strip()
    except Exception:
        pass
    return None

# 从config获取实际路径
ISSUES_WORKSPACE_PATH = get_config_path("workspace") or os.path.join(PROJECT_ROOT, 'output', 'issues-workspace')
ISSUES_OUTPUT_PATH = get_config_path("output") or os.path.join(PROJECT_ROOT, 'output', 'issues-output')
ISSUES_METADATA_PATH = get_config_path("metadata") or os.path.join(PROJECT_ROOT, 'output', 'issues-metadata')
ISSUES_DIR = get_config_path("issues") or os.path.join(PROJECT_ROOT, 'output', 'issues-workspace', 'issues')

def check_github_token():
    """检查GitHub Token"""
    token_file = os.path.join(PROJECT_ROOT, '.github_token')
    if os.environ.get('GITHUB_TOKEN'):
        return True
    if os.path.isfile(token_file):
        return True
    return False

def check_metadata_files():
    """检查metadata文件是否存在"""
    boards_file = os.path.join(ISSUES_METADATA_PATH, 'boards_metadata.json')
    team_file = os.path.join(ISSUES_METADATA_PATH, 'team_config.py')
    return os.path.isfile(boards_file) and os.path.isfile(team_file)

def initialize_metadata_files():
    """初始化metadata文件"""
    print("  📋 初始化boards metadata...")
    result = subprocess.run(['python3', '_scripts/helpers/get_boards.py'], cwd=SCRIPT_DIR, capture_output=True)
    if result.returncode == 0:
        print_colored(GREEN, "    ✅ boards metadata初始化完成")
    else:
        print_colored(YELLOW, "    ⚠️ boards metadata初始化失败，请稍后手动运行")
    
    print("  👥 初始化team members metadata...")
    result = subprocess.run(['python3', '_scripts/helpers/get_team_members.py'], cwd=SCRIPT_DIR, capture_output=True)
    if result.returncode == 0:
        print_colored(GREEN, "    ✅ team members metadata初始化完成")
    else:
        print_colored(YELLOW, "    ⚠️ team members metadata初始化失败，请稍后手动运行")
    
    print_colored(GREEN, "✅ 所有metadata文件初始化完成")

def auto_initialize_metadata():
    """自动初始化metadata文件"""
    print_colored(CYAN, "🔍 检查metadata文件状态...")
    
    if not check_metadata_files():
        print_colored(YELLOW, "📋 检测到metadata文件缺失，正在自动初始化...")
        print()
        initialize_metadata_files()
        print()
        
        if check_metadata_files():
            print_colored(GREEN, "🎉 metadata文件自动初始化成功！")
        else:
            print_colored(YELLOW, "⚠️ metadata文件初始化可能不完整，请检查")
    else:
        print_colored(GREEN, "✅ metadata文件检查完成，所有文件正常")

def first_time_setup():
    """首次使用向导"""
    token_file = os.path.join(PROJECT_ROOT, '.github_token')
    
    print_colored(YELLOW, "🌟 欢迎首次使用SAGE Issues管理工具！")
    print("================================================")
    print()
    print("为了正常使用所有功能，您需要配置GitHub Personal Access Token。")
    print()
    print_colored(CYAN, "📋 设置步骤：")
    print()
    print("1. 访问GitHub生成Personal Access Token:")
    print_colored(BLUE, "   https://github.com/settings/tokens")
    print()
    print("2. 点击 'Generate new token' > 'Generate new token (classic)'")
    print()
    print("3. 设置权限 (Scopes):")
    print("   ✅ repo (完整仓库访问权限)")
    print("   ✅ read:org (读取组织信息)")
    print("   ✅ project (项目访问权限)")
    print()
    print("4. 点击 'Generate token' 并复制生成的token")
    print()
    print_colored(RED, "⚠️ 重要提醒：")
    print("   - Token只会显示一次，请立即复制保存")
    print("   - 不要将token分享给他人或提交到版本控制系统")
    print()
    
    has_token = input("您已经获得GitHub Token了吗？(y/N): ").strip().lower()
    if has_token in ['y', 'yes']:
        print()
        print("请粘贴您的GitHub Token:")
        token = input()
        
        if token:
            print("🔍 验证Token有效性...")
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'Authorization': f'token {token}'
            }
            try:
                response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
                if response.status_code == 200:
                    with open(token_file, 'w') as f:
                        f.write(token)
                    os.chmod(token_file, 0o600)
                    print_colored(GREEN, f"✅ Token验证成功并已保存到: {token_file}")
                    print()
                    
                    print("🔄 正在初始化metadata文件...")
                    initialize_metadata_files()
                    
                    print_colored(GREEN, "🎉 设置完成！现在您可以使用所有功能了。")
                    print()
                    input("按回车键继续...")
                    return True
                else:
                    print_colored(RED, "❌ Token验证失败，请检查Token是否正确")
                    print()
                    input("按回车键继续...")
                    return False
            except Exception:
                print_colored(RED, "❌ Token验证失败，请检查网络连接")
                print()
                input("按回车键继续...")
                return False
        else:
            print_colored(RED, "❌ 未输入token")
            return False
    else:
        print()
        print_colored(YELLOW, "📝 您也可以稍后手动创建token文件：")
        print(f"   echo 'your_token_here' > {token_file}")
        print(f"   chmod 600 {token_file}")
        print()
        print_colored(CYAN, "💡 提示：没有token时可以使用匿名模式，但功能会受到限制。")
        print()
        input("按回车键继续...")
        return False

def show_main_menu():
    os.system('clear' if os.name == 'posix' else 'cls')
    print_colored(CYAN, "🎯 SAGE Issues 管理工具")
    print("==============================")
    
    if check_github_token():
        print_colored(GREEN, "✅ GitHub Token: 已配置")
    else:
        print_colored(YELLOW, "⚠️ GitHub Token: 未配置 (功能受限)")
    
    print()
    print_colored(BLUE, "核心功能:")
    print()
    print("  1. 📝 手动管理Issues")
    print("  2. 📥 下载远端Issues")
    print("  3. 🤖 AI智能管理") 
    print("  4. 📤 上传Issues到远端")
    print()
    print_colored(CYAN, "设置选项:")
    print()
    print("  6. ⚙️ 配置管理")
    if not check_github_token():
        print("  9. 🔑 配置GitHub Token")
    print()
    print("  5. 🚪 退出")
    print()

def download_menu():
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print_colored(BLUE, "📥 下载远端Issues")
        print("====================")
        print()
        print("  1. 下载所有Issues")
        print("  2. 下载开放的Issues")
        print("  3. 下载已关闭的Issues")
        print("  4. 🗑️ 清空本地Issues数据")
        print("  5. 返回主菜单")
        print()
        print_colored(CYAN, "💡 提示: 选项1-3会在下载前自动询问是否清空本地数据")
        print()
        choice = input("请选择 (1-5): ").strip()
        
        if choice == '1':
            download_all_issues()
        elif choice == '2':
            download_open_issues()
        elif choice == '3':
            download_closed_issues()
        elif choice == '4':
            clear_local_issues()
            input("按Enter键继续...")
        elif choice == '5':
            break
        else:
            print_colored(RED, "❌ 无效选择")
            subprocess.run(['sleep', '1'])

def ai_menu():
    has_local_data = os.path.isdir(ISSUES_DIR) and os.listdir(ISSUES_DIR)
    
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print_colored(BLUE, "🤖 AI智能管理")
        print("================")
        print()
        
        if has_local_data:
            print_colored(GREEN, "✅ 检测到本地Issues数据")
        else:
            print_colored(YELLOW, "⚠️ 未检测到本地Issues数据，请先下载Issues")
        
        print()
        print_colored(CYAN, "📊 Copilot分析助手:")
        print("  1. 📈 全部open issues分析")
        print("  2. 📅 近一周的open issues分析")  
        print("  3. 📆 近一个月的open issues分析")
        print()
        print_colored(CYAN, "🎯 AI智能操作:")
        print("  4. 🤖 基于Project智能分配Issues")
        print()
        print("  5. 📖 查看使用指南")
        
        if not has_local_data:
            print()
            print_colored(CYAN, "  d. 📥 前往下载Issues数据")
        
        print("  9. 返回主菜单")
        print()
        
        if has_local_data:
            choice = input("请选择 (1-5, 9): ").strip()
        else:
            choice = input("请选择 (1-5, d, 9): ").strip()
        
        if choice == '1':
            if has_local_data:
                copilot_time_range_menu("all")
            else:
                print_colored(RED, "❌ 需要先下载Issues数据")
                subprocess.run(['sleep', '1'])
        elif choice == '2':
            if has_local_data:
                copilot_time_range_menu("week")
            else:
                print_colored(RED, "❌ 需要先下载Issues数据")
                subprocess.run(['sleep', '1'])
        elif choice == '3':
            if has_local_data:
                copilot_time_range_menu("month")
            else:
                print_colored(RED, "❌ 需要先下载Issues数据")
                subprocess.run(['sleep', '1'])
        elif choice == '4':
            if has_local_data:
                project_based_assign_menu()
            else:
                print_colored(RED, "❌ 需要先下载Issues数据")
                subprocess.run(['sleep', '1'])
        elif choice == '5':
            copilot_show_usage_guide()
        elif choice.lower() == 'd':
            if not has_local_data:
                download_menu()
                has_local_data = os.path.isdir(ISSUES_DIR) and os.listdir(ISSUES_DIR)
            else:
                print_colored(RED, "❌ 无效选择")
                subprocess.run(['sleep', '1'])
        elif choice == '9':
            break
        else:
            print_colored(RED, "❌ 无效选择")
            subprocess.run(['sleep', '1'])

def upload_menu():
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print_colored(BLUE, "📤 上传Issues到远端")
        print("====================")
        print()
        print("  1. 同步所有修改")
        print("  2. 同步标签更新")
        print("  3. 同步状态更新")
        print("  4. 预览待同步更改")
        print("  5. 返回主菜单")
        print()
        choice = input("请选择 (1-5): ").strip()
        
        if choice == '1':
            sync_all_changes()
        elif choice == '2':
            sync_label_changes()
        elif choice == '3':
            sync_status_changes()
        elif choice == '4':
            preview_changes()
        elif choice == '5':
            break
        else:
            print_colored(RED, "❌ 无效选择")
            subprocess.run(['sleep', '1'])

def issues_management_menu():
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print_colored(BLUE, "📝 手动管理Issues")
        print("==================")
        print()
        print("  1. 📊 查看Issues统计和分析")
        print("  2. 🗂️ 自动归档已完成Issues")
        print("  3. 📋 查看Issues更新记录")
        print("  4. 返回主菜单")
        print()
        choice = input("请选择 (1-4): ").strip()
        
        if choice == '1':
            show_issues_statistics()
        elif choice == '2':
            archive_completed_issues()
        elif choice == '3':
            show_update_history_menu()
        elif choice == '4':
            break
        else:
            print_colored(RED, "❌ 无效选择")
            subprocess.run(['sleep', '1'])

def clear_local_issues():
    issues_dir = ISSUES_DIR
    
    if os.path.isdir(issues_dir) and os.listdir(issues_dir):
        print_colored(YELLOW, "🗑️ 发现本地Issues数据")
        print(f"目录: {issues_dir}")
        print()
        try:
            result = subprocess.run(['ls', '-la', issues_dir], capture_output=True, text=True)
            print(result.stdout.split('\n')[:10])
            if len(os.listdir(issues_dir)) > 10:
                print("... 以及更多文件")
        except:
            pass
        print()
        print_colored(RED, "⚠️ 警告: 此操作将删除所有本地Issues数据")
        print()
        confirm_clear = input("确认清空本地Issues目录？ (y/N): ").strip().lower()
        
        if confirm_clear in ['y', 'yes']:
            print()
            print("🗑️ 正在清空本地Issues目录...")
            for item in os.listdir(issues_dir):
                item_path = os.path.join(issues_dir, item)
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            print_colored(GREEN, "✅ 本地Issues目录已清空")
            print()
        else:
            print()
            print("❌ 取消清空操作")
            print()
    else:
        print_colored(CYAN, "ℹ️ 本地Issues目录为空或不存在，无需清空")
        print()

def download_all_issues():
    clear_local_issues()
    print("📥 正在下载所有Issues...")
    subprocess.run(['python3', '_scripts/download_issues.py', '--state=all'], cwd=SCRIPT_DIR)
    input("按Enter键继续...")

def download_open_issues():
    clear_local_issues()
    print("📥 正在下载开放的Issues...")
    subprocess.run(['python3', '_scripts/download_issues.py', '--state=open'], cwd=SCRIPT_DIR)
    input("按Enter键继续...")

def download_closed_issues():
    clear_local_issues()
    print("📥 正在下载已关闭的Issues...")
    subprocess.run(['python3', '_scripts/download_issues.py', '--state=closed'], cwd=SCRIPT_DIR)
    input("按Enter键继续...")

def project_based_assign_menu():
    has_local_data = os.path.isdir(ISSUES_DIR) and os.listdir(ISSUES_DIR)
    
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print_colored(BLUE, "🎯 基于Project智能分配Issues")
        print("===============================")
        print()
        
        if has_local_data:
            print_colored(GREEN, "✅ 检测到本地Issues数据")
            
            # 统计当前分配情况
            total_issues = 0
            assigned_issues = 0
            unassigned_issues = 0
            
            for file_path in Path(ISSUES_DIR).glob("open_*.md"):
                if file_path.is_file():
                    total_issues += 1
                    with open(file_path) as f:
                        content = f.read()
                    if '## 分配给' in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.strip() == '## 分配给':
                                assignee = lines[i+1].strip() if i+1 < len(lines) else ''
                                if assignee not in ['未分配', '']:
                                    assigned_issues += 1
                                else:
                                    unassigned_issues += 1
                                break
            
            print("📊 当前状态:")
            print(f"  - 总Issues数: {total_issues}")
            print(f"  - 已分配: {assigned_issues}")
            print(f"  - 未分配: {unassigned_issues}")
        else:
            print_colored(YELLOW, "⚠️ 未检测到本地Issues数据，请先下载Issues")
        
        print()
        print_colored(CYAN, "🛠️ 分配选项:")
        print("  1. 🚀 执行完整智能分配 (包含错误检测与修复)")
        print("  2. 📋 预览分配计划 (不实际修改文件)")
        print("  3. 📊 分析当前分配状态")
        print()
        
        if not has_local_data:
            print_colored(CYAN, "  d. 📥 前往下载Issues数据")
        
        print("  9. 返回上级菜单")
        print()
        
        if has_local_data:
            choice = input("请选择 (1-3, 9): ").strip()
        else:
            choice = input("请选择 (1-3, d, 9): ").strip()
        
        if choice == '1':
            if has_local_data:
                execute_project_based_assign()
            else:
                print_colored(RED, "❌ 需要先下载Issues数据")
                subprocess.run(['sleep', '2'])
        elif choice == '2':
            if has_local_data:
                preview_project_based_assign()
            else:
                print_colored(RED, "❌ 需要先下载Issues数据")
                subprocess.run(['sleep', '2'])
        elif choice == '3':
            if has_local_data:
                analyze_assignment_status()
            else:
                print_colored(RED, "❌ 需要先下载Issues数据")
                subprocess.run(['sleep', '2'])
        elif choice.lower() == 'd':
            if not has_local_data:
                download_menu()
                has_local_data = os.path.isdir(ISSUES_DIR) and os.listdir(ISSUES_DIR)
            else:
                print_colored(RED, "❌ 无效选择")
                subprocess.run(['sleep', '1'])
        elif choice == '9':
            break
        else:
            print_colored(RED, "❌ 无效选择")
            subprocess.run(['sleep', '1'])

def execute_project_based_assign():
    os.system('clear' if os.name == 'posix' else 'cls')
    print_colored(CYAN, "🚀 执行完整智能分配 (包含错误检测与修复)")
    print("=================================================")
    print()
    print_colored(CYAN, "此功能将自动执行以下操作：")
    print("  🔍 1. 检测错误分配的Issues (team与project不匹配)")
    print("  🔧 2. 自动修复检测到的分配问题")
    print("  🎯 3. 执行智能分配 (基于Project归属)")
    print("  📊 4. 显示分配结果统计")
    print()
    print_colored(YELLOW, "⚠️ 此操作将修改Issues文件中的分配信息")
    print()
    confirm = input("确认执行完整智能分配？ (y/N): ").strip().lower()
    
    if confirm in ['y', 'yes']:
        print()
        print_colored(CYAN, "🔍 步骤1: 检测错误分配的Issues...")
        result = subprocess.run(['python3', '_scripts/helpers/fix_misplaced_issues.py', '--dry-run'], cwd=SCRIPT_DIR)
        if result.returncode == 0:
            print_colored(GREEN, "✅ 错误检测完成")
            
            fix_plan_files = glob.glob(os.path.join(ISSUES_OUTPUT_PATH, 'issues_fix_plan_*.json'))
            fix_plan_files.sort(key=os.path.getctime, reverse=True)
            if fix_plan_files:
                latest_plan = fix_plan_files[0]
                print_colored(YELLOW, "⚠️ 发现需要修复的错误分配，自动执行修复...")
                print()
                print_colored(CYAN, "🔧 步骤2: 自动修复错误分配...")
                result = subprocess.run(['python3', '_scripts/helpers/execute_fix_plan.py', latest_plan, '--live'], cwd=SCRIPT_DIR)
                if result.returncode == 0:
                    print_colored(GREEN, "✅ 错误分配修复完成")
                else:
                    print_colored(RED, "❌ 错误分配修复失败")
            else:
                print_colored(GREEN, "✅ 未发现错误分配的Issues")
                print_colored(CYAN, "📝 跳过步骤2: 无需修复")
        else:
            print_colored(RED, "❌ 错误检测失败，继续执行智能分配...")
        
        print()
        print_colored(CYAN, "🎯 步骤3: 执行智能分配...")
        
        result = subprocess.run(['python3', '_scripts/project_based_assign.py', '--assign'], cwd=SCRIPT_DIR)
        if result.returncode == 0:
            print()
            print_colored(GREEN, "✅ 智能分配完成！")
            print()
            print_colored(CYAN, "📊 步骤4: 显示分配结果统计...")
            
            total = 0
            assigned = 0
            unassigned = 0
            by_team_kernel = 0
            by_team_middleware = 0
            by_team_apps = 0
            by_team_intellistream = 0
            
            for file_path in Path(ISSUES_DIR).glob("open_*.md"):
                if file_path.is_file():
                    total += 1
                    with open(file_path) as f:
                        content = f.read()
                    if '## 分配给' in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.strip() == '## 分配给':
                                assignee = lines[i+1].strip() if i+1 < len(lines) else ''
                                if assignee not in ['未分配', '']:
                                    assigned += 1
                                else:
                                    unassigned += 1
                                break
                    
                    if 'sage-kernel' in content:
                        by_team_kernel += 1
                    elif 'sage-middleware' in content:
                        by_team_middleware += 1
                    elif 'sage-apps' in content:
                        by_team_apps += 1
                    elif 'intellistream' in content:
                        by_team_intellistream += 1
            
            print("📈 分配结果统计:")
            print(f"  - 总Issues数: {total}")
            print(f"  - 已分配: {assigned}")
            print(f"  - 未分配: {unassigned}")
            if total > 0:
                print(f"  - 分配率: {assigned * 100 // total}%")
            print()
            print("📊 按项目归属分布:")
            print(f"  - intellistream: {by_team_intellistream} issues")
            print(f"  - sage-kernel: {by_team_kernel} issues")
            print(f"  - sage-middleware: {by_team_middleware} issues")
            print(f"  - sage-apps: {by_team_apps} issues")
            print()
            
            if unassigned == 0:
                print_colored(GREEN, "🎉 所有Issues都已成功分配！")
            else:
                print_colored(YELLOW, f"💡 还有 {unassigned} 个Issues未分配，可能需要手动处理")
            
            print()
            print_colored(CYAN, "📤 自动同步分配结果到GitHub远端...")
            print()
            
            print("🚀 正在智能同步分配结果...")
            result = subprocess.run(['python3', '_scripts/sync_issues.py', '--apply-projects', '--auto-confirm'], cwd=SCRIPT_DIR)
            if result.returncode == 0:
                print_colored(GREEN, "✅ 分配结果已成功同步到GitHub！")
            else:
                print_colored(YELLOW, "⚠️ 同步过程中遇到问题，但本地分配已完成")
                print("💡 您可以稍后通过上传菜单手动同步")
        else:
            print()
            print_colored(RED, "❌ 智能分配失败")
        
        print()
        input("按Enter键继续...")
    else:
        print()
        print("❌ 已取消智能分配操作")
        subprocess.run(['sleep', '1'])

def preview_project_based_assign():
    os.system('clear' if os.name == 'posix' else 'cls')
    print_colored(CYAN, "📋 预览基于Project的分配计划")
    print("===============================")
    print()
    print("🔍 分析Issues并生成分配计划(不修改文件)...")
    # 实现预览逻辑，使用 subprocess 调用 Python 脚本或模拟
    # 由于原脚本使用临时文件，这里简化使用 subprocess
    result = subprocess.run(['python3', '_scripts/project_based_assign.py', '--preview'], cwd=SCRIPT_DIR)
    print()
    input("按Enter键继续...")

def analyze_assignment_status():
    os.system('clear' if os.name == 'posix' else 'cls')
    print_colored(CYAN, "📊 分析当前分配状态")
    print("======================")
    print()
    print("🔍 正在分析当前Issues分配情况...")
    
    total = 0
    assigned = 0
    unassigned = 0
    by_team_kernel = 0
    by_team_middleware = 0
    by_team_apps = 0
    
    for file_path in Path(ISSUES_DIR).glob("open_*.md"):
        if file_path.is_file():
            total += 1
            with open(file_path) as f:
                content = f.read()
            if '## 分配给' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == '## 分配给':
                        assignee = lines[i+1].strip() if i+1 < len(lines) else ''
                        if assignee not in ['未分配', '']:
                            assigned += 1
                        else:
                            unassigned += 1
                        break
            
            if 'sage-kernel' in content:
                by_team_kernel += 1
            elif 'sage-middleware' in content:
                by_team_middleware += 1
            elif 'sage-apps' in content:
                by_team_apps += 1
    
    print("📈 总体统计:")
    print(f"  - 总Issues数: {total}")
    print(f"  - 已分配: {assigned}")
    print(f"  - 未分配: {unassigned}")
    print(f"  - 分配率: {assigned * 100 // total if total > 0 else 0}%")
    print()
    print("📊 按项目归属统计:")
    print(f"  - sage-kernel: {by_team_kernel} issues")
    print(f"  - sage-middleware: {by_team_middleware} issues")
    print(f"  - sage-apps: {by_team_apps} issues")
    print()
    
    if unassigned > 0:
        print_colored(YELLOW, f"💡 建议: 有 {unassigned} 个未分配的Issues，可以使用智能分配功能")
    else:
        print_colored(GREEN, "✅ 所有Issues都已分配！")
    
    print()
    input("按Enter键继续...")

def copilot_time_range_menu(time_filter):
    time_desc = {"all": "全部", "week": "近一周", "month": "近一个月"}.get(time_filter, "未知")
    
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print_colored(BLUE, f"🤖 Copilot分析 - {time_desc} 的Open Issues")
        print("===========================================")
        print()
        print_colored(CYAN, "📊 按团队分组生成分析文档:")
        print("  1. 🎯 生成综合分析文档 (所有团队概况)")
        print("  2. 👥 生成所有团队详细文档")
        print("  3. 📋 生成未分配Issues文档")
        print("  4. 🔄 生成完整分析包 (推荐)")
        print()
        print_colored(CYAN, "🏷️ 按单个团队生成:")
        print("  5. 📱 SAGE Apps团队文档")
        print("  6. ⚙️ SAGE Kernel团队文档")
        print("  7. 🔧 SAGE Middleware团队文档")
        print()
        print("  8. 返回时间选择")
        print()
        choice = input("请选择 (1-8): ").strip()
        
        if choice == '1':
            copilot_generate_comprehensive(time_filter)
        elif choice == '2':
            copilot_generate_teams(time_filter)
        elif choice == '3':
            copilot_generate_unassigned(time_filter)
        elif choice == '4':
            copilot_generate_all(time_filter)
        elif choice == '5':
            copilot_generate_single_team("sage-apps", time_filter)
        elif choice == '6':
            copilot_generate_single_team("sage-kernel", time_filter)
        elif choice == '7':
            copilot_generate_single_team("sage-middleware", time_filter)
        elif choice == '8':
            break
        else:
            print_colored(RED, "❌ 无效选择")
            subprocess.run(['sleep', '1'])

def copilot_generate_comprehensive(time_filter):
    time_desc = {"all": "全部", "week": "近一周", "month": "近一个月"}.get(time_filter, "全部")
    print(f"🎯 生成综合分析文档 ({time_desc})...")
    subprocess.run(['python3', '_scripts/copilot_issue_formatter.py', '--format=comprehensive', f'--time={time_filter}'], cwd=SCRIPT_DIR)
    print()
    print(f"✅ 综合分析文档已生成 (时间范围: {time_desc})")
    print("💡 请将生成的文档内容复制到Copilot聊天窗口进行分析")
    input("按Enter键继续...")

# 类似地实现其他 copilot_generate 函数，使用 subprocess 调用

def copilot_generate_teams(time_filter):
    time_desc = {"all": "全部", "week": "近一周", "month": "近一个月"}.get(time_filter, "全部")
    print(f"👥 生成所有团队详细文档 ({time_desc})...")
    subprocess.run(['python3', '_scripts/copilot_issue_formatter.py', '--format=teams', f'--time={time_filter}'], cwd=SCRIPT_DIR)
    print()
    print(f"✅ 团队详细文档已生成 (时间范围: {time_desc})")
    print("💡 可分别将各团队文档复制到Copilot进行针对性分析")
    input("按Enter键继续...")

def copilot_generate_unassigned(time_filter):
    time_desc = {"all": "全部", "week": "近一周", "month": "近一个月"}.get(time_filter, "全部")
    print(f"📋 生成未分配Issues文档 ({time_desc})...")
    subprocess.run(['python3', '_scripts/copilot_issue_formatter.py', '--format=unassigned', f'--time={time_filter}'], cwd=SCRIPT_DIR)
    print()
    print(f"✅ 未分配Issues文档已生成 (时间范围: {time_desc})")
    print("💡 将文档内容给Copilot分析如何分配这些Issues")
    input("按Enter键继续...")

def copilot_generate_all(time_filter):
    time_desc = {"all": "全部", "week": "近一周", "month": "近一个月"}.get(time_filter, "全部")
    print(f"🔄 生成完整分析包 ({time_desc})...")
    subprocess.run(['python3', '_scripts/copilot_issue_formatter.py', '--format=all', f'--time={time_filter}'], cwd=SCRIPT_DIR)
    print()
    print("✅ 完整分析包已生成，包括：")
    print("   - 综合分析文档 (时间范围: {time_desc})")
    print("   - 各团队详细文档")
    print("   - 未分配Issues文档")
    print("   - 使用指南")
    print()
    print("💡 建议先从综合分析文档开始，再深入到具体团队")
    input("按Enter键继续...")

def copilot_generate_single_team(team_name, time_filter):
    team_display = {"sage-apps": "SAGE Apps", "sage-kernel": "SAGE Kernel", "sage-middleware": "SAGE Middleware"}.get(team_name, team_name)
    time_desc = {"all": "全部", "week": "近一周", "month": "近一个月"}.get(time_filter, "全部")
    print(f"📱 生成 {team_display} 团队文档 ({time_desc})...")
    subprocess.run(['python3', '_scripts/copilot_issue_formatter.py', f'--team={team_name}', f'--time={time_filter}'], cwd=SCRIPT_DIR)
    print()
    print(f"✅ {team_display} 团队文档已生成 (时间范围: {time_desc})")
    print("💡 将文档内容给Copilot分析该团队的具体情况和建议")
    input("按Enter键继续...")

def copilot_show_usage_guide():
    os.system('clear' if os.name == 'posix' else 'cls')
    print("📖 Copilot使用指南")
    print("==================")
    print()
    print("🎯 使用流程：")
    print("1. 选择时间范围（全部/近一周/近一个月）")
    print("2. 生成分析文档（选择分析类型）")
    print("3. 打开VS Code Copilot聊天窗口")
    print("4. 复制生成的文档内容到聊天窗口")
    print("5. 向Copilot提出具体的分析问题")
    print()
    print("⏰ 时间范围选项：")
    print("   - 全部: 所有open状态的issues")
    print("   - 近一周: 最近7天创建的open issues")
    print("   - 近一个月: 最近30天创建的open issues")
    print()
    print("🤖 推荐的Copilot分析问题：")
    print()
    print("优先级分析：")
    print("   '请分析这些open issues，识别需要立即处理的高优先级问题'")
    print()
    print("工作负载分析：")
    print("   '分析各团队的工作负载分布，是否存在不均衡？'")
    print()
    print("问题分类：")
    print("   '将这些issues按类型分类并建议标签优化方案'")
    print()
    print("重复性分析：")
    print("   '识别是否存在重复或相似的issues，哪些可以合并？'")
    print()
    print("依赖关系：")
    print("   '分析issues之间的依赖关系，建议处理顺序'")
    print()
    print("流程改进：")
    print("   '基于这些issues状态，建议项目管理改进方案'")
    print()
    print("时间趋势分析：")
    print("   '分析近期issues的创建趋势和类型变化'")
    print()
    print(f"📁 文档位置: {ISSUES_OUTPUT_PATH}/")
    print("   查看最新生成的以 'copilot_' 开头的文档")
    print("   文档名包含时间范围标识: _week 或 _month")
    print()
    print("💡 提示：")
    print("   - 可以同时分析多个团队的文档")
    print("   - 根据Copilot建议制定具体行动计划")
    print("   - 定期重新生成文档跟踪进度")
    print("   - 使用时间过滤关注最新的问题")
    print()
    input("按Enter键继续...")

def sync_all_changes():
    print("📤 同步所有修改到远端...")
    subprocess.run(['python3', '_scripts/sync_issues.py', '--all'], cwd=SCRIPT_DIR)
    input("按Enter键继续...")

def sync_label_changes():
    print("📤 同步标签更新...")
    subprocess.run(['python3', '_scripts/sync_issues.py', '--labels-only'], cwd=SCRIPT_DIR)
    input("按Enter键继续...")

def sync_status_changes():
    print("📤 同步状态更新...")
    subprocess.run(['python3', '_scripts/sync_issues.py', '--status-only'], cwd=SCRIPT_DIR)
    input("按Enter键继续...")

def preview_changes():
    print("🔍 预览待同步更改...")
    subprocess.run(['python3', '_scripts/sync_issues.py', '--preview'], cwd=SCRIPT_DIR)
    input("按Enter键继续...")

def show_issues_statistics():
    print("📊 显示Issues统计信息...")
    subprocess.run(['python3', '_scripts/issues_manager.py', '--action=statistics'], cwd=SCRIPT_DIR)
    input("按Enter键继续...")

def archive_completed_issues():
    os.system('clear' if os.name == 'posix' else 'cls')
    print_colored(BLUE, "🗂️ 自动归档已完成Issues")
    print("==============================")
    print()
    print("此功能将根据Issues完成时间自动归档：")
    print("  📋 一周内的已完成Issues → Done列")
    print("  📦 超过一周但不到一个月 → Archive列")
    print("  📚 超过一个月 → History列（如不存在将创建）")
    print()
    
    preview_choice = input("🤔 是否要先预览归档计划？ (Y/n): ").strip().lower()
    preview_flag = '' if preview_choice in ['n', 'no'] else '--preview'
    
    print()
    print("🚀 开始处理已完成Issues归档...")
    print("============================")
    
    helper_dir = os.path.join(SCRIPT_DIR, '_scripts/helpers')
    if preview_flag:
        print("🔍 预览归档计划：")
        result = subprocess.run(['python3', 'archive_completed_issues.py', preview_flag], cwd=helper_dir)
        
        print()
        confirm_execute = input("是否执行归档操作？ (y/N): ").strip().lower()
        if confirm_execute in ['y', 'yes']:
            print()
            print("⚡ 执行归档操作...")
            subprocess.run(['python3', 'archive_completed_issues.py'], cwd=helper_dir)
        else:
            print("📋 归档操作已取消")
    else:
        print("⚡ 直接执行归档操作...")
        subprocess.run(['python3', 'archive_completed_issues.py'], cwd=helper_dir)
    
    print()
    input("按Enter键继续...")

def show_update_history_menu():
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print_colored(BLUE, "📋 Issues更新记录查看")
        print("========================")
        print()
        print("  1. 📋 列出所有有更新记录的Issues")
        print("  2. 🔍 查看特定Issue的更新记录")
        print("  3. ℹ️ 关于更新记录的说明")
        print("  4. 返回上级菜单")
        print()
        choice = input("请选择 (1-4): ").strip()
        
        if choice == '1':
            print_colored(CYAN, "📋 正在扫描Issues更新记录...")
            print()
            subprocess.run(['python3', '_scripts/show_update_history.py'], cwd=SCRIPT_DIR)
            print()
            input("按Enter键继续...")
        elif choice == '2':
            print()
            issue_id = input("🔍 请输入要查看的Issue编号: ").strip()
            if issue_id.isdigit():
                print()
                print_colored(CYAN, f"📋 显示Issue #{issue_id}的更新记录...")
                print()
                subprocess.run(['python3', '_scripts/show_update_history.py', f'--issue-id={issue_id}'], cwd=SCRIPT_DIR)
                print()
                input("按Enter键继续...")
            else:
                print_colored(RED, "❌ 请输入有效的Issue编号")
                subprocess.run(['sleep', '1'])
        elif choice == '3':
            os.system('clear' if os.name == 'posix' else 'cls')
            print_colored(BLUE, "ℹ️ 关于更新记录的说明")
            print("========================")
            print()
            print_colored(CYAN, "📝 更新记录的作用：")
            print("  • 记录我们对每个Issue的本地管理操作")
            print("  • 追踪Issue的下载、同步、修改历史")
            print("  • 提供本地管理的审计轨迹")
            print()
            print_colored(CYAN, "🔧 设计原则：")
            print("  • 更新记录是本地管理信息，不会同步到GitHub")
            print("  • GitHub本身有完整的活动历史记录")
            print("  • 这样避免污染GitHub上的原始Issue内容")
            print()
            print_colored(CYAN, "📊 查看GitHub活动历史：")
            print("  • 在GitHub网页上查看Issue可以看到完整的活动历史")
            print("  • 包括评论、标签变更、状态变更等所有操作")
            print()
            print_colored(YELLOW, "💡 如果需要在GitHub上记录管理操作，建议通过Issue评论的方式")
            print()
            input("按Enter键继续...")
        elif choice == '4':
            break
        else:
            print_colored(RED, "❌ 无效选择")
            subprocess.run(['sleep', '1'])

def config_management_menu():
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print_colored(BLUE, "⚙️ 配置管理")
        print("===============")
        print()
        print("  1. 📋 查看当前配置")
        print("  2. 🔄 交互式配置向导")
        print("  3. 📤 更新记录同步设置")
        print("  4. 💾 自动备份设置")
        print("  5. 返回主菜单")
        print()
        choice = input("请选择 (1-5): ").strip()
        
        if choice == '1':
            print_colored(CYAN, "📋 当前配置状态")
            print()
            subprocess.run(['python3', '_scripts/config_manager.py', '--show'], cwd=SCRIPT_DIR)
            print()
            input("按Enter键继续...")
        elif choice == '2':
            print_colored(CYAN, "🔄 交互式配置向导")
            print()
            subprocess.run(['python3', '_scripts/config_manager.py', '--interactive'], cwd=SCRIPT_DIR)
            print()
            input("按Enter键继续...")
        elif choice == '3':
            print_colored(CYAN, "📤 更新记录同步设置")
            print("========================")
            print()
            print("选择更新记录同步模式：")
            print("  on  - 将更新记录同步到GitHub (推荐)")
            print("  off - 更新记录仅保存在本地")
            print()
            sync_choice = input("请选择 (on/off): ").strip().lower()
            
            if sync_choice in ['on', 'off']:
                subprocess.run(['python3', '_scripts/config_manager.py', f'--sync-history={sync_choice}'], cwd=SCRIPT_DIR)
            else:
                print_colored(RED, "❌ 无效选择")
            print()
            input("按Enter键继续...")
        elif choice == '4':
            print_colored(CYAN, "💾 自动备份设置")
            print("==================")
            print()
            backup_choice = input("启用自动备份？ (on/off): ").strip().lower()
            
            if backup_choice in ['on', 'off']:
                subprocess.run(['python3', '_scripts/config_manager.py', f'--auto-backup={backup_choice}'], cwd=SCRIPT_DIR)
            else:
                print_colored(RED, "❌ 无效选择")
            print()
            input("按Enter键继续...")
        elif choice == '5':
            break
        else:
            print_colored(RED, "❌ 无效选择")
            subprocess.run(['sleep', '1'])

def main():
    print_colored(CYAN, "正在初始化SAGE Issues管理工具...")
    
    auto_initialize_metadata()
    
    if not check_github_token():
        print()
        print_colored(YELLOW, "⚠️ 检测到您是首次使用或未配置GitHub Token")
        print()
        setup_now = input("是否要现在进行初始设置？(Y/n): ").strip().lower()
        if setup_now not in ['n', 'no']:
            if first_time_setup():
                print()
                print_colored(GREEN, "🎉 设置完成！正在重新检查Token状态...")
    
    print()
    
    while True:
        show_main_menu()
        
        if check_github_token():
            choice = input("请选择功能 (1-6, 9 if needed, 5 to exit): ").strip()
        else:
            choice = input("请选择功能 (1-6, 9): ").strip()
        
        print()
        
        if choice == '1':
            issues_management_menu()
        elif choice == '2':
            download_menu()
        elif choice == '3':
            ai_menu()
        elif choice == '4':
            upload_menu()
        elif choice == '5':
            print_colored(GREEN, "👋 感谢使用SAGE Issues管理工具！")
            sys.exit(0)
        elif choice == '6':
            config_management_menu()
        elif choice == '9' and not check_github_token():
            print_colored(CYAN, "🔑 配置GitHub Token")
            print("====================")
            print()
            first_time_setup()
            print()
            input("按回车键返回主菜单...")
        elif choice == '':
            continue
        else:
            if check_github_token():
                print_colored(RED, "❌ 无效选择，请输入1-6")
            else:
                print_colored(RED, "❌ 无效选择，请输入1-6或9")
            subprocess.run(['sleep', '1'])

if __name__ == "__main__":
    main()