# Converted from publish_sage.sh
# SAGE Framework PyPI 发布脚本
# SAGE Framework PyPI Publishing Script
#
# 用于发布新重构的 SAGE 包到 PyPI
# For publishing the new restructured SAGE packages to PyPI

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
LOG_DIR = PROJECT_ROOT / "logs" / "pypi"
LOG_DIR.mkdir(parents=True, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f"publish_{TIMESTAMP}.log"

# 颜色配置
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
BOLD = '\033[1m'
NC = '\033[0m'

def log_info(msg: str):
    print(f"{BLUE}ℹ️  {msg}{NC}")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: {msg}\n")

def log_success(msg: str):
    print(f"{GREEN}✅ {msg}{NC}")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SUCCESS: {msg}\n")

def log_warning(msg: str):
    print(f"{YELLOW}⚠️  {msg}{NC}")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] WARNING: {msg}\n")

def log_error(msg: str):
    print(f"{RED}❌ {msg}{NC}")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {msg}\n")

def log_header(msg: str):
    print(f"{BOLD}{BLUE}{msg}{NC}")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] HEADER: {msg}\n")

def log_simple(msg: str, level: str = "INFO"):
    print(msg)
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {level}: {msg}\n")

def log_file_only(msg: str, level: str = "INFO"):
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {level}: {msg}\n")

def check_dependencies():
    log_header("🔍 检查依赖")
    
    if subprocess.run(["twine", "--version"], capture_output=True).returncode != 0:
        log_error("twine 未安装，请先安装: pip install twine")
        sys.exit(1)
    
    if subprocess.run(["python", "--version"], capture_output=True).returncode != 0:
        log_error("Python 未安装")
        sys.exit(1)
    
    log_success("依赖检查完成")

def clean_build_artifacts():
    log_header("🧹 清理构建产物")
    
    cleanup_script = PROJECT_ROOT / "cleanup_build_artifacts.py"
    if cleanup_script.exists():
        subprocess.run(["python", cleanup_script], cwd=PROJECT_ROOT, check=True)
    else:
        # 手动清理
        for path in PROJECT_ROOT.rglob("packages/*/dist"):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
        for path in PROJECT_ROOT.rglob("packages/*/build"):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
        for path in PROJECT_ROOT.rglob("packages/*/*.egg-info"):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
    
    log_success("构建产物清理完成")

def build_package(package_path: Path):
    package_name = package_path.name
    log_simple(f"{BLUE}📦 构建 {package_name}{NC}", "INFO: 开始构建包 " + package_name)
    
    os.chdir(package_path)
    
    if not (package_path / "pyproject.toml").exists():
        log_error(f"{package_name}: 缺少 pyproject.toml")
        return False
    
    try:
        with open(LOG_FILE, 'a') as f:
            subprocess.run(["python", "-m", "build", "--wheel"], stdout=f, stderr=subprocess.STDOUT, check=True)
        log_success(f"{package_name}: 构建完成")
        return True
    except subprocess.CalledProcessError:
        log_error(f"{package_name}: 构建失败")
        return False

def upload_package(package_path: Path, dry_run: bool):
    package_name = package_path.name
    log_simple(f"{YELLOW}⬆️  上传 {package_name}{NC}", "INFO: 开始上传包 " + package_name)
    
    os.chdir(package_path)
    
    dist_dir = package_path / "dist"
    if not dist_dir.exists():
        log_error(f"{package_name}: 缺少 dist 目录")
        return False
    
    cmd = ["twine", "upload", "dist/*"]
    if dry_run:
        cmd += ["--repository", "testpypi"]
        log_file_only(f"{package_name}: 上传到 TestPyPI (预演模式)")
    else:
        log_file_only(f"{package_name}: 上传到 PyPI")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        with open(LOG_FILE, 'a') as f:
            f.write(result.stdout + "\n")
        log_success(f"{package_name}: 上传成功")
        return True
    except subprocess.CalledProcessError as e:
        with open(LOG_FILE, 'a') as f:
            f.write(e.stdout + "\n" + e.stderr + "\n")
        log_error(f"{package_name}: 上传失败")
        
        output = e.stdout + e.stderr
        if "File already exists" in output or "already exists" in output or "400.*filename.*already.*exists" in output:
            log_warning(f"{package_name}: 文件已存在，跳过")
            return True
        return False

def publish_packages(dry_run: bool):
    if dry_run:
        log_header("🚀 SAGE 包发布 (TestPyPI 预演模式)")
    else:
        log_header("🚀 SAGE 包发布 (PyPI 正式发布)")
    
    publish_order = [
        "sage-common",
        "sage-kernel",
        "sage-middleware",
        "sage-libs",
        "sage"
    ]
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for package in publish_order:
        package_path = PROJECT_ROOT / "packages" / package
        if not package_path.exists():
            log_warning(f"{package}: 目录不存在，跳过")
            skipped_count += 1
            continue
        
        log_header(f"📦 处理包: {package}")
        
        if not build_package(package_path):
            failed_count += 1
            continue
        
        if upload_package(package_path, dry_run):
            success_count += 1
        else:
            failed_count += 1
    
    log_header("📊 发布摘要")
    log_success(f"成功: {success_count}")
    log_warning(f"跳过: {skipped_count}")
    log_error(f"失败: {failed_count}")
    print(f"总计: {success_count + skipped_count + failed_count}")
    
    if failed_count == 0:
        log_success("🎉 所有包发布完成！")
        return True
    else:
        log_error(f"💥 有 {failed_count} 个包发布失败")
        return False

def show_help():
    print("SAGE Framework PyPI 发布工具")
    print()
    print(f"用法: {sys.argv[0]} [选项]")
    print()
    print("选项:")
    print("  --dry-run    预演模式，上传到 TestPyPI")
    print("  --clean      仅清理构建产物，不发布")
    print("  --help       显示此帮助信息")
    print()
    print("示例:")
    print(f"  {sys.argv[0]}                # 发布到 PyPI")
    print(f"  {sys.argv[0]} --dry-run      # 预演模式，发布到 TestPyPI")
    print(f"  {sys.argv[0]} --clean        # 仅清理构建产物")

def main():
    dry_run = False
    clean_only = False
    
    with open(LOG_FILE, 'w') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ======== SAGE PyPI 发布脚本开始 ========\n")
    
    print(f"📝 详细日志: {LOG_FILE}")
    print()
    
    parser = argparse.ArgumentParser(description="SAGE Framework PyPI 发布工具", add_help=False)
    parser.add_argument("--dry-run", action="store_true", help="预演模式，上传到 TestPyPI")
    parser.add_argument("--clean", action="store_true", help="仅清理构建产物，不发布")
    parser.add_argument("--help", "-h", action="store_true", help="显示此帮助信息")
    args, unknown = parser.parse_known_args()
    
    if args.help:
        show_help()
        sys.exit(0)
    
    dry_run = args.dry_run
    clean_only = args.clean
    
    check_dependencies()
    clean_build_artifacts()
    
    if clean_only:
        log_success("仅清理模式完成")
        sys.exit(0)
    
    publish_packages(dry_run)

if __name__ == "__main__":
    main()