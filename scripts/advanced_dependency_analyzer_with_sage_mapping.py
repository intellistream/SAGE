#!/usr/bin/env python3
"""
高级依赖关系分析器 - 支持SAGE包的实际导入路径映射
分析packages目录中所有Python文件的依赖关系，并验证导入路径的正确性
考虑到安装后的包结构会映射到sage.xxx.xxx的命名空间
"""

import os
import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque
import importlib.util
import sys

class SAGEDependencyAnalyzer:
    def __init__(self, packages_root: str):
        self.packages_root = Path(packages_root)
        self.analysis_results = {
            'files_analyzed': 0,
            'total_imports': 0,
            'valid_imports': 0,
            'invalid_imports': 0,
            'circular_dependencies': [],
            'import_errors': [],
            'dependency_graph': {},
            'class_definitions': {},
            'function_definitions': {},
            'sage_package_mapping': {},
            'import_validation': {}
        }
        
        # 建立SAGE包的路径映射关系
        self.sage_mapping = self._build_sage_mapping()
    
    def _build_sage_mapping(self) -> Dict[str, str]:
        """
        建立SAGE包的实际路径映射关系
        从 packages/sage-xxx/src/sage/... 映射到 sage.xxx.xxx
        """
        mapping = {}
        
        for package_dir in self.packages_root.iterdir():
            if not package_dir.is_dir():
                continue
                
            # 查找src目录
            src_dir = package_dir / 'src'
            if not src_dir.exists():
                continue
            
            # 查找sage目录
            sage_dir = src_dir / 'sage'
            if not sage_dir.exists():
                continue
            
            # 构建映射关系
            package_name = package_dir.name.replace('-', '_')  # sage-kernel -> sage_kernel
            
            # 遍历sage子目录，建立完整的映射
            for root, dirs, files in os.walk(sage_dir):
                root_path = Path(root)
                relative_path = root_path.relative_to(sage_dir)
                
                # 构建导入路径
                if str(relative_path) == '.':
                    import_prefix = 'sage'
                else:
                    import_prefix = f'sage.{str(relative_path).replace(os.sep, ".")}'
                
                # 记录实际文件路径到导入路径的映射
                mapping[str(root_path)] = import_prefix
                
                # 对每个Python文件建立映射
                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        file_path = root_path / file
                        module_name = file.replace('.py', '')
                        full_import_path = f"{import_prefix}.{module_name}"
                        mapping[str(file_path)] = full_import_path
        
        return mapping
    
    def _get_sage_import_path(self, file_path: str) -> Optional[str]:
        """根据文件路径获取对应的SAGE导入路径"""
        file_path = str(Path(file_path).resolve())
        
        # 直接查找映射
        if file_path in self.sage_mapping:
            return self.sage_mapping[file_path]
        
        # 查找目录映射
        dir_path = str(Path(file_path).parent)
        if dir_path in self.sage_mapping:
            file_name = Path(file_path).stem
            return f"{self.sage_mapping[dir_path]}.{file_name}"
        
        return None
    
    def _extract_imports_and_definitions(self, file_path: str) -> Tuple[List[Dict], List[str], List[str]]:
        """从Python文件中提取导入语句和定义"""
        imports = []
        class_definitions = []
        function_definitions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                self.analysis_results['import_errors'].append({
                    'file': file_path,
                    'error': f'Syntax error: {str(e)}',
                    'type': 'syntax_error'
                })
                return imports, class_definitions, function_definitions
            
            for node in ast.walk(tree):
                # 提取from...import语句
                if isinstance(node, ast.ImportFrom):
                    if node.module:  # 确保module不为None
                        for alias in node.names:
                            imports.append({
                                'type': 'from_import',
                                'module': node.module,
                                'name': alias.name,
                                'asname': alias.asname,
                                'line': node.lineno
                            })
                
                # 提取import语句
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'name': alias.name,
                            'asname': alias.asname,
                            'line': node.lineno
                        })
                
                # 提取类定义
                elif isinstance(node, ast.ClassDef):
                    class_definitions.append(node.name)
                
                # 提取函数定义
                elif isinstance(node, ast.FunctionDef):
                    function_definitions.append(node.name)
        
        except Exception as e:
            self.analysis_results['import_errors'].append({
                'file': file_path,
                'error': str(e),
                'type': 'file_read_error'
            })
        
        return imports, class_definitions, function_definitions
    
    def _validate_sage_import(self, import_info: Dict, source_file: str) -> Dict:
        """验证SAGE相关的导入是否正确"""
        validation_result = {
            'is_valid': False,
            'error_type': None,
            'error_message': None,
            'suggested_import': None,
            'is_sage_import': False
        }
        
        module = import_info['module']
        imported_name = import_info['name']
        
        # 检查是否是SAGE相关的导入
        if module.startswith('sage.') or module.startswith('sage_'):
            validation_result['is_sage_import'] = True
            
            # 在SAGE包中查找对应的定义
            found = False
            for file_path, definitions in self.analysis_results['class_definitions'].items():
                sage_import_path = self._get_sage_import_path(file_path)
                if sage_import_path and sage_import_path.replace('.py', '') == module:
                    if imported_name in definitions or imported_name == '*':
                        validation_result['is_valid'] = True
                        found = True
                        break
            
            if not found:
                # 查找函数定义
                for file_path, definitions in self.analysis_results['function_definitions'].items():
                    sage_import_path = self._get_sage_import_path(file_path)
                    if sage_import_path and sage_import_path.replace('.py', '') == module:
                        if imported_name in definitions or imported_name == '*':
                            validation_result['is_valid'] = True
                            found = True
                            break
            
            if not found:
                validation_result['error_type'] = 'not_found'
                validation_result['error_message'] = f"Cannot find '{imported_name}' in module '{module}'"
                
                # 尝试提供建议
                suggestions = self._find_similar_imports(imported_name)
                if suggestions:
                    validation_result['suggested_import'] = suggestions[0]
        
        else:
            # 非SAGE导入，假设为外部库
            validation_result['is_valid'] = True
        
        return validation_result
    
    def _find_similar_imports(self, target_name: str) -> List[str]:
        """查找相似的导入建议"""
        suggestions = []
        
        # 在所有类定义中查找相似名称
        for file_path, class_names in self.analysis_results['class_definitions'].items():
            sage_import_path = self._get_sage_import_path(file_path)
            if sage_import_path:
                for class_name in class_names:
                    if class_name.lower() == target_name.lower() or target_name.lower() in class_name.lower():
                        suggestions.append(f"from {sage_import_path} import {class_name}")
        
        return suggestions[:3]  # 返回前3个建议
    
    def _detect_circular_dependencies(self):
        """检测循环依赖"""
        graph = self.analysis_results['dependency_graph']
        
        def dfs(node, visited, rec_stack, path):
            visited.add(node)
            rec_stack.add(node)
            current_path = path + [node]
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    result = dfs(neighbor, visited, rec_stack, current_path)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # 找到循环依赖
                    cycle_start = current_path.index(neighbor)
                    cycle = current_path[cycle_start:] + [neighbor]
                    return cycle
            
            rec_stack.remove(node)
            return None
        
        visited = set()
        for node in graph:
            if node not in visited:
                cycle = dfs(node, visited, set(), [])
                if cycle:
                    self.analysis_results['circular_dependencies'].append(cycle)
    
    def analyze(self) -> Dict:
        """执行完整的依赖关系分析"""
        print("开始分析SAGE包依赖关系...")
        print(f"包根目录: {self.packages_root}")
        print(f"发现的SAGE映射: {len(self.sage_mapping)} 个")
        
        # 遍历所有Python文件
        python_files = list(self.packages_root.rglob("*.py"))
        print(f"找到 {len(python_files)} 个Python文件")
        
        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue
                
            str_path = str(file_path)
            self.analysis_results['files_analyzed'] += 1
            
            # 提取导入和定义
            imports, classes, functions = self._extract_imports_and_definitions(str_path)
            
            # 记录定义
            if classes:
                self.analysis_results['class_definitions'][str_path] = classes
            if functions:
                self.analysis_results['function_definitions'][str_path] = functions
            
            # 记录依赖关系
            sage_import_path = self._get_sage_import_path(str_path)
            if sage_import_path:
                self.analysis_results['dependency_graph'][sage_import_path] = []
            
            # 验证导入
            for import_info in imports:
                self.analysis_results['total_imports'] += 1
                
                # 验证导入
                validation = self._validate_sage_import(import_info, str_path)
                
                import_key = f"{str_path}:{import_info['line']}"
                self.analysis_results['import_validation'][import_key] = {
                    'import_info': import_info,
                    'validation': validation,
                    'source_file': str_path
                }
                
                if validation['is_valid']:
                    self.analysis_results['valid_imports'] += 1
                else:
                    self.analysis_results['invalid_imports'] += 1
                
                # 构建依赖图
                if sage_import_path and validation['is_sage_import']:
                    target_module = import_info['module']
                    if sage_import_path not in self.analysis_results['dependency_graph']:
                        self.analysis_results['dependency_graph'][sage_import_path] = []
                    if target_module not in self.analysis_results['dependency_graph'][sage_import_path]:
                        self.analysis_results['dependency_graph'][sage_import_path].append(target_module)
        
        # 检测循环依赖
        self._detect_circular_dependencies()
        
        # 保存SAGE映射到结果中
        self.analysis_results['sage_package_mapping'] = self.sage_mapping
        
        print(f"\n分析完成:")
        print(f"  - 分析文件数: {self.analysis_results['files_analyzed']}")
        print(f"  - 总导入数: {self.analysis_results['total_imports']}")
        print(f"  - 有效导入: {self.analysis_results['valid_imports']}")
        print(f"  - 无效导入: {self.analysis_results['invalid_imports']}")
        print(f"  - 循环依赖: {len(self.analysis_results['circular_dependencies'])}")
        
        return self.analysis_results
    
    def generate_detailed_report(self, output_file: str):
        """生成详细的分析报告"""
        report_lines = []
        
        report_lines.append("SAGE包依赖关系分析报告")
        report_lines.append("=" * 50)
        report_lines.append(f"分析时间: {__import__('datetime').datetime.now()}")
        report_lines.append(f"包根目录: {self.packages_root}")
        report_lines.append("")
        
        # 统计信息
        report_lines.append("统计摘要:")
        report_lines.append("-" * 20)
        report_lines.append(f"分析文件数: {self.analysis_results['files_analyzed']}")
        report_lines.append(f"总导入语句: {self.analysis_results['total_imports']}")
        report_lines.append(f"有效导入: {self.analysis_results['valid_imports']}")
        report_lines.append(f"无效导入: {self.analysis_results['invalid_imports']}")
        report_lines.append(f"发现的类定义: {sum(len(classes) for classes in self.analysis_results['class_definitions'].values())}")
        report_lines.append(f"发现的函数定义: {sum(len(funcs) for funcs in self.analysis_results['function_definitions'].values())}")
        report_lines.append("")
        
        # SAGE包映射
        report_lines.append("SAGE包路径映射:")
        report_lines.append("-" * 20)
        for path, import_path in sorted(self.sage_mapping.items()):
            if 'src/sage' in path:
                report_lines.append(f"{path.split('src/sage')[-1]} -> {import_path}")
        report_lines.append("")
        
        # 无效导入详情
        if self.analysis_results['invalid_imports'] > 0:
            report_lines.append("无效导入详情:")
            report_lines.append("-" * 20)
            for import_key, validation_info in self.analysis_results['import_validation'].items():
                if not validation_info['validation']['is_valid'] and validation_info['validation']['is_sage_import']:
                    import_info = validation_info['import_info']
                    validation = validation_info['validation']
                    source_file = validation_info['source_file']
                    
                    report_lines.append(f"文件: {source_file}")
                    report_lines.append(f"  行 {import_info['line']}: from {import_info['module']} import {import_info['name']}")
                    report_lines.append(f"  错误: {validation['error_message']}")
                    if validation['suggested_import']:
                        report_lines.append(f"  建议: {validation['suggested_import']}")
                    report_lines.append("")
        
        # 循环依赖
        if self.analysis_results['circular_dependencies']:
            report_lines.append("循环依赖:")
            report_lines.append("-" * 20)
            for i, cycle in enumerate(self.analysis_results['circular_dependencies'], 1):
                report_lines.append(f"循环 {i}: {' -> '.join(cycle)}")
            report_lines.append("")
        
        # 保存报告
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"详细报告已保存到: {output_file}")

def main():
    analyzer = SAGEDependencyAnalyzer('/home/flecther/SAGE/packages')
    results = analyzer.analyze()
    
    # 保存JSON结果
    with open('/home/flecther/SAGE/sage_dependency_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 生成详细报告
    analyzer.generate_detailed_report('/home/flecther/SAGE/sage_dependency_analysis_report.txt')
    
    print("\n分析完成！结果文件:")
    print("- sage_dependency_analysis.json (JSON格式)")
    print("- sage_dependency_analysis_report.txt (文本报告)")

if __name__ == "__main__":
    main()
