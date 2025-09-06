#!/usr/bin/env python3
"""
测试Python绑定的基本功能
"""

import sys
import os

# 设置Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

try:
    import sage_flow_datastream as sf

    print("=== 测试Python绑定基本功能 ===")

    # 测试1: 创建MultiModalMessage
    print("测试1: 创建MultiModalMessage")
    msg = sf.MultiModalMessage(1, sf.ContentType.TEXT, "Hello World")
    print(f"消息UID: {msg.get_uid()}")
    print(f"消息内容: {msg.get_content_as_string()}")

    # 测试2: 创建DataStream (使用from_list)
    print("\n测试2: 创建DataStream")
    test_data = [{"id": "1", "name": "Test"}]
    stream = sf.from_list(test_data)
    print("DataStream创建成功")

    # 测试3: 测试from_list函数
    print("\n测试3: 测试from_list函数")
    test_data = [{"id": "1", "name": "Test"}]
    stream2 = sf.from_list(test_data)
    print("from_list创建成功")

    print("\n✅ Python绑定基本功能测试通过")

except ImportError as e:
    print(f"导入失败: {e}")
except Exception as e:
    print(f"其他错误: {e}")
    import traceback
    traceback.print_exc()