#!/usr/bin/env python3
"""
清理重构后不需要的旧文件
"""

from pathlib import Path
import shutil


def cleanup_old_files():
    """清理旧的命令文件"""
    commands_dir = Path(__file__).parent / "src/sage_dev_toolkit/cli/commands"
    
    # 需要删除的旧文件
    old_files = [
        "core.py",
        "maintenance.py", 
        "development.py",
        "commercial.py",
        "reporting.py",
        "package_mgmt.py",
        "package_mgmt.py.backup"
    ]
    
    print("🧹 清理旧的命令文件...")
    
    for file_name in old_files:
        file_path = commands_dir / file_name
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"✅ 删除: {file_name}")
            except Exception as e:
                print(f"❌ 删除失败 {file_name}: {e}")
        else:
            print(f"⚠️  文件不存在: {file_name}")
    
    # 清理 __pycache__ 
    pycache_dir = commands_dir / "__pycache__"
    if pycache_dir.exists():
        try:
            shutil.rmtree(pycache_dir)
            print("✅ 删除: __pycache__ 目录")
        except Exception as e:
            print(f"❌ 删除 __pycache__ 失败: {e}")
    
    print("🎉 清理完成!")


if __name__ == "__main__":
    cleanup_old_files()
