#!/usr/bin/env python3
"""
IDE支持配置脚本
================

确保拆分包后IDE代码跳转正常工作的配置脚本
"""

import os
import sys
import subprocess
from pathlib import Path
import json

class IDESetupManager:
    """IDE支持配置管理器"""
    
    def __init__(self, repo_root: Path | None = None):
        self.repo_root = repo_root or Path(__file__).parent.parent
        self.packages_dir = self.repo_root / 'packages'
        
    def setup_development_links(self):
        """设置开发环境链接，确保IDE能正确跳转"""
        print("🔧 设置开发环境链接...")
        
        # 获取所有包
        packages = [
            'sage-cli',
            'sage-core', 
            'sage-extensions',
            'sage-frontend',
            'sage-lib',
            'sage-plugins',
            'sage-service',
            'sage-utils',
        ]
        
        # 尝试不同的Python可执行文件
        python_executables = [sys.executable, 'python3', 'python']
        
        for python_exe in python_executables:
            try:
                # 测试pip是否可用
                result = subprocess.run([python_exe, '-m', 'pip', '--version'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ 使用Python: {python_exe}")
                    break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        else:
            print("⚠️  警告: 未找到可用的pip，跳过包安装")
            print("💡 请手动安装pip或使用虚拟环境")
            return
        
        for package in packages:
            package_path = self.packages_dir / package
            if package_path.exists():
                print(f"📦 安装开发模式: {package}")
                try:
                    subprocess.run([
                        python_exe, '-m', 'pip', 'install', '-e', str(package_path)
                    ], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"⚠️  警告: {package} 安装失败: {e}")
                    continue
        
        print("✅ 开发环境链接设置完成")
    
    def create_vscode_settings(self):
        """创建VS Code设置，优化Python路径解析"""
        print("⚙️  配置VS Code设置...")
        
        vscode_dir = self.repo_root / '.vscode'
        vscode_dir.mkdir(exist_ok=True)
        
        # Python路径配置
        python_paths = [
            str(self.packages_dir / 'sage-core' / 'src'),
            str(self.packages_dir / 'sage-utils' / 'src'),
            str(self.packages_dir / 'sage-extensions' / 'src'),
            str(self.packages_dir / 'sage-cli' / 'src'),
            str(self.packages_dir / 'sage-lib' / 'src'),
            str(self.packages_dir / 'sage-plugins' / 'src'),
            str(self.packages_dir / 'sage-service' / 'src'),
            str(self.packages_dir / 'sage-frontend'),  # 这个包没有src目录
            str(self.repo_root),  # 根目录
        ]
        
        settings = {
            "python.analysis.extraPaths": python_paths,
            "python.autoComplete.extraPaths": python_paths,
            "python.analysis.autoSearchPaths": True,
            "python.analysis.useLibraryCodeForTypes": True,
            "python.analysis.autoImportCompletions": True,
            "python.analysis.packageIndexDepths": [
                {
                    "name": "sage",
                    "depth": 10
                }
            ],
            # Pylance配置
            "pylance.insidersChannel": "off",
            "python.languageServer": "Pylance",
            "python.analysis.typeCheckingMode": "basic",
            # 工作区设置
            "python.defaultInterpreterPath": sys.executable,
            # 文件关联
            "files.associations": {
                "*.pyi": "python"
            }
        }
        
        settings_file = vscode_dir / 'settings.json'
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        
        print(f"✅ VS Code设置已保存到: {settings_file}")
        
        # 创建launch.json用于调试
        launch_config = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Python: Current File",
                    "type": "python",
                    "request": "launch",
                    "program": "${file}",
                    "console": "integratedTerminal",
                    "cwd": "${workspaceFolder}",
                    "env": {
                        "PYTHONPATH": ":".join(python_paths)
                    }
                },
                {
                    "name": "SAGE App Debug",
                    "type": "python", 
                    "request": "launch",
                    "program": "${workspaceFolder}/app/${input:appFile}",
                    "console": "integratedTerminal",
                    "cwd": "${workspaceFolder}",
                    "env": {
                        "PYTHONPATH": ":".join(python_paths)
                    }
                }
            ],
            "inputs": [
                {
                    "id": "appFile",
                    "description": "Choose app file",
                    "default": "hello_world.py",
                    "type": "promptString"
                }
            ]
        }
        
        launch_file = vscode_dir / 'launch.json'
        with open(launch_file, 'w', encoding='utf-8') as f:
            json.dump(launch_config, f, indent=2)
        
        print(f"✅ 调试配置已保存到: {launch_file}")
    
    def create_pyproject_workspace(self):
        """创建工作空间级别的Python配置"""
        print("📝 创建工作空间Python配置...")
        
        # 检查是否存在根级pyproject.toml
        root_pyproject = self.repo_root / 'pyproject.toml'
        
        if root_pyproject.exists():
            print("⚠️  根级pyproject.toml已存在，跳过创建")
            return
        
        # 创建简单的工作空间配置
        workspace_config = '''# SAGE Monorepo工作空间配置
# 这个文件主要为IDE和工具提供工作空间级别的配置

[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sage-workspace"
version = "1.0.0"
description = "SAGE Framework - Monorepo Workspace"
requires-python = ">=3.10"

# 这是一个虚拟包，用于工作空间管理
dependencies = []

[project.optional-dependencies]
# 完整安装 - 包含所有子包
full = [
    "sage-core",
    "sage-utils", 
    "sage-extensions",
    "sage-cli",
    "sage-lib",
    "sage-plugins",
    "sage-service",
    "sage-frontend"
]

# 开发环境
dev = [
    "pytest",
    "black>=23.0.0", 
    "isort>=5.12.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
    "pre-commit>=3.0.0"
]

[tool.black]
line-length = 88
target-version = ["py311"]
        # 应用到所有包
        extend-exclude = """
        /(
            \\.git
            | \\.venv
            | build
            | dist
            | packages/.*/build
            | packages/.*/dist
        )/
        """[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["sage"]
# 跨包导入支持
src_paths = [
    "packages/sage-core/src",
    "packages/sage-utils/src", 
    "packages/sage-extensions/src",
    "packages/tools/sage-cli/src",
    "packages/sage-lib/src",
    "packages/sage-plugins/src",
    "packages/sage-service/src",
    "packages/tools/sage-frontend"
]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
# 工作空间模式 - 支持跨包类型检查
namespace_packages = true
explicit_package_bases = true
mypy_path = [
    "packages/sage-core/src",
    "packages/sage-utils/src",
    "packages/sage-extensions/src",
    "packages/tools/sage-cli/src",
    "packages/sage-lib/src",
    "packages/sage-plugins/src",
    "packages/sage-service/src",
    "packages/tools/sage-frontend"
]

# 每个包的具体配置
[[tool.mypy.overrides]]
module = "sage.*"
ignore_missing_imports = false

[tool.pytest.ini_options]
# 工作空间级别的测试配置
testpaths = [
    "packages/sage-core/tests",
    "packages/sage-utils/tests",
    "packages/sage-extensions/tests", 
    "packages/tools/sage-cli/tests",
    "packages/sage-lib/tests",
    "packages/sage-plugins/tests",
    "packages/sage-service/tests",
    "packages/tools/sage-frontend/tests",
    "tests"  # 集成测试
]
python_files = ["test_*.py", "*_test.py"]
addopts = [
    "--cov=sage",
    "--cov-report=term-missing",
    "-v"
]
'''
        
        with open(root_pyproject, 'w', encoding='utf-8') as f:
            f.write(workspace_config)
        
        print(f"✅ 工作空间配置已保存到: {root_pyproject}")
    
    def verify_imports(self):
        """验证导入是否正常工作"""
        print("🧪 验证导入功能...")
        
        test_imports = [
            "from sage.utils import logging",
            "from sage.utils.config_loader import load_config", 
            "from sage.utils.logging.custom_logger import CustomLogger",
            "import sage.utils",
        ]
        
        for import_stmt in test_imports:
            try:
                exec(import_stmt)
                print(f"✅ {import_stmt}")
            except ImportError as e:
                print(f"❌ {import_stmt} - Error: {e}")
            except Exception as e:
                print(f"⚠️  {import_stmt} - Warning: {e}")
    
    def setup_ide_support(self):
        """完整的IDE支持设置"""
        print("🚀 设置完整的IDE支持...")
        print("=" * 60)
        
        try:
            # 1. 设置开发链接
            self.setup_development_links()
            
            # 2. 创建VS Code配置
            self.create_vscode_settings()
            
            # 3. 创建工作空间配置
            self.create_pyproject_workspace()
            
            # 4. 验证导入
            self.verify_imports()
            
            print("=" * 60)
            print("🎉 IDE支持设置完成！")
            print()
            print("📋 接下来的步骤:")
            print("1. 重启VS Code以加载新配置")
            print("2. 在VS Code中选择正确的Python解释器")
            print("3. 测试代码跳转功能 (Ctrl+Click 或 F12)")
            print("4. 运行代码验证功能正常")
            print()
            print("💡 提示:")
            print("- 如果跳转不工作，尝试重新加载VS Code窗口 (Ctrl+Shift+P -> Reload Window)")
            print("- 确保Pylance扩展已安装并启用")
            print("- 检查Python解释器是否指向正确的虚拟环境")
            
        except Exception as e:
            print(f"❌ 设置过程中出现错误: {e}")
            raise

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="IDE支持配置脚本")
    parser.add_argument("--repo-root", type=Path, default=None,
                       help="仓库根目录 (默认: 自动检测)")
    parser.add_argument("--verify-only", action="store_true",
                       help="只验证导入，不修改配置")
    
    args = parser.parse_args()
    
    manager = IDESetupManager(args.repo_root)
    
    if args.verify_only:
        manager.verify_imports()
    else:
        manager.setup_ide_support()

if __name__ == "__main__":
    main()
