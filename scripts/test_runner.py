#!/usr/bin/env python3
"""
SAGE 智能测试运行器 (多核并行版)

支持两种测试模式：
1. 全量测试：并行运行 sage/ 和 frontend/ 目录下所有的 test/tests 文件夹
2. 智能测试：根据 git diff，并行运行受影响文件的递归父目录中的 tests

特性:
- 多核并行执行测试，提升效率
- 自动生成日志，路径与源码结构对应 (./test_logs/)
- 实时进度显示和详细的最终报告

Usage:
    python test_runner.py --all                    # 运行所有测试
    python test_runner.py --diff                   # 基于git diff运行智能测试
    python test_runner.py --diff --base main       # 指定基准分支
    python test_runner.py --list                   # 列出所有测试目录
    python test_runner.py --all --workers 4        # 指定4个worker并行运行
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
    
    def run_tests_in_directory(self, test_dir: Path) -> Dict[str, any]:
        """在单个进程中运行指定目录的测试，并记录日志"""
        test_files = self.find_test_files_in_dir(test_dir)
        
        # 创建日志文件路径
        relative_test_dir = test_dir.relative_to(self.project_root)
        log_file_path = self.test_logs_dir / relative_test_dir.with_suffix('.log')
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        result = {
            "directory": str(relative_test_dir),
            "test_files": [str(f.relative_to(self.project_root)) for f in test_files],
            "success": True,
            "log_file": str(log_file_path),
            "duration": 0
        }
        
        if not test_files:
            with open(log_file_path, 'w', encoding='utf-8') as log_file:
                log_file.write("No test files found in this directory.\n")
            return result
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-v", "--tb=short", "--color=yes",
            str(test_dir)
        ]
        
        start_time = time.time()
        
        try:
            with open(log_file_path, 'w', encoding='utf-8') as log_file:
                proc_result = subprocess.run(
                    cmd, 
                    cwd=self.project_root, 
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    timeout=600  # 10分钟超时
                )
            
            result["duration"] = time.time() - start_time
            
            if proc_result.returncode == 0:
                result["success"] = True
            else:
                result["success"] = False
                
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

    def _execute_test_suite(self, test_dirs: List[Path], title: str, workers: int) -> bool:
        """并行执行测试套件的核心逻辑"""
        if not test_dirs:
            print("✅ 没有需要运行的测试。")
            return True

        print(f"\n🎯 准备运行 {len(test_dirs)} 个测试目录 (最多使用 {workers} 个并行进程):")
        for test_dir in test_dirs:
            print(f"  - {test_dir.relative_to(self.project_root)}")

        all_results = []
        start_time = time.time()

        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_dir = {executor.submit(self.run_tests_in_directory, test_dir): test_dir for test_dir in test_dirs}
            
            with tqdm(total=len(test_dirs), desc="执行测试", unit="dir") as pbar:
                for future in concurrent.futures.as_completed(future_to_dir):
                    result = future.result()
                    all_results.append(result)
                    pbar.update(1)
        
        total_duration = time.time() - start_time
        
        # 统计结果
        all_results.sort(key=lambda r: r["directory"])
        successful_tests = sum(1 for r in all_results if r["success"])
        failed_tests = len(all_results) - successful_tests
        total_test_files = sum(len(r["test_files"]) for r in all_results)
        
        # 打印总结
        print(f"\n{'='*60}")
        print(f"📊 {title}结果总结:")
        print(f"  📁 测试目录: {len(all_results)}")
        print(f"  📄 测试文件: {total_test_files}")
        print(f"  ✅ 成功: {successful_tests}")
        print(f"  ❌ 失败: {failed_tests}")
        print(f"  ⏱️ 总耗时: {total_duration:.2f}s")
        
        if failed_tests > 0:
            print(f"\n💥 失败的测试目录 (详情请查看日志):")
            for result in all_results:
                if not result["success"]:
                    status = "❌ 失败"
                    print(f"  {status} - {result['directory']} (耗时: {result['duration']:.2f}s)")
                    print(f"    └── 📄 日志: {result['log_file']}")
        
        return failed_tests == 0

    def run_all_tests(self, workers: int) -> bool:
        """运行所有测试目录中的测试"""
        print("🚀 运行全量测试...")
        test_dirs = self.find_all_test_directories()
        return self._execute_test_suite(test_dirs, "全量测试", workers)
    
    def run_smart_tests(self, base_branch: str, workers: int) -> bool:
        """基于git diff运行智能测试"""
        print("🎯 运行智能测试...")
        print(f"🌿 基准分支: {base_branch}")
        
        changed_files = self.get_changed_files(base_branch)
        if not changed_files:
            print("� 没有检测到文件变化，跳过测试")
            return True
        
        affected_test_dirs = self.get_affected_test_directories(changed_files)
        return self._execute_test_suite(list(affected_test_dirs), "智能测试", workers)
    
    def list_test_directories(self):
        """列出所有测试目录"""
        print("📋 所有测试目录:")
        test_dirs = self.find_all_test_directories()
        
        if not test_dirs:
            print("❌ 没有找到任何测试目录")
            return
        
        print(f"\n找到 {len(test_dirs)} 个测试目录:")
        for test_dir in test_dirs:
            test_files = self.find_test_files_in_dir(test_dir)
            print(f"  - {test_dir.relative_to(self.project_root)} ({len(test_files)} 个测试文件)")

def main():
    parser = argparse.ArgumentParser(
        description="SAGE 智能测试运行器 (多核并行版)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="运行所有测试目录中的测试")
    group.add_argument("--diff", action="store_true", help="基于git diff运行智能测试")
    group.add_argument("--list", action="store_true", help="列出所有测试目录")
    
    parser.add_argument("--base", default="HEAD~1", help="git diff的基准分支 (默认: HEAD~1)")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help=f"并行进程数 (默认: {os.cpu_count()})")
    parser.add_argument("--project-root", help="项目根目录路径 (默认: 当前目录)")
    
    args = parser.parse_args()
    
    runner = SAGETestRunner(args.project_root)
    
    try:
        if args.list:
            runner.list_test_directories()
            sys.exit(0)
        
        success = False
        if args.all:
            success = runner.run_all_tests(args.workers)
        elif args.diff:
            success = runner.run_smart_tests(args.base, args.workers)
        
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
