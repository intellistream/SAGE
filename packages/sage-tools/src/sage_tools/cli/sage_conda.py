# Converted from .sh for Python packaging
# 用于在 conda 环境中执行 sage 命令的包装脚本

import os
import sys
import subprocess
from pathlib import Path

def get_conda_env():
    """确定 conda 环境"""
    if 'CONDA_PREFIX' in os.environ:
        conda_env = os.environ['CONDA_PREFIX']
        print(f"Using current conda environment: {conda_env}")
        return conda_env
    else:
        # 尝试使用 sage 环境
        try:
            result = subprocess.run(['conda', 'env', 'list'], capture_output=True, text=True, check=True)
            for line in result.stdout.split('\n'):
                if 'sage' in line and line.strip():
                    conda_env = line.split()[1]
                    print(f"Using detected sage conda environment: {conda_env}")
                    return conda_env
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        print("Error: Not in a conda environment and no 'sage' environment found.")
        print("Please activate your conda environment first:")
        print("  conda activate sage")
        sys.exit(1)
    return None

def main():
    conda_env = get_conda_env()
    python_path = os.path.join(conda_env, 'bin', 'python')
    
    if not os.path.isfile(python_path):
        print(f"Error: Python executable not found at {python_path}")
        sys.exit(1)
    
    print(f"Using Python: {python_path}")
    print(f"Command: {' '.join(sys.argv[1:])}")
    print("---")
    
    # 执行命令
    result = subprocess.run([python_path, '-m', 'sage.cli.main'] + sys.argv[1:], check=False)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()