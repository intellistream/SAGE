#!/usr/bin/env python3
"""
高级依赖关系分析器
- 分析packages中所有Python文件的from导入依赖
- 验证导入路径是否正确
- 检测循环依赖
- 生成详细报告
"""

import os
import ast
import sys
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque
import traceback


class DependencyAnalyzer:
    def __init__(self, packages_dir: str):
        self.packages_dir = Path(packages_dir)
        self.python_files = []
        self.imports_data = {}
        self.class_definitions = {}
        self.function_definitions = {}
        self.module_map = {}
        self.import_errors = []
        self.circular_dependencies = []
        
    def find_python_files(self) -> List[Path]:
        """查找所有Python文件"""
        python_files = []
        for root, dirs, files in os.walk(self.packages_dir):
            # 跳过__pycache__等目录
            dirs[:] = [d for d in dirs if not d.startswith('__pycache__') and d != '.git']
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def extract_definitions(self, file_path: Path) -> Tuple[Set[str], Set[str]]:
        """提取文件中定义的类和函数"""
        classes = set()
        functions = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.add(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.add(node.name)
                elif isinstance(node, ast.AsyncFunctionDef):
                    functions.add(node.name)
                    
        except Exception as e:
            print(f"解析文件时出错 {file_path}: {e}")
            
        return classes, functions
    
    def get_module_path_from_file(self, file_path: Path) -> str:
        """从文件路径获取模块路径"""
        rel_path = file_path.relative_to(self.packages_dir)
        
        # 移除.py扩展名
        if rel_path.name == '__init__.py':
            module_parts = rel_path.parent.parts
        else:
            module_parts = rel_path.with_suffix('').parts
            
        return '.'.join(module_parts)
    
    def extract_imports(self, file_path: Path) -> Dict:
        """提取文件中的import语句"""
        imports = {
            'from_imports': [],
            'regular_imports': [],
            'import_errors': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module if node.module else ''
                    level = node.level  # 相对导入的级别
                    
                    for alias in node.names:
                        import_info = {
                            'module': module,
                            'name': alias.name,
                            'asname': alias.asname,
                            'level': level,
                            'line': node.lineno,
                            'is_relative': level > 0
                        }
                        imports['from_imports'].append(import_info)
                        
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        import_info = {
                            'module': alias.name,
                            'asname': alias.asname,
                            'line': node.lineno
                        }
                        imports['regular_imports'].append(import_info)
                        
        except Exception as e:
            error_info = {
                'file': str(file_path),
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            imports['import_errors'].append(error_info)
            self.import_errors.append(error_info)
            
        return imports
    
    def resolve_relative_import(self, current_module: str, import_module: str, level: int) -> str:
        """解析相对导入"""
        if level == 0:
            return import_module
            
        current_parts = current_module.split('.')
        
        # 计算要回退的级别
        if level > len(current_parts):
            return None  # 无效的相对导入
            
        # 回退到父级模块
        parent_parts = current_parts[:-level] if level < len(current_parts) else []
        
        if import_module:
            return '.'.join(parent_parts + [import_module])
        else:
            return '.'.join(parent_parts)
    
    def validate_import(self, file_path: Path, import_info: Dict) -> Dict:
        """验证导入是否有效"""
        current_module = self.get_module_path_from_file(file_path)
        validation_result = {
            'valid': False,
            'error': None,
            'resolved_module': None,
            'target_file': None
        }
        
        try:
            if import_info.get('level', 0) > 0:
                # 相对导入
                resolved_module = self.resolve_relative_import(
                    current_module, 
                    import_info['module'], 
                    import_info['level']
                )
                if not resolved_module:
                    validation_result['error'] = "Invalid relative import level"
                    return validation_result
            else:
                # 绝对导入
                resolved_module = import_info['module']
            
            validation_result['resolved_module'] = resolved_module
            
            # 检查模块是否存在于我们的代码库中
            target_file = self.find_module_file(resolved_module)
            if target_file:
                validation_result['target_file'] = str(target_file)
                
                # 检查导入的名称是否在目标文件中定义
                if import_info.get('name') and import_info['name'] != '*':
                    if self.is_name_defined_in_file(target_file, import_info['name']):
                        validation_result['valid'] = True
                    else:
                        validation_result['error'] = f"Name '{import_info['name']}' not found in {target_file}"
                else:
                    validation_result['valid'] = True
            else:
                # 可能是外部库，尝试导入验证
                try:
                    if resolved_module:
                        spec = importlib.util.find_spec(resolved_module)
                        if spec:
                            validation_result['valid'] = True
                            validation_result['target_file'] = "external_library"
                        else:
                            validation_result['error'] = f"Module '{resolved_module}' not found"
                    else:
                        validation_result['error'] = "Could not resolve module"
                except ImportError as e:
                    validation_result['error'] = f"Import error: {str(e)}"
                    
        except Exception as e:
            validation_result['error'] = f"Validation error: {str(e)}"
            
        return validation_result
    
    def find_module_file(self, module_path: str) -> Optional[Path]:
        """根据模块路径查找对应的文件"""
        # 在我们的模块映射中查找
        for file_path, file_module in self.module_map.items():
            if file_module == module_path:
                return file_path
                
        # 尝试构造文件路径
        parts = module_path.split('.')
        
        # 尝试作为__init__.py
        init_path = self.packages_dir / Path(*parts) / '__init__.py'
        if init_path.exists():
            return init_path
            
        # 尝试作为.py文件
        py_path = self.packages_dir / Path(*parts[:-1]) / f"{parts[-1]}.py"
        if py_path.exists():
            return py_path
            
        return None
    
    def is_name_defined_in_file(self, file_path: Path, name: str) -> bool:
        """检查名称是否在文件中定义"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == name:
                        return True
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == name:
                            return True
                elif isinstance(node, ast.ImportFrom):
                    # 检查是否从其他地方导入了这个名称
                    for alias in node.names:
                        if alias.name == name or alias.asname == name:
                            return True
                            
        except Exception as e:
            print(f"检查名称定义时出错 {file_path}: {e}")
            
        return False
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """检测循环依赖"""
        # 构建依赖图
        dependency_graph = defaultdict(set)
        
        for file_path, imports in self.imports_data.items():
            current_module = self.get_module_path_from_file(Path(file_path))
            
            for import_info in imports['from_imports']:
                if import_info.get('level', 0) > 0:
                    # 相对导入
                    resolved_module = self.resolve_relative_import(
                        current_module, 
                        import_info['module'], 
                        import_info['level']
                    )
                else:
                    resolved_module = import_info['module']
                
                if resolved_module and self.find_module_file(resolved_module):
                    dependency_graph[current_module].add(resolved_module)
        
        # 使用DFS检测循环
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # 找到循环
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
                
            if node in visited:
                return
                
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependency_graph.get(node, []):
                dfs(neighbor, path + [neighbor])
                
            rec_stack.remove(node)
        
        for node in dependency_graph:
            if node not in visited:
                dfs(node, [node])
        
        return cycles
    
    def analyze(self) -> Dict:
        """执行完整分析"""
        print("正在查找Python文件...")
        self.python_files = self.find_python_files()
        print(f"找到 {len(self.python_files)} 个Python文件")
        
        # 建立文件到模块的映射
        print("建立模块映射...")
        for file_path in self.python_files:
            module_path = self.get_module_path_from_file(file_path)
            self.module_map[file_path] = module_path
            
            # 提取定义
            classes, functions = self.extract_definitions(file_path)
            self.class_definitions[str(file_path)] = list(classes)
            self.function_definitions[str(file_path)] = list(functions)
        
        # 提取导入信息
        print("分析导入语句...")
        for file_path in self.python_files:
            imports = self.extract_imports(file_path)
            self.imports_data[str(file_path)] = imports
        
        # 验证导入
        print("验证导入路径...")
        validated_imports = {}
        for file_path, imports in self.imports_data.items():
            validated_imports[file_path] = {
                'from_imports': [],
                'regular_imports': imports['regular_imports'],
                'import_errors': imports['import_errors']
            }
            
            for import_info in imports['from_imports']:
                validation = self.validate_import(Path(file_path), import_info)
                import_info['validation'] = validation
                validated_imports[file_path]['from_imports'].append(import_info)
        
        self.imports_data = validated_imports
        
        # 检测循环依赖
        print("检测循环依赖...")
        self.circular_dependencies = self.detect_circular_dependencies()
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """生成分析报告"""
        total_files = len(self.python_files)
        total_imports = sum(len(data['from_imports']) + len(data['regular_imports']) 
                          for data in self.imports_data.values())
        
        invalid_imports = []
        valid_imports = []
        
        for file_path, imports in self.imports_data.items():
            for import_info in imports['from_imports']:
                if not import_info.get('validation', {}).get('valid', False):
                    invalid_imports.append({
                        'file': file_path,
                        'import': import_info,
                        'error': import_info.get('validation', {}).get('error', 'Unknown error')
                    })
                else:
                    valid_imports.append({
                        'file': file_path,
                        'import': import_info
                    })
        
        report = {
            'summary': {
                'total_files': total_files,
                'total_imports': total_imports,
                'valid_imports': len(valid_imports),
                'invalid_imports': len(invalid_imports),
                'circular_dependencies': len(self.circular_dependencies),
                'import_errors': len(self.import_errors)
            },
            'files_analyzed': [str(f) for f in self.python_files],
            'class_definitions': self.class_definitions,
            'function_definitions': self.function_definitions,
            'imports_data': self.imports_data,
            'invalid_imports': invalid_imports,
            'circular_dependencies': self.circular_dependencies,
            'import_errors': self.import_errors
        }
        
        return report


def main():
    """主函数"""
    packages_dir = '/home/flecther/SAGE/packages'
    
    if not os.path.exists(packages_dir):
        print(f"错误: packages目录不存在: {packages_dir}")
        sys.exit(1)
    
    print("高级依赖关系分析器")
    print("=" * 50)
    
    analyzer = DependencyAnalyzer(packages_dir)
    report = analyzer.analyze()
    
    # 保存详细报告
    report_file = '/home/flecther/SAGE/advanced_dependency_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细报告已保存到: {report_file}")
    
    # 打印摘要
    summary = report['summary']
    print(f"\n分析摘要:")
    print(f"- 总文件数: {summary['total_files']}")
    print(f"- 总导入数: {summary['total_imports']}")
    print(f"- 有效导入: {summary['valid_imports']}")
    print(f"- 无效导入: {summary['invalid_imports']}")
    print(f"- 循环依赖: {summary['circular_dependencies']}")
    print(f"- 导入错误: {summary['import_errors']}")
    
    # 显示无效导入
    if report['invalid_imports']:
        print(f"\n无效导入详情:")
        for invalid in report['invalid_imports'][:10]:  # 只显示前10个
            print(f"  文件: {invalid['file']}")
            print(f"  导入: from {invalid['import']['module']} import {invalid['import']['name']}")
            print(f"  错误: {invalid['error']}")
            print()
    
    # 显示循环依赖
    if report['circular_dependencies']:
        print(f"\n循环依赖:")
        for cycle in report['circular_dependencies']:
            print(f"  {' -> '.join(cycle)}")
    
    print(f"\n分析完成!")


if __name__ == '__main__':
    main()
