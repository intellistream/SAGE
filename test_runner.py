#!/usr/bin/env python3
"""
SAGE 智能测试运行器

支持两种测试模式：
1. 全量测试：运行 sage/ 目录下所有的 test/tests 文件夹
2. 智能测试：根据 git diff，只运行受影响文件的递归父目录中的 tests

Usage:
    python test_runner.py --all                    # 运行所有测试
    python test_runner.py --diff                   # 基于git diff运行智能测试
    python test_runner.py --diff --base main       # 指定基准分支
    python test_runner.py --list                   # 列出所有测试目录
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Set, Dict
import time

class SAGETestRunner:
    """SAGE 智能测试运行器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.sage_dir = self.project_root / "sage"
        self.frontend_dir = self.project_root / "frontend"
        
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
        """运行指定目录下的测试"""
        test_files = self.find_test_files_in_dir(test_dir)
        
        result = {
            "directory": str(test_dir.relative_to(self.project_root)),
            "test_files": [str(f.relative_to(self.project_root)) for f in test_files],
            "success": True,
            "output": "",
            "duration": 0
        }
        
        if not test_files:
            print(f"📂 {test_dir.relative_to(self.project_root)} 中没有找到测试文件")
            return result
        
        print(f"\n🧪 运行 {test_dir.relative_to(self.project_root)} 中的 {len(test_files)} 个测试文件:")
        for test_file in test_files:
            print(f"  - {test_file.relative_to(self.project_root)}")
        
        # 使用pytest运行测试
        cmd = [
            sys.executable, "-m", "pytest",
            "-v",  # 详细输出
            "--tb=short",  # 简短的错误追踪
            "--color=yes",  # 彩色输出
            str(test_dir)  # 运行整个目录
        ]
        
        start_time = time.time()
        
        try:
            proc_result = subprocess.run(
                cmd, 
                cwd=self.project_root, 
                capture_output=True, 
                text=True,
                timeout=300  # 5分钟超时
            )
            
            result["duration"] = time.time() - start_time
            result["output"] = proc_result.stdout + proc_result.stderr
            
            if proc_result.returncode == 0:
                print(f"✅ {test_dir.relative_to(self.project_root)} 测试通过 ({result['duration']:.2f}s)")
                result["success"] = True
            else:
                print(f"❌ {test_dir.relative_to(self.project_root)} 测试失败 (返回码: {proc_result.returncode}, {result['duration']:.2f}s)")
                result["success"] = False
                
        except subprocess.TimeoutExpired:
            result["duration"] = time.time() - start_time
            result["success"] = False
            result["output"] = "测试超时"
            print(f"⏰ {test_dir.relative_to(self.project_root)} 测试超时 ({result['duration']:.2f}s)")
            
        except Exception as e:
            result["duration"] = time.time() - start_time
            result["success"] = False
            result["output"] = str(e)
            print(f"💥 运行测试时出错: {e}")
        
        return result
    
    def run_all_tests(self) -> bool:
        """运行所有测试目录中的测试"""
        print("🚀 运行全量测试...")
        print(f"📂 项目根目录: {self.project_root}")
        
        # 查找所有测试目录
        test_dirs = self.find_all_test_directories()
        
        if not test_dirs:
            print("❌ 没有找到任何测试目录")
            return False
        
        print(f"\n📋 找到 {len(test_dirs)} 个测试目录:")
        for test_dir in test_dirs:
            print(f"  - {test_dir.relative_to(self.project_root)}")
        
        # 运行所有测试
        all_results = []
        start_time = time.time()
        
        for test_dir in test_dirs:
            print(f"\n{'='*60}")
            result = self.run_tests_in_directory(test_dir)
            all_results.append(result)
        
        total_duration = time.time() - start_time
        
        # 统计结果
        successful_tests = sum(1 for r in all_results if r["success"])
        failed_tests = len(all_results) - successful_tests
        total_test_files = sum(len(r["test_files"]) for r in all_results)
        
        # 打印总结
        print(f"\n{'='*60}")
        print("📊 全量测试结果总结:")
        print(f"  📁 测试目录: {len(all_results)}")
        print(f"  📄 测试文件: {total_test_files}")
        print(f"  ✅ 成功: {successful_tests}")
        print(f"  ❌ 失败: {failed_tests}")
        print(f"  ⏱️ 总耗时: {total_duration:.2f}s")
        
        if failed_tests > 0:
            print(f"\n💥 失败的测试目录:")
            for result in all_results:
                if not result["success"]:
                    print(f"  ❌ {result['directory']}")
        
        return failed_tests == 0
    
    def run_smart_tests(self, base_branch: str = "HEAD~1") -> bool:
        """基于git diff运行智能测试"""
        print("🎯 运行智能测试...")
        print(f"📂 项目根目录: {self.project_root}")
        print(f"🌿 基准分支: {base_branch}")
        
        # 获取变化的文件
        changed_files = self.get_changed_files(base_branch)
        
        if not changed_files:
            print("📝 没有检测到文件变化，跳过测试")
            return True
        
        print(f"\n📋 检测到 {len(changed_files)} 个变化文件:")
        for file in changed_files[:10]:  # 只显示前10个
            print(f"  - {file}")
        if len(changed_files) > 10:
            print(f"  ... 还有 {len(changed_files) - 10} 个文件")
        
        # 找到受影响的测试目录
        affected_test_dirs = self.get_affected_test_directories(changed_files)
        
        if not affected_test_dirs:
            print("📝 没有找到受影响的测试目录，跳过测试")
            return True
        
        print(f"\n🎯 需要运行的测试目录 ({len(affected_test_dirs)} 个):")
        for test_dir in sorted(affected_test_dirs):
            print(f"  - {test_dir.relative_to(self.project_root)}")
        
        # 运行受影响的测试
        all_results = []
        start_time = time.time()
        
        for test_dir in sorted(affected_test_dirs):
            print(f"\n{'='*60}")
            result = self.run_tests_in_directory(test_dir)
            all_results.append(result)
        
        total_duration = time.time() - start_time
        
        # 统计结果
        successful_tests = sum(1 for r in all_results if r["success"])
        failed_tests = len(all_results) - successful_tests
        total_test_files = sum(len(r["test_files"]) for r in all_results)
        
        # 打印总结
        print(f"\n{'='*60}")
        print("📊 智能测试结果总结:")
        print(f"  📄 变化文件: {len(changed_files)}")
        print(f"  📁 测试目录: {len(all_results)}")
        print(f"  📄 测试文件: {total_test_files}")
        print(f"  ✅ 成功: {successful_tests}")
        print(f"  ❌ 失败: {failed_tests}")
        print(f"  ⏱️ 总耗时: {total_duration:.2f}s")
        
        if failed_tests > 0:
            print(f"\n💥 失败的测试目录:")
            for result in all_results:
                if not result["success"]:
                    print(f"  ❌ {result['directory']}")
        
        return failed_tests == 0
    
    def list_test_directories(self):
        """列出所有测试目录"""
        print("📋 所有测试目录:")
        print(f"📂 项目根目录: {self.project_root}")
        
        test_dirs = self.find_all_test_directories()
        
        if not test_dirs:
            print("❌ 没有找到任何测试目录")
            return
        
        print(f"\n找到 {len(test_dirs)} 个测试目录:")
        
        # 按层级组织显示
        dir_tree = {}
        for test_dir in test_dirs:
            rel_path = test_dir.relative_to(self.project_root)
            parts = rel_path.parts
            
            current = dir_tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # 统计测试文件数量
            test_files = self.find_test_files_in_dir(test_dir)
            current[parts[-1]] = f"{len(test_files)} 个测试文件"
        
        def print_tree(tree, prefix=""):
            for key, value in sorted(tree.items()):
                if isinstance(value, dict):
                    print(f"{prefix}📁 {key}/")
                    print_tree(value, prefix + "  ")
                else:
                    print(f"{prefix}🧪 {key}/ ({value})")
        
        print_tree(dir_tree)


def main():
    parser = argparse.ArgumentParser(
        description="SAGE 智能测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python test_runner.py --all                    # 运行所有测试
  python test_runner.py --diff                   # 基于git diff运行智能测试
  python test_runner.py --diff --base main       # 指定基准分支为main
  python test_runner.py --list                   # 列出所有测试目录
        """
    )
    
    parser.add_argument("--all", action="store_true",
                       help="运行所有测试目录中的测试")
    parser.add_argument("--diff", action="store_true", 
                       help="基于git diff运行智能测试")
    parser.add_argument("--base", default="HEAD~1",
                       help="git diff的基准分支 (默认: HEAD~1)")
    parser.add_argument("--list", action="store_true",
                       help="列出所有测试目录")
    parser.add_argument("--project-root",
                       help="项目根目录路径 (默认: 当前目录)")
    
    args = parser.parse_args()
    
    # 检查参数
    if not any([args.all, args.diff, args.list]):
        parser.error("必须指定 --all, --diff 或 --list 中的一个选项")
    
    # 创建测试运行器
    runner = SAGETestRunner(args.project_root)
    
    try:
        if args.list:
            runner.list_test_directories()
            sys.exit(0)
        elif args.all:
            success = runner.run_all_tests()
        elif args.diff:
            success = runner.run_smart_tests(args.base)
        
        # 设置退出码
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 运行测试时出现异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
