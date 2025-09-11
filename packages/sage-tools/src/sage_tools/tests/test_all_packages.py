# Converted from .sh for Python packaging
# SAGE Framework 一键测试所有包脚本
# Test All Packages Script for SAGE Framework
# 自动发现并测试所有SAGE包，支持并行执行和详细配置
# Automatically discover and test all SAGE packages with parallel execution and detailed configuration

import os
import sys
import subprocess
import multiprocessing
import time
import shutil
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime

try:
    from sage_tools.utils.logging import log_info, log_success, log_warning, log_error
except ImportError:
    def log_info(msg): print(f"\033[0;34m[INFO]\033[0m {msg}")
    def log_success(msg): print(f"\033[0;32m[SUCCESS]\033[0m {msg}")
    def log_warning(msg): print(f"\033[1;33m[WARNING]\033[0m {msg}")
    def log_error(msg): print(f"\033[0;31m[ERROR]\033[0m {msg}")

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PACKAGES_DIR = PROJECT_ROOT / "packages"

DEFAULT_JOBS = 4
DEFAULT_TIMEOUT = 300
DEFAULT_VERBOSE = False
DEFAULT_QUIET = False
DEFAULT_SUMMARY = False
DEFAULT_CONTINUE_ON_ERROR = True
DEFAULT_FAILED_ONLY = False

def show_help():
    parser = ArgumentParser(description="SAGE Framework 包测试工具")
    parser.print_help()

def get_packages(packages_arg):
    """获取包列表"""
    packages = packages_arg or []
    if not packages:
        # 自动发现包
        for dir_path in PACKAGES_DIR.glob("sage-*"):
            if dir_path.is_dir():
                packages.append(dir_path.name)
    if not packages:
        log_error("未找到任何包进行测试")
        sys.exit(1)
    return packages

def has_tests(package):
    """检查包是否有测试"""
    package_dir = PACKAGES_DIR / package
    return (package_dir / "tests").exists() or (package_dir / "tests" / "run_tests.py").exists() or (package_dir / "run_tests.py").exists()

def test_package(package, timeout, log_file, verbose):
    """运行单个包的测试"""
    package_dir = PACKAGES_DIR / package
    with open(log_file, 'a') as f:
        f.write(f"📦 开始测试包: {package}\n")
        f.write(f"时间: {datetime.now()}\n")
        f.write(f"目录: {package_dir}\n")
        f.write("----------------------------------------\n")
    
    if not has_tests(package):
        with open(log_file, 'a') as f:
            f.write(f"⚠️ {package}: 未找到测试\n")
        return 'NO_TESTS'
    
    os.chdir(package_dir)
    
    test_cmd = None
    if (package_dir / "tests" / "run_tests.py").exists():
        test_cmd = ['python', 'tests/run_tests.py', '--unit', '--coverage']
    elif (package_dir / "run_tests.py").exists():
        test_cmd = ['python', 'run_tests.py', '--unit', '--coverage']
    elif (package_dir / "tests").exists():
        test_cmd = ['python', '-m', 'pytest', 'tests/', '-v']
    else:
        with open(log_file, 'a') as f:
            f.write(f"⚠️ {package}: 未找到合适的测试方法\n")
        return 'NO_TESTS'
    
    try:
        result = subprocess.run(test_cmd, timeout=timeout, capture_output=True, text=True, cwd=package_dir)
        with open(log_file, 'a') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write(result.stderr)
            f.write(f"完成时间: {datetime.now()}\n")
        
        if result.returncode == 0:
            with open(log_file, 'a') as f:
                f.write(f"✅ {package}: 测试通过\n")
            return 'PASSED'
        else:
            with open(log_file, 'a') as f:
                f.write(f"❌ {package}: 测试失败 (退出码: {result.returncode})\n")
            return 'FAILED'
    except subprocess.TimeoutExpired:
        with open(log_file, 'a') as f:
            f.write(f"❌ {package}: 测试超时 ({timeout}s)\n")
            f.write(f"完成时间: {datetime.now()}\n")
        return 'TIMEOUT'
    except Exception as e:
        with open(log_file, 'a') as f:
            f.write(f"❌ {package}: 测试异常 {str(e)}\n")
            f.write(f"完成时间: {datetime.now()}\n")
        return 'ERROR'

def test_packages_parallel(packages, jobs, timeout, verbose, quiet, continue_on_error, failed_only):
    """并行测试包"""
    test_log_dir = PROJECT_ROOT / ".testlogs"
    test_log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    results = {}
    log_files = {}
    
    def worker(package):
        log_file = test_log_dir / f"{package}_{timestamp}.log"
        log_files[package] = str(log_file)
        return package, test_package(package, timeout, str(log_file), verbose)
    
    with multiprocessing.Pool(processes=jobs) as pool:
        for package, result in pool.starmap(worker, [(p, ) for p in packages]):
            results[package] = result
            if not quiet and verbose:
                if result == 'PASSED':
                    log_success(f"{package}: 测试通过")
                elif result == 'FAILED':
                    log_error(f"{package}: 测试失败")
                elif result == 'NO_TESTS':
                    log_warning(f"{package}: 无测试")
    
    return results, log_files

def generate_report(packages, results, log_files, total_packages, passed_packages, failed_packages, skipped_packages, summary, quiet):
    """生成测试报告"""
    report_file = PROJECT_ROOT / ".testlogs" / f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(report_file, 'w') as f:
        f.write("SAGE Framework 测试报告\n")
        f.write("=======================\n")
        f.write(f"时间: {datetime.now()}\n")
        f.write(f"总包数: {total_packages}\n")
        f.write(f"通过: {passed_packages}\n")
        f.write(f"失败: {failed_packages}\n")
        f.write(f"跳过: {skipped_packages}\n")
        f.write("\n详细结果:\n")
        f.write("--------\n")
        
        for package in packages:
            result = results.get(package, 'UNKNOWN')
            if result == 'PASSED':
                f.write(f"✅ {package}\n")
            elif result == 'FAILED':
                f.write(f"❌ {package}\n")
            elif result == 'NO_TESTS':
                f.write(f"⚠️  {package} (无测试)\n")
            else:
                f.write(f"❓ {package} (未知状态)\n")
        
        if failed_packages > 0:
            f.write("\n失败的包详细信息:\n")
            f.write("----------------\n")
            for package in packages:
                if results.get(package) == 'FAILED':
                    f.write(f"📋 {package}: {log_files[package]}\n")
    
    if not quiet:
        if summary:
            print()
            log_info(f"测试摘要: {passed_packages}/{total_packages} 通过")
            if failed_packages > 0:
                log_warning(f"{failed_packages} 个包测试失败")
        else:
            print()
            log_info(f"详细报告已保存到: {report_file}")

def main():
    parser = ArgumentParser(description="SAGE Framework 包测试工具")
    parser.add_argument('-j', '--jobs', type=int, default=DEFAULT_JOBS, help=f"并行任务数量 (默认: {DEFAULT_JOBS})")
    parser.add_argument('-t', '--timeout', type=int, default=DEFAULT_TIMEOUT, help=f"每个包的超时时间(秒) (默认: {DEFAULT_TIMEOUT})")
    parser.add_argument('-v', '--verbose', action='store_true', help="详细输出模式")
    parser.add_argument('-q', '--quiet', action='store_true', help="静默模式，只显示结果")
    parser.add_argument('-s', '--summary', action='store_true', help="只显示摘要结果")
    parser.add_argument('-c', '--continue-on-error', action='store_true', default=DEFAULT_CONTINUE_ON_ERROR, help="遇到错误继续执行其他包 (默认)")
    parser.add_argument('-x', '--stop-on-error', action='store_true', help="遇到错误立即停止")
    parser.add_argument('-f', '--failed', action='store_true', help="只重新运行失败的测试")
    parser.add_argument('packages', nargs='*', help="指定包名")
    parser.add_argument('-h', '--help', action='store_true', help="显示此帮助信息")
    args = parser.parse_args()
    
    if args.help:
        show_help()
        return
    
    global VERBOSE, QUIET, SUMMARY, CONTINUE_ON_ERROR, FAILED_ONLY
    VERBOSE = args.verbose
    QUIET = args.quiet
    SUMMARY = args.summary
    CONTINUE_ON_ERROR = args.continue_on_error or not args.stop_on_error
    FAILED_ONLY = args.failed
    JOBS = args.jobs
    TIMEOUT = args.timeout
    
    if QUIET:
        VERBOSE = False
        SUMMARY = True
    
    if not QUIET:
        log_info("SAGE Framework 包测试工具启动")
        log_info(f"项目根目录: {PROJECT_ROOT}")
        log_info(f"并行任务数: {JOBS}")
        log_info(f"超时时间: {TIMEOUT}秒")
    
    packages = get_packages(args.packages)
    
    if not QUIET:
        log_info(f"发现 {len(packages)} 个包: { ' '.join(packages) }")
    
    start_time = time.time()
    
    results, log_files = test_packages_parallel(packages, JOBS, TIMEOUT, VERBOSE, QUIET, CONTINUE_ON_ERROR, FAILED_ONLY)
    
    end_time = time.time()
    duration = end_time - start_time
    
    total_packages = len(packages)
    passed_packages = sum(1 for r in results.values() if r == 'PASSED')
    failed_packages = sum(1 for r in results.values() if r == 'FAILED')
    skipped_packages = sum(1 for r in results.values() if r == 'NO_TESTS')
    
    generate_report(packages, results, log_files, total_packages, passed_packages, failed_packages, skipped_packages, SUMMARY, QUIET)
    
    if not QUIET:
        log_info(f"测试完成，耗时: {duration:.2f}秒")
    
    if failed_packages > 0 and not CONTINUE_ON_ERROR:
        sys.exit(1)

if __name__ == "__main__":
    main()