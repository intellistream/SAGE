#!/usr/bin/env python3
"""
专门检查packages中类名依赖的快速分析脚本
"""

import os
import re
import ast
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set

def extract_from_imports_and_classes(file_path: Path):
    """快速提取文件中的from导入和类定义"""
    from_imports = []
    class_names = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则表达式快速提取from导入
        from_pattern = r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import\s+([^#\n]+)'
        for match in re.finditer(from_pattern, content):
            module = match.group(1)
            imports = match.group(2)
            
            # 处理多个导入项
            import_items = [item.strip() for item in imports.split(',')]
            for item in import_items:
                # 处理 as 别名
                if ' as ' in item:
                    original, alias = item.split(' as ', 1)
                    item = original.strip()
                
                item = item.strip()
                if item and item != '*':
                    from_imports.append({
                        'module': module,
                        'name': item,
                        'line': content[:match.start()].count('\n') + 1
                    })
        
        # 使用正则表达式提取类定义
        class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]'
        for match in re.finditer(class_pattern, content):
            class_names.append(match.group(1))
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return from_imports, class_names

def analyze_class_dependencies():
    """分析类依赖关系"""
    packages_path = Path("/home/flecther/SAGE/packages")
    
    if not packages_path.exists():
        print("❌ packages目录不存在!")
        return
    
    # 收集数据
    class_definitions = defaultdict(list)  # 类名 -> 定义文件列表
    class_imports = defaultdict(list)      # 类名 -> 导入文件列表
    all_from_imports = defaultdict(list)   # 文件 -> from导入列表
    
    python_files = list(packages_path.rglob("*.py"))
    print(f"🔍 分析 {len(python_files)} 个Python文件...")
    
    for file_path in python_files:
        rel_path = str(file_path.relative_to(packages_path.parent))
        
        from_imports, classes = extract_from_imports_and_classes(file_path)
        
        # 记录类定义
        for class_name in classes:
            class_definitions[class_name].append(rel_path)
        
        # 记录from导入
        all_from_imports[rel_path] = from_imports
        for imp in from_imports:
            # 假设导入的项可能是类名
            class_imports[imp['name']].append({
                'file': rel_path,
                'from_module': imp['module'],
                'line': imp['line']
            })
    
    return class_definitions, class_imports, all_from_imports

def print_class_dependency_report():
    """打印类依赖报告"""
    print("\n" + "="*80)
    print("SAGE PACKAGES - 类名依赖分析报告")
    print("="*80)
    
    class_definitions, class_imports, all_from_imports = analyze_class_dependencies()
    
    print(f"\n📊 统计信息:")
    print(f"  • 定义的类总数: {len(class_definitions)}")
    print(f"  • 被导入的项总数: {len(class_imports)}")
    
    # 找出被多次定义的类
    multi_defined = {name: files for name, files in class_definitions.items() if len(files) > 1}
    if multi_defined:
        print(f"\n⚠️  多处定义的类 ({len(multi_defined)}):")
        for class_name, files in multi_defined.items():
            print(f"  • {class_name}: {len(files)} 处定义")
            for file_path in files:
                print(f"    - {file_path}")
    
    # 显示最常被导入的类名
    import_counts = {name: len(imports) for name, imports in class_imports.items()}
    top_imported = Counter(import_counts).most_common(20)
    
    print(f"\n🔝 最常被导入的类名/项 (Top 20):")
    for name, count in top_imported:
        if count > 1:  # 只显示被多次导入的
            print(f"  • {name}: 被 {count} 个文件导入")
            # 检查是否在本地定义
            if name in class_definitions:
                print(f"    ✓ 在本地定义: {', '.join(class_definitions[name])}")
            else:
                print(f"    ? 可能是外部依赖")
    
    # 分析内部vs外部依赖
    print(f"\n🔗 导入来源分析:")
    internal_imports = 0
    external_imports = 0
    sage_imports = 0
    
    module_stats = defaultdict(int)
    
    for file_path, imports in all_from_imports.items():
        for imp in imports:
            module = imp['module']
            module_stats[module] += 1
            
            if module.startswith('sage'):
                sage_imports += 1
            elif any(stdlib in module for stdlib in ['os', 'sys', 'json', 'typing', 'collections', 'asyncio', 'logging', 'pathlib', 'datetime', 're', 'abc']):
                internal_imports += 1
            else:
                external_imports += 1
    
    total_imports = internal_imports + external_imports + sage_imports
    print(f"  • SAGE内部模块导入: {sage_imports} ({sage_imports/total_imports*100:.1f}%)")
    print(f"  • Python标准库导入: {internal_imports} ({internal_imports/total_imports*100:.1f}%)")
    print(f"  • 第三方库导入: {external_imports} ({external_imports/total_imports*100:.1f}%)")
    
    # 显示最常用的外部模块
    external_modules = {mod: count for mod, count in module_stats.items() 
                       if not mod.startswith('sage') and count > 2}
    
    if external_modules:
        print(f"\n📦 主要外部依赖模块:")
        for module, count in sorted(external_modules.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"  • {module}: {count} 次导入")
    
    # 检查可能的类名匹配
    print(f"\n🎯 类名匹配分析:")
    matched_classes = 0
    unmatched_imports = []
    
    for imported_name, import_info in class_imports.items():
        if imported_name in class_definitions:
            matched_classes += 1
        else:
            # 检查是否看起来像类名（首字母大写）
            if imported_name[0].isupper() and len(import_info) > 1:
                unmatched_imports.append((imported_name, len(import_info)))
    
    print(f"  • 本地定义的类被导入: {matched_classes}")
    print(f"  • 可能的外部类导入: {len(unmatched_imports)}")
    
    if unmatched_imports:
        print(f"\n🔍 疑似外部类导入 (被多次使用):")
        for name, count in sorted(unmatched_imports, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  • {name}: {count} 次导入")
            # 显示来源模块
            sources = set()
            for imp_info in class_imports[name]:
                sources.add(imp_info['from_module'])
            print(f"    来自: {', '.join(sorted(sources))}")

def main():
    """主函数"""
    try:
        print_class_dependency_report()
        print(f"\n✅ 分析完成!")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ 分析被中断")
    except Exception as e:
        print(f"\n❌ 分析出错: {e}")

if __name__ == "__main__":
    main()
