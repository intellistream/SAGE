# Converted from common_utils.sh
# SAGE 项目通用工具模块
# 提供常用的工具函数

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
import logging
from typing import Optional, List

# 假设 logging 已配置，或使用标准 logging
try:
    from sage_tools.utils.logging import setup_logging, print_error, print_debug, print_status, print_warning
    setup_logging()
except ImportError:
    # Fallback to standard logging
    logging.basicConfig(level=logging.INFO)
    print_error = lambda msg: logging.error(msg)
    print_debug = lambda msg: logging.debug(msg)
    print_status = lambda msg: logging.info(msg)
    print_warning = lambda msg: logging.warning(msg)


def check_command(command: str) -> bool:
    """检查命令是否存在（必需）"""
    if shutil.which(command) is None:
        print_error(f"{command} 未安装，请先安装 {command}")
        return False
    return True


def check_command_optional(command: str) -> bool:
    """检查命令是否存在（可选）"""
    return shutil.which(command) is not None


def check_file_exists(file_path: str, description: Optional[str] = None) -> bool:
    """检查文件是否存在"""
    if description is None:
        description = "文件"
    if not os.path.isfile(file_path):
        print_error(f"{description} 不存在: {file_path}")
        return False
    return True


def check_dir_exists(dir_path: str, description: Optional[str] = None) -> bool:
    """检查目录是否存在"""
    if description is None:
        description = "目录"
    if not os.path.isdir(dir_path):
        print_error(f"{description} 不存在: {dir_path}")
        return False
    return True


def get_script_dir() -> str:
    """获取脚本绝对路径"""
    return os.path.dirname(os.path.abspath(__file__))


def find_project_root(current_dir: Optional[str] = None, marker_file: str = "pyproject.toml") -> Optional[str]:
    """查找项目根目录"""
    if current_dir is None:
        current_dir = os.getcwd()
    current_path = Path(current_dir).resolve()
    while current_path != current_path.parent:
        if (current_path / marker_file).exists():
            return str(current_path)
        current_path = current_path.parent
    return None


def validate_project_structure(project_root: str) -> bool:
    """验证项目目录结构"""
    required_files = ["pyproject.toml"]
    required_dirs = ["packages"]

    for file in required_files:
        if not check_file_exists(os.path.join(project_root, file), f"项目文件 {file}"):
            return False

    for dir in required_dirs:
        if not check_dir_exists(os.path.join(project_root, dir), f"项目目录 {dir}"):
            return False

    return True


def setup_project_env(project_root: str) -> None:
    """设置项目环境变量"""
    os.environ["SAGE_PROJECT_ROOT"] = project_root
    os.environ["SAGE_PACKAGES_DIR"] = os.path.join(project_root, "packages")
    os.environ["SAGE_SCRIPTS_DIR"] = os.path.join(project_root, "scripts")
    os.environ["SAGE_DOCS_DIR"] = os.path.join(project_root, "docs")
    os.environ["SAGE_TESTS_DIR"] = os.path.join(project_root, "tests")

    print_debug("设置项目环境变量:")
    print_debug(f"  SAGE_PROJECT_ROOT={os.environ['SAGE_PROJECT_ROOT']}")
    print_debug(f"  SAGE_PACKAGES_DIR={os.environ['SAGE_PACKAGES_DIR']}")
    print_debug(f"  SAGE_SCRIPTS_DIR={os.environ['SAGE_SCRIPTS_DIR']}")


def run_command(cmd: str, description: Optional[str] = None) -> bool:
    """执行命令并捕获输出"""
    if description is None:
        description = "执行命令"
    print_debug(f"执行命令: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print_debug(f"{description} 成功")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"{description} 失败 (退出码: {e.returncode})")
        return False


def safe_cd(target_dir: str, description: Optional[str] = None) -> bool:
    """安全地改变目录"""
    if description is None:
        description = "切换到目录"
    if not check_dir_exists(target_dir, description):
        return False

    try:
        os.chdir(target_dir)
        print_debug(f"已切换到目录: {os.getcwd()}")
        return True
    except OSError:
        print_error(f"无法切换到目录: {target_dir}")
        return False


def backup_file(file_path: str, backup_suffix: Optional[str] = None) -> None:
    """备份文件"""
    if backup_suffix is None:
        backup_suffix = f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if os.path.isfile(file_path):
        backup_path = f"{file_path}{backup_suffix}"
        shutil.copy2(file_path, backup_path)
        print_status(f"已备份文件: {file_path} -> {backup_path}")


def ensure_dir(dir_path: str) -> None:
    """创建目录（如果不存在）"""
    os.makedirs(dir_path, exist_ok=True)
    print_debug(f"创建目录: {dir_path}")


def check_disk_space(path: str = ".", required_mb: int = 1000) -> bool:
    """检查磁盘空间"""
    total, used, free = shutil.disk_usage(path)
    available_mb = free // (2**20)
    if available_mb < required_mb:
        print_warning(f"磁盘空间不足: 需要 {required_mb}MB，可用 {available_mb}MB")
        return False
    print_debug(f"磁盘空间检查通过: 可用 {available_mb}MB")
    return True


def check_network(test_url: str = "https://github.com") -> bool:
    """检查网络连接"""
    try:
        import requests
        response = requests.head(test_url, timeout=5)
        if response.status_code == 200:
            print_debug("网络连接正常")
            return True
    except ImportError:
        # Fallback to curl if requests not available
        if check_command_optional("curl"):
            result = subprocess.run(["curl", "-s", "--head", test_url], capture_output=True)
            if result.returncode == 0:
                print_debug("网络连接正常")
                return True
    except:
        pass

    print_warning("网络连接检查失败")
    return False


def wait_for_key(message: Optional[str] = None) -> None:
    """等待用户按键"""
    if message is None:
        message = "按任意键继续..."
    input(message)


def show_usage(script_name: str, description: str, options: Optional[List[str]] = None) -> None:
    """显示帮助信息"""
    if options is None:
        options = []
    print(f"用法: {script_name} [选项]")
    print()
    print(f"描述: {description}")
    print()
    if options:
        print("选项:")
        for option in options:
            print(f"  {option}")
        print()


def main():
    """主函数 - 对于工具模块，直接运行时显示用法"""
    parser = argparse.ArgumentParser(description="SAGE 通用工具模块")
    parser.add_argument("--help", action="help", help="显示帮助信息")
    args = parser.parse_args()
    show_usage("common_utils.py", "SAGE 项目通用工具模块", [])


if __name__ == "__main__":
    main()