#!/usr/bin/env python3
"""
Post-install hook for SAGE Extensions
确保编译好的 .so 文件在正确位置
"""

import os
import sys
import shutil
from pathlib import Path


def find_sage_extensions_install_path():
    """查找 sage-extensions 的安装路径"""
    try:
        import sage.extensions
        return Path(sage.extensions.__file__).parent
    except ImportError:
        # 如果导入失败，尝试从 site-packages 查找
        for path in sys.path:
            sage_path = Path(path) / "sage" / "extensions"
            if sage_path.exists():
                return sage_path
        return None


def copy_so_files():
    """复制 .so 文件到安装位置"""
    print("🔧 Running post-install setup for SAGE Extensions...")
    
    # 查找安装路径
    install_path = find_sage_extensions_install_path()
    if not install_path:
        print("❌ Could not find SAGE Extensions installation path")
        return False
    
    print(f"📍 Found installation at: {install_path}")
    
    # 查找构建的 .so 文件
    # 这里假设我们从项目根目录运行
    project_root = Path(__file__).parent.parent
    source_locations = [
        project_root / "src" / "sage" / "extensions" / "sage_db",
        project_root / "src" / "sage" / "extensions" / "sage_db" / "build",
        project_root / "src" / "sage" / "extensions" / "sage_db" / "python",
    ]
    
    target_dir = install_path / "sage_db"
    if not target_dir.exists():
        print(f"❌ Target directory does not exist: {target_dir}")
        return False
    
    copied_files = []
    
    for source_dir in source_locations:
        if not source_dir.exists():
            continue
            
        print(f"🔍 Searching for .so files in: {source_dir}")
        
        # 查找 .so, .pyd, .dll 文件
        for pattern in ["*.so", "*.pyd", "*.dll"]:
            for so_file in source_dir.glob(pattern):
                target_file = target_dir / so_file.name
                
                try:
                    shutil.copy2(so_file, target_file)
                    os.chmod(target_file, 0o755)
                    print(f"✓ Copied {so_file.name} → {target_file}")
                    copied_files.append(target_file)
                except Exception as e:
                    print(f"⚠ Failed to copy {so_file}: {e}")
    
    if copied_files:
        print(f"✅ Successfully copied {len(copied_files)} library files")
        
        # 测试导入
        try:
            sys.path.insert(0, str(target_dir))
            import _sage_db
            print("✓ C++ extension can be imported successfully")
            return True
        except Exception as e:
            print(f"⚠ Warning: Failed to import C++ extension: {e}")
            return False
    else:
        print("❌ No .so files found to copy")
        print("You may need to build the extensions first:")
        print("  python scripts/build.py")
        return False


def main():
    """主函数"""
    success = copy_so_files()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
