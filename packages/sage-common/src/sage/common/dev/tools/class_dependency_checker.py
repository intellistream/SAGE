"""
Class Dependency Checker - Integrated from scripts/quick_class_dependency_check.py

This tool analyzes class-level dependencies and relationships in the codebase.
"""

import os
import ast
from pathlib import Path
from typing import Dict, List, Any, Set
import json
from collections import defaultdict
from ..core.exceptions import SAGEDevToolkitError


class ClassDependencyChecker:
    """Tool for analyzing class-level dependencies."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        
    def analyze_class_dependencies(self, target_paths: List[str] = None) -> Dict[str, Any]:
        """Analyze class dependencies in specified paths or entire project."""
        try:
            if target_paths:
                paths_to_analyze = [Path(self.project_root) / p if not Path(p).is_absolute() else Path(p) for p in target_paths]
            else:
                paths_to_analyze = [self.project_root]
            
            analysis = {
                'project_root': str(self.project_root),
                'analyzed_paths': [str(p) for p in paths_to_analyze],
                'classes': {},
                'relationships': {
                    'inheritance': [],
                    'composition': [],
                    'imports': []
                },
                'summary': {
                    'total_classes': 0,
                    'total_files': 0,
                    'inheritance_chains': [],
                    'circular_imports': [],
                    'unused_classes': []
                }
            }
            
            # Find all Python files
            python_files = []
            for path in paths_to_analyze:
                if path.is_file() and path.suffix == '.py':
                    python_files.append(path)
                elif path.is_dir():
                    python_files.extend(path.rglob('*.py'))
            
            analysis['summary']['total_files'] = len(python_files)
            
            # Analyze each file
            for py_file in python_files:
                try:
                    file_analysis = self._analyze_file(py_file)
                    
                    # Merge file analysis into main analysis
                    for class_name, class_info in file_analysis['classes'].items():
                        full_class_name = f"{file_analysis['module']}.{class_name}"
                        analysis['classes'][full_class_name] = class_info
                        analysis['summary']['total_classes'] += 1
                    
                    # Add relationships
                    analysis['relationships']['inheritance'].extend(file_analysis['inheritance'])
                    analysis['relationships']['composition'].extend(file_analysis['composition'])
                    analysis['relationships']['imports'].extend(file_analysis['imports'])
                    
                except Exception as e:
                    print(f"Warning: Could not analyze {py_file}: {e}")
            
            # Analyze relationships
            analysis['summary']['inheritance_chains'] = self._find_inheritance_chains(analysis)
            analysis['summary']['circular_imports'] = self._find_circular_imports(analysis)
            analysis['summary']['unused_classes'] = self._find_unused_classes(analysis)
            
            return analysis
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Class dependency analysis failed: {e}")
    
    def check_class_usage(self, class_name: str, target_paths: List[str] = None) -> Dict[str, Any]:
        """Check where a specific class is used."""
        try:
            if target_paths:
                paths_to_search = [Path(p) for p in target_paths]
            else:
                paths_to_search = [self.project_root]
            
            usage_info = {
                'class_name': class_name,
                'searched_paths': [str(p) for p in paths_to_search],
                'usages': [],
                'summary': {
                    'total_usages': 0,
                    'files_with_usage': 0,
                    'usage_types': {
                        'import': 0,
                        'inheritance': 0,
                        'instantiation': 0,
                        'reference': 0
                    }
                }
            }
            
            # Find all Python files
            python_files = []
            for path in paths_to_search:
                if path.is_file() and path.suffix == '.py':
                    python_files.append(path)
                elif path.is_dir():
                    python_files.extend(path.rglob('*.py'))
            
            # Search for usage in each file
            files_with_usage = set()
            for py_file in python_files:
                try:
                    file_usages = self._find_class_usage_in_file(py_file, class_name)
                    if file_usages:
                        usage_info['usages'].extend(file_usages)
                        files_with_usage.add(str(py_file))
                        
                        # Count usage types
                        for usage in file_usages:
                            usage_type = usage['type']
                            if usage_type in usage_info['summary']['usage_types']:
                                usage_info['summary']['usage_types'][usage_type] += 1
                            usage_info['summary']['total_usages'] += 1
                            
                except Exception as e:
                    print(f"Warning: Could not search {py_file}: {e}")
            
            usage_info['summary']['files_with_usage'] = len(files_with_usage)
            
            return usage_info
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Class usage check failed: {e}")
    
    def generate_class_diagram(self, output_format: str = 'mermaid') -> str:
        """Generate class diagram in specified format."""
        try:
            analysis = self.analyze_class_dependencies()
            
            if output_format == 'mermaid':
                return self._generate_mermaid_diagram(analysis)
            elif output_format == 'dot':
                return self._generate_dot_diagram(analysis)
            else:
                raise SAGEDevToolkitError(f"Unsupported diagram format: {output_format}")
                
        except Exception as e:
            raise SAGEDevToolkitError(f"Class diagram generation failed: {e}")
    
    def _analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Get module name
            relative_path = file_path.relative_to(self.project_root)
            module_parts = relative_path.with_suffix('').parts
            module_name = '.'.join(module_parts)
            
            analysis = {
                'file_path': str(file_path),
                'module': module_name,
                'classes': {},
                'inheritance': [],
                'composition': [],
                'imports': []
            }
            
            # Walk AST
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = self._analyze_class_node(node, module_name)
                    analysis['classes'][node.name] = class_info
                    
                    # Record inheritance relationships
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            analysis['inheritance'].append({
                                'child': f"{module_name}.{node.name}",
                                'parent': base.id,
                                'file': str(file_path),
                                'line': node.lineno
                            })
                        elif isinstance(base, ast.Attribute):
                            parent_name = self._get_attribute_name(base)
                            analysis['inheritance'].append({
                                'child': f"{module_name}.{node.name}",
                                'parent': parent_name,
                                'file': str(file_path),
                                'line': node.lineno
                            })
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_info = self._analyze_import_node(node, module_name)
                    analysis['imports'].append(import_info)
            
            return analysis
            
        except Exception as e:
            raise SAGEDevToolkitError(f"File analysis failed for {file_path}: {e}")
    
    def _analyze_class_node(self, class_node: ast.ClassDef, module_name: str) -> Dict[str, Any]:
        """Analyze a class AST node."""
        class_info = {
            'name': class_node.name,
            'module': module_name,
            'line': class_node.lineno,
            'bases': [],
            'methods': [],
            'attributes': [],
            'decorators': []
        }
        
        # Analyze base classes
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                class_info['bases'].append(base.id)
            elif isinstance(base, ast.Attribute):
                class_info['bases'].append(self._get_attribute_name(base))
        
        # Analyze decorators
        for decorator in class_node.decorator_list:
            if isinstance(decorator, ast.Name):
                class_info['decorators'].append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                class_info['decorators'].append(self._get_attribute_name(decorator))
        
        # Analyze class body
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_info = {
                    'name': node.name,
                    'line': node.lineno,
                    'args': [arg.arg for arg in node.args.args],
                    'decorators': [
                        d.id if isinstance(d, ast.Name) else self._get_attribute_name(d)
                        for d in node.decorator_list
                    ]
                }
                class_info['methods'].append(method_info)
            
            elif isinstance(node, ast.Assign):
                # Simple attribute assignment
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        class_info['attributes'].append({
                            'name': target.id,
                            'line': node.lineno,
                            'type': 'assignment'
                        })
            
            elif isinstance(node, ast.AnnAssign):
                # Type annotated assignment
                if isinstance(node.target, ast.Name):
                    attr_info = {
                        'name': node.target.id,
                        'line': node.lineno,
                        'type': 'annotated'
                    }
                    if node.annotation:
                        attr_info['annotation'] = ast.unparse(node.annotation)
                    class_info['attributes'].append(attr_info)
        
        return class_info
    
    def _analyze_import_node(self, import_node: ast.AST, module_name: str) -> Dict[str, Any]:
        """Analyze an import AST node."""
        import_info = {
            'importing_module': module_name,
            'line': import_node.lineno,
            'type': 'import' if isinstance(import_node, ast.Import) else 'from_import'
        }
        
        if isinstance(import_node, ast.Import):
            import_info['modules'] = [alias.name for alias in import_node.names]
            import_info['aliases'] = {
                alias.name: alias.asname for alias in import_node.names if alias.asname
            }
        
        elif isinstance(import_node, ast.ImportFrom):
            import_info['from_module'] = import_node.module or ''
            import_info['names'] = [alias.name for alias in import_node.names]
            import_info['aliases'] = {
                alias.name: alias.asname for alias in import_node.names if alias.asname
            }
            import_info['level'] = import_node.level
        
        return import_info
    
    def _get_attribute_name(self, attr_node: ast.Attribute) -> str:
        """Get full attribute name from AST node."""
        try:
            return ast.unparse(attr_node)
        except:
            # Fallback for older Python versions
            parts = []
            node = attr_node
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return '.'.join(reversed(parts))
    
    def _find_class_usage_in_file(self, file_path: Path, class_name: str) -> List[Dict[str, Any]]:
        """Find usages of a class in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            usages = []
            
            for node in ast.walk(tree):
                # Check for class instantiation
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == class_name:
                        usages.append({
                            'type': 'instantiation',
                            'line': node.lineno,
                            'file': str(file_path),
                            'context': 'function_call'
                        })
                    elif isinstance(node.func, ast.Attribute):
                        attr_name = self._get_attribute_name(node.func)
                        if class_name in attr_name:
                            usages.append({
                                'type': 'instantiation',
                                'line': node.lineno,
                                'file': str(file_path),
                                'context': 'method_call'
                            })
                
                # Check for inheritance
                elif isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == class_name:
                            usages.append({
                                'type': 'inheritance',
                                'line': node.lineno,
                                'file': str(file_path),
                                'context': f'class {node.name}',
                                'child_class': node.name
                            })
                        elif isinstance(base, ast.Attribute):
                            attr_name = self._get_attribute_name(base)
                            if class_name in attr_name:
                                usages.append({
                                    'type': 'inheritance',
                                    'line': node.lineno,
                                    'file': str(file_path),
                                    'context': f'class {node.name}',
                                    'child_class': node.name
                                })
                
                # Check for imports
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if class_name in alias.name:
                                usages.append({
                                    'type': 'import',
                                    'line': node.lineno,
                                    'file': str(file_path),
                                    'context': f'import {alias.name}',
                                    'alias': alias.asname
                                })
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            if alias.name == class_name:
                                usages.append({
                                    'type': 'import',
                                    'line': node.lineno,
                                    'file': str(file_path),
                                    'context': f'from {node.module} import {alias.name}',
                                    'alias': alias.asname
                                })
                
                # Check for general references
                elif isinstance(node, ast.Name) and node.id == class_name:
                    usages.append({
                        'type': 'reference',
                        'line': node.lineno,
                        'file': str(file_path),
                        'context': 'name_reference'
                    })
            
            return usages
            
        except Exception as e:
            print(f"Warning: Could not analyze {file_path} for class {class_name}: {e}")
            return []
    
    def _find_inheritance_chains(self, analysis: Dict) -> List[List[str]]:
        """Find inheritance chains in the codebase."""
        chains = []
        
        # Build inheritance graph
        inheritance_map = defaultdict(list)
        for rel in analysis['relationships']['inheritance']:
            inheritance_map[rel['parent']].append(rel['child'])
        
        # Find chains starting from root classes
        visited = set()
        
        def build_chain(class_name, current_chain):
            if class_name in visited:
                return
            
            visited.add(class_name)
            current_chain.append(class_name)
            
            children = inheritance_map.get(class_name, [])
            if children:
                for child in children:
                    build_chain(child, current_chain.copy())
            else:
                # End of chain
                if len(current_chain) > 1:
                    chains.append(current_chain)
        
        # Start with classes that are not children of others
        all_children = set()
        for children_list in inheritance_map.values():
            all_children.update(children_list)
        
        root_classes = set(inheritance_map.keys()) - all_children
        
        for root_class in root_classes:
            build_chain(root_class, [])
        
        return chains
    
    def _find_circular_imports(self, analysis: Dict) -> List[List[str]]:
        """Find circular import dependencies."""
        # This is a simplified implementation
        # In practice, you'd want more sophisticated cycle detection
        import_graph = defaultdict(set)
        
        for import_info in analysis['relationships']['imports']:
            importing_module = import_info['importing_module']
            
            if import_info['type'] == 'import':
                for module in import_info['modules']:
                    import_graph[importing_module].add(module)
            elif import_info['type'] == 'from_import':
                from_module = import_info['from_module']
                if from_module:
                    import_graph[importing_module].add(from_module)
        
        return []  # Simplified - would need cycle detection algorithm
    
    def _find_unused_classes(self, analysis: Dict) -> List[str]:
        """Find classes that appear to be unused."""
        all_classes = set(analysis['classes'].keys())
        used_classes = set()
        
        # Mark classes used in inheritance
        for rel in analysis['relationships']['inheritance']:
            used_classes.add(rel['parent'])
            used_classes.add(rel['child'])
        
        # Mark classes used in imports
        for import_info in analysis['relationships']['imports']:
            if import_info['type'] == 'from_import':
                for name in import_info['names']:
                    # Simple heuristic: if name starts with capital, it's likely a class
                    if name[0].isupper():
                        used_classes.add(name)
        
        return list(all_classes - used_classes)
    
    def _generate_mermaid_diagram(self, analysis: Dict) -> str:
        """Generate Mermaid class diagram."""
        lines = ['classDiagram']
        
        # Add classes
        for class_name, class_info in analysis['classes'].items():
            simple_name = class_name.split('.')[-1]
            lines.append(f'    class {simple_name} {{')
            
            # Add methods
            for method in class_info['methods']:
                lines.append(f'        +{method["name"]}()')
            
            lines.append('    }')
        
        # Add inheritance relationships
        for rel in analysis['relationships']['inheritance']:
            parent_simple = rel['parent'].split('.')[-1]
            child_simple = rel['child'].split('.')[-1]
            lines.append(f'    {parent_simple} <|-- {child_simple}')
        
        return '\n'.join(lines)
    
    def _generate_dot_diagram(self, analysis: Dict) -> str:
        """Generate Graphviz DOT diagram."""
        lines = ['digraph ClassDiagram {']
        lines.append('    rankdir=TB;')
        lines.append('    node [shape=record];')
        
        # Add classes
        for class_name, class_info in analysis['classes'].items():
            simple_name = class_name.split('.')[-1]
            methods_str = '\\n'.join([f'+ {m["name"]}()' for m in class_info['methods']])
            lines.append(f'    {simple_name} [label="{{class {simple_name}|{methods_str}}}"];')
        
        # Add inheritance relationships
        for rel in analysis['relationships']['inheritance']:
            parent_simple = rel['parent'].split('.')[-1]
            child_simple = rel['child'].split('.')[-1]
            lines.append(f'    {parent_simple} -> {child_simple} [arrowhead=empty];')
        
        lines.append('}')
        return '\n'.join(lines)
