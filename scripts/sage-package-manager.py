#!/usr/bin/env python3
"""
SAGE Monorepo包管理器
====================

统一管理SAGE项目中的所有Python包
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Set
import json

class SagePackageManager:
    """SAGE包管理器"""
    
    def __init__(self, repo_root: Path | None = None):
        self.repo_root = repo_root or Path(__file__).parent.parent
        self.packages_dir = self.repo_root / 'packages'
        
        # 定义包及其依赖关系
        self.packages = {
            'sage-utils': {
                'path': self.packages_dir / 'sage-utils',
                'namespace': 'sage.utils',
                'dependencies': [],  # 基础包，无依赖
                'description': '通用工具包'
            },
            'sage-core': {
                'path': self.packages_dir / 'sage-core', 
                'namespace': 'sage.core',
                'dependencies': ['sage-utils'],
                'description': '核心框架'
            },
            'sage-lib': {
                'path': self.packages_dir / 'sage-lib',
                'namespace': 'sage.lib', 
                'dependencies': ['sage-utils'],
                'description': '核心库组件'
            },
            'sage-extensions': {
                'path': self.packages_dir / 'sage-extensions',
                'namespace': 'sage.extensions',
                'dependencies': ['sage-core', 'sage-utils'],
                'description': '高性能C++扩展'
            },
            'sage-plugins': {
                'path': self.packages_dir / 'sage-plugins',
                'namespace': 'sage.plugins',
                'dependencies': ['sage-core', 'sage-utils'], 
                'description': '插件系统'
            },
            'sage-service': {
                'path': self.packages_dir / 'sage-service',
                'namespace': 'sage.service',
                'dependencies': ['sage-core', 'sage-lib', 'sage-utils'],
                'description': '服务层组件'
            },
            'sage-cli': {
                'path': self.packages_dir / 'sage-cli',
                'namespace': 'sage.cli',
                'dependencies': ['sage-core', 'sage-utils'],
                'description': '命令行界面'
            }
        }
    
    def get_dependency_order(self, package_names: List[str] | None = None) -> List[str]:
        """获取按依赖关系排序的包列表"""
        if package_names is None:
            package_names = list(self.packages.keys())
        
        # 拓扑排序
        visited = set()
        result = []
        temp = set()
        
        def visit(pkg_name):
            if pkg_name in temp:
                raise ValueError(f"Circular dependency detected involving {pkg_name}")
            if pkg_name in visited:
                return
            
            temp.add(pkg_name)
            for dep in self.packages[pkg_name]['dependencies']:
                if dep in package_names:
                    visit(dep)
            temp.remove(pkg_name)
            visited.add(pkg_name)
            result.append(pkg_name)
        
        for pkg in package_names:
            if pkg not in visited:
                visit(pkg)
        
        return result
    
    def install_package(self, package_name: str, dev: bool = False, editable: bool = True):
        """安装单个包"""
        if package_name not in self.packages:
            print(f"❌ 未知包: {package_name}")
            return False
        
        pkg_info = self.packages[package_name]
        pkg_path = pkg_info['path']
        
        if not pkg_path.exists():
            print(f"❌ 包路径不存在: {pkg_path}")
            return False
        
        print(f"📦 安装 {package_name} ({pkg_info['description']})")
        
        # 使用当前Python解释器（支持虚拟环境）
        install_cmd = [sys.executable, '-m', 'pip', 'install']
        
        if editable:
            install_cmd.append('-e')
        
        install_cmd.append(str(pkg_path))
        
        if dev:
            install_cmd[-1] += '[dev]'
        
        try:
            subprocess.run(install_cmd, check=True)
            print(f"✅ {package_name} 安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ {package_name} 安装失败: {e}")
            return False
    
    def install_all(self, dev: bool = False, editable: bool = True):
        """按依赖顺序安装所有包"""
        print("🚀 安装所有SAGE包...")
        
        # 获取按依赖顺序排列的包列表
        ordered_packages = self.get_dependency_order()
        
        success_count = 0
        for package_name in ordered_packages:
            if self.install_package(package_name, dev=dev, editable=editable):
                success_count += 1
                
        # 如果是开发模式，安装工作空间级别的开发依赖
        if dev:
            print("\n🔧 安装工作空间开发依赖...")
            try:
                # 先安装关键的开发工具，不依赖工作空间配置
                essential_dev_deps = [
                    'tqdm>=4.60.0',
                    'pytest', 
                    'pytest-cov>=4.0.0',
                    'pytest-asyncio>=0.21.0',
                    'black>=23.0.0',
                    'isort>=5.12.0',
                    'mypy>=1.0.0',
                    'ruff>=0.1.0'
                ]
                
                print("📋 安装关键开发工具...")
                for dep in essential_dev_deps:
                    install_cmd = [sys.executable, '-m', 'pip', 'install', dep]
                    subprocess.run(install_cmd, check=True, capture_output=True)
                    
                print("✅ 关键开发工具安装成功")
                
                # 尝试安装工作空间的开发依赖（如果失败也没关系）
                workspace_pyproject = self.repo_root / "pyproject.toml"
                if workspace_pyproject.exists():
                    print("📋 尝试安装工作空间开发依赖...")
                    install_cmd = [sys.executable, '-m', 'pip', 'install', '-e', f"{self.repo_root}[dev]"]
                    result = subprocess.run(install_cmd, capture_output=True)
                    if result.returncode == 0:
                        print("✅ 工作空间开发依赖安装成功")
                    else:
                        print("⚠️  工作空间开发依赖安装失败（但关键工具已安装）")
                else:
                    print("⚠️  未找到工作空间 pyproject.toml")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  开发依赖安装失败: {e}")
                print("但这不影响包的正常使用")

        print(f"\n✅ 成功安装 {success_count}/{len(ordered_packages)} 个包")
        
        if success_count == len(ordered_packages):
            print("🎉 所有包安装完成！")
        else:
            print("⚠️  部分包安装失败，请检查错误信息")
    
    def test_package(self, package_name: str):
        """测试单个包"""
        if package_name not in self.packages:
            print(f"❌ 未知包: {package_name}")
            return False
        
        pkg_info = self.packages[package_name]
        pkg_path = pkg_info['path']
        
        print(f"🧪 测试 {package_name}")
        
        try:
            subprocess.run([
                'python3', '-m', 'pytest', 
                str(pkg_path / 'tests'), 
                '-v', '--tb=short'
            ], cwd=pkg_path, check=True)
            print(f"✅ {package_name} 测试通过")
            return True
        except subprocess.CalledProcessError:
            print(f"❌ {package_name} 测试失败")
            return False
        except FileNotFoundError:
            print(f"⚠️  {package_name} 没有测试目录")
            return True
    
    def test_all(self):
        """测试所有包"""  
        print("🧪 测试所有SAGE包...")
        
        success_count = 0
        for package_name in self.packages.keys():
            if self.test_package(package_name):
                success_count += 1
        
        print(f"\n✅ {success_count}/{len(self.packages)} 个包测试通过")
    
    def build_package(self, package_name: str):
        """构建单个包"""
        if package_name not in self.packages:
            print(f"❌ 未知包: {package_name}")
            return False
        
        pkg_info = self.packages[package_name]
        pkg_path = pkg_info['path']
        
        print(f"🏗️  构建 {package_name}")
        
        try:
            subprocess.run([
                'python3', '-m', 'build'
            ], cwd=pkg_path, check=True)
            print(f"✅ {package_name} 构建成功")
            return True
        except subprocess.CalledProcessError:
            print(f"❌ {package_name} 构建失败")
            return False
    
    def list_packages(self):
        """列出所有包"""
        print("📋 SAGE包列表:")
        print("=" * 60)
        
        for pkg_name, pkg_info in self.packages.items():
            deps = ", ".join(pkg_info['dependencies']) or "无"
            print(f"📦 {pkg_name}")
            print(f"   命名空间: {pkg_info['namespace']}")
            print(f"   描述: {pkg_info['description']}")
            print(f"   依赖: {deps}")
            print(f"   路径: {pkg_info['path']}")
            print()
    
    def verify_imports(self):
        """验证所有包的导入"""
        print("🔍 验证包导入...")
        
        for pkg_name, pkg_info in self.packages.items():
            namespace = pkg_info['namespace']
            
            try:
                exec(f"import {namespace}")
                print(f"✅ {namespace}")
            except ImportError as e:
                print(f"❌ {namespace} - {e}")
            except Exception as e:
                print(f"⚠️  {namespace} - {e}")

def main():
    parser = argparse.ArgumentParser(description="SAGE包管理器")
    parser.add_argument('command', choices=[
        'list', 'install', 'install-all', 'test', 'test-all', 
        'build', 'verify', 'deps'
    ])
    parser.add_argument('package', nargs='?', help='包名 (install, test, build命令需要)')
    parser.add_argument('--dev', action='store_true', help='安装开发依赖')
    parser.add_argument('--no-editable', action='store_true', help='不使用可编辑安装')
    
    args = parser.parse_args()
    
    manager = SagePackageManager()
    
    if args.command == 'list':
        manager.list_packages()
    elif args.command == 'install':
        if not args.package:
            print("❌ install命令需要指定包名")
            return 1
        manager.install_package(args.package, dev=args.dev, editable=not args.no_editable)
    elif args.command == 'install-all':
        manager.install_all(dev=args.dev, editable=not args.no_editable)
    elif args.command == 'test':
        if not args.package:
            print("❌ test命令需要指定包名")  
            return 1
        manager.test_package(args.package)
    elif args.command == 'test-all':
        manager.test_all()
    elif args.command == 'build':
        if not args.package:
            print("❌ build命令需要指定包名")
            return 1
        manager.build_package(args.package)
    elif args.command == 'verify':
        manager.verify_imports()
    elif args.command == 'deps':
        if args.package:
            deps = manager.get_dependency_order([args.package])
            print(f"{args.package} 的依赖顺序: {' -> '.join(deps)}")
        else:
            deps = manager.get_dependency_order()
            print(f"所有包的安装顺序: {' -> '.join(deps)}")
    
    return 0

if __name__ == '__main__':
    exit(main())
