#!/usr/bin/env python3
"""
本地智能测试系统
检测代码变化并自动运行相关测试

使用方法:
  python scripts/run_smart_tests.py                    # 检测git变化并运行相关测试
  python scripts/run_smart_tests.py --all              # 运行所有测试
  python scripts/run_smart_tests.py --files file1.py file2.py  # 指定文件运行测试
  python scripts/run_smart_tests.py --since HEAD~3     # 检测最近3个commit的变化
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from typing import List, Set
import time


class SmartTestRunner:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        os.chdir(self.project_root)
        
        # 定义目录到测试的映射
        self.test_mappings = {
            # 核心模块测试映射
            'sage.core/': [
                'tests/test_final_verification.py',
                'tests/test_service_task_base.py'
            ],
            'sage.runtime/': [
                'tests/test_final_verification.py',
                'tests/test_service_task_base.py'
            ],
            'sage.jobmanager/': [
                'tests/test_service_task_base.py'
            ],
            'sage.utils/mmap_queue/': [
                'sage.utils/mmap_queue/tests/test_comprehensive.py',
                'sage.utils/mmap_queue/tests/test_multiprocess_concurrent.py',
                'sage.utils/mmap_queue/tests/test_performance_benchmark.py',
                'sage.utils/mmap_queue/tests/test_ray_integration.py'
            ],
            'sage_libs/': [
                'tests/test_final_verification.py'
            ],
            'sage_examples/': [
                'tests/test_final_verification.py',
                'tests/test_service_task_base.py'
            ],
            # 测试文件自身的变化
            'tests/': [
                'tests/run_core_tests.py'
            ],
        }
        
        # 触发所有测试的文件
        self.critical_files = {
            'setup.py', 'requirements.txt', 'pyproject.toml'
        }
        
        # 所有可用的测试
        self.all_tests = [
            'tests/test_final_verification.py',
            'tests/test_service_task_base.py',
            'sage.utils/mmap_queue/tests/test_comprehensive.py',
            'sage.utils/mmap_queue/tests/test_multiprocess_concurrent.py',
            'sage.utils/mmap_queue/tests/test_performance_benchmark.py',
            'sage.utils/mmap_queue/tests/test_ray_integration.py'
        ]

    def get_changed_files(self, since: str = "HEAD~1") -> List[str]:
        """获取变化的文件列表"""
        try:
            # 检查是否在git仓库中
            subprocess.run(['git', 'status'], check=True, capture_output=True)
            
            # 获取变化的文件
            if since == "working":
                # 工作目录中的变化（包括未提交的）
                result = subprocess.run(
                    ['git', 'diff', '--name-only', 'HEAD'],
                    capture_output=True, text=True, check=True
                )
                staged_result = subprocess.run(
                    ['git', 'diff', '--name-only', '--cached'],
                    capture_output=True, text=True, check=True
                )
                untracked_result = subprocess.run(
                    ['git', 'ls-files', '--others', '--exclude-standard'],
                    capture_output=True, text=True, check=True
                )
                
                changed_files = []
                changed_files.extend(result.stdout.strip().split('\n') if result.stdout.strip() else [])
                changed_files.extend(staged_result.stdout.strip().split('\n') if staged_result.stdout.strip() else [])
                changed_files.extend(untracked_result.stdout.strip().split('\n') if untracked_result.stdout.strip() else [])
                
            else:
                # 与指定commit比较
                result = subprocess.run(
                    ['git', 'diff', '--name-only', since],
                    capture_output=True, text=True, check=True
                )
                changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # 过滤空字符串和非Python文件
            changed_files = [f for f in changed_files if f and (f.endswith('.py') or f in self.critical_files)]
            
            return changed_files
            
        except subprocess.CalledProcessError:
            print("Warning: Not in a git repository or git command failed")
            return []

    def find_tests_for_files(self, changed_files: List[str]) -> Set[str]:
        """根据变化的文件找到相应的测试"""
        tests_to_run = set()
        run_all_tests = False
        
        print(f"Analyzing {len(changed_files)} changed files...")
        
        for changed_file in changed_files:
            print(f"  📁 {changed_file}")
            
            # 检查是否是关键文件（触发所有测试）
            if any(changed_file.endswith(critical) for critical in self.critical_files):
                run_all_tests = True
                print(f"    ⚡ Critical file detected - will run ALL tests")
                continue
            
            # 检查是否匹配到测试映射
            matched = False
            for pattern, tests in self.test_mappings.items():
                if changed_file.startswith(pattern):
                    for test in tests:
                        if self.project_root.joinpath(test).exists():
                            tests_to_run.add(test)
                            print(f"    ✅ Added test: {test}")
                        else:
                            print(f"    ⚠️  Test not found: {test}")
                    matched = True
                    break
            
            if not matched:
                # 对于未映射的文件，检查同目录下是否有tests目录
                file_path = Path(changed_file)
                current_dir = file_path.parent
                
                # 向上查找tests目录
                for parent in [current_dir] + list(current_dir.parents):
                    tests_dir = self.project_root / parent / 'tests'
                    if tests_dir.exists() and tests_dir.is_dir():
                        # 找到tests目录，添加其中的所有测试文件
                        for test_file in tests_dir.glob('test_*.py'):
                            test_path = str(test_file.relative_to(self.project_root))
                            tests_to_run.add(test_path)
                            print(f"    📋 Found test in {tests_dir.name}: {test_path}")
                        matched = True
                        break
                
                if not matched:
                    print(f"    ❓ No specific tests found")
        
        # 如果需要运行所有测试
        if run_all_tests:
            print("\n⚡ Running ALL tests due to critical file changes...")
            tests_to_run.update(self.all_tests)
        
        # 过滤存在的测试文件
        existing_tests = set()
        for test in tests_to_run:
            test_path = self.project_root / test
            if test_path.exists():
                existing_tests.add(test)
            else:
                print(f"⚠️  Test file not found: {test}")
        
        return existing_tests

    def run_tests(self, test_files: Set[str]) -> dict:
        """运行指定的测试文件"""
        if not test_files:
            print("No tests to run.")
            return {"total": 0, "passed": 0, "failed": 0, "results": []}
        
        print(f"\n🚀 Running {len(test_files)} tests...")
        print("=" * 60)
        
        results = []
        total_tests = len(test_files)
        passed_tests = 0
        failed_tests = 0
        
        for i, test_file in enumerate(sorted(test_files), 1):
            print(f"\n[{i}/{total_tests}] Running: {test_file}")
            print("-" * 50)
            
            start_time = time.time()
            
            try:
                result = subprocess.run(
                    [sys.executable, str(test_file)],
                    cwd=self.project_root,
                    capture_output=False,  # 显示实时输出
                    timeout=300  # 5分钟超时
                )
                
                duration = time.time() - start_time
                
                if result.returncode == 0:
                    print(f"✅ PASSED: {test_file} ({duration:.2f}s)")
                    passed_tests += 1
                    results.append({"test": test_file, "status": "PASSED", "duration": duration})
                else:
                    print(f"❌ FAILED: {test_file} ({duration:.2f}s)")
                    failed_tests += 1
                    results.append({"test": test_file, "status": "FAILED", "duration": duration})
                    
            except subprocess.TimeoutExpired:
                print(f"⏰ TIMEOUT: {test_file}")
                failed_tests += 1
                results.append({"test": test_file, "status": "TIMEOUT", "duration": 300})
            except Exception as e:
                print(f"💥 ERROR: {test_file} - {e}")
                failed_tests += 1
                results.append({"test": test_file, "status": "ERROR", "duration": 0})
        
        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "results": results
        }

    def print_summary(self, test_results: dict, changed_files: List[str]):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("🧪 SMART TESTING SUMMARY")
        print("=" * 60)
        
        print(f"📁 Changed files analyzed: {len(changed_files)}")
        for f in changed_files[:5]:  # 只显示前5个
            print(f"   - {f}")
        if len(changed_files) > 5:
            print(f"   ... and {len(changed_files) - 5} more")
        
        print(f"\n📊 Test results:")
        print(f"   Total tests: {test_results['total']}")
        print(f"   Passed: {test_results['passed']}")
        print(f"   Failed: {test_results['failed']}")
        
        if test_results['failed'] == 0:
            print("\n🎉 All tests passed! Ready to commit.")
        else:
            print(f"\n⚠️  {test_results['failed']} tests failed. Please fix before committing.")
            print("\nFailed tests:")
            for result in test_results['results']:
                if result['status'] != 'PASSED':
                    print(f"   ❌ {result['test']} ({result['status']})")


def main():
    parser = argparse.ArgumentParser(
        description="Smart Test Runner - Automatically run tests based on code changes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Test changed files since last commit
  %(prog)s --all                     # Run all tests
  %(prog)s --since HEAD~5            # Test changes since 5 commits ago
  %(prog)s --since working           # Test working directory changes
  %(prog)s --files file1.py file2.py # Test specific files
        """
    )
    
    parser.add_argument('--all', action='store_true',
                        help='Run all available tests')
    parser.add_argument('--since', default='HEAD~1',
                        help='Git reference to compare against (default: HEAD~1)')
    parser.add_argument('--files', nargs='+',
                        help='Specific files to analyze for testing')
    parser.add_argument('--project-root',
                        help='Project root directory (default: auto-detect)')
    
    args = parser.parse_args()
    
    # 创建测试运行器
    runner = SmartTestRunner(args.project_root)
    
    print("🔍 SAGE Smart Test Runner")
    print("=" * 40)
    
    if args.all:
        # 运行所有测试
        print("Running ALL tests...")
        test_files = set(runner.all_tests)
        changed_files = ["<all tests requested>"]
        
    elif args.files:
        # 运行指定文件的相关测试
        print(f"Analyzing specified files: {args.files}")
        test_files = runner.find_tests_for_files(args.files)
        changed_files = args.files
        
    else:
        # 自动检测变化的文件
        changed_files = runner.get_changed_files(args.since)
        
        if not changed_files:
            print("No changes detected. Running core tests as fallback...")
            test_files = {
                'tests/test_final_verification.py',
                'tests/test_service_task_base.py'
            }
        else:
            test_files = runner.find_tests_for_files(changed_files)
    
    # 过滤存在的测试文件
    existing_tests = {t for t in test_files if (runner.project_root / t).exists()}
    
    if not existing_tests:
        print("No valid tests found to run.")
        return 0
    
    print(f"\n🎯 Tests to run ({len(existing_tests)}):")
    for test in sorted(existing_tests):
        print(f"   - {test}")
    
    # 运行测试
    test_results = runner.run_tests(existing_tests)
    
    # 打印摘要
    runner.print_summary(test_results, changed_files)
    
    # 返回适当的退出码
    return 0 if test_results['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
