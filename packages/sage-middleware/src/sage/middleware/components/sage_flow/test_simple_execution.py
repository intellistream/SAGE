#!/usr/bin/env python3
"""
简单的DataStream执行测试，不使用collect()方法
"""

import sys
import os

# 设置Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

try:
    import sage_flow_datastream as sf

    print("=== 简单DataStream执行测试 ===")

    # 创建测试数据
    test_data = [{"id": "1", "name": "Alice"}]
    print(f"测试数据: {test_data}")

    # 使用from_list创建流
    stream = sf.from_list(test_data)
    print("流创建成功")

    # 检查流的基本属性
    print(f"操作符数量: {stream.get_operator_count()}")

    # 添加一个简单的sink操作
    def simple_sink(msg):
        print(f"收到消息: UID={msg.get_uid()}, 内容={msg.get_content_as_string()}")

    print("添加sink操作...")
    stream.sink(simple_sink)

    print("执行流...")
    stream.execute()

    print("✅ 执行成功完成")

except ImportError as e:
    print(f"导入失败: {e}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()