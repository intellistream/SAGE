#!/usr/bin/env python3
"""
批量修复类型注解问题

修复模式：
1. list[T] = None -> list[T] | None = None
2. dict[K, V] = None -> dict[K, V] | None = None
3. set[T] = None -> set[T] | None = None
4. tuple[T] = None -> tuple[T] | None = None
5. Type = None -> Type | None = None (for simple types like str, int, etc.)
"""

import re
import sys
from pathlib import Path


def fix_type_annotations_in_file(file_path: Path) -> tuple[bool, int]:
    """
    修复单个文件中的类型注解
    
    Returns:
        (是否修改, 修改次数)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        changes = 0
        
        # 模式1: list[...] = None
        pattern1 = r'(\b\w+\s*:\s*)(list\[[^\]]+\])(\s*=\s*None)'
        replacement1 = r'\1\2 | None\3'
        content, count1 = re.subn(pattern1, replacement1, content)
        changes += count1
        
        # 模式2: dict[..., ...] = None
        pattern2 = r'(\b\w+\s*:\s*)(dict\[[^\]]+\])(\s*=\s*None)'
        replacement2 = r'\1\2 | None\3'
        content, count2 = re.subn(pattern2, replacement2, content)
        changes += count2
        
        # 模式3: set[...] = None
        pattern3 = r'(\b\w+\s*:\s*)(set\[[^\]]+\])(\s*=\s*None)'
        replacement3 = r'\1\2 | None\3'
        content, count3 = re.subn(pattern3, replacement3, content)
        changes += count3
        
        # 模式4: tuple[...] = None
        pattern4 = r'(\b\w+\s*:\s*)(tuple\[[^\]]+\])(\s*=\s*None)'
        replacement4 = r'\1\2 | None\3'
        content, count4 = re.subn(pattern4, replacement4, content)
        changes += count4
        
        # 模式5: 简单类型 str/int/float/bool = None
        pattern5 = r'(\b\w+\s*:\s*)(str|int|float|bool)(\s*=\s*None)(?!\s*\|)'
        replacement5 = r'\1\2 | None\3'
        content, count5 = re.subn(pattern5, replacement5, content)
        changes += count5
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True, changes
        
        return False, 0
        
    except Exception as e:
        print(f"❌ 错误处理 {file_path}: {e}", file=sys.stderr)
        return False, 0


def main():
    # 要处理的目录
    packages_dir = Path(__file__).parent.parent.parent / "packages"
    
    if not packages_dir.exists():
        print(f"❌ 目录不存在: {packages_dir}")
        return 1
    
    # 统计
    total_files = 0
    modified_files = 0
    total_changes = 0
    
    # 遍历所有 Python 文件（排除 build, vendor 等目录）
    exclude_patterns = {
        'build', 'dist', '.venv', 'venv', '__pycache__', 
        '.pytest_cache', 'node_modules', 'vendors', 'sageLLM'
    }
    
    for py_file in packages_dir.rglob("*.py"):
        # 跳过排除的目录
        if any(part in exclude_patterns for part in py_file.parts):
            continue
        
        # 跳过非 src 目录的文件（只处理源代码）
        if 'src' not in py_file.parts and 'tests' not in py_file.parts:
            continue
        
        total_files += 1
        modified, changes = fix_type_annotations_in_file(py_file)
        
        if modified:
            modified_files += 1
            total_changes += changes
            rel_path = py_file.relative_to(packages_dir.parent)
            print(f"✅ {rel_path}: {changes} 处修改")
    
    # 输出统计
    print("\n" + "=" * 60)
    print(f"📊 统计:")
    print(f"  - 扫描文件: {total_files}")
    print(f"  - 修改文件: {modified_files}")
    print(f"  - 总修改数: {total_changes}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
