#!/usr/bin/env python3
"""
SAGE Python 版本同步工具
自动更新项目中所有文件的Python版本配置
"""

import re
import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from python_config import get_python_config

class PythonVersionSyncer:
    """Python版本同步器"""
    
    def __init__(self):
        self.config = get_python_config()
        self.root_dir = self.config.root_dir
    
    def update_pyproject_files(self):
        """更新所有pyproject.toml文件中的Python版本配置"""
        print("📦 更新 pyproject.toml 文件中的Python版本配置...")
        
        pyproject_files = list(self.root_dir.glob("**/pyproject.toml"))
        
        for file_path in pyproject_files:
            if self._update_pyproject_file(file_path):
                print(f"  ✅ 更新 {file_path.relative_to(self.root_dir)}")
    
    def _update_pyproject_file(self, file_path: Path) -> bool:
        """更新单个pyproject.toml文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 更新requires-python
            content = re.sub(
                r'requires-python\s*=\s*"[^"]*"',
                f'requires-python = "{self.config.python_requires}"',
                content
            )
            
            # 更新Python分类器
            classifiers_pattern = r'(\s*"Programming Language :: Python :: 3(?:\.\d+)?",?\s*\n)+'
            python_classifiers = '\n'.join([f'    "{classifier}",' for classifier in self.config.get_python_classifiers()])
            
            # 先移除旧的Python分类器
            content = re.sub(classifiers_pattern, '', content)
            
            # 在Programming Language :: Python :: 3之前插入新的分类器
            if '"Programming Language :: Python :: 3"' not in content:
                # 如果没有Python 3分类器，在合适位置添加
                license_pattern = r'(\s*"License :: OSI Approved[^"]*",?\s*\n)'
                if re.search(license_pattern, content):
                    content = re.sub(
                        license_pattern,
                        r'\1' + python_classifiers + '\n',
                        content
                    )
            
            # 更新ruff target-version
            ruff_targets = self.config.get_ruff_target_versions()
            if len(ruff_targets) > 1:
                ruff_target_str = "[" + ", ".join([f'"{v}"' for v in ruff_targets]) + "]"
            else:
                ruff_target_str = f'"{ruff_targets[0]}"'
            
            content = re.sub(
                r'target-version\s*=\s*(?:\[[^\]]*\]|"[^"]*")',
                f'target-version = {ruff_target_str}',
                content
            )
            
            # 更新mypy python_version
            content = re.sub(
                r'python_version\s*=\s*"[^"]*"',
                f'python_version = "{self.config.mypy_python_version}"',
                content
            )
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            
            return False
            
        except Exception as e:
            print(f"  ❌ 更新失败 {file_path}: {e}")
            return False
    
    def update_github_workflows(self):
        """更新GitHub Actions工作流中的Python版本"""
        print("⚙️  更新 GitHub Actions 工作流...")
        
        workflow_files = list(self.root_dir.glob(".github/workflows/*.yml"))
        
        for file_path in workflow_files:
            if self._update_workflow_file(file_path):
                print(f"  ✅ 更新 {file_path.relative_to(self.root_dir)}")
    
    def _update_workflow_file(self, file_path: Path) -> bool:
        """更新单个workflow文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 更新PYTHON_VERSION环境变量
            content = re.sub(
                r'PYTHON_VERSION:\s*[\'"]?[0-9.]+[\'"]?',
                f"PYTHON_VERSION: '{self.config.python_default_version}'",
                content
            )
            
            # 更新python-version
            content = re.sub(
                r'python-version:\s*[\'"]?[0-9x.]+[\'"]?',
                f"python-version: '{self.config.python_default_version}'",
                content
            )
            
            # 更新Python版本矩阵（如果存在）
            matrix_versions = self.config.get_github_actions_matrix()
            matrix_str = "[" + ", ".join([f"'{v}'" for v in matrix_versions]) + "]"
            
            content = re.sub(
                r"python-version:\s*\[[^\]]*\]",
                f"python-version: {matrix_str}",
                content
            )
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            
            return False
            
        except Exception as e:
            print(f"  ❌ 更新失败 {file_path}: {e}")
            return False
    
    def update_scripts(self):
        """更新脚本文件中的Python版本"""
        print("📜 更新脚本文件中的Python版本...")
        
        script_files = list(self.root_dir.glob("scripts/*.sh"))
        script_files.extend(self.root_dir.glob("tools/**/*.sh"))
        script_files.append(self.root_dir / "quickstart.sh")
        
        for file_path in script_files:
            if file_path.exists() and self._update_script_file(file_path):
                print(f"  ✅ 更新 {file_path.relative_to(self.root_dir)}")
    
    def _update_script_file(self, file_path: Path) -> bool:
        """更新单个脚本文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 更新SAGE_PYTHON_VERSION
            content = re.sub(
                r'SAGE_PYTHON_VERSION="?[0-9.]+"?',
                f'SAGE_PYTHON_VERSION="{self.config.python_default_version}"',
                content
            )
            
            # 更新默认Python版本参数
            content = re.sub(
                r'python_version="\${[^}]*:-[0-9.]+}"',
                f'python_version="${{2:-{self.config.python_default_version}}}"',
                content
            )
            
            # 更新conda create命令中的Python版本
            content = re.sub(
                r'python=[0-9.]+',
                f'python={self.config.python_default_version}',
                content
            )
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            
            return False
            
        except Exception as e:
            print(f"  ❌ 更新失败 {file_path}: {e}")
            return False
    
    def sync_all(self):
        """同步所有文件中的Python版本配置"""
        print("🔄 开始同步所有Python版本配置...")
        print()
        
        # 显示当前配置
        self.config.show_config()
        print()
        
        # 更新各类文件
        self.update_pyproject_files()
        self.update_github_workflows()
        self.update_scripts()
        
        print()
        print("🎉 Python版本配置同步完成！")

def main():
    syncer = PythonVersionSyncer()
    syncer.sync_all()

if __name__ == "__main__":
    main()
