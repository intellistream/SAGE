#!/usr/bin/env python3
"""
最终调试collect()方法的测试脚本
使用正确的Python绑定
"""

import sys
import os

# 设置Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

try:
    import sage_flow_datastream as sf

    print("=== 最终collect()调试测试 ===")

    # 步骤1: 创建测试数据
    print("步骤1: 创建测试数据")
    test_data = [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
    print(f"测试数据: {test_data}")

    # 步骤2: 使用from_list创建流
    print("步骤2: 使用from_list创建流")
    stream = sf.from_list(test_data)
    print("流创建成功")

    # 步骤3: 检查流的基本属性
    print("步骤3: 检查流属性")
    print(f"操作符数量: {stream.get_operator_count()}")

    # 步骤4: 调用collect - 关键测试
    print("步骤4: 调用collect() - 关键测试点")
    try:
        print("正在调用stream.collect()...")
        results = stream.collect()
        print(f"✅ collect()成功完成，返回 {len(results)} 条消息")

        # 检查结果
        for i, msg in enumerate(results):
            print(f"消息 {i+1}: UID={msg.get_uid()}")
            print(f"  内容类型: {msg.get_content_type()}")
            print(f"  内容: {msg.get_content_as_string()}")

        print("\n🎉 测试成功！collect()方法工作正常")

    except Exception as e:
        print(f"❌ collect()调用失败: {e}")
        print("错误类型:", type(e).__name__)
        import traceback
        traceback.print_exc()

        # 分析可能的段错误原因
        print("\n=== 调试信息 ===")
        print("如果看到段错误，可能是以下原因:")
        print("1. C++对象生命周期问题")
        print("2. Python绑定中的内存管理问题")
        print("3. lambda回调中的this指针问题")
        print("4. shared_ptr引用计数问题")

except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保项目已正确构建且Python绑定可用。")
except Exception as e:
    print(f"其他错误: {e}")
    import traceback
    traceback.print_exc()