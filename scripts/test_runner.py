#!/usr/bin/env python3
"""
SAGE 智能测试运行器 (monorepo版本)

适用于新的 packages/ 结构，支持多包并行测试

支持两种测试模式：
1. 全量测试：并行运行所有 packages/ 目录下的测试文件
2. 智能测试：根据 git diff，并行运行受影响包的测试文件

特性:
- 支持 monorepo 架构，自动发现各个包的测试
- 文件级多核并行执行测试，提升效率和粒度
- 为每个测试文件生成独立日志，路径与源码结构对应 (./test_logs/)
- 实时进度显示和详细的最终报告
- 支持GitHub Actions集成，输出markdown格式报告

Usage:
    python test_runner.py --all                    # 运行所有测试文件
    python test_runner.py --diff                   # 基于git diff运行智能测试
    python test_runner.py --diff --base main       # 指定基准分支
    python test_runner.py --list                   # 列出所有测试目录和文件
    python test_runner.py --package sage-core      # 只运行指定包的测试
    python test_runner.py --all --workers 4        # 指定4个worker并行运行
    python test_runner.py --diff --output-format markdown  # 输出markdown格式
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Set, Dict, Optional
import time
import concurrent.futures
import json
from tqdm import tqdm

class SAGETestRunner:
    """SAGE 智能测试运行器 - Monorepo 版本"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.packages_dir = self.project_root / "packages"
        self.test_logs_dir = self.project_root / "test_logs"
        self.test_logs_dir.mkdir(exist_ok=True)
        
        # 包列表
        self.packages = [
            "sage-cli",
            "sage-core", 
            "sage-extensions",
            "sage-frontend",
            "sage-lib",
            "sage-plugins",
            "sage-service",
            "sage-utils"
        ]
        
    def find_all_test_files(self, package_filter: Optional[str] = None) -> List[Path]:
        """查找所有包中的测试文件"""
        test_files = []
        
        packages_to_scan = [package_filter] if package_filter else self.packages
        
        for package_name in packages_to_scan:
            package_dir = self.packages_dir / package_name
            if not package_dir.exists():
                print(f"⚠️  包目录不存在: {package_dir}")
                continue
                
            # 查找测试文件的模式
            test_patterns = [
                "**/test*.py",
                "**/*test*.py", 
                "**/tests/**/*.py"
            ]
            
            for pattern in test_patterns:
                for test_file in package_dir.rglob(pattern):
                    # 排除 __pycache__ 和其他非测试文件
                    if ("__pycache__" not in str(test_file) and 
                        test_file.suffix == ".py" and
                        not test_file.name.startswith(".")):
                        test_files.append(test_file)
        
        # 去重并排序
        test_files = list(set(test_files))
        test_files.sort()
        
        return test_files
    
    def find_test_directories(self, package_filter: Optional[str] = None) -> List[Path]:
        """查找所有包中的测试目录"""
        test_dirs = []
        
        packages_to_scan = [package_filter] if package_filter else self.packages
        
        for package_name in packages_to_scan:
            package_dir = self.packages_dir / package_name
            if not package_dir.exists():
                continue
                
            # 查找测试目录
            for test_dir in package_dir.rglob("test*"):
                if test_dir.is_dir() and "test" in test_dir.name.lower():
                    test_dirs.append(test_dir)
        
        return sorted(list(set(test_dirs)))
    
    def get_changed_files(self, base_branch: str = "main") -> Set[str]:
        """获取相对于指定分支的变更文件"""
        try:
            # 获取当前分支名
            current_branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_root,
                text=True
            ).strip()
            
            print(f"🔍 当前分支: {current_branch}")
            print(f"🔍 基准分支: {base_branch}")
            
            # 获取变更的文件
            result = subprocess.check_output([
                "git", "diff", "--name-only", f"{base_branch}...HEAD"
            ], cwd=self.project_root, text=True)
            
            changed_files = set(result.strip().split('\n')) if result.strip() else set()
            
            print(f"🔍 发现 {len(changed_files)} 个变更文件")
            for file in sorted(changed_files):
                print(f"   📝 {file}")
                
            return changed_files
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git 命令执行失败: {e}")
            return set()
    
    def find_related_test_files(self, changed_files: Set[str]) -> List[Path]:
        """根据变更文件找到相关的测试文件"""
        if not changed_files:
            return []
        
        related_packages = set()
        
        # 确定哪些包受到了影响
        for changed_file in changed_files:
            changed_path = Path(changed_file)
            
            # 检查是否在 packages/ 目录下
            if len(changed_path.parts) >= 2 and changed_path.parts[0] == "packages":
                package_name = changed_path.parts[1]
                related_packages.add(package_name)
            
            # 检查根目录的重要文件
            elif changed_file in ["pyproject.toml", "pytest.ini", "one_click_setup_and_test.py"]:
                # 如果核心配置文件变更，测试所有包
                related_packages.update(self.packages)
        
        print(f"🎯 受影响的包: {sorted(related_packages)}")
        
        # 收集相关包的所有测试文件
        test_files = []
        for package_name in related_packages:
            package_tests = self.find_all_test_files(package_name)
            test_files.extend(package_tests)
            print(f"   📦 {package_name}: {len(package_tests)} 个测试文件")
        
        return test_files
    
    def run_test_file(self, test_file: Path) -> Dict:
        """运行单个测试文件"""
        # 生成日志文件路径
        relative_path = test_file.relative_to(self.project_root)
        log_file = self.test_logs_dir / f"{str(relative_path).replace('/', '_').replace('.py', '.log')}"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        
        try:
            # 运行 pytest，指定配置文件以避免第三方依赖测试
            cmd = [
                sys.executable, "-m", "pytest", 
                str(test_file),
                "-c", "pytest-no-cov.ini",  # 使用专门的配置文件
                "-v",
                "--tb=short",
                "--ignore-glob=**/build/**",  # 额外忽略构建目录
                "--ignore-glob=**/_deps/**",  # 额外忽略依赖目录
                # f"--junitxml={log_file.with_suffix('.xml')}"
            ]
            
            with open(log_file, 'w') as f:
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            
            duration = time.time() - start_time
            
            return {
                "test_file": str(relative_path),
                "return_code": result.returncode,
                "duration": duration,
                "log_file": str(log_file),
                "success": result.returncode == 0
            }
            
        except Exception as e:
            duration = time.time() - start_time
            return {
                "test_file": str(relative_path),
                "return_code": -1,
                "duration": duration,
                "log_file": str(log_file),
                "success": False,
                "error": str(e)
            }
    
    def run_tests_parallel(self, test_files: List[Path], max_workers: int = 4) -> List[Dict]:
        """并行运行测试文件"""
        if not test_files:
            print("📋 没有找到测试文件")
            return []
        
        print(f"🚀 准备运行 {len(test_files)} 个测试文件，使用 {max_workers} 个worker")
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_test = {
                executor.submit(self.run_test_file, test_file): test_file 
                for test_file in test_files
            }
            
            # 使用进度条显示进度
            with tqdm(total=len(test_files), desc="运行测试") as pbar:
                for future in concurrent.futures.as_completed(future_to_test):
                    result = future.result()
                    results.append(result)
                    
                    # 更新进度条
                    status = "✅" if result["success"] else "❌"
                    test_name = Path(result["test_file"]).name
                    pbar.set_postfix_str(f"{status} {test_name}")
                    pbar.update(1)
        
        return results
    
    def generate_report(self, results: List[Dict], output_format: str = "console") -> str:
        """生成测试报告"""
        if not results:
            return "没有测试结果"
        
        # 统计
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["success"])
        failed_tests = total_tests - passed_tests
        total_duration = sum(r["duration"] for r in results)
        
        if output_format == "markdown":
            return self._generate_markdown_report(results, total_tests, passed_tests, failed_tests, total_duration)
        else:
            return self._generate_console_report(results, total_tests, passed_tests, failed_tests, total_duration)
    
    def _generate_console_report(self, results: List[Dict], total_tests: int, passed_tests: int, failed_tests: int, total_duration: float) -> str:
        """生成控制台格式报告"""
        report = []
        report.append("\n" + "="*80)
        report.append("🧪 SAGE 测试报告")
        report.append("="*80)
        report.append(f"📊 总计: {total_tests} 个测试文件")
        report.append(f"✅ 通过: {passed_tests} 个")
        report.append(f"❌ 失败: {failed_tests} 个")
        report.append(f"⏱️  总耗时: {total_duration:.2f} 秒")
        report.append(f"📈 成功率: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            report.append("\n❌ 失败的测试:")
            report.append("-" * 60)
            for result in results:
                if not result["success"]:
                    report.append(f"  📄 {result['test_file']}")
                    report.append(f"     💥 退出码: {result['return_code']}")
                    report.append(f"     📝 日志: {result['log_file']}")
                    if "error" in result:
                        report.append(f"     🐛 错误: {result['error']}")
        
        report.append("\n✅ 通过的测试:")
        report.append("-" * 60)
        for result in results:
            if result["success"]:
                report.append(f"  📄 {result['test_file']} ({result['duration']:.2f}s)")
        
        return "\n".join(report)
    
    def _generate_markdown_report(self, results: List[Dict], total_tests: int, passed_tests: int, failed_tests: int, total_duration: float) -> str:
        """生成Markdown格式报告"""
        report = []
        report.append("# 🧪 SAGE 测试报告")
        report.append("")
        report.append("## 📊 测试统计")
        report.append("")
        report.append(f"| 指标 | 数值 |")
        report.append(f"|------|------|")
        report.append(f"| 总测试文件数 | {total_tests} |")
        report.append(f"| ✅ 通过 | {passed_tests} |")
        report.append(f"| ❌ 失败 | {failed_tests} |")
        report.append(f"| ⏱️ 总耗时 | {total_duration:.2f}s |")
        report.append(f"| 📈 成功率 | {(passed_tests/total_tests)*100:.1f}% |")
        report.append("")
        
        if failed_tests > 0:
            report.append("## ❌ 失败的测试")
            report.append("")
            report.append("| 测试文件 | 退出码 | 耗时 | 日志文件 |")
            report.append("|----------|--------|------|----------|")
            for result in results:
                if not result["success"]:
                    report.append(f"| `{result['test_file']}` | {result['return_code']} | {result['duration']:.2f}s | `{result['log_file']}` |")
            report.append("")
        
        report.append("## ✅ 通过的测试")
        report.append("")
        report.append("| 测试文件 | 耗时 |")
        report.append("|----------|------|")
        for result in results:
            if result["success"]:
                report.append(f"| `{result['test_file']}` | {result['duration']:.2f}s |")
        
        return "\n".join(report)
    
    def list_all_tests(self, package_filter: Optional[str] = None):
        """列出所有测试"""
        print("🔍 扫描测试文件...")
        
        if package_filter:
            print(f"📦 指定包: {package_filter}")
        
        test_files = self.find_all_test_files(package_filter)
        test_dirs = self.find_test_directories(package_filter)
        
        print(f"\n📁 发现 {len(test_dirs)} 个测试目录:")
        for test_dir in test_dirs:
            relative_path = test_dir.relative_to(self.project_root)
            print(f"  📂 {relative_path}")
        
        print(f"\n📄 发现 {len(test_files)} 个测试文件:")
        
        # 按包分组显示
        files_by_package = {}
        for test_file in test_files:
            relative_path = test_file.relative_to(self.project_root)
            parts = relative_path.parts
            if len(parts) >= 2 and parts[0] == "packages":
                package_name = parts[1]
                if package_name not in files_by_package:
                    files_by_package[package_name] = []
                files_by_package[package_name].append(str(relative_path))
        
        for package_name in sorted(files_by_package.keys()):
            print(f"\n  📦 {package_name} ({len(files_by_package[package_name])} 个文件):")
            for test_file in sorted(files_by_package[package_name]):
                print(f"    📄 {test_file}")


def main():
    parser = argparse.ArgumentParser(
        description="SAGE 智能测试运行器 - Monorepo版本"
    )
    
    # 基本选项
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--diff", action="store_true", help="运行智能差异测试")
    parser.add_argument("--list", action="store_true", help="列出所有测试文件")
    parser.add_argument("--package", type=str, help="只运行指定包的测试")
    
    # 配置选项
    parser.add_argument("--base", type=str, default="main", help="diff 模式的基准分支")
    parser.add_argument("--workers", type=int, default=4, help="并行worker数量")
    parser.add_argument("--output-format", choices=["console", "markdown"], 
                       default="console", help="输出格式")
    
    # GitHub Actions 支持
    parser.add_argument("--pr-branch", type=str, help="PR分支名")
    parser.add_argument("--base-branch", type=str, help="基准分支名")
    
    args = parser.parse_args()
    
    # 创建测试运行器
    runner = SAGETestRunner()
    
    # 列出测试
    if args.list:
        runner.list_all_tests(args.package)
        return
    
    # 确定要运行的测试文件
    test_files = []
    
    if args.all:
        print("🎯 运行所有测试...")
        test_files = runner.find_all_test_files(args.package)
    elif args.diff:
        print("🎯 运行智能差异测试...")
        base_branch = args.base_branch or args.base
        changed_files = runner.get_changed_files(base_branch)
        test_files = runner.find_related_test_files(changed_files)
    elif args.package:
        print(f"🎯 运行包 '{args.package}' 的测试...")
        test_files = runner.find_all_test_files(args.package)
    else:
        parser.print_help()
        return
    
    if not test_files:
        print("📋 没有找到需要运行的测试文件")
        return
    
    # 运行测试
    results = runner.run_tests_parallel(test_files, args.workers)
    
    # 生成报告
    report = runner.generate_report(results, args.output_format)
    print(report)
    
    # 保存报告到文件
    report_file = runner.test_logs_dir / f"test_report_{int(time.time())}.txt"
    if args.output_format == "markdown":
        report_file = report_file.with_suffix(".md")
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📄 测试报告已保存到: {report_file}")
    
    # 设置退出码
    failed_count = sum(1 for r in results if not r["success"])
    sys.exit(1 if failed_count > 0 else 0)


if __name__ == "__main__":
    main()
