#!/usr/bin/env python3
"""
SAGE 重构脚本 - 识别核心依赖模块
===============================

分析哪些模块是核心依赖，需要保留在 sage.common 中
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict

def analyze_imports():
    """分析所有导入，识别核心依赖模块"""
    project_root = Path("/home/shuhao/SAGE")
    
    # 收集所有导入信息
    imports_by_module = defaultdict(set)
    
    # 扫描所有 Python 文件
    for root, dirs, files in os.walk(project_root):
        # 跳过某些目录
        if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', '.venv', 'site']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # 查找 sage.common 的导入
                    imports = re.findall(r'from sage\.common\.([a-zA-Z0-9_.]+)', content)
                    imports.extend(re.findall(r'import sage\.common\.([a-zA-Z0-9_.]+)', content))
                    
                    for imp in imports:
                        imports_by_module[imp].add(str(file_path))
                        
                except Exception as e:
                    print(f"警告：无法读取文件 {file_path}: {e}")
    
    return imports_by_module

def main():
    print("🔍 分析 SAGE 项目中的 sage.common 依赖...")
    
    imports_by_module = analyze_imports()
    
    print("\n📋 详细的依赖分析：")
    
    # 分类模块
    core_utils = []
    dev_tools = []
    
    for module, files in imports_by_module.items():
        print(f"\n🔸 sage.common.{module}")
        print(f"   被 {len(files)} 个文件使用:")
        for file_path in sorted(list(files)[:5]):  # 只显示前5个
            relative_path = str(Path(file_path).relative_to(Path("/home/shuhao/SAGE")))
            print(f"     - {relative_path}")
        if len(files) > 5:
            print(f"     ... 还有 {len(files) - 5} 个文件")
            
        # 分类
        if module.startswith('utils.') and not any(x in module for x in ['cli', 'frontend', 'dev']):
            core_utils.append(module)
        elif module.startswith('_version'):
            core_utils.append(module)
        else:
            dev_tools.append(module)
    
    print(f"\n📊 统计：")
    print(f"  核心工具模块: {len(core_utils)}")
    print(f"  开发工具模块: {len(dev_tools)}")
    
    print(f"\n💡 迁移建议：")
    print("保留在新 sage-common 的核心模块：")
    for module in sorted(core_utils):
        print(f"  ✅ {module}")
    
    print("\n已经在 sage-tools 中的开发工具：")
    for module in sorted(dev_tools):
        print(f"  🔄 {module}")

if __name__ == "__main__":
    main()
