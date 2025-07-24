#!/usr/bin/env python3
"""
本地智能测试运行器 - 方便在本地快速测试代码变化

使用方法:
- python run_smart_tests_local.py                 # 测试相对于HEAD~1的变化
- python run_smart_tests_local.py --base main     # 测试相对于main分支的变化
- python run_smart_tests_local.py --base HEAD~5   # 测试相对于HEAD~5的变化
"""

import subprocess
import sys
from pathlib import Path

def main():
    script_path = Path(__file__).parent / "scripts" / "smart_test_runner.py"
    
    # 将所有参数传递给智能测试运行器
    cmd = [sys.executable, str(script_path)] + sys.argv[1:]
    
    print("🚀 启动本地智能测试...")
    print(f"📝 运行命令: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
