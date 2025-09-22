# Converted from update_sage_packages.sh
# SAGE 闭源包精确更新脚本
# 只清理和更新 intellistream-sage 相关包，保留其他依赖项缓存

import os
import sys
import subprocess
import site
import shutil
from pathlib import Path

# 颜色
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[0;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def print_header(msg: str):
    print(f"\n{BLUE}==== {msg} ===={NC}\n")

def print_success(msg: str):
    print(f"{GREEN}✓ {msg}{NC}")

def print_error(msg: str):
    print(f"{RED}✗ {msg}{NC}", file=sys.stderr)

def print_warning(msg: str):
    print(f"{YELLOW}! {msg}{NC}")

def print_info(msg: str):
    print(f"{BLUE}i {msg}{NC}")

def confirm(msg: str) -> bool:
    response = input(f"{msg} (y/N): ").strip().lower()
    return response in ['y', 'yes']

def check_python():
    print_header("检查 Python 环境")
    
    try:
        result = subprocess.run(["python3", "--version"], capture_output=True, text=True, check=True)
        print_info(f"Python 版本: {result.stdout.strip()}")
    except:
        print_error("未找到 python3 命令")
        sys.exit(1)
    
    try:
        result = subprocess.run(["pip", "--version"], capture_output=True, text=True, check=True)
        print_info(f"Pip 版本: {result.stdout.strip()}")
    except:
        print_error("未找到 pip 命令")
        sys.exit(1)
    
    print_success("Python 环境检查通过")

def uninstall_intellistream_sage():
    print_header("精确卸载 intellistream-sage 相关包")
    
    # 列出已安装的包
    print_info("当前已安装的 intellistream-sage 相关包:")
    try:
        result = subprocess.run(["pip", "list"], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if 'intellistream-sage' in line.lower():
                print(line)
    except:
        pass
    
    # 获取包列表
    try:
        result = subprocess.run(["pip", "list"], capture_output=True, text=True, check=True)
        sage_packages = [line.split()[0] for line in result.stdout.splitlines() if 'intellistream-sage' in line.lower()]
    except:
        sage_packages = []
    
    if not sage_packages:
        print_warning("未找到已安装的 intellistream-sage 包")
        return
    
    # 卸载
    for pkg in sage_packages:
        print_info(f"卸载 {pkg}...")
        subprocess.run(["pip", "uninstall", "-y", pkg], check=False)
    
    # 清理 pip 缓存
    print_info("清理 pip 缓存中的 intellistream-sage 包...")
    try:
        subprocess.run(["pip", "cache", "purge"], check=False)
    except:
        pass
    
    print_success("intellistream-sage 相关包卸载完成")

def clean_site_packages():
    print_header("清理 site-packages 中的残留文件")
    
    site_packages = site.getsitepackages()[0]
    print_info(f"检查 {site_packages} 中的残留文件")
    
    # 删除目录
    for dir_path in [Path(site_packages) / "intellistream_sage", ] + [Path(site_packages) / f"intellistream_sage*egg-info" for _ in range(10)]:
        if dir_path.exists():
            print_info(f"删除 {dir_path}")
            shutil.rmtree(dir_path, ignore_errors=True)
    
    # 删除 sage/kernel 等
    sage_path = Path(site_packages) / "sage"
    if sage_path.exists():
        for subdir in ["kernel", "middleware", "utils"]:
            sub_path = sage_path / subdir
            if sub_path.exists():
                print_info(f"删除 {sub_path}")
                shutil.rmtree(sub_path, ignore_errors=True)
    
    print_success("残留文件清理完成")

def install_latest():
    print_header("安装最新版本")
    
    packages = ["intellistream-sage-kernel", "intellistream-sage-utils", "intellistream-sage-middleware", "intellistream-sage"]
    for pkg in packages:
        print_info(f"安装 {pkg}...")
        subprocess.run(["pip", "install", "--no-cache-dir", pkg], check=True)
    
    print_success("安装完成")

def verify_installation():
    print_header("验证安装")
    
    print_info("已安装的 intellistream-sage 相关包:")
    subprocess.run(["pip", "list"], check=False)
    
    # 导入检查
    print_info("尝试导入 sage.kernel.JobManagerClient...")
    try:
        exec("from sage.kernel import JobManagerClient; print('导入成功: JobManagerClient 版本', getattr(JobManagerClient, '__version__', 'Unknown'))")
        print_success("JobManagerClient 导入成功")
    except Exception as e:
        print_error(f"JobManagerClient 导入失败: {e}")
        try:
            exec("import sage.kernel; print('sage.kernel 中的内容:', dir(sage.kernel))")
        except:
            pass
    
    print_info("验证完成")

def main():
    print_header("SAGE 闭源包精确更新工具")
    
    check_python()
    
    if confirm("是否卸载当前已安装的 intellistream-sage 相关包?"):
        uninstall_intellistream_sage()
        clean_site_packages()
    else:
        print_warning("跳过卸载步骤")
    
    if confirm("是否安装最新版本的 intellistream-sage 相关包?"):
        install_latest()
        verify_installation()
    else:
        print_warning("跳过安装步骤")
    
    print_header("操作完成")

if __name__ == "__main__":
    main()