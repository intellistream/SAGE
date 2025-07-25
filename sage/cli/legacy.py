#!/usr/bin/env python3
"""
Legacy JobManager Controller
保持向后兼容的jobmanager控制器
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    # 重定向到新的CLI工具
    from sage.cli.job import app
    
    if __name__ == "__main__":
        print("🔄 Redirecting to new SAGE CLI...")
        print("💡 Consider using 'sage job' instead of 'sage-jm' in the future")
        app()
        
except ImportError:
    print("❌ SAGE CLI not properly installed")
    print("Run: python sage/cli/setup.py")
    sys.exit(1)
