#!/usr/bin/env python3
"""
SAGE 一键安装脚本
==============

这个脚本提供 SAGE 框架的一键安装功能，支持不同的安装模式：
1. 纯 Python 安装（推荐用于快速体验）
2. 完整安装（包含 C++ 扩展，需要编译环境）

使用方法:
    python install.py                 # 交互式安装
    python install.py --python-only   # 仅安装 Python 部分
    python install.py --full         # 完整安装（需要编译环境）
    python install.py --check        # 检查安装状态
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path

class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'  
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️ {msg}{Colors.RESET}")

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️ {msg}{Colors.RESET}")

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
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        raise

def check_python_version():
    """检查 Python 版本"""
    print_info("检查 Python 版本...")
    if sys.version_info < (3, 11):
        print_error(f"SAGE 需要 Python 3.11 或更高版本，当前版本: {sys.version}")
        return False
    print_success(f"Python 版本: {sys.version.split()[0]} ✓")
    return True

def check_pip():
    """检查 pip"""
    print_info("检查 pip...")
    try:
        result = run_command([sys.executable, "-m", "pip", "--version"])
        print_success(f"pip 可用 ✓")
        return True
    except:
        print_error("pip 不可用")
        return False

def check_build_tools():
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

def install_python_only():
    """仅安装 Python 部分"""
    print_info("开始纯 Python 安装...")
    
    try:
        # 升级 pip
        print_info("升级 pip...")
        run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # 安装基础依赖
        print_info("安装基础构建工具...")
        run_command([sys.executable, "-m", "pip", "install", "setuptools", "wheel"])
        
        # 安装 SAGE（仅 Python 部分）
        print_info("安装 SAGE Python 包...")
        if Path("pyproject.toml").exists():
            # 使用 pyproject.toml
            run_command([sys.executable, "-m", "pip", "install", "-e", ".", "--no-build-isolation"])
        else:
            # 回退到 setup.py
            run_command([sys.executable, "-m", "pip", "install", "-e", "."])
        
        print_success("🎉 SAGE Python 部分安装成功！")
        return True
        
    except Exception as e:
        print_error(f"安装失败: {e}")
        return False

def install_full():
    """完整安装（包含 C++ 扩展）"""
    print_info("开始完整安装...")
    
    # 检查构建工具
    if not check_build_tools():
        print_error("缺少必要的构建工具，无法进行完整安装")
        print_info("请安装以下工具后重试:")
        print("  - gcc/g++ (C++ 编译器)")
        print("  - cmake (构建系统)")
        print("  - make (构建工具)")
        return False
    
    try:
        # 先安装 Python 部分
        if not install_python_only():
            return False
        
        # 构建 C++ 扩展
        print_info("构建 C++ 扩展...")
        
        # 检查并构建 sage_queue
        sage_queue_dir = Path("sage_ext/sage_queue")
        if sage_queue_dir.exists():
            print_info("构建 sage_queue 扩展...")
            build_script = sage_queue_dir / "build.sh"
            if build_script.exists():
                result = run_command(["bash", str(build_script)], check=False)
                if result.returncode == 0:
                    print_success("sage_queue 构建成功 ✓")
                else:
                    print_warning("sage_queue 构建失败，但继续安装...")
            else:
                print_warning("未找到 sage_queue 构建脚本")
        
        # 检查并构建 sage_db
        sage_db_dir = Path("sage_ext/sage_db")
        if sage_db_dir.exists():
            print_info("构建 sage_db 扩展...")
            build_script = sage_db_dir / "build.sh"
            if build_script.exists():
                result = run_command(["bash", str(build_script)], check=False)
                if result.returncode == 0:
                    print_success("sage_db 构建成功 ✓")
                else:
                    print_warning("sage_db 构建失败，但继续安装...")
            else:
                print_warning("未找到 sage_db 构建脚本")
        
        print_success("🎉 SAGE 完整安装成功！")
        return True
        
    except Exception as e:
        print_error(f"完整安装失败: {e}")
        return False

def check_installation():
    """检查安装状态"""
    print_info("检查 SAGE 安装状态...")
    
    try:
        # 检查 sage 包
        result = run_command([sys.executable, "-c", "import sage; print(f'SAGE version: {sage.__version__}')"])
        print_success("SAGE Python 包 ✓")
        
        # 检查 CLI 命令
        result = run_command([sys.executable, "-c", "from sage.cli.main import app; print('CLI available')"], check=False)
        if result.returncode == 0:
            print_success("SAGE CLI ✓")
        else:
            print_warning("SAGE CLI 不可用")
        
        # 检查 C++ 扩展
        result = run_command([sys.executable, "-c", "import sage_ext; print('C++ extensions available')"], check=False)
        if result.returncode == 0:
            print_success("C++ 扩展 ✓")
        else:
            print_warning("C++ 扩展不可用")
        
        print_success("✨ 安装状态检查完成")
        return True
        
    except Exception as e:
        print_error(f"SAGE 未正确安装: {e}")
        return False

def interactive_install():
    """交互式安装"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("=" * 60)
    print("     SAGE 框架一键安装向导")
    print("=" * 60)
    print(f"{Colors.RESET}")
    
    print(f"{Colors.YELLOW}💡 安装说明:{Colors.RESET}")
    print("• 纯Python安装: 使用 'pip install .' 即可完成基础安装")
    print("• 完整安装: 需要此脚本来正确构建C++扩展")
    print()
    
    print("选择安装模式:")
    print("1. 纯 Python 安装 (推荐，快速安装)")
    print("2. 完整安装 (包含 C++ 扩展，需要编译环境)")
    print("3. 检查安装状态")
    print("4. 退出")
    
    while True:
        choice = input(f"\n{Colors.YELLOW}请选择 (1-4): {Colors.RESET}").strip()
        
        if choice == "1":
            return install_python_only()
        elif choice == "2":
            return install_full()
        elif choice == "3":
            return check_installation()
        elif choice == "4":
            print("安装已取消")
            return True
        else:
            print_error("无效选择，请输入 1-4")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="SAGE 一键安装脚本")
    parser.add_argument("--python-only", action="store_true", help="仅安装 Python 部分")
    parser.add_argument("--full", action="store_true", help="完整安装（包含 C++ 扩展）")
    parser.add_argument("--check", action="store_true", help="检查安装状态")
    
    args = parser.parse_args()
    
    # 基础检查
    if not check_python_version() or not check_pip():
        sys.exit(1)
    
    try:
        if args.python_only:
            success = install_python_only()
        elif args.full:
            success = install_full()
        elif args.check:
            success = check_installation()
        else:
            success = interactive_install()
        
        if success:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 操作成功完成！{Colors.RESET}")
            if not args.check:
                print(f"\n{Colors.BLUE}下一步：{Colors.RESET}")
                print("• 测试安装: python -c 'import sage; print(sage.__version__)'")
                print("• 查看帮助: sage --help")
                print("• 运行示例: 查看 app/ 目录下的示例代码")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ 操作失败{Colors.RESET}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}安装被用户取消{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print_error(f"安装过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
