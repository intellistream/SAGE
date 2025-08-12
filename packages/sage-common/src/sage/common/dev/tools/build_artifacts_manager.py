"""
Build Artifacts Manager for SAGE Development Toolkit.

This module provides functionality to manage pip install artifacts and build
intermediates across the entire SAGE project, including:
- *.egg-info directories
- dist/ directories  
- __pycache__ directories
- build/ directories
- Other build artifacts

Author: SAGE Team
"""

import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
import logging


class BuildArtifactsManager:
    """Manages build artifacts and pip install intermediates."""
    
    # 默认要清理的构建产物模式
    DEFAULT_PATTERNS = {
        'egg_info': ['*.egg-info', '*egg-info'],
        'dist': ['dist'],
        'build': ['build'],
        'pycache': ['__pycache__'],
        'coverage': ['.coverage', 'coverage.xml', 'htmlcov'],
        'pytest': ['.pytest_cache'],
        'mypy': ['.mypy_cache'],
        'temp': ['*.tmp', '*.temp', '.tmp'],
        'logs': ['*.log', 'logs'],
    }
    
    # 受保护的目录（不会被清理）
    PROTECTED_PATHS = {
        '.git', '.venv', '.idea', '.vscode', 
        'node_modules', 'venv', 'env',
        '.sage'  # SAGE的配置目录
    }
    
    def __init__(self, project_root: str):
        """
        Initialize the BuildArtifactsManager.
        
        Args:
            project_root: Path to the project root directory
        """
        self.project_root = Path(project_root).resolve()
        self.logger = logging.getLogger(__name__)
        
        # 统计信息
        self.stats = {
            'total_files_removed': 0,
            'total_dirs_removed': 0,
            'total_size_freed': 0,
            'errors': []
        }
    
    def scan_artifacts(self, patterns: Optional[Dict[str, List[str]]] = None) -> Dict[str, List[Path]]:
        """
        扫描项目中的构建产物。
        
        Args:
            patterns: 自定义扫描模式，如果为None则使用默认模式
            
        Returns:
            按类型分组的构建产物路径字典
        """
        if patterns is None:
            patterns = self.DEFAULT_PATTERNS
        
        artifacts = {category: [] for category in patterns.keys()}
        
        # 扫描整个项目目录
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            
            # 跳过受保护的目录
            if any(protected in root_path.parts for protected in self.PROTECTED_PATHS):
                continue
            
            # 检查目录模式
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    # 检查目录名是否匹配模式
                    for dir_name in dirs[:]:  # 使用切片来避免修改正在迭代的列表
                        if self._match_pattern(dir_name, pattern):
                            artifact_path = root_path / dir_name
                            artifacts[category].append(artifact_path)
                    
                    # 检查文件名是否匹配模式
                    for file_name in files:
                        if self._match_pattern(file_name, pattern):
                            artifact_path = root_path / file_name
                            artifacts[category].append(artifact_path)
        
        # 去重并排序
        for category in artifacts:
            artifacts[category] = sorted(list(set(artifacts[category])))
        
        return artifacts
    
    def _match_pattern(self, name: str, pattern: str) -> bool:
        """检查名称是否匹配模式。"""
        if '*' in pattern:
            # 简单的通配符匹配
            if pattern.startswith('*') and pattern.endswith('*'):
                return pattern[1:-1] in name
            elif pattern.startswith('*'):
                return name.endswith(pattern[1:])
            elif pattern.endswith('*'):
                return name.startswith(pattern[:-1])
            else:
                return name == pattern
        else:
            return name == pattern
    
    def calculate_size(self, path: Path) -> int:
        """计算路径的总大小。"""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            total_size = 0
            try:
                for item in path.rglob('*'):
                    if item.is_file():
                        total_size += item.stat().st_size
            except (PermissionError, OSError):
                pass
            return total_size
        return 0
    
    def get_artifacts_summary(self, artifacts: Dict[str, List[Path]]) -> Dict[str, Dict]:
        """获取构建产物的统计摘要。"""
        summary = {}
        
        for category, paths in artifacts.items():
            if not paths:
                summary[category] = {
                    'count': 0,
                    'total_size': 0,
                    'size_formatted': '0 B'
                }
                continue
            
            total_size = sum(self.calculate_size(path) for path in paths)
            
            summary[category] = {
                'count': len(paths),
                'total_size': total_size,
                'size_formatted': self._format_size(total_size),
                'paths': [str(path.relative_to(self.project_root)) for path in paths[:5]]  # 显示前5个
            }
        
        return summary
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小。"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
    
    def clean_artifacts(
        self, 
        categories: Optional[List[str]] = None,
        dry_run: bool = False,
        force: bool = False,
        older_than_days: Optional[int] = None
    ) -> Dict[str, any]:
        """
        清理构建产物。
        
        Args:
            categories: 要清理的类别列表，None表示清理所有
            dry_run: 是否只是预览而不实际删除
            force: 是否强制删除而不询问
            older_than_days: 只删除超过指定天数的文件
            
        Returns:
            清理结果统计
        """
        # 重置统计信息
        self.stats = {
            'total_files_removed': 0,
            'total_dirs_removed': 0,
            'total_size_freed': 0,
            'errors': [],
            'cleaned_categories': {}
        }
        
        # 扫描构建产物
        artifacts = self.scan_artifacts()
        
        # 过滤要清理的类别
        if categories:
            artifacts = {k: v for k, v in artifacts.items() if k in categories}
        
        # 应用时间过滤
        if older_than_days is not None:
            cutoff_time = time.time() - (older_than_days * 24 * 3600)
            for category in artifacts:
                artifacts[category] = [
                    path for path in artifacts[category]
                    if path.stat().st_mtime < cutoff_time
                ]
        
        # 执行清理
        for category, paths in artifacts.items():
            if not paths:
                continue
                
            category_stats = {
                'files_removed': 0,
                'dirs_removed': 0,
                'size_freed': 0,
                'items_cleaned': []
            }
            
            for path in paths:
                try:
                    if dry_run:
                        # 预览模式，只计算大小
                        size = self.calculate_size(path)
                        category_stats['size_freed'] += size
                        category_stats['items_cleaned'].append(str(path.relative_to(self.project_root)))
                        
                        if path.is_file():
                            category_stats['files_removed'] += 1
                        else:
                            category_stats['dirs_removed'] += 1
                    else:
                        # 实际删除
                        size = self.calculate_size(path)
                        
                        if path.is_file():
                            path.unlink()
                            category_stats['files_removed'] += 1
                        elif path.is_dir():
                            shutil.rmtree(path)
                            category_stats['dirs_removed'] += 1
                        
                        category_stats['size_freed'] += size
                        category_stats['items_cleaned'].append(str(path.relative_to(self.project_root)))
                        
                except Exception as e:
                    error_msg = f"Failed to remove {path}: {str(e)}"
                    self.stats['errors'].append(error_msg)
                    self.logger.error(error_msg)
            
            self.stats['cleaned_categories'][category] = category_stats
            self.stats['total_files_removed'] += category_stats['files_removed']
            self.stats['total_dirs_removed'] += category_stats['dirs_removed']
            self.stats['total_size_freed'] += category_stats['size_freed']
        
        return self.stats
    
    def create_cleanup_script(self, output_path: Optional[str] = None) -> str:
        """
        创建清理脚本文件。
        
        Args:
            output_path: 输出脚本的路径，None则使用默认路径
            
        Returns:
            生成的脚本文件路径
        """
        if output_path is None:
            output_path = self.project_root / "scripts" / "cleanup_build_artifacts.sh"
        
        script_path = Path(output_path)
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        script_content = f'''#!/bin/bash
# SAGE Build Artifacts Cleanup Script
# Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

set -e

PROJECT_ROOT="{self.project_root}"
cd "$PROJECT_ROOT"

echo "🧹 SAGE Build Artifacts Cleanup"
echo "================================"
echo "Project Root: $PROJECT_ROOT"
echo

# Function to show size
show_size() {{
    if command -v du >/dev/null 2>&1; then
        du -sh "$1" 2>/dev/null || echo "0"
    else
        echo "Unknown"
    fi
}}

# Function to safely remove
safe_remove() {{
    local path="$1"
    local type="$2"
    
    if [ -e "$path" ]; then
        echo "  🗑️  Removing $type: $path"
        if [ "$type" = "directory" ]; then
            rm -rf "$path"
        else
            rm -f "$path"
        fi
    fi
}}

echo "📊 Scanning for build artifacts..."

# Clean egg-info directories
echo
echo "🥚 Cleaning egg-info directories..."
find . -name "*.egg-info" -type d -not -path "./.venv/*" -not -path "./.git/*" | while read -r dir; do
    if [ -d "$dir" ]; then
        size=$(show_size "$dir")
        safe_remove "$dir" "directory"
    fi
done

# Clean dist directories  
echo
echo "📦 Cleaning dist directories..."
find . -name "dist" -type d -not -path "./.venv/*" -not -path "./.git/*" | while read -r dir; do
    if [ -d "$dir" ]; then
        size=$(show_size "$dir")
        safe_remove "$dir" "directory"
    fi
done

# Clean __pycache__ directories
echo
echo "🐍 Cleaning __pycache__ directories..."
find . -name "__pycache__" -type d -not -path "./.venv/*" -not -path "./.git/*" | while read -r dir; do
    if [ -d "$dir" ]; then
        safe_remove "$dir" "directory"
    fi
done

# Clean build directories
echo  
echo "🔨 Cleaning build directories..."
find . -name "build" -type d -not -path "./.venv/*" -not -path "./.git/*" | while read -r dir; do
    if [ -d "$dir" ]; then
        size=$(show_size "$dir")
        safe_remove "$dir" "directory"
    fi
done

# Clean coverage files
echo
echo "📊 Cleaning coverage files..."
find . -name ".coverage" -o -name "coverage.xml" -o -name "htmlcov" -type f -o -type d | while read -r item; do
    if [ -e "$item" ]; then
        if [ -d "$item" ]; then
            safe_remove "$item" "directory"
        else
            safe_remove "$item" "file"
        fi
    fi
done

# Clean pytest cache
echo
echo "🧪 Cleaning pytest cache..."
find . -name ".pytest_cache" -type d -not -path "./.venv/*" -not -path "./.git/*" | while read -r dir; do
    if [ -d "$dir" ]; then
        safe_remove "$dir" "directory"
    fi
done

echo
echo "✅ Cleanup completed!"
echo "🗑️  To see what would be removed without actually deleting, use: sage-dev clean --dry-run"
'''
        
        # 写入脚本文件
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # 设置可执行权限
        script_path.chmod(0o755)
        
        return str(script_path)
    
    def setup_gitignore_rules(self) -> Dict[str, any]:
        """
        设置或更新.gitignore规则以忽略构建产物。
        
        Returns:
            操作结果
        """
        gitignore_path = self.project_root / ".gitignore"
        
        # 要添加的规则
        rules_to_add = [
            "# Build artifacts managed by SAGE dev toolkit",
            "**/*.egg-info/",
            "**/dist/",
            "**/__pycache__/", 
            "**/build/",
            "**/.coverage",
            "**/coverage.xml",
            "**/htmlcov/",
            "**/.pytest_cache/",
            "**/.mypy_cache/",
            "**/*.tmp",
            "**/*.temp",
            "**/.tmp/",
        ]
        
        existing_rules = set()
        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                existing_rules = set(line.strip() for line in f.readlines())
        
        # 找出需要添加的新规则
        new_rules = [rule for rule in rules_to_add if rule not in existing_rules]
        
        if new_rules:
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                f.write('\n')
                for rule in new_rules:
                    f.write(f"{rule}\n")
        
        return {
            'gitignore_path': str(gitignore_path),
            'rules_added': len(new_rules),
            'new_rules': new_rules,
            'total_rules': len(rules_to_add)
        }
    
    def create_maintenance_schedule(self) -> str:
        """创建维护计划建议。"""
        return """
# SAGE Build Artifacts Maintenance Schedule

## Daily (Automated)
- Clean __pycache__ directories during development
- Remove temporary files older than 1 day

## Weekly (Recommended)  
```bash
sage-dev clean --categories pycache,temp --older-than-days 7
```

## Monthly (Deep Clean)
```bash
sage-dev clean --categories all --older-than-days 30 --dry-run
sage-dev clean --categories all --older-than-days 30
```

## Before Release
```bash
sage-dev clean --categories all --force
sage-dev clean --update-gitignore
```

## Setup Automated Cleanup
Create maintenance scripts using SAGE toolkit:

### Daily cleanup script
```bash
#!/bin/bash
# scripts/daily_cleanup.sh
sage-dev clean --categories pycache,temp --older-than-days 1 --force
```

### Weekly cleanup script  
```bash
#!/bin/bash
# scripts/weekly_cleanup.sh
sage-dev clean --categories all --older-than-days 7 --force
```

### Generate shell script
```bash
sage-dev clean --create-script
bash scripts/cleanup_build_artifacts.sh
```
"""
