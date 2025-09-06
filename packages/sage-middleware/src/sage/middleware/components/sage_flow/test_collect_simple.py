#!/usr/bin/env python3
"""
简化测试脚本 - 直接测试collect()方法中的段错误
"""

import sys
import os

# 设置Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

try:
    import sage_flow_datastream as sf

    print("=== 简化collect()测试 ===")

    # 创建环境
    env = sf.Environment("test")

    # 创建简单的数据
    test_data = [{"id": "1", "name": "Test"}]

    # 使用from_list创建流
    stream = sf.from_list(test_data)

    print("流创建成功")

    # 直接调用collect - 这应该会触发段错误
    print("调用collect()...")
    results = stream.collect()

    print(f"collect()成功，返回 {len(results)} 条消息")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()