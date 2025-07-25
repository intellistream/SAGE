#!/usr/bin/env python3
"""
清理旧的测试目录结构

这个脚本用于清理sage/tests/目录，在确认新的测试结构工作正常后执行。
"""

import os
import shutil
from pathlib import Path

def main():
    project_root = Path(__file__).parent
    old_tests_dir = project_root / "sage" / "tests"
    
    if not old_tests_dir.exists():
        print("✅ 旧的测试目录已经不存在")
        return
    
    print("🧹 准备清理旧的测试目录结构...")
    print(f"目标目录: {old_tests_dir}")
    
    # 显示将要删除的内容
    print("\n📋 将要删除的内容:")
    for item in old_tests_dir.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(old_tests_dir)
            print(f"  - {rel_path}")
    
    # 确认删除
    response = input("\n❓ 确认删除旧的测试目录? (y/N): ").strip().lower()
    
    if response == 'y':
        try:
            shutil.rmtree(old_tests_dir)
            print("✅ 旧的测试目录已成功删除")
        except Exception as e:
            print(f"❌ 删除失败: {e}")
    else:
        print("ℹ️  取消删除操作")

if __name__ == "__main__":
    main()
