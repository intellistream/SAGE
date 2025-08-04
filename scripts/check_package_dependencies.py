#!/usr/bin/env python3
"""
检查packages中所有from导入的依赖关系分析脚本
使用类名作为关键字来分析依赖关系
"""

import os
import re
import ast
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
import json

class DependencyAnalyzer:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.packages_path = self.root_path / "packages"
        
        # 存储分析结果
        self.imports_by_file = defaultdict(list)  # 文件 -> 导入列表
        self.class_definitions = defaultdict(set)  # 类名 -> 定义它的文件集合
        self.class_imports = defaultdict(set)     # 类名 -> 导入它的文件集合
        self.module_dependencies = defaultdict(set)  # 模块 -> 依赖的模块集合
        self.from_imports = defaultdict(list)     # 文件 -> from导入列表
        
    def extract_imports_and_classes(self, file_path: Path) -> Tuple[List[dict], List[str]]:
        """提取文件中的导入语句和类定义"""
        imports = []
        classes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # 提取from导入
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        import_info = {
                            'type': 'from',
                            'module': module,
                            'name': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        }
                        imports.append(import_info)
                
                # 提取普通导入
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        import_info = {
                            'type': 'import',
                            'module': "",
                            'name': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        }
                        imports.append(import_info)
                
                # 提取类定义
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                    
        except (SyntaxError, UnicodeDecodeError, Exception) as e:
            print(f"Error parsing {file_path}: {e}")
            
        return imports, classes
    
    def analyze_packages(self):
        """分析packages目录下的所有Python文件"""
        python_files = list(self.packages_path.rglob("*.py"))
        
        print(f"Found {len(python_files)} Python files in packages/")
        
        for file_path in python_files:
            relative_path = file_path.relative_to(self.root_path)
            
            imports, classes = self.extract_imports_and_classes(file_path)
            
            # 存储导入信息
            self.imports_by_file[str(relative_path)] = imports
            
            # 存储from导入
            from_imports = [imp for imp in imports if imp['type'] == 'from']
            self.from_imports[str(relative_path)] = from_imports
            
            # 存储类定义
            for class_name in classes:
                self.class_definitions[class_name].add(str(relative_path))
            
            # 记录类的导入关系
            for imp in imports:
                if imp['type'] == 'from' and imp['name'] != '*':
                    # 假设导入的是类（这里可以进一步优化判断）
                    self.class_imports[imp['name']].add(str(relative_path))
    
    def find_class_dependencies(self) -> Dict[str, Dict]:
        """查找类的依赖关系"""
        class_deps = {}
        
        for class_name in self.class_definitions.keys():
            class_deps[class_name] = {
                'defined_in': list(self.class_definitions[class_name]),
                'imported_by': list(self.class_imports[class_name]),
                'import_count': len(self.class_imports[class_name])
            }
        
        return class_deps
    
    def find_external_dependencies(self) -> Dict[str, List]:
        """查找外部依赖"""
        external_deps = defaultdict(list)
        
        for file_path, imports in self.from_imports.items():
            for imp in imports:
                module = imp['module']
                name = imp['name']
                
                # 判断是否为外部依赖（不在packages内部）
                if module and not module.startswith('sage'):
                    external_deps[module].append({
                        'file': file_path,
                        'import_name': name,
                        'line': imp['line']
                    })
        
        return dict(external_deps)
    
    def find_internal_dependencies(self) -> Dict[str, List]:
        """查找内部依赖（sage模块间的依赖）"""
        internal_deps = defaultdict(list)
        
        for file_path, imports in self.from_imports.items():
            for imp in imports:
                module = imp['module']
                name = imp['name']
                
                # 判断是否为内部依赖
                if module and module.startswith('sage'):
                    internal_deps[module].append({
                        'file': file_path,
                        'import_name': name,
                        'line': imp['line']
                    })
        
        return dict(internal_deps)
    
    def generate_report(self) -> Dict:
        """生成分析报告"""
        class_deps = self.find_class_dependencies()
        external_deps = self.find_external_dependencies()
        internal_deps = self.find_internal_dependencies()
        
        # 统计信息
        total_files = len(self.imports_by_file)
        total_classes = len(self.class_definitions)
        total_from_imports = sum(len(imports) for imports in self.from_imports.values())
        
        # 最常用的外部模块
        external_module_counts = Counter()
        for module, usages in external_deps.items():
            external_module_counts[module] = len(usages)
        
        # 最常导入的类
        class_import_counts = Counter()
        for class_name, info in class_deps.items():
            class_import_counts[class_name] = info['import_count']
        
        report = {
            'summary': {
                'total_files': total_files,
                'total_classes_defined': total_classes,
                'total_from_imports': total_from_imports,
                'external_modules_count': len(external_deps),
                'internal_modules_count': len(internal_deps)
            },
            'class_dependencies': class_deps,
            'external_dependencies': external_deps,
            'internal_dependencies': internal_deps,
            'top_external_modules': dict(external_module_counts.most_common(10)),
            'top_imported_classes': dict(class_import_counts.most_common(10))
        }
        
        return report
    
    def print_summary(self, report: Dict):
        """打印分析摘要"""
        summary = report['summary']
        
        print("\n" + "="*80)
        print("SAGE PACKAGES DEPENDENCY ANALYSIS REPORT")
        print("="*80)
        
        print(f"\n📊 SUMMARY:")
        print(f"  • Total Python files analyzed: {summary['total_files']}")
        print(f"  • Total classes defined: {summary['total_classes_defined']}")
        print(f"  • Total 'from' imports: {summary['total_from_imports']}")
        print(f"  • External modules used: {summary['external_modules_count']}")
        print(f"  • Internal sage modules used: {summary['internal_modules_count']}")
        
        print(f"\n🔝 TOP EXTERNAL DEPENDENCIES:")
        for module, count in report['top_external_modules'].items():
            print(f"  • {module}: {count} usages")
        
        print(f"\n🏆 MOST IMPORTED CLASSES:")
        for class_name, count in report['top_imported_classes'].items():
            if count > 0:  # Only show classes that are actually imported
                print(f"  • {class_name}: imported by {count} files")
        
        print(f"\n🔍 INTERNAL SAGE MODULE DEPENDENCIES:")
        internal_modules = sorted(report['internal_dependencies'].keys())
        for module in internal_modules[:10]:  # Show top 10
            count = len(report['internal_dependencies'][module])
            print(f"  • {module}: {count} imports")
    
    def save_detailed_report(self, report: Dict, output_file: str):
        """保存详细报告到JSON文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Detailed report saved to: {output_file}")
    
    def print_class_analysis(self, report: Dict, class_name: str = None):
        """打印特定类的分析或所有类的简要分析"""
        class_deps = report['class_dependencies']
        
        if class_name:
            if class_name in class_deps:
                info = class_deps[class_name]
                print(f"\n🔍 ANALYSIS FOR CLASS '{class_name}':")
                print(f"  • Defined in: {', '.join(info['defined_in'])}")
                print(f"  • Imported by {info['import_count']} files:")
                for file_path in info['imported_by']:
                    print(f"    - {file_path}")
            else:
                print(f"\n❌ Class '{class_name}' not found in the analysis.")
        else:
            print(f"\n📋 ALL DEFINED CLASSES ({len(class_deps)}):")
            for class_name, info in sorted(class_deps.items()):
                print(f"  • {class_name}: defined in {len(info['defined_in'])} files, imported by {info['import_count']} files")


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python check_package_dependencies.py [class_name]")
        print("  class_name: Optional. Analyze specific class dependencies")
        return
    
    # 获取项目根目录
    script_dir = Path(__file__).parent
    root_path = script_dir.parent  # 假设脚本在scripts目录下
    
    if not (root_path / "packages").exists():
        print("❌ Error: packages directory not found!")
        print(f"Looking for: {root_path / 'packages'}")
        return
    
    # 创建分析器并运行分析
    analyzer = DependencyAnalyzer(str(root_path))
    
    print("🔄 Analyzing packages directory...")
    analyzer.analyze_packages()
    
    print("📝 Generating report...")
    report = analyzer.generate_report()
    
    # 打印摘要
    analyzer.print_summary(report)
    
    # 保存详细报告
    output_file = root_path / "dependency_analysis_report.json"
    analyzer.save_detailed_report(report, str(output_file))
    
    # 如果指定了特定类名，显示该类的详细分析
    if len(sys.argv) > 1:
        class_name = sys.argv[1]
        analyzer.print_class_analysis(report, class_name)
    else:
        # 显示所有类的简要信息
        analyzer.print_class_analysis(report)
    
    print(f"\n✅ Analysis complete!")
    print(f"📄 Run with a class name to get detailed analysis: python {Path(__file__).name} <ClassName>")


if __name__ == "__main__":
    main()
