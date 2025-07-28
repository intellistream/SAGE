#!/usr/bin/env python3
"""
验证测试文件的import路径

这个脚本检查所有测试文件的import语句，确保它们使用正确的路径。
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def find_test_files(root_dir: Path) -> List[Path]:
    """查找所有测试文件"""
    test_files = []
    
    for test_dir in root_dir.rglob("tests"):
        if test_dir.is_dir():
            for test_file in test_dir.rglob("*.py"):
                if test_file.name != "__init__.py":
                    test_files.append(test_file)
    
    return test_files

def check_import_paths(file_path: Path) -> List[Tuple[int, str, str]]:
    """检查文件中的import路径"""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查相对import
            if re.match(r'^from\s+(core|runtime|service|utils|memory)\.', line):
                suggestion = line.replace('from ', 'from sage.')
                issues.append((i, line, suggestion))
            
            # 检查其他可能的问题import
            if re.match(r'^from\s+sage_', line):
                suggestion = line.replace('sage_', 'sage.')
                issues.append((i, line, suggestion))
                
    except Exception as e:
        issues.append((0, f"无法读取文件: {e}", ""))
    
    return issues

def main():
    project_root = Path(__file__).parent
    
    print("🔍 验证测试文件的import路径...")
    print("=" * 50)
    
    test_files = find_test_files(project_root)
    print(f"📋 找到 {len(test_files)} 个测试文件")
    
    total_issues = 0
    files_with_issues = 0
    
    for test_file in test_files:
        rel_path = test_file.relative_to(project_root)
        issues = check_import_paths(test_file)
        
        if issues:
            files_with_issues += 1
            total_issues += len(issues)
            
            print(f"\n❌ {rel_path}:")
            for line_num, original, suggestion in issues:
                if line_num > 0:
                    print(f"  行 {line_num}: {original}")
                    if suggestion:
                        print(f"     建议: {suggestion}")
                else:
                    print(f"  错误: {original}")
    
    print("\n" + "=" * 50)
    print("📊 验证总结:")
    print(f"  - 总文件数: {len(test_files)}")
    print(f"  - 有问题的文件数: {files_with_issues}")
    print(f"  - 总问题数: {total_issues}")
    
    if total_issues == 0:
        print("✅ 所有测试文件的import路径都正确!")
    else:
        print("⚠️  发现import路径问题，请修复后再运行测试")
    
    # 显示测试文件分布
    print(f"\n📁 测试文件分布:")
    test_dirs = {}
    for test_file in test_files:
        test_dir = str(test_file.parent.relative_to(project_root))
        test_dirs[test_dir] = test_dirs.get(test_dir, 0) + 1
    
    for test_dir, count in sorted(test_dirs.items()):
        print(f"  - {test_dir}: {count} 个文件")

if __name__ == "__main__":
    main()
