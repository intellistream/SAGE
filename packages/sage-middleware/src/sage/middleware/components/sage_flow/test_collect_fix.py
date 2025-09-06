#!/usr/bin/env python3
"""
测试DataStream::collect()方法的修复
"""

import sys
import os

try:
    import sage_flow as sf

    # 创建环境
    env = sf.Environment("test_collect")

    # 创建DataStream
    stream = env.create_datastream()

    # 创建一些测试数据
    test_data = [
        {"id": "1", "name": "Alice", "age": 25},
        {"id": "2", "name": "Bob", "age": 30},
        {"id": "3", "name": "Charlie", "age": 35}
    ]

    # 使用from_list创建流
    stream = sf.from_list(test_data)

    # 测试collect方法
    results = stream.collect()

    print(f"收集到 {len(results)} 条消息:")
    for i, msg in enumerate(results):
        print(f"消息 {i+1}: UID={msg.get_uid()}, 内容类型={msg.get_content_type()}")
        content = msg.get_content_as_string()
        print(f"  内容: {content}")

    # 验证结果
    if len(results) == len(test_data):
        print("✅ collect()方法修复成功！正确收集了所有消息。")
    else:
        print(f"❌ collect()方法仍有问题。期望 {len(test_data)} 条消息，实际得到 {len(results)} 条。")

except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保项目已正确构建且Python绑定可用。")
except Exception as e:
    print(f"测试过程中发生错误: {e}")
    import traceback
    traceback.print_exc()