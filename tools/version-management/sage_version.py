#!/usr/bin/env python3
"""
SAGE 版本管理器 - 统一工具
一个脚本解决所有版本管理需求
"""

import sys
import os
import re
import argparse
from pathlib import Path
from datetime import datetime

class SAGEVersionManager:
    """SAGE项目版本管理器"""
    
    def __init__(self):
        self.root_dir = self._find_sage_root()
        self.version_file = self.root_dir / "_version.py"
    
    def _find_sage_root(self):
        """查找SAGE项目根目录"""
        current_path = Path(__file__).resolve()
        
        # 从当前目录向上查找_version.py
        for parent in [current_path.parent.parent.parent] + list(current_path.parents):
            if (parent / "_version.py").exists():
                return parent
        
        raise FileNotFoundError("找不到SAGE项目根目录（_version.py文件）")
    
    def get_version_info(self):
        """获取当前版本信息"""
        if not self.version_file.exists():
            raise FileNotFoundError(f"版本文件不存在: {self.version_file}")
        
        # 执行_version.py获取所有变量
        version_globals = {}
        with open(self.version_file, 'r', encoding='utf-8') as f:
            exec(f.read(), version_globals)
        
        return {
            'project_name': version_globals.get('__project_name__', 'SAGE'),
            'project_full_name': version_globals.get('__project_full_name__', 'Streaming-Augmented Generative Execution'),
            'version': version_globals.get('__version__', 'unknown'),
            'version_info': version_globals.get('__version_info__', (0, 0, 0)),
            'release_date': version_globals.get('__release_date__', ''),
            'release_status': version_globals.get('__release_status__', 'development'),
            'author': version_globals.get('__author__', ''),
            'email': version_globals.get('__email__', ''),
            'homepage': version_globals.get('__homepage__', ''),
            'repository': version_globals.get('__repository__', ''),
            'documentation': version_globals.get('__documentation__', ''),
        }
    
    def show_version(self):
        """显示版本信息"""
        try:
            info = self.get_version_info()
            print("📋 SAGE 项目信息")
            print("=" * 50)
            print(f"项目名称: {info['project_name']}")
            print(f"完整名称: {info['project_full_name']}")
            print(f"版本号: {info['version']}")
            print(f"发布日期: {info['release_date']}")
            print(f"状态: {info['release_status']}")
            print(f"作者: {info['author']}")
            print(f"邮箱: {info['email']}")
            print(f"主页: {info['homepage']}")
            print(f"仓库: {info['repository']}")
            print(f"文档: {info['documentation']}")
            return True
        except Exception as e:
            print(f"❌ 获取版本信息失败: {e}")
            return False
    
    def set_version(self, new_version):
        """设置新版本号并更新所有相关文件"""
        print(f"🔄 设置版本号为: {new_version}")
        
        # 1. 更新_version.py
        if not self._update_version_file(new_version):
            return False
        
        # 2. 更新所有pyproject.toml文件
        self._update_pyproject_files(new_version)
        
        # 3. 更新所有Python __init__.py文件
        self._update_python_files(new_version)
        
        print(f"🎉 版本号已统一更新为: {new_version}")
        return True
    
    def _update_version_file(self, new_version):
        """更新_version.py文件"""
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 更新版本号
            content = re.sub(
                r'__version__ = "[^"]*"',
                f'__version__ = "{new_version}"',
                content
            )
            
            # 更新版本元组
            version_parts = new_version.split('.')
            if len(version_parts) >= 3:
                version_tuple = f"({version_parts[0]}, {version_parts[1]}, {version_parts[2]})"
                content = re.sub(
                    r'__version_info__ = \([^)]*\)',
                    f'__version_info__ = {version_tuple}',
                    content
                )
            
            with open(self.version_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ 已更新版本文件: {self.version_file}")
            return True
        except Exception as e:
            print(f"❌ 更新版本文件失败: {e}")
            return False
    
    def _update_pyproject_files(self, new_version):
        """更新所有pyproject.toml文件"""
        print("📦 更新所有 pyproject.toml 文件...")
        
        pyproject_files = list(self.root_dir.glob("**/pyproject.toml"))
        
        for file_path in pyproject_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 更新version字段，但不更新target-version或python_version
                content = re.sub(
                    r'^version\s*=\s*"[^"]*"',
                    f'version = "{new_version}"',
                    content,
                    flags=re.MULTILINE
                )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"  更新 {file_path.relative_to(self.root_dir)}")
            except Exception as e:
                print(f"  ❌ 更新失败 {file_path}: {e}")
    
    def _update_python_files(self, new_version):
        """更新所有Python __init__.py文件中的__version__"""
        print("🐍 更新所有 Python 文件...")
        
        # 查找所有__init__.py文件
        init_files = list(self.root_dir.glob("**/__init__.py"))
        
        # 还要查找其他可能包含版本号的Python文件
        other_python_files = [
            "packages/sage-common/src/sage/common/cli/commands/version.py",
            "packages/sage-common/src/sage/common/frontend/web_ui/app.py"
        ]
        
        all_files = init_files + [self.root_dir / f for f in other_python_files if (self.root_dir / f).exists()]
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查是否包含版本号定义，但不是Python版本或目标版本
                if '__version__' in content and 'python_version' not in content and 'target-version' not in content:
                    content = re.sub(
                        r'__version__\s*=\s*["\'][^"\']*["\']',
                        f'__version__ = "{new_version}"',
                        content
                    )
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"  更新 {file_path.relative_to(self.root_dir)}")
            except Exception as e:
                print(f"  ❌ 更新失败 {file_path}: {e}")
    
    def update_project_info(self):
        """更新项目信息（邮箱等）"""
        print("📧 更新项目信息...")
        
        # 统一的邮箱地址
        new_email = "shuhao_zhang@hust.edu.cn"
        
        # 查找所有需要更新的文件
        file_patterns = ["**/*.py", "**/*.toml", "**/*.md", "**/*.yml", "**/*.yaml"]
        all_files = []
        
        for pattern in file_patterns:
            all_files.extend(self.root_dir.glob(pattern))
        
        # 邮箱替换模式
        email_patterns = [
            r'shuhao\.zhang@hust\.edu\.cn',
            r'shuhaoz@student\.unimelb\.edu\.au',
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        ]
        
        updated_count = 0
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                original_content = content
                
                # 替换邮箱
                for pattern in email_patterns:
                    content = re.sub(pattern, new_email, content, flags=re.IGNORECASE)
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    updated_count += 1
                    print(f"  更新 {file_path.relative_to(self.root_dir)}")
            
            except Exception:
                continue  # 跳过无法处理的文件
        
        print(f"✅ 项目信息更新完成，共更新 {updated_count} 个文件")

def sync_python_versions():
    """同步Python版本配置"""
    print("🐍 同步Python版本配置...")
    
    try:
        # 导入并运行Python版本同步工具
        from sync_python_versions import PythonVersionSyncer
        syncer = PythonVersionSyncer()
        syncer.sync_all()
    except Exception as e:
        print(f"❌ Python版本同步失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="SAGE 版本管理器 - 统一工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # show命令
    subparsers.add_parser('show', help='显示当前版本信息')
    
    # set命令
    set_parser = subparsers.add_parser('set', help='设置新版本号')
    set_parser.add_argument('version', help='新版本号，如: 0.2.0')
    
    # update-info命令
    subparsers.add_parser('update-info', help='更新项目信息（邮箱等）')
    
    # sync-python命令
    subparsers.add_parser('sync-python', help='同步Python版本配置')
    
    # show-python命令
    subparsers.add_parser('show-python', help='显示Python版本配置')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        manager = SAGEVersionManager()
        
        if args.command == 'show':
            return 0 if manager.show_version() else 1
        
        elif args.command == 'set':
            return 0 if manager.set_version(args.version) else 1
        
        elif args.command == 'update-info':
            manager.update_project_info()
            return 0
        
        elif args.command == 'sync-python':
            sync_python_versions()
            return 0
        
        elif args.command == 'show-python':
            from python_config import get_python_config
            config = get_python_config()
            config.show_config()
            return 0
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
