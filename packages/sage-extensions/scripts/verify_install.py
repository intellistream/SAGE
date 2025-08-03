#!/usr/bin/env python3
"""
SAGE Extensions 安装后验证脚本
"""

import sys
import os
from pathlib import Path


def main():
    """验证安装"""
    print("Verifying SAGE Extensions installation...")
    print("=" * 50)
    
    # 设置库路径
    import os
    sage_db_dir = os.path.join(os.path.dirname(__file__), "..", "src", "sage", "extensions", "sage_db")
    if "LD_LIBRARY_PATH" in os.environ:
        os.environ["LD_LIBRARY_PATH"] = f"{sage_db_dir}:{os.environ['LD_LIBRARY_PATH']}"
    else:
        os.environ["LD_LIBRARY_PATH"] = sage_db_dir
    
    # 测试基本导入
    try:
        import sage.extensions
        print("✓ Basic import successful")
        
        # 检查扩展状态
        status = sage.extensions.get_extension_status()
        print(f"Extension status: {status}")
        
        if sage.extensions.check_extensions():
            print("✅ All extensions loaded successfully!")
        else:
            print("⚠ Some extensions failed to load")
            
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return 1
    
    # 运行更详细的测试
    test_script = Path(__file__).parent / "test_install.py"
    if test_script.exists():
        print("\nRunning detailed tests...")
        import subprocess
        result = subprocess.run([sys.executable, str(test_script)])
        return result.returncode
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
