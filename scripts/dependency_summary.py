#!/usr/bin/env python3
"""
SAGE包依赖关系总结报告
基于依赖分析结果生成简明总结
"""

import json
from pathlib import Path
from collections import defaultdict, Counter

def generate_summary_report():
    """生成总结报告"""
    
    # 读取JSON报告
    report_file = Path("/home/flecther/SAGE/dependency_analysis_report.json")
    if not report_file.exists():
        print("❌ dependency_analysis_report.json 文件不存在!")
        print("请先运行 python scripts/check_package_dependencies.py")
        return
    
    with open(report_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("="*80)
    print("SAGE PACKAGES 依赖关系总结报告")
    print("="*80)
    
    # 基本统计
    summary = data['summary']
    print(f"\n📊 基本统计:")
    print(f"  • Python文件总数: {summary['total_files']}")
    print(f"  • 定义的类总数: {summary['total_classes_defined']}")
    print(f"  • from导入总数: {summary['total_from_imports']}")
    print(f"  • 外部模块数量: {summary['external_modules_count']}")
    print(f"  • 内部模块数量: {summary['internal_modules_count']}")
    
    # 核心类分析
    class_deps = data['class_dependencies']
    
    # 找出核心的SAGE类（被导入次数最多的本地定义类）
    sage_core_classes = []
    for class_name, info in class_deps.items():
        if info['import_count'] > 10:  # 被超过10个文件导入
            sage_core_classes.append((class_name, info['import_count'], info['defined_in']))
    
    sage_core_classes.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n🏗️ 核心SAGE类 (被导入超过10次):")
    for class_name, count, defined_in in sage_core_classes[:15]:
        print(f"  • {class_name}: {count} 次导入")
        if len(defined_in) == 1:
            file_path = defined_in[0].replace('packages/', '')
            print(f"    定义在: {file_path}")
        else:
            print(f"    ⚠️ 多处定义 ({len(defined_in)} 处)")
    
    # 重复定义的类
    duplicate_classes = []
    for class_name, info in class_deps.items():
        if len(info['defined_in']) > 1:
            duplicate_classes.append((class_name, len(info['defined_in']), info['defined_in']))
    
    duplicate_classes.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n⚠️ 重复定义的类 (Top 15):")
    for class_name, count, locations in duplicate_classes[:15]:
        print(f"  • {class_name}: {count} 处定义")
        # 只显示前3个位置
        for loc in locations[:3]:
            short_path = loc.replace('packages/', '').replace('/src/sage/', '/').replace('/src/', '/')
            print(f"    - {short_path}")
        if len(locations) > 3:
            print(f"    ... 还有 {len(locations)-3} 个位置")
    
    # 外部依赖分析
    external_deps = data['external_dependencies']
    
    print(f"\n📦 主要外部依赖 (Top 10):")
    external_counts = Counter()
    for module, usages in external_deps.items():
        external_counts[module] = len(usages)
    
    for module, count in external_counts.most_common(10):
        print(f"  • {module}: {count} 次使用")
    
    # 内部模块依赖分析
    internal_deps = data['internal_dependencies']
    
    print(f"\n🔗 内部模块依赖 (Top 10):")
    internal_counts = Counter()
    for module, usages in internal_deps.items():
        internal_counts[module] = len(usages)
    
    for module, count in internal_counts.most_common(10):
        print(f"  • {module}: {count} 次导入")
    
    # 分析模块结构
    print(f"\n🏛️ 包结构分析:")
    package_stats = defaultdict(int)
    class_by_package = defaultdict(int)
    
    for class_name, info in class_deps.items():
        for file_path in info['defined_in']:
            # 提取包名
            parts = file_path.split('/')
            if len(parts) >= 2 and parts[0] == 'packages':
                package = parts[1]
                package_stats[package] += info['import_count']
                class_by_package[package] += 1
    
    print("  按导入频次排序的包:")
    for package, import_count in sorted(package_stats.items(), key=lambda x: x[1], reverse=True):
        class_count = class_by_package[package]
        print(f"    • {package}: {class_count} 个类, 总导入 {import_count} 次")
    
    # 问题识别
    print(f"\n🚨 潜在问题识别:")
    
    # 1. 重复定义最严重的类
    if duplicate_classes:
        worst_class, worst_count, _ = duplicate_classes[0]
        print(f"  • 最严重的重复定义: {worst_class} ({worst_count} 处定义)")
    
    # 2. 循环依赖检查
    circular_deps = 0
    for module, usages in internal_deps.items():
        for usage in usages:
            file_path = usage['file']
            # 简单检查：如果一个模块导入了定义在同一包中的另一个模块
            if module.startswith('sage.') and file_path.startswith('packages/'):
                if module.replace('.', '/') in file_path:
                    circular_deps += 1
    
    if circular_deps > 0:
        print(f"  • 可能的循环依赖: {circular_deps} 个")
    
    # 3. 未使用的类
    unused_classes = [name for name, info in class_deps.items() if info['import_count'] == 0]
    print(f"  • 未被导入的类: {len(unused_classes)} 个")
    
    print(f"\n✅ 分析完成!")
    print(f"📄 详细信息请查看: dependency_analysis_report.json")

if __name__ == "__main__":
    generate_summary_report()
