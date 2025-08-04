#!/usr/bin/env python3
"""
自动修复SAGE包中的导入路径错误
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple

class ImportPathFixer:
    def __init__(self, packages_root: str):
        self.packages_root = Path(packages_root)
        self.fixes_applied = []
        self.fixes_failed = []
        
        # 常见的路径映射规则
        self.path_mappings = {
            # 错误的导入 -> 正确的导入
            'sage.utils.logging.custom_logger': 'sage.utils.logging.custom_logger',
            'sage.llm.clients.base': 'sage.llm.clients.base',
            'sage.utils.state_persistence': 'sage.llm.persistence.state',
            'sage_ext.sage_queue': 'sage.extensions.sage_queue',
            'sage_queue': 'sage.extensions.sage_queue.python.sage_queue',
            'sage_plugins': 'sage.plugins',
        }
        
        # 需要检查的文件模式
        self.file_patterns = ['*.py']
        
    def find_python_files(self) -> List[Path]:
        """找到所有需要检查的Python文件"""
        python_files = []
        for pattern in self.file_patterns:
            python_files.extend(self.packages_root.rglob(pattern))
        return [f for f in python_files if not f.name.startswith('.') and 'build' not in str(f)]
    
    def analyze_import_statement(self, line: str) -> Tuple[str, str, str]:
        """分析导入语句，返回(import_type, module, items)"""
        line = line.strip()
        
        # from module import items
        from_match = re.match(r'from\s+([\w.]+)\s+import\s+(.+)', line)
        if from_match:
            return 'from', from_match.group(1), from_match.group(2)
        
        # import module
        import_match = re.match(r'import\s+([\w.]+)', line)
        if import_match:
            return 'import', import_match.group(1), ''
        
        return '', '', ''
    
    def fix_import_path(self, module_path: str) -> str:
        """修复导入路径"""
        # 直接映射
        if module_path in self.path_mappings:
            return self.path_mappings[module_path]
        
        # 模式匹配修复
        fixed_path = module_path
        
        # 修复 sage_ext -> sage.extensions
        if fixed_path.startswith('sage_ext.'):
            fixed_path = fixed_path.replace('sage_ext.', 'sage.extensions.')
        
        # 修复 sage_plugins -> sage.plugins
        if fixed_path.startswith('sage_plugins.'):
            fixed_path = fixed_path.replace('sage_plugins.', 'sage.plugins.')
        
        # 修复 logger 路径
        if 'sage.utils.logging' in fixed_path:
            fixed_path = fixed_path.replace('sage.utils.logging', 'sage.utils.logging')
        
        # 修复一些常见的错误路径
        path_fixes = {
            'sage.utils.clients': 'sage.llm.clients',
            'sage.utils.state_persistence': 'sage.llm.persistence.state',
        }
        
        for wrong, correct in path_fixes.items():
            if fixed_path.startswith(wrong):
                fixed_path = fixed_path.replace(wrong, correct)
        
        return fixed_path
    
    def fix_file_imports(self, file_path: Path) -> bool:
        """修复单个文件的导入路径"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"无法读取文件 {file_path}: {e}")
            return False
        
        modified = False
        new_lines = []
        
        for i, line in enumerate(lines):
            original_line = line
            import_type, module, items = self.analyze_import_statement(line)
            
            if import_type and module:
                fixed_module = self.fix_import_path(module)
                if fixed_module != module:
                    if import_type == 'from':
                        new_line = f"from {fixed_module} import {items}\n"
                    else:
                        new_line = f"import {fixed_module}\n"
                    
                    if new_line != original_line:
                        new_lines.append(new_line)
                        modified = True
                        self.fixes_applied.append({
                            'file': str(file_path),
                            'line': i + 1,
                            'original': original_line.strip(),
                            'fixed': new_line.strip()
                        })
                        continue
            
            new_lines.append(original_line)
        
        if modified:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                print(f"✅ 修复了文件: {file_path}")
                return True
            except Exception as e:
                print(f"❌ 无法写入文件 {file_path}: {e}")
                self.fixes_failed.append({
                    'file': str(file_path),
                    'error': str(e)
                })
                return False
        
        return True
    
    def run_fixes(self):
        """运行所有修复"""
        python_files = self.find_python_files()
        print(f"找到 {len(python_files)} 个Python文件")
        
        total_files = len(python_files)
        processed = 0
        
        for file_path in python_files:
            self.fix_file_imports(file_path)
            processed += 1
            if processed % 50 == 0:
                print(f"进度: {processed}/{total_files}")
        
        print(f"\n修复完成!")
        print(f"应用了 {len(self.fixes_applied)} 个修复")
        print(f"失败了 {len(self.fixes_failed)} 个修复")
        
        # 保存修复报告
        self.save_report()
    
    def save_report(self):
        """保存修复报告"""
        report = {
            'fixes_applied': self.fixes_applied,
            'fixes_failed': self.fixes_failed,
            'summary': {
                'total_fixes': len(self.fixes_applied),
                'failed_fixes': len(self.fixes_failed)
            }
        }
        
        report_file = self.packages_root.parent / 'import_fixes_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"修复报告已保存到: {report_file}")
        
        # 打印一些修复示例
        if self.fixes_applied:
            print("\n修复示例:")
            for fix in self.fixes_applied[:10]:
                print(f"  {fix['file']}:{fix['line']}")
                print(f"    - {fix['original']}")
                print(f"    + {fix['fixed']}")
                print()

def main():
    packages_root = "/home/flecther/SAGE/packages"
    
    if not os.path.exists(packages_root):
        print(f"错误: packages目录不存在: {packages_root}")
        return
    
    print("开始修复SAGE包的导入路径...")
    fixer = ImportPathFixer(packages_root)
    fixer.run_fixes()

if __name__ == "__main__":
    main()
