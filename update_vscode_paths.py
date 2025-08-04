#!/usr/bin/env python3
"""
自动更新VS Code settings.json中的Python路径配置
扫描packages目录下所有包含pyproject.toml的包，并添加其src路径到Python分析路径中
"""

import os
import json
import glob
from pathlib import Path
from typing import List, Dict, Any


def find_packages_with_pyproject() -> List[str]:
    """
    递归搜索packages目录下所有包含pyproject.toml的包
    返回相对于工作区根目录的src路径列表
    """
    packages_dir = Path("packages")
    if not packages_dir.exists():
        print("Warning: packages directory not found")
        return []
    
    src_paths = []
    
    # 使用glob递归搜索所有pyproject.toml文件
    pyproject_files = glob.glob("packages/**/pyproject.toml", recursive=True)
    
    for pyproject_file in pyproject_files:
        package_dir = Path(pyproject_file).parent
        potential_src = package_dir / "src"
        
        if potential_src.exists():
            # 转换为相对路径字符串，使用正斜杠
            relative_path = f"./{potential_src.as_posix()}"
            src_paths.append(relative_path)
            print(f"Found package with src: {relative_path}")
        else:
            print(f"Package found but no src directory: {package_dir}")
    
    return sorted(src_paths)


def load_vscode_settings() -> Dict[str, Any]:
    """加载当前的VS Code settings.json"""
    settings_file = Path(".vscode/settings.json")
    
    if not settings_file.exists():
        print("Creating new .vscode/settings.json")
        settings_file.parent.mkdir(exist_ok=True)
        return {}
    
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 简单处理注释（这不是完整的JSON-C解析器，但对于基本情况足够）
            lines = content.split('\n')
            clean_lines = []
            for line in lines:
                # 移除行注释
                if '//' in line:
                    line = line[:line.index('//')]
                clean_lines.append(line)
            clean_content = '\n'.join(clean_lines)
            
            return json.loads(clean_content)
    except json.JSONDecodeError as e:
        print(f"Error parsing settings.json: {e}")
        print("Creating backup and starting fresh")
        settings_file.rename(settings_file.with_suffix('.json.backup'))
        return {}


def update_python_paths(settings: Dict[str, Any], src_paths: List[str]) -> Dict[str, Any]:
    """更新Python路径配置"""
    # 添加当前目录
    all_paths = src_paths + ["."]
    
    # 更新python.analysis.extraPaths
    settings["python.analysis.extraPaths"] = all_paths
    
    # 更新python.autoComplete.extraPaths  
    settings["python.autoComplete.extraPaths"] = all_paths
    
    # 确保其他重要的Python设置存在
    settings.setdefault("python.analysis.autoSearchPaths", True)
    settings.setdefault("python.analysis.useLibraryCodeForTypes", True)
    settings.setdefault("python.analysis.autoImportCompletions", True)
    settings.setdefault("pylance.insidersChannel", "off")
    settings.setdefault("python.languageServer", "Pylance")
    settings.setdefault("python.analysis.typeCheckingMode", "off")
    settings.setdefault("python.defaultInterpreterPath", "/usr/bin/python3")
    
    return settings


def save_vscode_settings(settings: Dict[str, Any]) -> None:
    """保存VS Code settings.json"""
    settings_file = Path(".vscode/settings.json")
    settings_file.parent.mkdir(exist_ok=True)
    
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    
    print(f"Updated {settings_file}")


def main():
    """主函数"""
    print("Scanning packages directory for Python packages...")
    
    # 扫描所有包
    src_paths = find_packages_with_pyproject()
    
    if not src_paths:
        print("No packages with src directories found")
        return
    
    print(f"\nFound {len(src_paths)} packages with src directories:")
    for path in src_paths:
        print(f"  - {path}")
    
    # 加载当前设置
    print("\nLoading current VS Code settings...")
    settings = load_vscode_settings()
    
    # 更新Python路径
    print("Updating Python paths...")
    updated_settings = update_python_paths(settings, src_paths)
    
    # 保存设置
    save_vscode_settings(updated_settings)
    
    print("\n✅ VS Code settings updated successfully!")
    print("\nPython analysis paths:")
    for path in updated_settings.get("python.analysis.extraPaths", []):
        print(f"  - {path}")


if __name__ == "__main__":
    main()
