#!/usr/bin/env python3
"""
SAGE Python 版本配置管理工具
统一管理项目中所有Python版本相关的配置
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Any

class SAGEPythonConfig:
    """SAGE Python版本配置管理器"""
    
    def __init__(self):
        self.root_dir = self._find_sage_root()
        self.version_file = self.root_dir / "_version.py"
        self._load_config()
    
    def _find_sage_root(self):
        """查找SAGE项目根目录"""
        current_path = Path(__file__).resolve()
        
        # 从当前目录向上查找_version.py
        for parent in [current_path.parent.parent.parent] + list(current_path.parents):
            if (parent / "_version.py").exists():
                return parent
        
        raise FileNotFoundError("找不到SAGE项目根目录（_version.py文件）")
    
    def _load_config(self):
        """从_version.py加载配置"""
        if not self.version_file.exists():
            raise FileNotFoundError(f"版本文件不存在: {self.version_file}")
        
        # 执行_version.py获取所有变量
        version_globals = {}
        with open(self.version_file, 'r', encoding='utf-8') as f:
            exec(f.read(), version_globals)
        
        # 提取Python版本相关配置
        self.python_requires = version_globals.get('__python_requires__', '>=3.10')
        self.python_min_version = version_globals.get('__python_min_version__', '3.10')
        self.python_default_version = version_globals.get('__python_default_version__', '3.11')
        self.python_max_version = version_globals.get('__python_max_version__', '3.12')
        self.python_supported_versions = version_globals.get('__python_supported_versions__', ['3.10', '3.11', '3.12'])
        self.ruff_target_version = version_globals.get('__ruff_target_version__', 'py311')
        self.mypy_python_version = version_globals.get('__mypy_python_version__', '3.11')
    
    def get_python_classifiers(self) -> List[str]:
        """获取Python版本的PyPI分类器"""
        classifiers = ["Programming Language :: Python :: 3"]
        for version in self.python_supported_versions:
            classifiers.append(f"Programming Language :: Python :: {version}")
        return classifiers
    
    def get_ruff_target_versions(self) -> List[str]:
        """获取Ruff支持的目标版本列表"""
        return [f"py{version.replace('.', '')}" for version in self.python_supported_versions]
    
    def get_github_actions_matrix(self) -> List[str]:
        """获取GitHub Actions使用的Python版本矩阵"""
        return self.python_supported_versions.copy()
    
    def get_setup_python_version(self) -> str:
        """获取setup-python action使用的版本"""
        return self.python_default_version
    
    def show_config(self):
        """显示当前配置"""
        print("📋 SAGE Python 版本配置")
        print("=" * 50)
        print(f"Python要求: {self.python_requires}")
        print(f"最小版本: {self.python_min_version}")
        print(f"默认版本: {self.python_default_version}")
        print(f"最大版本: {self.python_max_version}")
        print(f"支持版本: {', '.join(self.python_supported_versions)}")
        print(f"Ruff目标: {self.ruff_target_version}")
        print(f"MyPy版本: {self.mypy_python_version}")
        print()
        print("🔧 生成的配置值:")
        print(f"PyPI分类器: {self.get_python_classifiers()}")
        print(f"Ruff目标版本: {self.get_ruff_target_versions()}")
        print(f"GitHub Actions矩阵: {self.get_github_actions_matrix()}")

def get_python_config():
    """获取Python配置实例（供其他脚本导入使用）"""
    return SAGEPythonConfig()

if __name__ == "__main__":
    config = SAGEPythonConfig()
    config.show_config()
