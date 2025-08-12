#!/usr/bin/env python3
"""
SAGE Kernel 模块重构迁移工具

自动化地将旧的深层次导入转换为新的模块化导入结构。
"""

import re
import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
import argparse


@dataclass
class ImportMapping:
    """导入映射配置"""
    old_import: str
    new_import: str
    symbols: List[str] = None  # 如果为None，表示导入整个模块


class ModuleRefactorTool:
    """模块重构工具"""
    
    def __init__(self):
        # 定义导入映射规则
        self.import_mappings = [
            # 函数相关
            ImportMapping(
                "sage.core.api.function.lambda_function",
                "sage.kernel.function",
                ["wrap_lambda"]
            ),
            ImportMapping(
                "sage.core.api.function.base_function",
                "sage.kernel.function",
                ["BaseFunction"]
            ),
            ImportMapping(
                "sage.core.api.function.kafka_source",
                "sage.kernel.function",
                ["KafkaSourceFunction"]
            ),
            
            # API相关
            ImportMapping(
                "sage.core.api.datastream",
                "sage.core.api",
                ["DataStream"]
            ),
            
            # 转换相关
            ImportMapping(
                "sage.core.transformation.base_transformation",
                "sage.kernel.transformation",
                ["BaseTransformation"]
            ),
            ImportMapping(
                "sage.core.transformation.source_transformation",
                "sage.kernel.transformation",
                ["SourceTransformation"]
            ),
            ImportMapping(
                "sage.core.transformation.batch_transformation",
                "sage.kernel.transformation",
                ["BatchTransformation"]
            ),
            ImportMapping(
                "sage.core.transformation.future_transformation",
                "sage.kernel.transformation",
                ["FutureTransformation"]
            ),
            ImportMapping(
                "sage.core.transformation.map_transformation",
                "sage.kernel.transformation",
                ["MapTransformation"]
            ),
            ImportMapping(
                "sage.core.transformation.filter_transformation",
                "sage.kernel.transformation",
                ["FilterTransformation"]
            ),
            ImportMapping(
                "sage.core.transformation.flatmap_transformation",
                "sage.kernel.transformation",
                ["FlatMapTransformation"]
            ),
            ImportMapping(
                "sage.core.transformation.sink_transformation",
                "sage.kernel.transformation",
                ["SinkTransformation"]
            ),
            ImportMapping(
                "sage.core.transformation.keyby_transformation",
                "sage.kernel.transformation",
                ["KeyByTransformation"]
            ),
            
            # 通信相关
            ImportMapping(
                "sage.kernel.runtime.communication.queue_descriptor.base_queue_descriptor",
                "sage.kernel.communication",
                ["BaseQueueDescriptor"]
            ),
            
            # 日志相关
            ImportMapping(
                "sage.utils.logging.custom_logger",
                "sage.kernel.logging",
                ["CustomLogger"]
            ),
            
            # 作业管理相关
            ImportMapping(
                "sage.kernel.jobmanager.utils.name_server",
                "sage.kernel.jobmanager",
                ["get_name"]
            ),
            ImportMapping(
                "sage.kernel.jobmanager_client",
                "sage.kernel.jobmanager",
                ["JobManagerClient"]
            ),
            ImportMapping(
                "sage.kernel",
                "sage.kernel.jobmanager",
                ["JobManager"]
            ),
            
            # 工厂相关
            ImportMapping(
                "sage.core.factory.service_factory",
                "sage.kernel.factory",
                ["ServiceFactory"]
            ),
        ]
        
        # 构建查找表
        self.old_to_new_mapping = {}
        for mapping in self.import_mappings:
            if mapping.symbols:
                for symbol in mapping.symbols:
                    self.old_to_new_mapping[f"{mapping.old_import}.{symbol}"] = (mapping.new_import, symbol)
                    self.old_to_new_mapping[mapping.old_import] = (mapping.new_import, mapping.symbols)
            else:
                self.old_to_new_mapping[mapping.old_import] = (mapping.new_import, None)

    def refactor_file(self, file_path: Path) -> Tuple[str, List[str]]:
        """
        重构单个文件的导入语句
        
        Returns:
            Tuple[新的文件内容, 变更列表]
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        changes = []
        new_content = content
        
        # 分析文件中的导入语句
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"警告: 无法解析文件 {file_path}: {e}")
            return content, []
        
        # 收集所有的导入语句
        imports_to_replace = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.old_to_new_mapping:
                        imports_to_replace.append((node, alias.name, None))
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module in self.old_to_new_mapping:
                    for alias in node.names:
                        imports_to_replace.append((node, node.module, alias.name))
        
        # 生成新的导入语句
        new_imports = self._generate_new_imports(imports_to_replace)
        
        # 替换导入语句
        lines = content.split('\n')
        for node, old_module, symbol in imports_to_replace:
            old_line = lines[node.lineno - 1]
            new_line = self._generate_replacement_line(old_module, symbol, old_line)
            if new_line != old_line:
                lines[node.lineno - 1] = new_line
                changes.append(f"第{node.lineno}行: {old_line.strip()} -> {new_line.strip()}")
        
        new_content = '\n'.join(lines)
        return new_content, changes

    def _generate_new_imports(self, imports_to_replace: List[Tuple]) -> Dict[str, Set[str]]:
        """生成新的导入语句组织"""
        new_imports = {}
        
        for node, old_module, symbol in imports_to_replace:
            if old_module in self.old_to_new_mapping:
                new_module, symbols = self.old_to_new_mapping[old_module]
                if new_module not in new_imports:
                    new_imports[new_module] = set()
                
                if symbol:
                    new_imports[new_module].add(symbol)
                elif symbols:
                    new_imports[new_module].update(symbols)
        
        return new_imports

    def _generate_replacement_line(self, old_module: str, symbol: str, old_line: str) -> str:
        """生成替换的导入行"""
        if old_module not in self.old_to_new_mapping:
            return old_line
        
        new_module, symbols = self.old_to_new_mapping[old_module]
        
        if symbol:
            # from old_module import symbol
            return f"from {new_module} import {symbol}"
        else:
            # import old_module
            return f"import {new_module}"

    def refactor_directory(self, directory: Path, dry_run: bool = False) -> Dict[str, List[str]]:
        """
        重构目录中的所有Python文件
        
        Args:
            directory: 要重构的目录
            dry_run: 是否只是试运行，不实际修改文件
            
        Returns:
            Dict[文件路径, 变更列表]
        """
        results = {}
        
        for py_file in directory.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            print(f"处理文件: {py_file}")
            
            try:
                new_content, changes = self.refactor_file(py_file)
                
                if changes:
                    results[str(py_file)] = changes
                    
                    if not dry_run:
                        # 备份原文件
                        backup_path = py_file.with_suffix('.py.backup')
                        py_file.rename(backup_path)
                        
                        # 写入新内容
                        with open(py_file, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        print(f"  已更新，备份保存为: {backup_path}")
                    else:
                        print(f"  [试运行] 将进行 {len(changes)} 项更改")
                
            except Exception as e:
                print(f"错误: 处理文件 {py_file} 时出错: {e}")
        
        return results

    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否应该跳过某个文件"""
        # 跳过备份文件、测试文件等
        if file_path.name.endswith('.backup'):
            return True
        if '__pycache__' in str(file_path):
            return True
        if 'test_' in file_path.name:
            return True
        if file_path.name.startswith('.'):
            return True
        
        return False

    def generate_summary_report(self, results: Dict[str, List[str]]) -> str:
        """生成总结报告"""
        total_files = len(results)
        total_changes = sum(len(changes) for changes in results.values())
        
        report = [
            "=" * 60,
            "SAGE Kernel 模块重构报告",
            "=" * 60,
            f"处理的文件数量: {total_files}",
            f"总变更数量: {total_changes}",
            "",
            "详细变更:",
            "-" * 40
        ]
        
        for file_path, changes in results.items():
            report.append(f"\n文件: {file_path}")
            for change in changes:
                report.append(f"  {change}")
        
        return "\n".join(report)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="SAGE Kernel 模块重构工具")
    parser.add_argument("path", help="要重构的文件或目录路径")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不实际修改文件")
    parser.add_argument("--output", help="报告输出文件路径")
    
    args = parser.parse_args()
    
    path = Path(args.path)
    if not path.exists():
        print(f"错误: 路径 {path} 不存在")
        sys.exit(1)
    
    tool = ModuleRefactorTool()
    
    print(f"开始重构路径: {path}")
    print(f"模式: {'试运行' if args.dry_run else '实际执行'}")
    print("-" * 50)
    
    if path.is_file():
        # 处理单个文件
        if path.suffix == '.py':
            new_content, changes = tool.refactor_file(path)
            results = {str(path): changes} if changes else {}
        else:
            print(f"错误: {path} 不是Python文件")
            sys.exit(1)
    else:
        # 处理目录
        results = tool.refactor_directory(path, dry_run=args.dry_run)
    
    # 生成报告
    report = tool.generate_summary_report(results)
    print("\n" + report)
    
    # 保存报告到文件
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n报告已保存到: {args.output}")


if __name__ == "__main__":
    main()
