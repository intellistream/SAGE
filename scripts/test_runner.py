#!/usr/bin/env python3
"""
SAGE 智能测试运行器 (多核并行版 - 文件级)

支持两种测试模式：
1. 全量测试：并行运行 sage/ 和 frontend/ 目录下所有的测试文件
2. 智能测试：根据 git diff，并行运行受影响文件的递归父目录中的所有测试文件

特性:
- 文件级多核并行执行测试，提升效率和粒度
- 为每个测试文件生成独立日志，路径与源码结构对应 (./test_logs/)
- 实时进度显示和详细的最终报告
- 支持GitHub Actions集成，输出markdown格式报告

Usage:
    python test_runner.py --all                    # 运行所有测试文件
    python test_runner.py --diff                   # 基于git diff运行智能测试
    python test_runner.py --diff --base main       # 指定基准分支
    python test_runner.py --list                   # 列出所有测试目录和文件
    python test_runner.py --all --workers 4        # 指定4个worker并行运行
    python test_runner.py --diff --output-format markdown  # 输出markdown格式
    python test_runner.py --diff --pr-branch feature-branch --base-branch main  # PR模式
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Set, Dict
import time
import concurrent.futures
from tqdm import tqdm

class SAGETestRunner:
    """SAGE 智能测试运行器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.sage_dir = self.project_root / "sage"
        self.frontend_dir = self.project_root / "frontend"
        self.test_logs_dir = self.project_root / "test_logs"
        self.test_logs_dir.mkdir(exist_ok=True)
        
    def find_all_test_directories(self) -> List[Path]:
        """查找 sage/ 和 frontend/ 目录下所有的 test/tests 目录"""
        test_dirs = []
        
        # 搜索 sage/ 目录
        if self.sage_dir.exists():
            for test_dir in self.sage_dir.rglob("test"):
                if test_dir.is_dir():
                    test_dirs.append(test_dir)
            for test_dir in self.sage_dir.rglob("tests"):
                if test_dir.is_dir():
                    test_dirs.append(test_dir)
        
        # 搜索 frontend/ 目录
        if self.frontend_dir.exists():
            for test_dir in self.frontend_dir.rglob("test"):
                if test_dir.is_dir():
                    test_dirs.append(test_dir)
            for test_dir in self.frontend_dir.rglob("tests"):
                if test_dir.is_dir():
                    test_dirs.append(test_dir)
        
        # 去重并排序
        unique_dirs = sorted(list(set(test_dirs)))
        return unique_dirs
    
    def get_changed_files(self, base_branch: str = "HEAD~1") -> List[str]:
        """获取相对于基准分支的变化文件列表"""
        try:
            # 在GitHub Actions中，使用origin/main作为基准
            if os.getenv('GITHUB_ACTIONS') and base_branch == "HEAD~1":
                base_branch = "origin/main"
            
            cmd = ["git", "diff", "--name-only", base_branch]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=self.project_root)
            
            changed_files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            return changed_files
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 获取变化文件失败: {e}")
            return []
    
    def find_parent_test_directories(self, file_path: str) -> List[Path]:
        """查找文件路径的所有父目录中的 test/tests 目录"""
        test_dirs = []
        file_path_obj = Path(file_path)
        
        # 从文件所在目录开始，向上递归查找父目录
        current_dir = file_path_obj.parent if file_path_obj.is_file() else file_path_obj
        
        while current_dir != self.project_root and current_dir != current_dir.parent:
            # 检查当前目录下是否有 test 或 tests 目录
            test_dir = current_dir / "test"
            if test_dir.exists() and test_dir.is_dir():
                test_dirs.append(test_dir)
            
            tests_dir = current_dir / "tests"
            if tests_dir.exists() and tests_dir.is_dir():
                test_dirs.append(tests_dir)
            
            # 移动到父目录
            current_dir = current_dir.parent
        
        return test_dirs
    
    def get_affected_test_directories(self, changed_files: List[str]) -> Set[Path]:
        """根据变化的文件，找到所有受影响的测试目录"""
        affected_test_dirs = set()
        
        print(f"🔍 分析 {len(changed_files)} 个变化文件的影响范围:")
        
        for file_path in changed_files:
            # 跳过非Python文件
            if not file_path.endswith('.py'):
                continue
            
            # 转换为项目相对路径
            full_path = self.project_root / file_path
            
            print(f"  📄 {file_path}")
            
            # 查找该文件所有父目录中的测试目录
            parent_test_dirs = self.find_parent_test_directories(full_path)
            
            for test_dir in parent_test_dirs:
                affected_test_dirs.add(test_dir)
                rel_test_dir = test_dir.relative_to(self.project_root)
                print(f"    → {rel_test_dir}")
        
        return affected_test_dirs
    
    def find_test_files_in_dir(self, test_dir: Path) -> List[Path]:
        """查找指定目录下的所有测试文件"""
        test_files = []
        
        # 递归查找所有测试文件
        patterns = ["test_*.py", "*_test.py"]
        
        for pattern in patterns:
            for test_file in test_dir.rglob(pattern):
                if test_file.is_file():
                    test_files.append(test_file)
        
        # 去重并排序
        return sorted(list(set(test_files)))
    
    def run_single_test_file(self, test_file: Path) -> Dict[str, any]:
        """在单个进程中运行单个测试文件，并记录日志"""
        start_time = time.time()
        
        # 生成日志文件路径，保持与源码文件结构对应
        rel_test_file = test_file.relative_to(self.project_root)
        log_file_path = self.test_logs_dir / f"{str(rel_test_file).replace('/', '_')}.log"
        
        result = {
            "test_file": str(test_file),
            "log_file": str(log_file_path),
            "success": False,
            "duration": 0.0,
            "has_warnings": False,
            "return_code": 0
        }
        
        try:
            # 运行pytest针对单个文件
            cmd = ["python", "-m", "pytest", str(test_file), "-v", "-s", "--maxfail=1", "--tb=short"]

            with open(log_file_path, 'w', encoding='utf-8') as log_file:
                log_file.write(f"Running test file: {test_file}\n")
                log_file.write(f"Command: {' '.join(cmd)}\n")
                log_file.write("=" * 60 + "\n\n")
                log_file.flush()
                
                process = subprocess.run(
                    cmd, 
                    cwd=self.project_root,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=180  # 2分钟超时
                )
                
                # 将输出写入日志文件
                log_file.write(process.stdout)
                
                # 分析pytest输出来判断是否真正失败
                result["return_code"] = process.returncode
                result["success"], result["has_warnings"] = self._analyze_pytest_output(process.returncode, process.stdout)
                result["duration"] = time.time() - start_time
                
        except subprocess.TimeoutExpired:
            result["duration"] = time.time() - start_time
            result["success"] = False
            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                log_file.write("\n\nERROR: Test execution timed out.\n")
            
        except Exception as e:
            result["duration"] = time.time() - start_time
            result["success"] = False
            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n\nERROR: An unexpected error occurred: {e}\n")
        
        return result

    def get_all_test_files(self) -> List[Path]:
        """获取所有测试文件的列表"""
        test_files = []
        test_dirs = self.find_all_test_directories()
        
        for test_dir in test_dirs:
            files_in_dir = self.find_test_files_in_dir(test_dir)
            test_files.extend(files_in_dir)
        
        # 去重并排序
        return sorted(list(set(test_files)))
    
    def get_test_files_from_directories(self, test_dirs: List[Path]) -> List[Path]:
        """从指定的测试目录中获取所有测试文件"""
        test_files = []
        
        for test_dir in test_dirs:
            files_in_dir = self.find_test_files_in_dir(test_dir)
            test_files.extend(files_in_dir)
        
        # 去重并排序
        return sorted(list(set(test_files)))
    
    def _execute_test_suite(self, test_files: List[Path], title: str, workers: int, output_format: str = "text") -> bool:
        """并行执行测试套件的核心逻辑"""
        if not test_files:
            if output_format == "markdown":
                print("## ✅ Test Results\n\nNo tests need to be run.")
            else:
                print("✅ 没有需要运行的测试。")
            return True

        if output_format == "text":
            print(f"\n🎯 准备运行 {len(test_files)} 个测试文件 (最多使用 {workers} 个并行进程):")
            for test_file in test_files:
                print(f"  - {test_file.relative_to(self.project_root)}")

        all_results = []
        start_time = time.time()

        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_file = {executor.submit(self.run_single_test_file, test_file): test_file for test_file in test_files}
            
            if output_format == "text":
                with tqdm(total=len(test_files), desc="执行测试", unit="file") as pbar:
                    for future in concurrent.futures.as_completed(future_to_file):
                        result = future.result()
                        all_results.append(result)
                        pbar.update(1)
            else:
                for future in concurrent.futures.as_completed(future_to_file):
                    result = future.result()
                    all_results.append(result)
        
        total_duration = time.time() - start_time
        
        # 统计结果
        all_results.sort(key=lambda r: r["test_file"])
        successful_tests = sum(1 for r in all_results if r["success"])
        failed_tests = len(all_results) - successful_tests
        warning_tests = sum(1 for r in all_results if r.get("has_warnings", False) and r["success"])
        
        # 输出结果
        if output_format == "markdown":
            self._print_markdown_summary(title, all_results, total_duration, successful_tests, failed_tests, warning_tests)
        else:
            self._print_text_summary(title, all_results, total_duration, successful_tests, failed_tests, warning_tests)
        
        return failed_tests == 0
    
    def _print_text_summary(self, title: str, all_results: List[Dict], total_duration: float, 
                           successful_tests: int, failed_tests: int, warning_tests: int):
        """打印文本格式的测试总结"""
        print(f"\n{'='*60}")
        print(f"📊 {title}结果总结:")
        print(f"  � 测试文件: {len(all_results)}")
        print(f"  ✅ 成功: {successful_tests}")
        print(f"  ❌ 失败: {failed_tests}")
        if warning_tests > 0:
            print(f"  ⚠️  有警告: {warning_tests}")
        print(f"  ⏱️ 总耗时: {total_duration:.2f}s")
        
        if failed_tests > 0:
            print(f"\n💥 失败的测试文件 (详情请查看日志):")
            for result in all_results:
                if not result["success"]:
                    status = "❌ 失败"
                    rel_test_file = Path(result["test_file"]).relative_to(self.project_root)
                    print(f"  {status} - {rel_test_file} (耗时: {result['duration']:.2f}s)")
                    print(f"    └── 📄 日志: {Path(result['log_file']).relative_to(self.project_root)}")
        
        if warning_tests > 0:
            print(f"\n⚠️ 有警告的测试文件:")
            for result in all_results:
                if result["success"] and result.get("has_warnings", False):
                    rel_test_file = Path(result["test_file"]).relative_to(self.project_root)
                    print(f"  ⚠️ 警告 - {rel_test_file} (耗时: {result['duration']:.2f}s)")
                    print(f"    └── 📄 日志: {Path(result['log_file']).relative_to(self.project_root)}")
    
    def _print_markdown_summary(self, title: str, all_results: List[Dict], total_duration: float,
                               successful_tests: int, failed_tests: int, warning_tests: int):
        """打印Markdown格式的测试总结"""
        print(f"## 📊 {title}结果总结\n")
        
        # 基本统计
        print("### 📈 统计信息")
        print(f"- **测试文件**: {len(all_results)}")
        print(f"- **成功**: {successful_tests}")
        print(f"- **失败**: {failed_tests}")
        if warning_tests > 0:
            print(f"- **有警告**: {warning_tests}")
        print(f"- **总耗时**: {total_duration:.2f}s")
        print()
        
        # 详细结果表格
        print("### 📋 详细结果")
        print("| 测试文件 | 状态 | 耗时(s) | 日志文件 |")
        print("|----------|------|---------|----------|")
        
        for result in all_results:
            if not result["success"]:
                status = "❌ 失败"
            elif result.get("has_warnings", False):
                status = "⚠️ 警告"
            else:
                status = "✅ 成功"
            
            rel_file = Path(result["test_file"]).relative_to(self.project_root)
            rel_log = Path(result["log_file"]).relative_to(self.project_root)
            print(f"| `{rel_file}` | {status} | {result['duration']:.2f} | `{rel_log}` |")
        
        print()
        
        # 失败详情
        if failed_tests > 0:
            print("### ❌ 失败详情")
            for result in all_results:
                if not result["success"]:
                    rel_file = Path(result["test_file"]).relative_to(self.project_root)
                    rel_log = Path(result["log_file"]).relative_to(self.project_root)
                    print(f"- **{rel_file}**: 测试失败 (耗时: {result['duration']:.2f}s)")
                    print(f"  - 日志文件: `{rel_log}`")
            print()
        
        # 警告详情
        if warning_tests > 0:
            print("### ⚠️ 警告详情")
            for result in all_results:
                if result["success"] and result.get("has_warnings", False):
                    rel_file = Path(result["test_file"]).relative_to(self.project_root)
                    rel_log = Path(result["log_file"]).relative_to(self.project_root)
                    print(f"- **{rel_file}**: 测试通过但有警告 (耗时: {result['duration']:.2f}s)")
                    print(f"  - 日志文件: `{rel_log}`")
            print()
        
        # 推荐操作
        if failed_tests > 0:
            print("### 💡 建议操作")
            print("- 检查失败的测试日志文件了解详细错误信息")
            print("- 考虑运行完整测试套件以确保代码质量")
            print("- 如果测试失败涉及核心组件，建议进行更全面的测试")
            print()
            print("RUN_FULL_TESTS=true")
        else:
            print("### ✅ 所有测试通过")
            if warning_tests > 0:
                print("代码变更没有破坏现有功能，但存在警告需要关注。")
            else:
                print("代码变更没有破坏现有功能，可以安全合并。")
            print()
            print("RUN_FULL_TESTS=false")
        
        # 输出推荐的测试文件列表
        if all_results:
            print("\n### 📝 已测试的文件")
            with open("recommended_tests.txt", "w") as f:
                for result in all_results:
                    rel_test_file = Path(result["test_file"]).relative_to(self.project_root)
                    f.write(f"{rel_test_file}\n")
                    print(f"- `{rel_test_file}`")
            print()
            print("测试文件列表已保存到 `recommended_tests.txt`")

    def run_all_tests(self, workers: int, output_format: str = "text") -> bool:
        """运行所有测试文件中的测试"""
        if output_format == "text":
            print("🚀 运行全量测试...")
        test_files = self.get_all_test_files()
        return self._execute_test_suite(test_files, "全量测试", workers, output_format)
    
    def run_smart_tests(self, base_branch: str, workers: int, output_format: str = "text") -> bool:
        """基于git diff运行智能测试"""
        if output_format == "text":
            print("🎯 运行智能测试...")
            print(f"🌿 基准分支: {base_branch}")
        elif output_format == "markdown":
            print(f"# 🎯 SAGE 智能测试报告\n")
            print(f"**基准分支**: `{base_branch}`\n")
        
        changed_files = self.get_changed_files(base_branch)
        if not changed_files:
            if output_format == "markdown":
                print("## ✅ 无变更文件\n\n没有检测到文件变化，跳过测试。")
            else:
                print("✅ 没有检测到文件变化，跳过测试")
            return True
        
        # Markdown格式输出变更文件信息
        if output_format == "markdown":
            print(f"## 📝 变更文件分析\n")
            print(f"检测到 **{len(changed_files)}** 个文件变更:\n")
            python_files = [f for f in changed_files if f.endswith('.py')]
            other_files = [f for f in changed_files if not f.endswith('.py')]
            
            if python_files:
                print("### Python 文件")
                for file_path in python_files:
                    print(f"- `{file_path}`")
                print()
                
            if other_files:
                print("### 其他文件")
                for file_path in other_files:
                    print(f"- `{file_path}`")
                print()
        
        affected_test_dirs = self.get_affected_test_directories(changed_files)
        
        if output_format == "markdown":
            print(f"## 🔍 影响分析\n")
            if affected_test_dirs:
                print(f"基于文件变更，需要测试 **{len(affected_test_dirs)}** 个测试目录:\n")
                for test_dir in sorted(affected_test_dirs):
                    rel_dir = test_dir.relative_to(self.project_root)
                    print(f"- `{rel_dir}`")
                print()
            else:
                print("没有找到受影响的测试目录。")
        
        # 从受影响的测试目录中获取所有测试文件
        test_files = self.get_test_files_from_directories(list(affected_test_dirs))
                
        return self._execute_test_suite(test_files, "智能测试", workers, output_format)
    
    def list_test_directories(self):
        """列出所有测试目录和测试文件"""
        print("📋 所有测试目录和文件:")
        test_dirs = self.find_all_test_directories()
        
        if not test_dirs:
            print("❌ 没有找到任何测试目录")
            return
        
        total_test_files = 0
        print(f"\n找到 {len(test_dirs)} 个测试目录:")
        for test_dir in test_dirs:
            test_files = self.find_test_files_in_dir(test_dir)
            total_test_files += len(test_files)
            print(f"  📁 {test_dir.relative_to(self.project_root)} ({len(test_files)} 个测试文件)")
            for test_file in test_files:
                print(f"    📄 {test_file.relative_to(self.project_root)}")
        
        print(f"\n总计: {total_test_files} 个测试文件将会并行执行")

    def _analyze_pytest_output(self, return_code: int, output: str) -> tuple[bool, bool]:
        """
        分析pytest输出，判断是否真正失败
        
        Args:
            return_code: pytest进程的退出码
            output: pytest的输出内容
            
        Returns:
            tuple: (是否成功, 是否有警告)
        """
        output_lower = output.lower()
        has_warnings = "warning" in output_lower or "warnings summary" in output_lower
        
        if return_code == 0:
            return True, has_warnings
        
        # 如果退出码非零，首先检查是否有明确的失败指示符
        # 优先检查 "failed" 关键字，这是最明确的失败标志
        if "failed" in output_lower:
            return False, has_warnings
        
        # 检查其他明确的失败指示符
        critical_failures = [
            "error collecting",
            "errors",
            "assertion error", 
            "assertionerror",
            "exception:",
            "traceback (most recent call last):",
            "segmentation fault",
            "core dumped",
            "syntax error",
            "import error",
            "module not found"
        ]
        
        # 如果输出中包含任何明确的失败指示符，直接判断为失败
        for failure in critical_failures:
            if failure in output_lower:
                return False, has_warnings
        
        # 如果没有明确的失败指示符，检查pytest的结果行
        # 查找类似 "5 passed, 4 warnings in 27.15s" 的行
        lines = output.split('\n')
        for line in lines:
            line_lower = line.lower().strip()
            
            # 匹配pytest结果总结行的几种模式
            if ('passed' in line_lower and 
                ('in ' in line_lower and line_lower.endswith('s')) or
                'passed,' in line_lower):
                # 找到了结果行，且包含passed，认为成功
                return True, has_warnings
        
        # 如果没有找到明确的成功指示符，且退出码非零，判断为失败
        return False, has_warnings

def main():
    parser = argparse.ArgumentParser(
        description="SAGE 智能测试运行器 (多核并行版 - 文件级)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="运行所有测试文件中的测试")
    group.add_argument("--diff", action="store_true", help="基于git diff运行智能测试")
    group.add_argument("--list", action="store_true", help="列出所有测试目录和文件")
    
    parser.add_argument("--base", default="HEAD~1", help="git diff的基准分支 (默认: HEAD~1)")
    parser.add_argument("--base-branch", help="PR基准分支 (用于GitHub Actions)")
    parser.add_argument("--pr-branch", help="PR分支 (用于GitHub Actions)")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help=f"并行进程数 (默认: {os.cpu_count()})")
    parser.add_argument("--project-root", help="项目根目录路径 (默认: 当前目录)")
    parser.add_argument("--output-format", choices=["text", "markdown"], default="text", help="输出格式")
    
    args = parser.parse_args()
    
    # GitHub Actions模式下的参数处理
    if args.base_branch:
        args.base = f"origin/{args.base_branch}"
    
    runner = SAGETestRunner(args.project_root)
    
    try:
        if args.list:
            runner.list_test_directories()
            sys.exit(0)
        
        success = False
        if args.all:
            success = runner.run_all_tests(args.workers, args.output_format)
        elif args.diff:
            success = runner.run_smart_tests(args.base, args.workers, args.output_format)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 运行测试时出现致命异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
