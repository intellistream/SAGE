# Converted from submodule_manager.sh
# SAGE 子模块管理工具
# 用于独立管理 SAGE 项目的 Git 子模块

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 尝试导入 common_utils
try:
    from sage_tools.utils.common_utils import print_error, print_warning, print_status, print_success, print_debug, print_header
except ImportError:
    # Fallback
    print_error = lambda msg: print(f"[ERROR] {msg}", file=sys.stderr)
    print_warning = lambda msg: print(f"[WARNING] {msg}")
    print_status = lambda msg: print(f"[STATUS] {msg}")
    print_success = lambda msg: print(f"[SUCCESS] {msg}")
    print_debug = lambda msg: print(f"[DEBUG] {msg}")
    print_header = lambda msg: print(f"### {msg} ###")

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.resolve()

def run_git_command(cmd: list, cwd: Path = REPO_ROOT, check: bool = True) -> subprocess.CompletedProcess:
    """运行 git 命令"""
    try:
        result = subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Git 命令失败: {' '.join(cmd)} - {e.stderr}")
        raise

def check_git_repo():
    """检查是否在git仓库中"""
    if not (REPO_ROOT / ".git").is_dir():
        print_error("错误：当前目录不是git仓库")
        sys.exit(1)
    
    if not (REPO_ROOT / ".gitmodules").exists():
        print_warning("未找到.gitmodules文件")
        print("当前项目没有配置任何子模块。")
        sys.exit(0)

def show_submodule_status():
    """显示子模块状态"""
    print_header("📊 子模块状态")
    
    try:
        result = run_git_command(["git", "submodule", "status"])
        print(result.stdout)
        print()
        print_status("子模块详细信息：")
        run_git_command(["git", "submodule", "foreach", 'echo "  模块: $name | 路径: $sm_path | URL: $(git remote get-url origin)"'], check=False)
    except:
        print_error("无法获取子模块状态")
        return False
    return True

def init_submodules():
    """初始化子模块"""
    print_header("🔧 初始化子模块")
    
    print_status("正在初始化子模块...")
    try:
        result = run_git_command(["git", "submodule", "init"])
        print_success("子模块初始化完成")
        
        print_status("正在下载子模块内容...")
        run_git_command(["git", "submodule", "update"])
        print_success("子模块内容下载完成")
    except:
        print_error("子模块内容下载失败")
        return False
    return True

def update_submodules():
    """更新子模块"""
    print_header("🔄 更新子模块")
    
    print_status("正在更新所有子模块到最新版本...")
    try:
        run_git_command(["git", "submodule", "update", "--recursive", "--remote"])
        print_success("所有子模块更新完成")
        print()
        show_submodule_status()
    except:
        print_error("子模块更新失败")
        return False
    return True

def reset_submodules():
    """重置子模块"""
    print_header("🔄 重置子模块")
    
    print_warning("这将强制重新下载所有子模块，本地未提交的更改将丢失！")
    response = input("确定要继续吗？ [y/N]: ").strip().lower()
    if response not in ['y', 'yes']:
        print_status("操作已取消")
        return True
    
    print_status("正在重置子模块...")
    
    try:
        run_git_command(["git", "submodule", "deinit", "--all", "-f"])
        print_success("子模块清理完成")
        run_git_command(["git", "submodule", "update", "--init", "--recursive", "--force"])
        print_success("子模块重置完成")
    except:
        print_error("子模块重置失败")
        return False
    return True

def sync_submodules():
    """同步子模块URL"""
    print_header("🔗 同步子模块URL")
    
    print_status("正在同步子模块URL配置...")
    try:
        run_git_command(["git", "submodule", "sync", "--recursive"])
        print_success("子模块URL同步完成")
    except:
        print_error("子模块URL同步失败")
        return False
    return True

def clean_submodules():
    """清理子模块"""
    print_header("🧹 清理子模块")
    
    print_status("正在清理未跟踪的子模块文件...")
    try:
        run_git_command(["git", "submodule", "foreach", "git clean -fd"], check=False)
        print_success("子模块清理完成")
    except:
        pass
    return True

def update_docs_submodule():
    """专门更新docs-public子模块"""
    print_header("📚 更新 docs-public 子模块")
    
    docs_path = REPO_ROOT / "docs-public"
    if not docs_path.exists():
        print_warning("docs-public 子模块不存在，尝试初始化...")
        try:
            run_git_command(["git", "submodule", "update", "--init", "docs-public"])
            print_success("docs-public 子模块初始化完成")
        except:
            print_error("docs-public 子模块初始化失败")
            return False
    
    print_status("正在更新 docs-public 到最新版本...")
    try:
        run_git_command(["git", "submodule", "update", "--remote", "docs-public"])
        print_success("docs-public 更新完成")
        
        # 文档统计
        doc_count = len(list(docs_path.rglob("*.md")))
        example_count = len(list((docs_path / "simple_examples").rglob("*.py"))) if (docs_path / "simple_examples").exists() else 0
        
        print_status("文档统计：")
        print(f"  • Markdown文档: {doc_count} 个")
        print(f"  • 示例代码: {example_count} 个")
        
        # 构建提示
        if (docs_path / "requirements.txt").exists():
            print()
            print_status("💡 构建本地文档：")
            print("  cd docs-public && pip install -r requirements.txt && mkdocs serve")
    except:
        print_error("docs-public 更新失败")
        return False
    return True

def show_usage():
    """显示使用说明"""
    print("SAGE 子模块管理工具")
    print()
    print(f"用法: {sys.argv[0]} [命令]")
    print()
    print("命令:")
    print("  init              初始化所有子模块")
    print("  update            更新所有子模块到最新版本")
    print("  reset             重置所有子模块（强制重新下载）")
    print("  status            显示子模块状态")
    print("  sync              同步子模块URL配置")
    print("  clean             清理未跟踪的子模块文件")
    print("  docs-update       专门更新docs-public子模块")
    print("  help, -h, --help  显示此帮助信息")
    print()
    print("示例:")
    print(f"  {sys.argv[0]} status         # 查看当前子模块状态")
    print(f"  {sys.argv[0]} init          # 初始化所有子模块")
    print(f"  {sys.argv[0]} update        # 更新到最新版本")
    print(f"  {sys.argv[0]} reset         # 强制重置所有子模块")
    print(f"  {sys.argv[0]} docs-update   # 只更新文档子模块")

def main():
    os.chdir(REPO_ROOT)
    check_git_repo()
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?", default="status", choices=["init", "update", "reset", "status", "sync", "clean", "docs-update", "help"])
    parser.add_argument("-h", "--help", action="store_true")
    args = parser.parse_args()
    
    if args.help:
        show_usage()
        return
    
    command = args.command
    success = True
    if command == "init":
        success = init_submodules()
    elif command == "update":
        success = update_submodules()
    elif command == "reset":
        success = reset_submodules()
    elif command == "status":
        success = show_submodule_status()
    elif command == "sync":
        success = sync_submodules()
    elif command == "clean":
        success = clean_submodules()
    elif command == "docs-update":
        success = update_docs_submodule()
    else:
        print_error(f"未知命令: {command}")
        print()
        show_usage()
        sys.exit(1)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()