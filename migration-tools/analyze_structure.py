#!/usr/bin/env python3
"""
SAGE代码结构分析器
=================

分析当前SAGE项目的代码结构，为迁移规划提供数据支持。
生成详细的依赖关系图和模块分析报告。
"""

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import argparse

@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    path: str
    size_lines: int
    imports: List[str]
    from_imports: List[str]
    classes: List[str]
    functions: List[str]
    dependencies: Set[str]
    reverse_dependencies: Set[str]

@dataclass
class ProjectAnalysis:
    """项目分析结果"""
    total_files: int
    total_lines: int
    modules: Dict[str, ModuleInfo]
    dependency_graph: Dict[str, Set[str]]
    circular_dependencies: List[List[str]]
    migration_groups: Dict[str, List[str]]

class CodeAnalyzer:
    """代码分析器"""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.modules: Dict[str, ModuleInfo] = {}
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        
    def analyze_file(self, file_path: Path) -> ModuleInfo:
        """分析单个Python文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            # 计算模块名
            relative_path = file_path.relative_to(self.project_root)
            module_name = str(relative_path.with_suffix('')).replace('/', '.')
            
            # 提取信息
            imports = []
            from_imports = []
            classes = []
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        from_imports.append(node.module)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_'):  # 排除私有函数
                        functions.append(node.name)
            
            # 计算依赖关系
            dependencies = set()
            for imp in imports + from_imports:
                if imp and imp.startswith('sage'):
                    dependencies.add(imp)
            
            return ModuleInfo(
                name=module_name,
                path=str(relative_path),
                size_lines=len(content.splitlines()),
                imports=imports,
                from_imports=from_imports,
                classes=classes,
                functions=functions,
                dependencies=dependencies,
                reverse_dependencies=set()
            )
            
        except Exception as e:
            print(f"警告: 分析文件 {file_path} 时出错: {e}")
            return None
    
    def find_python_files(self) -> List[Path]:
        """查找所有Python文件"""
        python_files = []
        for pattern in ['**/*.py']:
            for file_path in self.project_root.glob(pattern):
                # 排除一些目录
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                if '__pycache__' in file_path.parts:
                    continue
                if 'build' in file_path.parts:
                    continue
                python_files.append(file_path)
        return python_files
    
    def build_dependency_graph(self):
        """构建依赖关系图"""
        # 构建依赖关系
        for module_name, module_info in self.modules.items():
            for dep in module_info.dependencies:
                # 尝试匹配到实际的模块
                matching_modules = [m for m in self.modules.keys() if dep.startswith(m) or m.startswith(dep)]
                for match in matching_modules:
                    if match != module_name:
                        self.dependency_graph[module_name].add(match)
                        self.modules[match].reverse_dependencies.add(module_name)
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """查找循环依赖"""
        def dfs(node: str, path: List[str], visited: Set[str]) -> List[List[str]]:
            if node in path:
                # 找到循环
                cycle_start = path.index(node)
                return [path[cycle_start:] + [node]]
            
            if node in visited:
                return []
            
            visited.add(node)
            path.append(node)
            
            cycles = []
            for dep in self.dependency_graph.get(node, []):
                cycles.extend(dfs(dep, path[:], visited))
            
            return cycles
        
        all_cycles = []
        visited = set()
        
        for module in self.modules.keys():
            if module not in visited:
                cycles = dfs(module, [], visited)
                all_cycles.extend(cycles)
        
        # 去重
        unique_cycles = []
        for cycle in all_cycles:
            if cycle not in unique_cycles:
                unique_cycles.append(cycle)
        
        return unique_cycles
    
    def categorize_modules(self) -> Dict[str, List[str]]:
        """根据功能将模块分类到迁移组"""
        migration_groups = {
            'core': [],           # 核心API和环境
            'runtime': [],        # 运行时系统
            'lib': [],           # 函数库
            'service': [],       # 服务模块
            'utils': [],         # 工具模块
            'jobmanager': [],    # 作业管理
            'cli': [],           # 命令行工具
            'plugins': [],       # 插件系统
            'extensions': [],    # C++扩展
            'dashboard': [],     # Web界面
            'tests': [],         # 测试文件
            'examples': [],      # 示例代码
            'other': []          # 其他
        }
        
        for module_name, module_info in self.modules.items():
            path_parts = module_info.path.split('/')
            
            # 根据路径判断分类
            if path_parts[0] == 'sage':
                if len(path_parts) > 1:
                    second_part = path_parts[1]
                    if second_part in migration_groups:
                        migration_groups[second_part].append(module_name)
                    else:
                        migration_groups['other'].append(module_name)
                else:
                    migration_groups['core'].append(module_name)
            elif path_parts[0] == 'sage_ext':
                migration_groups['extensions'].append(module_name)
            elif path_parts[0] == 'frontend':
                migration_groups['dashboard'].append(module_name)
            elif path_parts[0] == 'app':
                migration_groups['examples'].append(module_name)
            elif 'test' in module_info.path.lower():
                migration_groups['tests'].append(module_name)
            else:
                migration_groups['other'].append(module_name)
        
        return migration_groups
    
    def analyze_project(self) -> ProjectAnalysis:
        """分析整个项目"""
        print("🔍 开始分析SAGE项目结构...")
        
        # 查找所有Python文件
        python_files = self.find_python_files()
        print(f"📋 找到 {len(python_files)} 个Python文件")
        
        # 分析每个文件
        total_lines = 0
        for file_path in python_files:
            module_info = self.analyze_file(file_path)
            if module_info:
                self.modules[module_info.name] = module_info
                total_lines += module_info.size_lines
        
        print(f"📊 分析了 {len(self.modules)} 个模块，总计 {total_lines} 行代码")
        
        # 构建依赖关系图
        print("🔗 构建依赖关系图...")
        self.build_dependency_graph()
        
        # 查找循环依赖
        print("🔄 检查循环依赖...")
        circular_deps = self.find_circular_dependencies()
        if circular_deps:
            print(f"⚠️  发现 {len(circular_deps)} 个循环依赖")
        else:
            print("✅ 未发现循环依赖")
        
        # 模块分类
        print("📂 模块分类...")
        migration_groups = self.categorize_modules()
        
        return ProjectAnalysis(
            total_files=len(python_files),
            total_lines=total_lines,
            modules=self.modules,
            dependency_graph=dict(self.dependency_graph),
            circular_dependencies=circular_deps,
            migration_groups=migration_groups
        )
    
    def generate_report(self, analysis: ProjectAnalysis, output_file: Path):
        """生成分析报告"""
        report = {
            'project_summary': {
                'total_files': analysis.total_files,
                'total_lines': analysis.total_lines,
                'total_modules': len(analysis.modules),
                'circular_dependencies_count': len(analysis.circular_dependencies)
            },
            'migration_groups': {
                group: {
                    'module_count': len(modules),
                    'total_lines': sum(analysis.modules[m].size_lines for m in modules if m in analysis.modules),
                    'modules': modules[:10] if len(modules) > 10 else modules  # 只显示前10个
                }
                for group, modules in analysis.migration_groups.items()
                if modules  # 只包含非空组
            },
            'top_modules_by_size': sorted(
                [(name, info.size_lines) for name, info in analysis.modules.items()],
                key=lambda x: x[1],
                reverse=True
            )[:20],
            'modules_with_most_dependencies': sorted(
                [(name, len(info.dependencies)) for name, info in analysis.modules.items()],
                key=lambda x: x[1],
                reverse=True
            )[:20],
            'modules_with_most_reverse_dependencies': sorted(
                [(name, len(info.reverse_dependencies)) for name, info in analysis.modules.items() if info.reverse_dependencies],
                key=lambda x: x[1],
                reverse=True
            )[:20],
            'circular_dependencies': analysis.circular_dependencies
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📄 分析报告已保存到: {output_file}")
    
    def generate_migration_plan(self, analysis: ProjectAnalysis, output_file: Path):
        """生成具体的迁移计划"""
        plan = {}
        
        # sage-core 迁移计划
        sage_core_modules = []
        for group in ['core', 'runtime', 'lib', 'service', 'utils', 'jobmanager', 'cli', 'plugins']:
            sage_core_modules.extend(analysis.migration_groups.get(group, []))
        
        plan['sage-core'] = {
            'description': 'Python核心框架',
            'target_structure': 'src/sage/',
            'modules': sage_core_modules,
            'estimated_lines': sum(analysis.modules[m].size_lines for m in sage_core_modules if m in analysis.modules),
            'key_dependencies': [],
            'migration_priority': 1,
            'estimated_effort_days': 10
        }
        
        # sage-extensions 迁移计划
        extensions_modules = analysis.migration_groups.get('extensions', [])
        plan['sage-extensions'] = {
            'description': '高性能C++扩展',
            'target_structure': 'src/sage/extensions/',
            'modules': extensions_modules,
            'estimated_lines': sum(analysis.modules[m].size_lines for m in extensions_modules if m in analysis.modules),
            'key_dependencies': ['sage-core'],
            'migration_priority': 2,
            'estimated_effort_days': 8
        }
        
        # sage-dashboard 迁移计划
        dashboard_modules = analysis.migration_groups.get('dashboard', [])
        plan['sage-dashboard'] = {
            'description': 'Web界面和API',
            'target_structure': 'backend/src/sage/dashboard/',
            'modules': dashboard_modules,
            'estimated_lines': sum(analysis.modules[m].size_lines for m in dashboard_modules if m in analysis.modules),
            'key_dependencies': ['sage-core'],
            'migration_priority': 3,
            'estimated_effort_days': 6
        }
        
        # 添加风险评估
        plan['risk_assessment'] = {
            'circular_dependencies': len(analysis.circular_dependencies),
            'high_coupling_modules': [
                name for name, info in analysis.modules.items()
                if len(info.dependencies) > 10 or len(info.reverse_dependencies) > 10
            ][:10],
            'large_modules': [
                name for name, size in sorted(
                    [(name, info.size_lines) for name, info in analysis.modules.items()],
                    key=lambda x: x[1], reverse=True
                )[:10]
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📋 迁移计划已保存到: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="SAGE代码结构分析器")
    parser.add_argument("--project-root", "-p", type=Path, default=".", 
                       help="项目根目录路径 (默认: 当前目录)")
    parser.add_argument("--output-dir", "-o", type=Path, default="migration-analysis",
                       help="输出目录 (默认: migration-analysis)")
    parser.add_argument("--detailed", "-d", action="store_true",
                       help="生成详细的模块信息 (包含所有模块的完整信息)")
    
    args = parser.parse_args()
    
    # 确保输出目录存在
    args.output_dir.mkdir(exist_ok=True)
    
    # 分析项目
    analyzer = CodeAnalyzer(args.project_root)
    analysis = analyzer.analyze_project()
    
    # 生成报告
    report_file = args.output_dir / "project_analysis.json"
    analyzer.generate_report(analysis, report_file)
    
    # 生成迁移计划
    plan_file = args.output_dir / "migration_plan.json"
    analyzer.generate_migration_plan(analysis, plan_file)
    
    # 生成详细信息（如果请求）
    if args.detailed:
        detailed_file = args.output_dir / "detailed_modules.json"
        detailed_data = {
            name: asdict(info) for name, info in analysis.modules.items()
        }
        # 转换set为list以便JSON序列化
        for module_data in detailed_data.values():
            module_data['dependencies'] = list(module_data['dependencies'])
            module_data['reverse_dependencies'] = list(module_data['reverse_dependencies'])
        
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_data, f, indent=2, ensure_ascii=False)
        print(f"📄 详细模块信息已保存到: {detailed_file}")
    
    # 打印摘要
    print("\n" + "="*60)
    print("📊 分析摘要")
    print("="*60)
    print(f"总文件数: {analysis.total_files}")
    print(f"总代码行数: {analysis.total_lines:,}")
    print(f"总模块数: {len(analysis.modules)}")
    print(f"循环依赖数: {len(analysis.circular_dependencies)}")
    
    print("\n📂 迁移组分布:")
    for group, modules in analysis.migration_groups.items():
        if modules:
            total_lines = sum(analysis.modules[m].size_lines for m in modules if m in analysis.modules)
            print(f"  {group}: {len(modules)} 个模块, {total_lines:,} 行代码")
    
    if analysis.circular_dependencies:
        print("\n⚠️  循环依赖:")
        for i, cycle in enumerate(analysis.circular_dependencies[:5], 1):
            print(f"  {i}. {' -> '.join(cycle)}")
        if len(analysis.circular_dependencies) > 5:
            print(f"  ... 还有 {len(analysis.circular_dependencies) - 5} 个")
    
    print(f"\n📄 详细报告请查看: {report_file}")
    print(f"📋 迁移计划请查看: {plan_file}")

if __name__ == "__main__":
    main()
