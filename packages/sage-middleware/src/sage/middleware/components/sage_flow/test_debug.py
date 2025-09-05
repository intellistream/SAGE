#!/usr/bin/env python3
"""
简单的调试测试
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import sage_flow_datastream as sfd
    print("✓ Module imported successfully")

    # 测试基本创建
    env = sfd.Environment("debug_test")
    print("✓ Environment created")

    stream = env.create_datastream()
    print("✓ DataStream created")

    # 测试from_list
    test_data = [{"id": 1, "name": "Alice"}]
    print("Creating DataStream from list...")
    stream2 = sfd.from_list(test_data)
    print("✓ DataStream.from_list worked")

    print("All debug tests passed!")

except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()