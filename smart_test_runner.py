#!/usr/bin/env python3
"""
SAGE Smart Test Runner

这个脚本根据git diff自动确定需要运行的测试，并执行相应的测试模块。
支持按模块运行测试，提高CI/CD效率。

Usage:
    python smart_test_runner.py                    # 运行所有测试
    python smart_test_runner.py --diff             # 基于git diff运行测试
    python smart_test_runner.py --module core      # 运行特定模块测试
    python smart_test_runner.py --category unit    # 运行特定类别测试
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
import pytest
import time
from typing import List, Set

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sage.test_config import (
    TEST_MODULE_MAP, 
    TEST_CATEGORIES, 
    get_test_modules_for_changed_files,
    get_all_test_modules
)

class SmartTestRunner:
    """智能测试运行器"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
    
    def get_changed_files(self, base_branch="main"):
        """获取相对于base分支的变更文件"""
        try:
            # 获取变更的文件
            cmd = f"git diff --name-only {base_branch}...HEAD"
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, cwd=self.project_root
            )
            
            if result.returncode != 0:
                print(f"⚠️  无法获取git diff: {result.stderr}")
                return []
            
            changed_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            return changed_files
            
        except Exception as e:
            print(f"❌ 获取变更文件时出错: {e}")
            return []
    
    def run_test_module(self, test_path: str, category: str = None):
        """运行指定测试模块"""
        full_test_path = self.project_root / test_path
        
        if not full_test_path.exists():
            print(f"⚠️  测试路径不存在: {full_test_path}")
            return False
        
        print(f"\n🧪 运行测试模块: {test_path}")
        print("-" * 50)
        
        # 构建pytest命令
        pytest_args = [
            str(full_test_path),
            "-v",  # 详细输出
            "--tb=short",  # 简短的traceback
            "--color=yes",  # 彩色输出
        ]
        
        # 根据类别添加过滤
        if category and category in TEST_CATEGORIES:
            patterns = TEST_CATEGORIES[category]["patterns"]
            for pattern in patterns:
                pytest_args.extend(["-k", pattern])
        
        try:
            start_time = time.time()
            result = pytest.main(pytest_args)
            duration = time.time() - start_time
            
            print(f"⏱️  测试耗时: {duration:.2f}秒")
            
            if result == 0:
                print(f"✅ {test_path} 测试通过")
                self.results["passed"] += 1
                return True
            else:
                print(f"❌ {test_path} 测试失败 (退出码: {result})")
                self.results["failed"] += 1
                self.results["errors"].append(f"{test_path}: 测试失败")
                return False
                
        except Exception as e:
            print(f"❌ 运行测试时出错: {e}")
            self.results["errors"].append(f"{test_path}: {str(e)}")
            return False
    
    def run_all_tests(self, category: str = None):
        """运行所有测试"""
        print("🚀 运行所有测试模块")
        print("=" * 50)
        
        test_modules = get_all_test_modules()
        success_count = 0
        
        for test_module in test_modules:
            if self.run_test_module(test_module, category):
                success_count += 1
        
        return success_count == len(test_modules)
    
    def run_diff_tests(self, base_branch="main", category: str = None):
        """基于git diff运行测试"""
        print(f"🔍 分析与 {base_branch} 分支的差异...")
        
        changed_files = self.get_changed_files(base_branch)
        
        if not changed_files:
            print("📝 没有发现文件变更，跳过测试")
            return True
        
        print(f"📋 发现 {len(changed_files)} 个变更文件:")
        for file in changed_files:
            print(f"  - {file}")
        
        # 确定需要运行的测试模块
        test_modules = get_test_modules_for_changed_files(changed_files)
        
        if not test_modules:
            print("📝 变更文件不影响任何测试模块，跳过测试")
            return True
        
        print(f"\n🎯 需要运行 {len(test_modules)} 个测试模块:")
        for module in test_modules:
            print(f"  - {module}")
        
        print("\n" + "=" * 50)
        
        success_count = 0
        for test_module in test_modules:
            if self.run_test_module(test_module, category):
                success_count += 1
        
        return success_count == len(test_modules)
    
    def run_module_tests(self, module_name: str, category: str = None):
        """运行特定模块的测试"""
        # 查找匹配的测试模块
        matching_modules = []
        for source_path, test_path in TEST_MODULE_MAP.items():
            if module_name in source_path or module_name in test_path:
                matching_modules.append(test_path)
        
        if not matching_modules:
            print(f"❌ 未找到模块 '{module_name}' 的测试")
            return False
        
        print(f"🎯 运行模块 '{module_name}' 的测试:")
        for module in matching_modules:
            print(f"  - {module}")
        
        success_count = 0
        for test_module in matching_modules:
            if self.run_test_module(test_module, category):
                success_count += 1
        
        return success_count == len(matching_modules)
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 50)
        print("📊 测试总结")
        print("=" * 50)
        print(f"✅ 通过: {self.results['passed']}")
        print(f"❌ 失败: {self.results['failed']}")
        print(f"⏭️  跳过: {self.results['skipped']}")
        
        if self.results["errors"]:
            print(f"\n❌ 错误详情:")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        total = self.results["passed"] + self.results["failed"]
        if total > 0:
            success_rate = (self.results["passed"] / total) * 100
            print(f"\n🎯 成功率: {success_rate:.1f}%")

def main():
    parser = argparse.ArgumentParser(description="SAGE Smart Test Runner")
    parser.add_argument(
        "--diff", "-d", 
        action="store_true",
        help="基于git diff运行相关测试"
    )
    parser.add_argument(
        "--module", "-m",
        type=str,
        help="运行特定模块的测试 (如: core, service, runtime)"
    )
    parser.add_argument(
        "--category", "-c",
        choices=list(TEST_CATEGORIES.keys()),
        help=f"运行特定类别的测试 ({', '.join(TEST_CATEGORIES.keys())})"
    )
    parser.add_argument(
        "--base-branch", "-b",
        default="main",
        help="用于diff比较的基础分支 (默认: main)"
    )
    parser.add_argument(
        "--list-modules", "-l",
        action="store_true",
        help="列出所有可用的测试模块"
    )
    
    args = parser.parse_args()
    
    if args.list_modules:
        print("📋 可用的测试模块:")
        for source, test in TEST_MODULE_MAP.items():
            test_path = PROJECT_ROOT / test
            exists = "✅" if test_path.exists() else "❌"
            print(f"  {source} → {test} {exists}")
        return
    
    runner = SmartTestRunner()
    
    try:
        if args.diff:
            success = runner.run_diff_tests(args.base_branch, args.category)
        elif args.module:
            success = runner.run_module_tests(args.module, args.category)
        else:
            success = runner.run_all_tests(args.category)
        
        runner.print_summary()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 运行测试时出现异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
