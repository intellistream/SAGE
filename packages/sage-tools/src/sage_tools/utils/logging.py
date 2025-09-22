# Converted from .sh for Python packaging
# SAGE 项目日志工具模块
# 提供统一的彩色日志输出功能

import os
import sys
import datetime

# 尝试加载配置
try:
    from sage_tools.utils.config import set_sage_config
    set_sage_config()
except ImportError:
    pass

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
PURPLE = '\033[0;35m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

def print_status(message):
    """打印带颜色的消息 - INFO"""
    print(f"{BLUE}[INFO]{NC} {message}")

def print_success(message):
    """打印成功消息"""
    print(f"{GREEN}[SUCCESS]{NC} {message}")

def print_warning(message):
    """打印警告消息"""
    print(f"{YELLOW}[WARNING]{NC} {message}")

def print_error(message):
    """打印错误消息"""
    print(f"{RED}[ERROR]{NC} {message}")

def print_header(message):
    """打印标题"""
    print(f"\n{PURPLE}================================{NC}")
    print(f"{PURPLE}{message}{NC}")
    print(f"{PURPLE}================================{NC}\n")

def print_debug(message):
    """打印调试消息（仅当 SAGE_DEBUG=1 时）"""
    if os.environ.get('SAGE_DEBUG', '0') == '1':
        print(f"{CYAN}[DEBUG]{NC} {message}")

def print_timestamped(level, message):
    """带时间戳的日志"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if level == "INFO":
        print(f"{BLUE}[{timestamp}][INFO]{NC} {message}")
    elif level == "SUCCESS":
        print(f"{GREEN}[{timestamp}][SUCCESS]{NC} {message}")
    elif level == "WARNING":
        print(f"{YELLOW}[{timestamp}][WARNING]{NC} {message}")
    elif level == "ERROR":
        print(f"{RED}[{timestamp}][ERROR]{NC} {message}")
    else:
        print(f"[{timestamp}][{level}] {message}")

def print_progress(current, total, description):
    """进度条显示"""
    width = 50
    percentage = (current * 100) // total
    filled = (current * width) // total
    empty = width - filled
    
    progress_bar = '#' * filled + '-' * empty
    sys.stdout.write(f"\r{BLUE}[INFO]{NC} {description} [{progress_bar}] {percentage}%")
    sys.stdout.flush()
    
    if current == total:
        print()

def confirm_action(message, default='n'):
    """确认提示"""
    if default == 'y':
        prompt = f"{message} [Y/n]: "
    else:
        prompt = f"{message} [y/N]: "
    
    response = input(prompt).strip()
    response = response or default
    
    return response.lower() in ['y', 'yes']

def is_tty():
    """检查是否为TTY（支持颜色输出）"""
    return sys.stdout.isatty()

def disable_colors():
    """禁用颜色输出（用于管道或重定向）"""
    global RED, GREEN, YELLOW, BLUE, PURPLE, CYAN, NC
    RED = GREEN = YELLOW = BLUE = PURPLE = CYAN = NC = ''

def main():
    """Main function to initialize logging setup."""
    if not is_tty():
        disable_colors()

if __name__ == "__main__":
    main()