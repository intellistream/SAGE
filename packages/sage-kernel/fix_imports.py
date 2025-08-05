#!/usr/bin/env python3
"""
Script to fix import paths after sage-kernel restructuring
"""
import os
import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix import statements in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix imports - update old paths to new paths
        replacements = [
            # Core imports that moved to kernels/core
            (r'from sage\.core\.', 'from sage.kernels.core.'),
            (r'import sage\.core\.', 'import sage.kernels.core.'),
            
            # Jobmanager imports that moved to kernels/jobmanager
            (r'from sage\.jobmanager\.', 'from sage.kernels.jobmanager.'),
            (r'import sage\.jobmanager\.', 'import sage.kernels.jobmanager.'),
            
            # Runtime imports that moved to kernels/runtime
            (r'from sage\.runtime\.', 'from sage.kernels.runtime.'),
            (r'import sage\.runtime\.', 'import sage.kernels.runtime.'),
            
            # Special case: function and api that moved to api/
            (r'from sage\.kernels\.core\.function\.', 'from sage.api.function.'),
            (r'import sage\.kernels\.core\.function\.', 'import sage.api.function.'),
            (r'from sage\.kernels\.core\.api\.', 'from sage.api.'),
            (r'import sage\.kernels\.core\.api\.', 'import sage.api.'),
        ]
        
        for old_pattern, new_replacement in replacements:
            content = re.sub(old_pattern, new_replacement, content)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed imports in: {file_path}")
            return True
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all imports"""
    sage_kernel_path = Path("/home/shuhao/SAGE/packages/sage-kernel/src")
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk(sage_kernel_path):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Found {len(python_files)} Python files to process")
    
    fixed_count = 0
    for file_path in python_files:
        if fix_imports_in_file(file_path):
            fixed_count += 1
    
    print(f"Fixed imports in {fixed_count} files")

if __name__ == "__main__":
    main()
