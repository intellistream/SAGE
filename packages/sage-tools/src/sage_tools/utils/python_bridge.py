# Converted from .sh for Python packaging
# SAGE Python工具接口
# 为脚本提供Python工具的接口函数

import os
import sys
import subprocess

try:
    from sage_tools.utils.logging import (
        print_status, print_success, print_warning, print_error,
        print_header
    )
except ImportError:
    def print_status(msg): print(f"[INFO] {msg}")
    def print_success(msg): print(f"[SUCCESS] {msg}")
    def print_warning(msg): print(f"[WARNING] {msg}")
    def print_error(msg): print(f"[ERROR] {msg}")
    def print_header(msg): print(f"\n{'='*32}\n{msg}\n{'='*32}\n")

# 获取Python helper的路径
def get_python_helper_path(project_root):
    return os.path.join(project_root, 'packages', 'sage-common', 'src', 'sage', 'common', 'internal', '_quickstart_helper.py')

def check_python_helper(project_root):
    """检查Python helper是否存在"""
    helper_path = get_python_helper_path(project_root)
    if not os.path.isfile(helper_path):
        print_error(f"Python助手不存在: {helper_path}")
        print_status("请确保已正确克隆项目或安装sage-common包")
        return False
    return True

def py_check_system(project_root):
    """检查系统"""
    if not check_python_helper(project_root):
        return "FAILURE: Helper not found", 1
    helper_path = get_python_helper_path(project_root)
    result = subprocess.run([sys.executable, helper_path, 'check-system'], 
                            capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if result.returncode == 0 and output.startswith('SUCCESS:'):
        return output, 0
    else:
        return result.stderr or output or "FAILURE: Unknown error", 1

def py_list_conda_envs(project_root):
    """列出conda环境"""
    if not check_python_helper(project_root):
        return "FAILURE: Helper not found", 1
    helper_path = get_python_helper_path(project_root)
    result = subprocess.run([sys.executable, helper_path, 'list-conda-envs'], 
                            capture_output=True, text=True, timeout=30)
    return result.stdout, result.returncode

def py_check_conda_env(project_root, env_name):
    """检查conda环境是否存在"""
    if not check_python_helper(project_root):
        return False
    helper_path = get_python_helper_path(project_root)
    result = subprocess.run([sys.executable, helper_path, 'check-conda-env', env_name], 
                            capture_output=True, text=True, timeout=30)
    return result.stdout.strip() == 'EXISTS' and result.returncode == 0

def py_create_conda_env(project_root, env_name, python_version='3.11'):
    """创建conda环境"""
    if not check_python_helper(project_root):
        return "FAILURE: Helper not found", 1
    helper_path = get_python_helper_path(project_root)
    result = subprocess.run([sys.executable, helper_path, 'create-conda-env', env_name, python_version], 
                            capture_output=True, text=True, timeout=300)
    output = result.stdout.strip()
    if result.returncode == 0 and output.startswith('SUCCESS:'):
        return output, 0
    else:
        return result.stderr or output or "FAILURE: Unknown error", 1

def py_install_requirements(project_root):
    """安装requirements"""
    if not check_python_helper(project_root):
        return "FAILURE: Helper not found", 1
    helper_path = get_python_helper_path(project_root)
    result = subprocess.run([sys.executable, helper_path, 'install-requirements', project_root], 
                            capture_output=True, text=True, timeout=600)
    output = result.stdout.strip()
    if result.returncode == 0 and output.startswith('SUCCESS:'):
        return output, 0
    else:
        return result.stderr or output or "FAILURE: Unknown error", 1

def py_test_installation(project_root):
    """测试安装"""
    if not check_python_helper(project_root):
        return "FAILURE: Helper not found", 1
    helper_path = get_python_helper_path(project_root)
    result = subprocess.run([sys.executable, helper_path, 'test-installation'], 
                            capture_output=True, text=True, timeout=300)
    output = result.stdout.strip()
    if result.returncode == 0 and output.startswith('SUCCESS:'):
        return output, 0
    else:
        return result.stderr or output or "FAILURE: Unknown error", 1

def py_get_system_info(project_root):
    """获取系统信息"""
    if not check_python_helper(project_root):
        return "FAILURE: Helper not found", 1
    helper_path = get_python_helper_path(project_root)
    result = subprocess.run([sys.executable, helper_path, 'get-system-info'], 
                            capture_output=True, text=True, timeout=30)
    return result.stdout, result.returncode

def main():
    """Main function to test Python bridge."""
    # Find project root if not set
    project_root = os.environ.get('SAGE_PROJECT_ROOT', os.getcwd())
    if not os.path.isfile(os.path.join(project_root, 'pyproject.toml')):
        project_root = find_project_root(project_root)  # Assume common_utils available
        if not project_root:
            print_error("无法找到项目根目录")
            sys.exit(1)
    check_python_helper(project_root)

if __name__ == "__main__":
    main()