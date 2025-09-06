#!/usr/bin/env python3
"""
详细调试collect()方法的测试脚本
逐步分析每个执行步骤
"""

import sys
import os

# 设置Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

try:
    import sage_flow_datastream as sf

    print("=== 详细调试collect()方法 ===")

    # 步骤1: 创建环境
    print("步骤1: 创建环境")
    env = sf.Environment("debug_detailed")
    print("环境创建成功")

    # 步骤2: 创建简单数据
    print("步骤2: 创建测试数据")
    test_data = [{"id": "1", "name": "Debug Test"}]
    print(f"测试数据: {test_data}")

    # 步骤3: 使用from_list创建流
    print("步骤3: 使用from_list创建流")
    stream = sf.from_list(test_data)
    print("流创建成功")

    # 步骤4: 检查流的基本属性
    print("步骤4: 检查流属性")
    print(f"流对象: {stream}")
    print(f"流类型: {type(stream)}")

    # 步骤5: 手动执行collect的前置步骤
    print("步骤5: 手动执行collect的前置步骤")

    # 检查canExecute
    print("检查canExecute...")
    # 注意: 这里我们无法直接调用canExecute，因为它是私有的
    # 但我们可以尝试直接调用collect

    # 步骤6: 调用collect - 关键步骤
    print("步骤6: 调用collect() - 这是关键调试点")
    try:
        print("准备调用stream.collect()...")
        results = stream.collect()
        print(f"collect()成功完成，返回 {len(results)} 条消息")

        # 检查结果
        for i, msg in enumerate(results):
            print(f"消息 {i+1}: UID={msg.get_uid()}")
            print(f"  内容类型: {msg.get_content_type()}")
            print(f"  内容: {msg.get_content_as_string()}")

    except Exception as e:
        print(f"❌ collect()调用失败: {e}")
        import traceback
        traceback.print_exc()

        # 如果是段错误，我们应该在这里看到它
        print("注意: 如果看到段错误，说明问题出现在collect()的内部执行中")

except ImportError as e:
    print(f"导入失败: {e}")
except Exception as e:
    print(f"其他错误: {e}")
    import traceback
    traceback.print_exc()