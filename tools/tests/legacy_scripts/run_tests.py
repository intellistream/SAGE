#!/usr/bin/env python3
"""
SAGE Framework 集成测试运行器
Integrated Test Runner for SAGE Framework

⚠️  DEPRECATION WARNING ⚠️
本脚本已被弃用，请使用新的统一测试命令：
  sage dev test --test-type unit      # 单元测试
  sage dev test --test-type integration  # 集成测试  
  sage dev test --verbose            # 详细输出

详情请查看 MIGRATION.md 文档

统一的测试入口点，支持各种测试模式和配置
Unified test entry point with support for various test modes and configurations
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
import json
from typing import List, Dict, Optional
import concurrent.futures
import time

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
PACKAGES_DIR = PROJECT_ROOT / "packages"
TOOLS_DIR = PROJECT_ROOT / "tools" / "tests"

# 颜色输出
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'

def log_info(msg: str):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")

def log_success(msg: str):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")

def log_warning(msg: str):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")

def log_error(msg: str):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")

class SAGETestRunner:
    """SAGE测试运行器"""
    
    def __init__(self):
        # 显示弃用警告
        print(f"{Colors.YELLOW}⚠️  DEPRECATION WARNING ⚠️{Colors.NC}")
        print(f"{Colors.YELLOW}本脚本已被弃用，请使用新的统一测试命令：{Colors.NC}")
        print(f"  {Colors.CYAN}sage dev test --test-type unit{Colors.NC}      # 单元测试")
        print(f"  {Colors.CYAN}sage dev test --test-type integration{Colors.NC}  # 集成测试")
        print(f"  {Colors.CYAN}sage dev test --verbose{Colors.NC}            # 详细输出")
        print(f"{Colors.YELLOW}详情请查看 tools/tests/MIGRATION.md 文档{Colors.NC}")
        print()
        
        self.project_root = PROJECT_ROOT
        self.packages_dir = PACKAGES_DIR
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    def discover_packages(self) -> List[str]:
        """发现所有SAGE包"""
        packages = []
        if self.packages_dir.exists():
            for item in self.packages_dir.iterdir():
                if item.is_dir() and item.name.startswith('sage-'):
                    packages.append(item.name)
        return sorted(packages)
    
    def has_tests(self, package: str) -> bool:
        """检查包是否有测试"""
        package_dir = self.packages_dir / package
        return (
            (package_dir / "tests").exists() or
            (package_dir / "tests" / "run_tests.py").exists() or
            (package_dir / "run_tests.py").exists()
        )
    
    def run_package_tests(self, package: str, test_type: str = "unit", 
                         timeout: int = 300, verbose: bool = False) -> Dict:
        """运行单个包的测试"""
        package_dir = self.packages_dir / package
        
        if not self.has_tests(package):
            return {
                'package': package,
                'status': 'NO_TESTS',
                'duration': 0,
                'output': f"No tests found for {package}"
            }
        
        start_time = time.time()
        
        # 确定测试命令
        test_cmd = []
        
        if (package_dir / "tests" / "run_tests.py").exists():
            test_cmd = [
                sys.executable, "tests/run_tests.py",
                f"--{test_type}"
            ]
        elif (package_dir / "run_tests.py").exists():
            test_cmd = [
                sys.executable, "run_tests.py",
                f"--{test_type}"
            ]
        elif (package_dir / "tests").exists():
            test_cmd = [
                sys.executable, "-m", "pytest", "tests/", "-v"
            ]
        
        if verbose:
            test_cmd.append("--verbose")
        
        try:
            result = subprocess.run(
                test_cmd,
                cwd=package_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            return {
                'package': package,
                'status': 'PASSED' if result.returncode == 0 else 'FAILED',
                'duration': duration,
                'output': result.stdout + result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                'package': package,
                'status': 'TIMEOUT',
                'duration': duration,
                'output': f"Test timeout after {timeout} seconds"
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                'package': package,
                'status': 'ERROR',
                'duration': duration,
                'output': f"Error running tests: {str(e)}"
            }
    
    def run_tests_parallel(self, packages: List[str], max_workers: int = 4, 
                          test_type: str = "unit", timeout: int = 300,
                          verbose: bool = False) -> Dict:
        """并行运行测试"""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有测试任务
            future_to_package = {
                executor.submit(
                    self.run_package_tests, package, test_type, timeout, verbose
                ): package for package in packages
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_package):
                package = future_to_package[future]
                try:
                    result = future.result()
                    results[package] = result
                    
                    # 实时输出进度
                    status_emoji = {
                        'PASSED': '✅',
                        'FAILED': '❌',
                        'NO_TESTS': '⚠️',
                        'TIMEOUT': '⏰',
                        'ERROR': '💥'
                    }
                    
                    if not verbose:
                        print(f"{status_emoji.get(result['status'], '❓')} {package}: {result['status']}")
                    
                except Exception as e:
                    results[package] = {
                        'package': package,
                        'status': 'ERROR',
                        'duration': 0,
                        'output': f"Future execution error: {str(e)}"
                    }
        
        return results
    
    def generate_report(self, results: Dict, output_file: Optional[str] = None) -> str:
        """生成测试报告"""
        total = len(results)
        passed = sum(1 for r in results.values() if r['status'] == 'PASSED')
        failed = sum(1 for r in results.values() if r['status'] == 'FAILED')
        no_tests = sum(1 for r in results.values() if r['status'] == 'NO_TESTS')
        others = total - passed - failed - no_tests
        
        total_duration = sum(r['duration'] for r in results.values())
        
        report = f"""
SAGE Framework 测试报告
=====================
时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
总运行时间: {total_duration:.2f}秒

测试统计:
--------
总包数: {total}
通过: {passed}
失败: {failed}
无测试: {no_tests}
其他: {others}

详细结果:
--------
"""
        
        for package, result in sorted(results.items()):
            status_emoji = {
                'PASSED': '✅',
                'FAILED': '❌',
                'NO_TESTS': '⚠️',
                'TIMEOUT': '⏰',
                'ERROR': '💥'
            }
            emoji = status_emoji.get(result['status'], '❓')
            duration = result['duration']
            report += f"{emoji} {package:<20} {result['status']:<10} ({duration:.2f}s)\n"
        
        if failed > 0:
            report += "\n失败详情:\n--------\n"
            for package, result in results.items():
                if result['status'] == 'FAILED':
                    report += f"\n📋 {package}:\n"
                    report += result['output'][:500]  # 限制输出长度
                    if len(result['output']) > 500:
                        report += "\n... (输出截断)"
                    report += "\n"
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            log_info(f"报告已保存到: {output_file}")
        
        return report
    
    def run_diagnostics(self):
        """运行诊断脚本"""
        log_info("运行 SAGE 安装诊断...")
        
        diagnose_script = TOOLS_DIR / "diagnose_sage.py"
        if diagnose_script.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(diagnose_script)],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                print(result.stdout)
                if result.stderr:
                    print(result.stderr)
            except Exception as e:
                log_error(f"诊断脚本运行失败: {e}")
        else:
            log_warning("诊断脚本不存在")
    
    def check_package_status(self):
        """检查包状态"""
        log_info("检查包状态...")
        
        status_script = TOOLS_DIR / "check_packages_status.sh"
        if status_script.exists():
            try:
                result = subprocess.run(
                    ["bash", str(status_script)],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                print(result.stdout)
                if result.stderr:
                    print(result.stderr)
            except Exception as e:
                log_error(f"状态检查脚本运行失败: {e}")
        else:
            log_warning("状态检查脚本不存在")

def main():
    parser = argparse.ArgumentParser(
        description="SAGE Framework 集成测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --all                       运行所有包的测试
  %(prog)s --packages sage-libs sage-kernel  只测试指定包
  %(prog)s --quick                     快速测试主要包
  %(prog)s --unit --verbose            运行单元测试并显示详细输出
  %(prog)s --integration --jobs 8      运行集成测试，8并发
  %(prog)s --diagnose                  只运行诊断和状态检查
        """
    )
    
    # 测试模式
    parser.add_argument("--all", action="store_true", help="测试所有包")
    parser.add_argument("--quick", action="store_true", help="快速测试主要包")
    parser.add_argument("--packages", nargs="+", help="指定要测试的包")
    parser.add_argument("--diagnose", action="store_true", help="只运行诊断")
    
    # 测试类型
    parser.add_argument("--unit", action="store_true", help="运行单元测试")
    parser.add_argument("--integration", action="store_true", help="运行集成测试")
    parser.add_argument("--performance", action="store_true", help="运行性能测试")
    
    # 执行选项
    parser.add_argument("--jobs", type=int, default=4, help="并行任务数 (默认: 4)")
    parser.add_argument("--timeout", type=int, default=300, help="每个包的超时时间 (默认: 300秒)")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    parser.add_argument("--summary", action="store_true", help="只显示摘要结果")
    parser.add_argument("--report", help="报告输出文件")
    
    args = parser.parse_args()
    
    runner = SAGETestRunner()
    
    # 只运行诊断
    if args.diagnose:
        runner.run_diagnostics()
        runner.check_package_status()
        return
    
    # 确定测试类型
    test_type = "unit"
    if args.integration:
        test_type = "integration"
    elif args.performance:
        test_type = "performance"
    
    # 确定要测试的包
    packages = []
    if args.all:
        packages = runner.discover_packages()
    elif args.quick:
        packages = ["sage-common", "sage-kernel", "sage-libs", "sage-middleware"]
        packages = [p for p in packages if (runner.packages_dir / p).exists()]
    elif args.packages:
        packages = args.packages
    else:
        # 默认运行快速测试
        packages = ["sage-common", "sage-kernel", "sage-libs", "sage-middleware"]
        packages = [p for p in packages if (runner.packages_dir / p).exists()]
    
    if not packages:
        log_error("没有找到要测试的包")
        sys.exit(1)
    
    log_info(f"发现 {len(packages)} 个包: {', '.join(packages)}")
    log_info(f"测试类型: {test_type}")
    log_info(f"并行任务: {args.jobs}")
    log_info(f"超时时间: {args.timeout}秒")
    
    # 运行测试
    runner.start_time = time.time()
    results = runner.run_tests_parallel(
        packages, 
        max_workers=args.jobs,
        test_type=test_type,
        timeout=args.timeout,
        verbose=args.verbose
    )
    runner.end_time = time.time()
    
    # 生成报告
    report = runner.generate_report(results, args.report)
    
    if not args.verbose and not args.summary:
        print(report)
    elif args.summary:
        # 只显示统计摘要
        total = len(results)
        passed = sum(1 for r in results.values() if r['status'] == 'PASSED')
        failed = sum(1 for r in results.values() if r['status'] == 'FAILED')
        print(f"\n📊 测试摘要: {passed}/{total} 通过")
        if failed > 0:
            print(f"❌ {failed} 个包测试失败")
        else:
            print("✅ 所有测试通过!")
    
    # 设置退出码
    failed_count = sum(1 for r in results.values() if r['status'] == 'FAILED')
    if failed_count > 0:
        log_warning(f"{failed_count} 个包测试失败")
        sys.exit(1)
    else:
        log_success("所有测试通过!")

if __name__ == "__main__":
    main()
