#!/usr/bin/env python3
"""
SAGE Extensions Manager
======================

管理SAGE框架的C++扩展安装和检查
"""

import sys
import subprocess
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(name="extensions", help="🧩 扩展管理 - 安装和管理C++扩展")

class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'  
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_info(msg: str):
    typer.echo(f"{Colors.BLUE}ℹ️ {msg}{Colors.RESET}")

def print_success(msg: str):
    typer.echo(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg: str):
    typer.echo(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_warning(msg: str):
    typer.echo(f"{Colors.YELLOW}⚠️ {msg}{Colors.RESET}")

def run_command(cmd, check=True):
    """运行命令"""
    print_info(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        result = subprocess.run(cmd, shell=isinstance(cmd, str), check=check, 
                              capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e}")
        if e.stdout:
            typer.echo(f"STDOUT: {e.stdout}")
        if e.stderr:
            typer.echo(f"STDERR: {e.stderr}")
        raise

def check_build_tools() -> bool:
    """检查构建工具"""
    print_info("检查构建工具...")
    tools_available = True
    
    # 检查 gcc/g++
    try:
        result = run_command(["gcc", "--version"], check=False)
        if result.returncode == 0:
            print_success("gcc 可用 ✓")
        else:
            print_warning("gcc 不可用")
            tools_available = False
    except:
        print_warning("gcc 不可用")
        tools_available = False
    
    # 检查 cmake
    try:
        result = run_command(["cmake", "--version"], check=False)
        if result.returncode == 0:
            print_success("cmake 可用 ✓")
        else:
            print_warning("cmake 不可用")
            tools_available = False
    except:
        print_warning("cmake 不可用")
        tools_available = False
    
    return tools_available

def find_sage_root() -> Optional[Path]:
    """查找SAGE项目根目录"""
    current = Path.cwd()
    
    # 向上查找包含sage_ext目录的路径
    for parent in [current] + list(current.parents):
        sage_ext_dir = parent / "sage_ext"
        if sage_ext_dir.exists() and sage_ext_dir.is_dir():
            return parent
    
    # 检查当前Python环境中的sage包位置
    try:
        import sage
        sage_path = Path(sage.__file__).parent.parent
        sage_ext_dir = sage_path / "sage_ext"
        if sage_ext_dir.exists():
            return sage_path
    except ImportError:
        pass
    
    return None

@app.command()
def install(
    extension: Optional[str] = typer.Argument(None, help="要安装的扩展名 (sage_queue, sage_db, 或 all)"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新构建")
):
    """
    安装C++扩展
    
    Examples:
        sage extensions install                # 安装所有扩展
        sage extensions install sage_queue    # 只安装队列扩展
        sage extensions install sage_db       # 只安装数据库扩展
        sage extensions install all --force   # 强制重新安装所有扩展
    """
    typer.echo(f"{Colors.BOLD}{Colors.BLUE}🧩 SAGE C++ 扩展安装器{Colors.RESET}")
    typer.echo("=" * 50)
    
    # 检查构建工具
    if not check_build_tools():
        print_error("缺少必要的构建工具，无法安装C++扩展")
        typer.echo("\n请安装以下工具:")
        typer.echo("  • gcc/g++ (C++ 编译器)")
        typer.echo("  • cmake (构建系统)")
        typer.echo("  • make (构建工具)")
        typer.echo("\nUbuntu/Debian: sudo apt install build-essential cmake")
        typer.echo("CentOS/RHEL: sudo yum groupinstall 'Development Tools' && sudo yum install cmake")
        typer.echo("macOS: xcode-select --install && brew install cmake")
        raise typer.Exit(1)
    
    # 查找SAGE根目录
    sage_root = find_sage_root()
    if not sage_root:
        print_error("未找到SAGE项目根目录")
        typer.echo("请在SAGE项目目录中运行此命令")
        raise typer.Exit(1)
    
    print_info(f"SAGE项目根目录: {sage_root}")
    
    # 确定要安装的扩展
    extensions_to_install = []
    if extension is None or extension == "all":
        extensions_to_install = ["sage_queue", "sage_db"]
    else:
        extensions_to_install = [extension]
    
    success_count = 0
    total_count = len(extensions_to_install)
    
    for ext_name in extensions_to_install:
        typer.echo(f"\n{Colors.YELLOW}━━━ 安装 {ext_name} ━━━{Colors.RESET}")
        
        ext_dir = sage_root / "sage_ext" / ext_name
        if not ext_dir.exists():
            print_warning(f"扩展目录不存在: {ext_dir}")
            continue
        
        # 查找构建脚本
        build_script = ext_dir / "build.sh"
        if not build_script.exists():
            print_warning(f"未找到构建脚本: {build_script}")
            continue
        
        try:
            # 如果需要强制重建，先清理
            if force:
                build_dir = ext_dir / "build"
                if build_dir.exists():
                    print_info(f"清理构建目录: {build_dir}")
                    import shutil
                    shutil.rmtree(build_dir)
            
            # 执行构建
            print_info(f"构建 {ext_name}...")
            result = run_command(["bash", str(build_script)], check=False)
            
            if result.returncode == 0:
                print_success(f"{ext_name} 构建成功 ✓")
                success_count += 1
            else:
                print_error(f"{ext_name} 构建失败")
                if result.stderr:
                    typer.echo(f"错误信息: {result.stderr}")
                    
        except Exception as e:
            print_error(f"{ext_name} 构建失败: {e}")
    
    # 总结
    typer.echo(f"\n{Colors.BOLD}安装完成{Colors.RESET}")
    typer.echo(f"成功: {success_count}/{total_count}")
    
    if success_count == total_count:
        print_success("🎉 所有扩展安装成功！")
        typer.echo("\n运行 'sage extensions status' 验证安装")
    else:
        print_warning(f"⚠️ 部分扩展安装失败 ({total_count - success_count}个)")

@app.command()
def status():
    """检查扩展安装状态"""
    typer.echo(f"{Colors.BOLD}{Colors.BLUE}🔍 SAGE 扩展状态检查{Colors.RESET}")
    typer.echo("=" * 40)
    
    extensions = {
        "sage_ext": "扩展包基础模块",
        "sage_ext.sage_queue": "队列扩展 (C++)",
        "sage_ext.sage_db": "数据库扩展 (C++)"
    }
    
    available_count = 0
    
    for module_name, description in extensions.items():
        try:
            __import__(module_name)
            print_success(f"{description} ✓")
            available_count += 1
        except ImportError as e:
            print_warning(f"{description} ✗")
            typer.echo(f"  原因: {e}")
    
    typer.echo(f"\n总计: {available_count}/{len(extensions)} 扩展可用")
    
    if available_count < len(extensions):
        typer.echo(f"\n{Colors.YELLOW}💡 提示:{Colors.RESET}")
        typer.echo("运行 'sage extensions install' 安装缺失的扩展")

@app.command()
def clean():
    """清理扩展构建文件"""
    typer.echo(f"{Colors.BOLD}{Colors.BLUE}🧹 清理扩展构建文件{Colors.RESET}")
    
    sage_root = find_sage_root()
    if not sage_root:
        print_error("未找到SAGE项目根目录")
        raise typer.Exit(1)
    
    import shutil
    cleaned_count = 0
    
    for ext_name in ["sage_queue", "sage_db"]:
        ext_dir = sage_root / "sage_ext" / ext_name
        if not ext_dir.exists():
            continue
            
        # 清理build目录
        build_dir = ext_dir / "build"
        if build_dir.exists():
            print_info(f"清理 {ext_name}/build")
            shutil.rmtree(build_dir)
            cleaned_count += 1
        
        # 清理编译产物
        for pattern in ["*.so", "*.o", "*.a"]:
            for file in ext_dir.rglob(pattern):
                if file.is_file():
                    print_info(f"删除 {file.relative_to(sage_root)}")
                    file.unlink()
    
    if cleaned_count > 0:
        print_success(f"清理完成，共处理 {cleaned_count} 个目录")
    else:
        typer.echo("没有需要清理的文件")

@app.command()
def info():
    """显示扩展信息"""
    typer.echo(f"{Colors.BOLD}{Colors.BLUE}📋 SAGE C++ 扩展信息{Colors.RESET}")
    typer.echo("=" * 50)
    
    extensions_info = {
        "sage_queue": {
            "description": "高性能队列实现",
            "features": ["Ring Buffer", "无锁队列", "内存映射"],
            "status": "stable"
        },
        "sage_db": {
            "description": "数据库接口扩展", 
            "features": ["原生C++接口", "高性能查询", "内存优化"],
            "status": "experimental"
        }
    }
    
    for ext_name, info in extensions_info.items():
        typer.echo(f"\n{Colors.YELLOW}{ext_name}{Colors.RESET}")
        typer.echo(f"  描述: {info['description']}")
        typer.echo(f"  特性: {', '.join(info['features'])}")
        typer.echo(f"  状态: {info['status']}")
        
        # 检查是否已安装
        try:
            __import__(f"sage_ext.{ext_name}")
            typer.echo(f"  安装: {Colors.GREEN}✓ 已安装{Colors.RESET}")
        except ImportError:
            typer.echo(f"  安装: {Colors.RED}✗ 未安装{Colors.RESET}")

if __name__ == "__main__":
    app()
