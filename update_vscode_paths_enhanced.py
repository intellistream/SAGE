#!/usr/bin/env python3
"""
增强版VS Code settings.json Python路径更新脚本
扫描packages目录下所有Python包，不仅限于有pyproject.toml的包
"""

import os
import json
import glob
from pathlib import Path
from typing import List, Dict, Any, Set


def find_all_python_packages() -> List[str]:
    """
    扫描packages目录下所有Python包的源码路径
    包括有pyproject.toml的包和其他包含Python代码的目录
    """
    packages_dir = Path("packages")
    if not packages_dir.exists():
        print("Warning: packages directory not found")
        return []
    
    src_paths = set()
    
    # 方法1: 查找有pyproject.toml的包
    pyproject_files = glob.glob("packages/**/pyproject.toml", recursive=True)
    
    for pyproject_file in pyproject_files:
        package_dir = Path(pyproject_file).parent
        potential_src = package_dir / "src"
        
        if potential_src.exists():
            relative_path = f"./{potential_src.as_posix()}"
            src_paths.add(relative_path)
            print(f"Found package with pyproject.toml and src: {relative_path}")
    
    # 方法2: 查找其他有Python文件的目录结构
    # 查找所有packages下的Python文件
    python_files = glob.glob("packages/**/*.py", recursive=True)
    
    for py_file in python_files:
        py_path = Path(py_file)
        
        # 查找可能的包根目录
        parts = py_path.parts
        if len(parts) >= 3:  # packages, package_name, ...
            # 检查是否在src目录下
            if 'src' in parts:
                src_index = parts.index('src')
                if src_index >= 2:  # packages/package_name/src/...
                    src_dir_path = Path(*parts[:src_index+1])
                    relative_path = f"./{src_dir_path.as_posix()}"
                    if src_dir_path.exists():
                        src_paths.add(relative_path)
            else:
                # 如果没有src目录，检查是否应该添加包根目录
                package_root = Path(parts[0]) / parts[1]  # packages/package_name
                if package_root.exists() and has_python_module_structure(package_root):
                    relative_path = f"./{package_root.as_posix()}"
                    src_paths.add(relative_path)
                    print(f"Found Python package without src: {relative_path}")
    
    return sorted(list(src_paths))


def has_python_module_structure(directory: Path) -> bool:
    """
    检查目录是否具有Python模块结构
    (包含__init__.py文件或多个.py文件)
    """
    if not directory.is_dir():
        return False
    
    py_files = list(directory.glob("*.py"))
    init_file = directory / "__init__.py"
    
    # 如果有__init__.py或者有多个Python文件，认为是Python包
    return init_file.exists() or len(py_files) >= 2


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
            # 简单处理注释
            lines = content.split('\n')
            clean_lines = []
            for line in lines:
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
    print("Scanning packages directory for all Python packages...")
    
    # 扫描所有包
    src_paths = find_all_python_packages()
    
    if not src_paths:
        print("No Python packages found")
        return
    
    print(f"\nFound {len(src_paths)} Python package paths:")
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
