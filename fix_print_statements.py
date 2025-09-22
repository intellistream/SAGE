#!/usr/bin/env python3
"""
import logging
Script to replace print statements with logging calls in SAGE codebase.
This script will:
1. Find all Python files with print statements
2. Replace logging.info() calls with appropriate logging calls
3. Add logging import if needed
"""

import os
import re
import ast
import sys
from pathlib import Path

def has_logging_import(tree):
    """Check if file already imports logging"""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'logging':
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == 'logging':
                return True
    return False

def has_custom_logger_import(tree):
    """Check if file imports CustomLogger"""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == 'sage.common.utils.logging.custom_logger':
                return True
    return False

def add_logging_import(content):
    """Add logging import at the top of the file"""
    lines = content.split('\n')
    # Find the first import or the shebang/docstring
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith('#!') or line.startswith('"""') or line.startswith("'''"):
            continue
        elif line.startswith('import ') or line.startswith('from '):
            insert_pos = i
            break
        elif line.strip() and not line.startswith('#'):
            insert_pos = i
            break

    lines.insert(insert_pos, 'import logging')
    return '\n'.join(lines)

def add_custom_logger_import(content):
    """Add CustomLogger import"""
    lines = content.split('\n')
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith('#!') or line.startswith('"""') or line.startswith("'''"):
            continue
        elif line.startswith('import ') or line.startswith('from '):
            insert_pos = i
            break
        elif line.strip() and not line.startswith('#'):
            insert_pos = i
            break

    lines.insert(insert_pos, 'from sage.common.utils.logging.custom_logger import CustomLogger')
    return '\n'.join(lines)

def replace_print_with_log(content, file_path):
    """Replace print statements with logging calls"""
    # Parse the AST
    try:
        tree = ast.parse(content, filename=file_path)
    except SyntaxError:
        logging.info(f"Skipping {file_path}: syntax error")
        return content

    # Check if it's a core package file
    is_core = 'packages/sage-' in file_path and not 'tests' in file_path

    # Check existing imports
    has_logging = has_logging_import(tree)
    has_custom = has_custom_logger_import(tree)

    # For core files, use CustomLogger
    if is_core and not has_custom:
        content = add_custom_logger_import(content)
        # Replace print with logger.info, assuming logger is initialized
        # Simple regex replacement for logging.info(
        content = re.sub(r'\bprint\(', 'self.logger.info(', content)
    elif not is_core:
        # For examples/tools, use standard logging
        if not has_logging:
            content = add_logging_import(content)
        content = re.sub(r'\bprint\(', 'logging.info(', content)

    return content

def main():
    # Find all Python files with print statements
    cmd = 'find /home/shuhao/SAGE -name "*.py" -not -path "*/.sage/*" -not -path "*/__pycache__/*" -exec grep -l "logging.info(" {} \\;'
    import subprocess
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    files = result.stdout.strip().split('\n') if result.stdout.strip() else []

    logging.info(f"Found {len(files)} files with print statements")

    for file_path in files:
        if not file_path or not os.path.exists(file_path):
            continue

        logging.info(f"Processing {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content = replace_print_with_log(content, file_path)

            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                logging.info(f"Updated {file_path}")
            else:
                logging.info(f"No changes needed for {file_path}")

        except Exception as e:
            logging.info(f"Error processing {file_path}: {e}")

if __name__ == '__main__':
    main()