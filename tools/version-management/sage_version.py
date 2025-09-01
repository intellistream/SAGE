#!/usr/bin/env python3
"""
SAGE版本管理工具 - 动态版本加载时代的简化版本

在动态版本加载系统下，这个工具的主要功能：
1. 设置版本号：只需更新 _version.py，所有包会自动动态加载
2. 显示版本信息：查看当前项目的版本和元数据
3. 更新项目信息：统一更新邮箱、项目名称等元数据
4. 一致性检查：确保项目信息在各文件中保持一致

注意：不再需要手动更新 96 个 __init__.py 文件，动态加载会自动处理！
"""

import re
import argparse
import yaml
from pathlib import Path
from typing import Dict, List, Any


# 配置文件 - 可扩展的项目信息管理
PROJECT_CONFIG = {
    # 正确的项目信息
    "correct_info": {
        "project_name": "SAGE",
        "project_full_name": "Streaming-Augmented Generative Execution",
        "email": "shuhao_zhang@hust.edu.cn",
        "author": "SAGE Team",
        "homepage": "https://github.com/intellistream/SAGE",
        "repository": "https://github.com/intellistream/SAGE",
        "documentation": "https://intellistream.github.io/SAGE-Pub/"
    },
    
    # 需要修复的错误信息 - 可以随时添加新的
    "incorrect_patterns": {
        "project_descriptions": [
            "Intelligent Stream Analytics Gateway Engine",
            "intelligent stream analytics gateway engine",
            "Stream Analytics Gateway Engine",
            "智能流分析网关引擎",
        ],
        "emails": [
            "shuhaoz@student.unimelb.edu.au",
            "sage@intellistream.com",
            "admin@sage.com",
        ],
        "urls": [
            "https://sage-docs.old.com",
            "https://old-sage.github.io",
        ]
    },
    
    # 文件类型和搜索模式
    "file_patterns": [
        "**/*.py",
        "**/*.toml", 
        "**/*.md",
        "**/*.yml",
        "**/*.yaml",
        "**/*.txt",
        "**/*.rst"
    ],
    
    # 排除的路径模式
    "exclude_patterns": [
        "**/.*",  # 隐藏文件
        "**/node_modules/**",
        "**/venv/**",
        "**/env/**", 
        "**/__pycache__/**",
        "**/build/**",
        "**/dist/**",
        "**/logs/**",
        "**/output/**"
    ]
}


class SAGEVersionManager:
    """SAGE项目版本管理器"""
    
    def __init__(self, config_file=None):
        self.root_dir = self._find_sage_root()
        self.version_file = self.root_dir / "_version.py"
        self.config = self._load_config(config_file)
    
    def _load_config(self, config_file):
        """加载配置，支持自定义配置文件"""
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                        import yaml
                        return yaml.safe_load(f)
                    else:
                        # 假设是Python配置文件
                        config_globals = {}
                        exec(f.read(), config_globals)
                        return config_globals.get('PROJECT_CONFIG', PROJECT_CONFIG)
            except Exception as e:
                print(f"⚠️ 无法加载配置文件 {config_file}: {e}")
                print("使用默认配置...")
        
        return PROJECT_CONFIG
    
    def _should_exclude_path(self, file_path):
        """检查路径是否应该被排除"""
        path_str = str(file_path)
        for pattern in self.config.get("exclude_patterns", []):
            if file_path.match(pattern):
                return True
        return False
    
    def _get_all_files(self):
        """获取所有需要检查的文件"""
        all_files = []
        for pattern in self.config.get("file_patterns", ["**/*.py"]):
            files = list(self.root_dir.glob(pattern))
            for file_path in files:
                if not self._should_exclude_path(file_path.relative_to(self.root_dir)):
                    all_files.append(file_path)
        return all_files
    
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
        """设置新版本号 - 现在只需要更新 _version.py，其他文件会动态加载"""
        # 验证版本号格式
        if not re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9-]+)?$', new_version):
            print("❌ 版本号格式错误！应该类似: 1.0.0 或 1.0.0-alpha")
            return False
        
        print(f"🚀 设置新版本号: {new_version}")
        
        # 只需要更新 _version.py（主要版本文件）
        # 所有其他文件会通过动态加载自动获取新版本
        self._update_version_file(new_version)
        
        # 可选：更新 pyproject.toml 文件（如果需要的话）
        self._update_pyproject_files(new_version)
        
        print(f"✅ 版本号已更新到 {new_version}")
        print("💡 提示：所有 Python 包现在会动态加载这个版本号，无需手动更新")
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
    
    def update_project_info(self):
        """更新项目信息（邮箱、项目名称等）"""
        print("📧 更新项目信息...")
        
        # 获取当前正确的项目信息
        try:
            info = self.get_version_info()
            correct_project_name = info['project_name']  # SAGE
            correct_full_name = info['project_full_name']  # Streaming-Augmented Generative Execution
        except:
            correct_project_name = "SAGE"
            correct_full_name = "Streaming-Augmented Generative Execution"
        
        # 统一的邮箱地址
        new_email = "shuhao_zhang@hust.edu.cn"
        
        # 查找所有需要更新的文件
        file_patterns = ["**/*.py", "**/*.toml", "**/*.md", "**/*.yml", "**/*.yaml"]
        all_files = []
        
        for pattern in file_patterns:
            all_files.extend(self.root_dir.glob(pattern))
        
        # 错误的项目名称描述
        wrong_descriptions = [
            "Streaming-Augmented Generative Execution",
            "Streaming-Augmented Generative Execution",
        ]
        
        # 邮箱替换模式
        email_patterns = [
            r'shuhaoz@student\.unimelb\.edu\.au',
            r'sage@intellistream\.com',
        ]
        
        updated_count = 0
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                original_content = content
                
                # 替换错误的项目描述
                for wrong_desc in wrong_descriptions:
                    content = content.replace(wrong_desc, correct_full_name)
                
                # 替换邮箱（但保留正确的邮箱）
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
        
        # 额外检查并报告仍存在问题的文件
        self._check_remaining_issues()
    
    def _check_remaining_issues(self):
        """检查项目中仍存在的问题"""
        print("\n🔍 检查剩余问题...")
        
        # 要检查的错误内容
        issues_to_check = [
            "Streaming-Augmented Generative Execution",
            "Streaming-Augmented Generative Execution",
            "shuhao_zhang@hust.edu.cn",
            "shuhao_zhang@hust.edu.cn"
        ]
        
        file_patterns = ["**/*.py", "**/*.toml", "**/*.md", "**/*.yml", "**/*.yaml"]
        all_files = []
        
        for pattern in file_patterns:
            all_files.extend(self.root_dir.glob(pattern))
        
        issues_found = {}
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                for issue in issues_to_check:
                    if issue in content:
                        if issue not in issues_found:
                            issues_found[issue] = []
                        issues_found[issue].append(file_path.relative_to(self.root_dir))
            
            except Exception:
                continue
        
        if issues_found:
            print("⚠️  发现剩余问题:")
            for issue, files in issues_found.items():
                print(f"  📝 '{issue}' 在以下文件中:")
                for file_path in files:
                    print(f"    - {file_path}")
        else:
            print("✅ 未发现剩余问题")
    
    def check_project_consistency(self):
        """检查项目一致性"""
        print("🔍 检查项目信息一致性...")
        
        issues_found = []
        
        # 检查错误的项目名称描述
        wrong_descriptions = [
            "Streaming-Augmented Generative Execution",
            "Streaming-Augmented Generative Execution",
        ]
        
        # 检查错误的邮箱
        wrong_emails = [
            "shuhao_zhang@hust.edu.cn",
            "shuhao_zhang@hust.edu.cn"
        ]
        
        file_patterns = ["**/*.py", "**/*.toml", "**/*.md"]
        all_files = []
        
        for pattern in file_patterns:
            all_files.extend(self.root_dir.glob(pattern))
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                file_issues = []
                
                # 检查项目描述
                for wrong_desc in wrong_descriptions:
                    if wrong_desc in content:
                        file_issues.append(f"错误的项目描述: '{wrong_desc}'")
                
                # 检查邮箱
                for wrong_email in wrong_emails:
                    if wrong_email in content:
                        file_issues.append(f"错误的邮箱: '{wrong_email}'")
                
                if file_issues:
                    issues_found.append({
                        'file': file_path.relative_to(self.root_dir),
                        'issues': file_issues
                    })
            
            except Exception:
                continue
        
        if issues_found:
            print("⚠️  发现一致性问题:")
            for item in issues_found:
                print(f"📁 {item['file']}:")
                for issue in item['issues']:
                    print(f"  - {issue}")
            return False
        else:
            print("✅ 项目信息一致性良好")
            return True
        
        # 额外检查并报告仍存在问题的文件
        self._check_remaining_issues()


def main():
    parser = argparse.ArgumentParser(description="SAGE 版本管理器 - 动态版本加载时代的简化工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # show命令
    subparsers.add_parser('show', help='显示当前版本信息')
    
    # set命令
    set_parser = subparsers.add_parser('set', help='设置新版本号（自动更新 _version.py）')
    set_parser.add_argument('version', help='新版本号，如: 0.2.0')
    
    # update-info命令
    subparsers.add_parser('update-info', help='更新项目信息（邮箱、项目名称等）')
    
    # check命令
    subparsers.add_parser('check', help='检查项目信息一致性')
    
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
        
        elif args.command == 'check':
            return 0 if manager.check_project_consistency() else 1
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
