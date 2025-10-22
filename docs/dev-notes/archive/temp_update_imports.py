#!/usr/bin/env python3
"""临时脚本：更新所有 sage.kernel.core 导入到 sage.common.core"""

import os
import re
from pathlib import Path

# 需要更新的文件列表
files_to_update = [
    "packages/sage-kernel/src/sage/kernel/fault_tolerance/impl/checkpoint_recovery.py",
    "packages/sage-kernel/src/sage/kernel/fault_tolerance/impl/lifecycle_impl.py",
    "packages/sage-kernel/src/sage/kernel/fault_tolerance/impl/checkpoint_impl.py",
    "packages/sage-kernel/src/sage/kernel/fault_tolerance/impl/restart_recovery.py",
    "packages/sage-kernel/src/sage/kernel/fault_tolerance/impl/restart_strategy.py",
]

def update_imports(filepath):
    """更新文件中的导入语句"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换导入语句
        original_content = content
        content = re.sub(
            r'from sage\.kernel\.core\.',
            'from sage.common.core.',
            content
        )
        content = re.sub(
            r'import sage\.kernel\.core\.',
            'import sage.common.core.',
            content
        )
        
        # 如果有修改，写回文件
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Updated: {filepath}")
            return True
        else:
            print(f"- No changes: {filepath}")
            return False
    except Exception as e:
        print(f"✗ Error updating {filepath}: {e}")
        return False

# 主逻辑
if __name__ == "__main__":
    base_dir = Path(__file__).parent
    updated_count = 0
    
    for file_rel_path in files_to_update:
        file_path = base_dir / file_rel_path
        if file_path.exists():
            if update_imports(file_path):
                updated_count += 1
        else:
            print(f"! File not found: {file_path}")
    
    print(f"\n完成！共更新 {updated_count} 个文件")
