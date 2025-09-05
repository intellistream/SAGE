#!/usr/bin/env python3
"""
简单的SAGE Flow测试
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    import sage_flow_datastream as sfd
    print("✓ Module imported successfully")

    # 测试基本功能
    env = sfd.Environment("simple_test")
    print("✓ Environment created")

    stream = env.create_datastream()
    print("✓ DataStream created")

    print("All basic tests passed!")

except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()