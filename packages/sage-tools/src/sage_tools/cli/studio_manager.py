# Converted from .sh for Python packaging
# SAGE Studio 启动脚本
# 用于启动和管理 Studio 前端服务

import os
import sys
import subprocess
import shutil
import signal
from pathlib import Path
from argparse import ArgumentParser

try:
    from sage_tools.utils.logging import print_info, print_success, print_warning, print_error
except ImportError:
    def print_info(msg): print(f"ℹ️  {msg}")
    def print_success(msg): print(f"✅ {msg}")
    def print_warning(msg): print(f"⚠️  {msg}")
    def print_error(msg): print(f"❌ {msg}")

SCRIPT_DIR = Path(__file__).parent
SAGE_ROOT = SCRIPT_DIR.parent

STUDIO_DIR = SAGE_ROOT / "packages" / "sage-common" / "src" / "sage" / "common" / "frontend" / "studio"
STUDIO_PORT = 4200
STUDIO_HOST = "0.0.0.0"
RUN_DIR = Path.home() / ".sage" / "run"
PID_FILE = RUN_DIR / "sage-studio.pid"
LOG_DIR = Path.home() / ".sage" / "logs"
LOG_FILE = LOG_DIR / "sage-studio.log"

def ensure_dirs():
    """确保目录存在"""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(str(LOG_DIR), 0o700)

def check_dependencies():
    """检查依赖"""
    print_info("检查依赖...")
    
    # 检查 Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, check=True)
        node_version = result.stdout.strip().lstrip('v').split('.')[0]
        if int(node_version) < 18:
            print_error(f"Node.js 版本过低，需要 18+，当前版本: {result.stdout.strip()}")
            sys.exit(1)
        print_success("Node.js 检查通过")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Node.js 未安装，请先安装 Node.js 18+")
        sys.exit(1)
    
    # 检查 npm
    try:
        subprocess.run(['npm', '--version'], capture_output=True, check=True)
        print_success("npm 检查通过")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("npm 未安装")
        sys.exit(1)
    
    # 检查项目目录
    if not STUDIO_DIR.exists():
        print_error(f"Studio 项目目录不存在: {STUDIO_DIR}")
        sys.exit(1)
    
    print_success("依赖检查通过")

def install_dependencies():
    """安装依赖"""
    print_info("安装 Studio 依赖...")
    
    os.chdir(STUDIO_DIR)
    
    if not (STUDIO_DIR / "node_modules").exists() or not (STUDIO_DIR / "package-lock.json").exists():
        print_info("正在安装 npm 依赖...")
        result = subprocess.run(['npm', 'install'], check=True)
        if result.returncode == 0:
            print_success("依赖安装完成")
        else:
            print_error("依赖安装失败")
            sys.exit(1)
    else:
        print_info("依赖已存在，跳过安装")

def start_studio():
    """启动 Studio"""
    print_info("启动 SAGE Studio...")
    
    # 检查是否已经运行
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            if os.kill(pid, 0) == 0:  # 进程存在
                print_warning(f"Studio 已经在运行 (PID: {pid})")
                print_info(f"访问地址: http://localhost:{STUDIO_PORT}")
                return
        except (ValueError, OSError):
            PID_FILE.unlink()  # 清理无效 PID 文件
    
    os.chdir(STUDIO_DIR)
    
    # 后台启动
    with open(LOG_FILE, 'a') as log_f:
        process = subprocess.Popen(['npm', 'start'], stdout=log_f, stderr=log_f)
    
    # 保存 PID
    with open(PID_FILE, 'w') as f:
        f.write(str(process.pid))
    
    # 等待启动
    print_info("等待服务启动...")
    subprocess.run(['sleep', '5'])
    
    # 检查是否启动成功
    if os.kill(process.pid, 0) == 0:
        print_success("Studio 启动成功!")
        print_info(f"PID: {process.pid}")
        print_info(f"访问地址: http://localhost:{STUDIO_PORT}")
        print_info(f"日志文件: {LOG_FILE}")
    else:
        print_error("Studio 启动失败")
        PID_FILE.unlink()
        sys.exit(1)

def stop_studio():
    """停止 Studio"""
    print_info("停止 SAGE Studio...")
    
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            if os.kill(pid, 0) == 0:
                os.kill(pid, signal.SIGTERM)
                subprocess.run(['sleep', '2'])
                
                # 等待进程退出，最多 10 秒
                timeout = 10
                while timeout > 0:
                    if os.kill(pid, 0) != 0:
                        break
                    subprocess.run(['sleep', '1'])
                    timeout -= 1
                
                # 强制杀死如果还在运行
                if os.kill(pid, 0) == 0:
                    print_warning("进程未能在规定时间内退出，强制杀死 (SIGKILL)")
                    os.kill(pid, signal.SIGKILL)
                
                PID_FILE.unlink()
                print_success("Studio 已停止")
            else:
                print_warning("Studio 进程不存在")
                PID_FILE.unlink()
        except (ValueError, OSError):
            print_warning("Studio 进程不存在")
            PID_FILE.unlink()
    else:
        print_warning("Studio 未运行")

def check_status():
    """检查状态"""
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            if os.kill(pid, 0) == 0:
                print_success(f"Studio 正在运行 (PID: {pid})")
                print_info(f"访问地址: http://localhost:{STUDIO_PORT}")
                
                # 检查端口 (使用 lsof or netstat if available)
                try:
                    result = subprocess.run(['lsof', '-i', f':{STUDIO_PORT}'], capture_output=True, text=True)
                    if result.returncode == 0 and 'LISTEN' in result.stdout:
                        print_success(f"端口 {STUDIO_PORT} 监听正常")
                    else:
                        print_warning(f"端口 {STUDIO_PORT} 未监听")
                except FileNotFoundError:
                    print_warning("无法检查端口 (lsof 未安装)")
            else:
                print_error("Studio 进程不存在 (PID文件存在但进程已死)")
                PID_FILE.unlink()
        except (ValueError, OSError):
            print_error("Studio 进程不存在 (PID文件存在但进程已死)")
            PID_FILE.unlink()
    else:
        print_warning("Studio 未运行")

def show_logs():
    """查看日志"""
    if LOG_FILE.exists():
        print_info("显示最近 50 行日志:")
        print()
        result = subprocess.run(['tail', '-n', '50', LOG_FILE], capture_output=True, text=True)
        print(result.stdout)
    else:
        print_warning(f"日志文件不存在: {LOG_FILE}")

def main():
    parser = ArgumentParser(description="SAGE Studio 启动脚本")
    parser.add_argument('command', choices=['start', 'stop', 'restart', 'status', 'logs', 'install'], help="命令")
    args = parser.parse_args()
    
    ensure_dirs()
    
    if args.command == 'start':
        check_dependencies()
        install_dependencies()
        start_studio()
    elif args.command == 'stop':
        stop_studio()
    elif args.command == 'restart':
        stop_studio()
        subprocess.run(['sleep', '2'])
        check_dependencies()
        install_dependencies()
        start_studio()
    elif args.command == 'status':
        check_status()
    elif args.command == 'logs':
        show_logs()
    elif args.command == 'install':
        check_dependencies()
        install_dependencies()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()