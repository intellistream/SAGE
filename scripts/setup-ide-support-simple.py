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

def setup_development_links(repo_root: Path):
    """设置开发环境链接，确保IDE能正确跳转"""
    print("🔧 设置开发环境链接...")
    
    packages_dir = repo_root / 'packages'
    packages = [
        'sage-cli',
        'sage-core', 
        'sage-extensions',
        'sage-frontend',
        'sage-lib',
        'sage-plugins',
        'sage-service',
        'sage-utils'
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
        package_path = packages_dir / package
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

def create_vscode_settings(repo_root: Path):
    """创建VS Code设置，优化Python路径解析"""
    print("⚙️  配置VS Code设置...")
    
    vscode_dir = repo_root / '.vscode'
    vscode_dir.mkdir(exist_ok=True)
    
    packages_dir = repo_root / 'packages'
    python_paths = [
        str(packages_dir / 'sage-core' / 'src'),
        str(packages_dir / 'sage-utils' / 'src'),
        str(packages_dir / 'sage-extensions' / 'src'),
        str(packages_dir / 'sage-cli' / 'src'),
        str(packages_dir / 'sage-lib' / 'src'),
        str(packages_dir / 'sage-plugins' / 'src'),
        str(packages_dir / 'sage-service' / 'src'),
        str(packages_dir / 'sage-frontend'),  # 这个包没有src目录
        str(repo_root),
    ]
    
    settings = {
        "python.analysis.extraPaths": python_paths,
        "python.autoComplete.extraPaths": python_paths,
        "python.analysis.autoSearchPaths": True,
        "python.analysis.useLibraryCodeForTypes": True,
        "python.analysis.autoImportCompletions": True,
        "pylance.insidersChannel": "off",
        "python.languageServer": "Pylance",
        "python.analysis.typeCheckingMode": "basic",
        "python.defaultInterpreterPath": sys.executable,
    }
    
    settings_file = vscode_dir / 'settings.json'
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
    
    print(f"✅ VS Code设置已保存到: {settings_file}")

def verify_imports():
    """验证导入是否正常工作"""
    print("🧪 验证导入功能...")
    
    test_imports = [
        "import sage.utils",
        "from sage.utils.config_loader import load_config", 
        "from sage.utils.logger.custom_logger import CustomLogger",
    ]
    
    for import_stmt in test_imports:
        try:
            exec(import_stmt)
            print(f"✅ {import_stmt}")
        except ImportError as e:
            print(f"❌ {import_stmt} - Error: {e}")
        except Exception as e:
            print(f"⚠️  {import_stmt} - Warning: {e}")

def main():
    repo_root = Path(__file__).parent.parent
    
    print("🚀 设置IDE支持...")
    print("=" * 60)
    
    try:
        setup_development_links(repo_root)
        create_vscode_settings(repo_root)
        verify_imports()
        
        print("=" * 60)
        print("🎉 IDE支持设置完成！")
        print()
        print("📋 接下来的步骤:")
        print("1. 重启VS Code以加载新配置")
        print("2. 在VS Code中选择正确的Python解释器")
        print("3. 测试代码跳转功能 (Ctrl+Click 或 F12)")
        
    except Exception as e:
        print(f"❌ 设置过程中出现错误: {e}")
        raise

if __name__ == "__main__":
    main()
