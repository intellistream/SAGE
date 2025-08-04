#!/usr/bin/env python3
"""
最终版本的VS Code settings.json Python路径更新脚本
智能扫描packages目录下所有Python包并更新路径配置
"""

import os
import json
import glob
from pathlib import Path
from typing import List, Dict, Any, Set


def find_all_python_packages() -> List[str]:
    """
    扫描packages目录下所有Python包的源码路径
    优先级：src目录 > 包含__init__.py的目录 > 包含多个.py文件的目录
    """
    packages_dir = Path("packages")
    if not packages_dir.exists():
        print("Warning: packages directory not found")
        return []
    
    src_paths = set()
    
    # 步骤1: 查找所有有pyproject.toml的包的src目录
    pyproject_files = glob.glob("packages/**/pyproject.toml", recursive=True)
    
    for pyproject_file in pyproject_files:
        package_dir = Path(pyproject_file).parent
        potential_src = package_dir / "src"
        
        if potential_src.exists():
            relative_path = f"./{potential_src.as_posix()}"
            src_paths.add(relative_path)
            print(f"✓ Package with src: {relative_path}")
    
    # 步骤2: 查找其他Python包目录
    # 特别处理tools目录下的子包
    tools_dir = packages_dir / "tools"
    if tools_dir.exists():
        for item in tools_dir.iterdir():
            if item.is_dir() and item.name != "__pycache__":
                # 检查是否有src目录
                src_dir = item / "src"
                if src_dir.exists():
                    relative_path = f"./{src_dir.as_posix()}"
                    src_paths.add(relative_path)
                    print(f"✓ Tools package with src: {relative_path}")
                # 检查是否为Python包（有__init__.py或多个.py文件）
                elif has_python_module_structure(item):
                    relative_path = f"./{item.as_posix()}"
                    src_paths.add(relative_path)
                    print(f"✓ Tools Python package: {relative_path}")
    
    # 步骤3: 查找commercial目录下的包
    commercial_dir = packages_dir / "commercial"
    if commercial_dir.exists():
        for item in commercial_dir.iterdir():
            if item.is_dir() and item.name != "__pycache__":
                src_dir = item / "src"
                if src_dir.exists():
                    relative_path = f"./{src_dir.as_posix()}"
                    src_paths.add(relative_path)
                    print(f"✓ Commercial package with src: {relative_path}")
    
    # 步骤4: 查找根级别的包
    for item in packages_dir.iterdir():
        if item.is_dir() and item.name not in ["commercial", "tools", "__pycache__"]:
            src_dir = item / "src"
            if src_dir.exists():
                relative_path = f"./{src_dir.as_posix()}"
                src_paths.add(relative_path)
                print(f"✓ Root package with src: {relative_path}")
    
    return sorted(list(src_paths))


def has_python_module_structure(directory: Path) -> bool:
    """
    检查目录是否具有Python模块结构
    """
    if not directory.is_dir():
        return False
    
    # 检查是否有__init__.py
    if (directory / "__init__.py").exists():
        return True
    
    # 检查是否有多个Python文件
    py_files = list(directory.glob("*.py"))
    return len(py_files) >= 2


def load_vscode_settings() -> Dict[str, Any]:
    """加载当前的VS Code settings.json"""
    settings_file = Path(".vscode/settings.json")
    
    if not settings_file.exists():
        print("Creating new .vscode/settings.json")
        settings_file.parent.mkdir(exist_ok=True)
        return {}
    
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing settings.json: {e}")
        print("Creating backup and starting fresh")
        backup_file = settings_file.with_name(f"{settings_file.stem}.backup{settings_file.suffix}")
        settings_file.rename(backup_file)
        return {}


def update_python_paths(settings: Dict[str, Any], src_paths: List[str]) -> Dict[str, Any]:
    """更新Python路径配置"""
    # 添加当前目录到路径列表
    all_paths = src_paths + ["."]
    
    # 更新Python分析路径
    settings["python.analysis.extraPaths"] = all_paths
    settings["python.autoComplete.extraPaths"] = all_paths
    
    # 确保关键的Python设置存在
    python_settings = {
        "python.analysis.autoSearchPaths": True,
        "python.analysis.useLibraryCodeForTypes": True,
        "python.analysis.autoImportCompletions": True,
        "pylance.insidersChannel": "off",
        "python.languageServer": "Pylance",
        "python.analysis.typeCheckingMode": "off",
        "python.defaultInterpreterPath": "/usr/bin/python3"
    }
    
    for key, value in python_settings.items():
        settings.setdefault(key, value)
    
    return settings


def save_vscode_settings(settings: Dict[str, Any]) -> None:
    """保存VS Code settings.json"""
    settings_file = Path(".vscode/settings.json")
    settings_file.parent.mkdir(exist_ok=True)
    
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Updated {settings_file}")


def main():
    """主函数"""
    print("🔍 Scanning packages directory for Python packages...\n")
    
    # 扫描所有包
    src_paths = find_all_python_packages()
    
    if not src_paths:
        print("❌ No Python packages found")
        return
    
    print(f"\n📦 Found {len(src_paths)} Python package paths:")
    for i, path in enumerate(src_paths, 1):
        print(f"   {i:2d}. {path}")
    
    # 加载和更新设置
    print("\n⚙️  Loading and updating VS Code settings...")
    settings = load_vscode_settings()
    updated_settings = update_python_paths(settings, src_paths)
    save_vscode_settings(updated_settings)
    
    print("\n🎉 VS Code Python paths updated successfully!")
    print("\n📋 Final Python analysis paths:")
    for i, path in enumerate(updated_settings.get("python.analysis.extraPaths", []), 1):
        print(f"   {i:2d}. {path}")


if __name__ == "__main__":
    main()
