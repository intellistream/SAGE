#!/usr/bin/env python3
"""
智能测试运行器 - 基于代码变化映射到 sage_tests 目录运行测试

根据git变化的文件，自动映射到相应的sage_tests/xxx_tests目录并运行测试。
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Set, Dict

class SmartTestRunner:
    """智能测试运行器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.sage_tests_dir = self.project_root / "sage_tests"
        
        # 定义源代码目录到测试目录的映射关系
        self.source_to_test_mapping = {
            # 核心模块映射
            "sage.core/": "core_tests/",
            "sage.runtime/": "runtime_tests/", 
            "sage.service.memory./": "memory_tests/",
            "sage_vector/": "vector_tests/",
            "frontend/": "frontend_tests/",
            "sage_utils/": "utils_tests/",
            "sage_libs/": "function_tests/",  # sage_libs 主要包含函数实现
            "sage_plugins/": "function_tests/",  # plugins 也归类到函数测试
            
            # 特殊映射
            "sage.core/service/": "service_tests/",
            "sage.core/function/": "function_tests/",
            "sage_libs/io/": "function_tests/io_tests/",
            "sage_libs/rag/": "function_tests/rag_tests/",
        }
    
    def get_changed_files(self, base_branch: str = "HEAD~1") -> List[str]:
        """获取相对于基准分支的变化文件列表"""
        try:
            # 在GitHub Actions中，使用origin/main作为基准
            if os.getenv('GITHUB_ACTIONS'):
                base_branch = "origin/main"
            
            cmd = ["git", "diff", "--name-only", base_branch]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            changed_files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            print(f"🔍 检测到 {len(changed_files)} 个文件发生变化:")
            for file in changed_files:
                print(f"  - {file}")
            
            return changed_files
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 获取变化文件失败: {e}")
            # 如果git命令失败，返回空列表（不运行任何测试）
            return []
    
    def map_source_to_test_dirs(self, changed_files: List[str]) -> Set[str]:
        """将源文件映射到对应的测试目录"""
        test_dirs = set()
        
        for file_path in changed_files:
            # 跳过非Python文件和测试文件本身
            if not file_path.endswith('.py') or file_path.startswith('sage_tests/'):
                continue
            
            # 根据映射规则找到对应的测试目录
            mapped = False
            for source_prefix, test_prefix in self.source_to_test_mapping.items():
                if file_path.startswith(source_prefix):
                    test_dir = self.sage_tests_dir / test_prefix
                    if test_dir.exists():
                        test_dirs.add(str(test_dir))
                        print(f"📁 {file_path} -> {test_prefix}")
                        mapped = True
                        break
            
            if not mapped:
                # 尝试通用映射：从顶级sage_xxx目录映射到对应的xxx_tests
                parts = file_path.split('/')
                if len(parts) >= 1 and parts[0].startswith('sage_'):
                    module_name = parts[0].replace('sage_', '')
                    test_dir = self.sage_tests_dir / f"{module_name}_tests"
                    if test_dir.exists():
                        test_dirs.add(str(test_dir))
                        print(f"📁 {file_path} -> {module_name}_tests/ (通用映射)")
                    else:
                        print(f"⚠️  {file_path} 无对应测试目录: {test_dir}")
                else:
                    print(f"⚠️  {file_path} 无法映射到测试目录")
        
        return test_dirs
    
    def find_test_files_in_dir(self, test_dir: str) -> List[str]:
        """查找指定目录下的所有测试文件"""
        test_files = []
        test_dir_path = Path(test_dir)
        
        # 递归查找所有以test_开头的.py文件
        for test_file in test_dir_path.rglob("test_*.py"):
            test_files.append(str(test_file))
        
        # 也查找以_test.py结尾的文件
        for test_file in test_dir_path.rglob("*_test.py"):
            test_files.append(str(test_file))
        
        return sorted(list(set(test_files)))  # 去重并排序
    
    def run_tests_in_directory(self, test_dir: str) -> bool:
        """运行指定目录下的测试"""
        test_files = self.find_test_files_in_dir(test_dir)
        
        if not test_files:
            print(f"📂 {test_dir} 中没有找到测试文件")
            return True
        
        print(f"\n🧪 运行 {test_dir} 中的测试:")
        for test_file in test_files:
            print(f"  - {test_file}")
        
        # 使用pytest运行测试
        cmd = [
            sys.executable, "-m", "pytest",
            "-v",  # 详细输出
            "--tb=short",  # 简短的错误追踪
            *test_files
        ]
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root, check=False)
            if result.returncode == 0:
                print(f"✅ {test_dir} 测试通过")
                return True
            else:
                print(f"❌ {test_dir} 测试失败 (返回码: {result.returncode})")
                return False
        except Exception as e:
            print(f"❌ 运行测试时出错: {e}")
            return False
    
    def run_smart_tests(self, base_branch: str = "HEAD~1") -> bool:
        """运行智能测试"""
        print("🚀 开始智能测试...")
        print(f"📂 项目根目录: {self.project_root}")
        print(f"📂 测试目录: {self.sage_tests_dir}")
        
        # 检查sage_tests目录是否存在
        if not self.sage_tests_dir.exists():
            print(f"❌ 测试目录不存在: {self.sage_tests_dir}")
            return False
        
        # 获取变化的文件
        changed_files = self.get_changed_files(base_branch)
        if not changed_files:
            print("📝 没有检测到相关的代码变化，跳过测试")
            return True
        
        # 映射到测试目录
        test_dirs = self.map_source_to_test_dirs(changed_files)
        if not test_dirs:
            print("📝 没有找到对应的测试目录，跳过测试")
            return True
        
        print(f"\n🎯 需要运行的测试目录 ({len(test_dirs)} 个):")
        for test_dir in sorted(test_dirs):
            print(f"  - {test_dir}")
        
        # 运行每个测试目录中的测试
        all_passed = True
        results = {}
        
        for test_dir in sorted(test_dirs):
            print(f"\n{'='*60}")
            success = self.run_tests_in_directory(test_dir)
            results[test_dir] = success
            if not success:
                all_passed = False
        
        # 打印总结
        print(f"\n{'='*60}")
        print("📊 测试结果总结:")
        for test_dir, success in results.items():
            status = "✅ 通过" if success else "❌ 失败"
            print(f"  {status} {test_dir}")
        
        if all_passed:
            print(f"\n🎉 所有测试通过! ({len(results)} 个测试目录)")
        else:
            failed_count = sum(1 for success in results.values() if not success)
            print(f"\n💥 有 {failed_count}/{len(results)} 个测试目录失败")
        
        return all_passed


def main():
    parser = argparse.ArgumentParser(description="智能测试运行器")
    parser.add_argument("--base-branch", default="HEAD~1", 
                       help="比较的基准分支 (默认: HEAD~1)")
    parser.add_argument("--github-actions", action="store_true",
                       help="在GitHub Actions环境中运行")
    parser.add_argument("--project-root", 
                       help="项目根目录路径")
    
    args = parser.parse_args()
    
    # 设置基准分支
    base_branch = args.base_branch
    if args.github_actions:
        base_branch = "origin/main"
    
    # 创建测试运行器
    runner = SmartTestRunner(args.project_root)
    
    # 运行测试
    success = runner.run_smart_tests(base_branch)
    
    # 设置退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
