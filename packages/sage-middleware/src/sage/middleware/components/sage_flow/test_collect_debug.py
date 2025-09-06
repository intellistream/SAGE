#!/usr/bin/env python3
"""
逐步调试DataStream::collect()方法的测试脚本
用于确定段错误的具体位置
"""

import sys
import os
import traceback

try:
    import sage_flow_datastream as sf

    def debug_step(step_name, step_func):
        """执行调试步骤并捕获异常"""
        print(f"\n=== {step_name} ===")
        try:
            result = step_func()
            print(f"✅ {step_name} 成功完成")
            return result
        except Exception as e:
            print(f"❌ {step_name} 失败: {e}")
            print("详细错误信息:")
            traceback.print_exc()
            return None

    def test_collect_step_by_step():
        """逐步测试collect()方法"""
        print("开始逐步调试collect()方法...")

        # 步骤1: 创建环境
        env = debug_step("创建环境", lambda: sf.Environment("debug_collect"))
        if env is None:
            return

        # 步骤2: 创建DataStream
        stream = debug_step("创建DataStream", lambda: env.create_datastream())
        if stream is None:
            return

        # 步骤3: 创建测试数据
        test_data = [
            {"id": "1", "name": "Alice", "age": 25},
            {"id": "2", "name": "Bob", "age": 30}
        ]
        print(f"创建测试数据: {len(test_data)} 条记录")

        # 步骤4: 使用from_list创建流
        stream = debug_step("使用from_list创建流", lambda: sf.from_list(test_data))
        if stream is None:
            return

        # 步骤5: 检查流状态
        debug_step("检查流状态", lambda: print(f"操作符数量: {stream.getOperatorCount()}"))

        # 步骤6: 测试collect方法 - 这是关键步骤
        print("\n=== 测试collect()方法 ===")
        try:
            print("调用stream.collect()...")
            results = stream.collect()
            print(f"✅ collect()成功，返回 {len(results)} 条消息")

            # 检查结果
            for i, msg in enumerate(results):
                print(f"消息 {i+1}: UID={msg.get_uid()}, 内容类型={msg.get_content_type()}")
                content = msg.get_content_as_string()
                print(f"  内容: {content}")

        except Exception as e:
            print(f"❌ collect()失败: {e}")
            print("这可能是段错误的位置！")
            traceback.print_exc()

    def test_simple_collect():
        """测试简化版本的collect"""
        print("\n=== 测试简化collect流程 ===")

        try:
            # 创建环境
            env = sf.Environment("simple_test")

            # 创建测试数据
            test_data = [{"id": "1", "name": "Test"}]

            # 使用from_list
            stream = sf.from_list(test_data)

            # 直接测试collect
            results = stream.collect()
            print(f"简化测试成功: {len(results)} 条消息")

        except Exception as e:
            print(f"简化测试失败: {e}")
            traceback.print_exc()

    def test_manual_collect():
        """手动模拟collect()的步骤"""
        print("\n=== 手动模拟collect()步骤 ===")

        try:
            # 步骤1: 创建流
            test_data = [{"id": "1", "name": "Manual"}]
            stream = sf.from_list(test_data)

            # 步骤2: 手动创建sink函数
            collected_messages = []

            def manual_sink(msg):
                print(f"接收到消息: UID={msg.get_uid()}")
                try:
                    cloned = msg.clone()
                    collected_messages.append(cloned)
                    print("消息克隆成功")
                except Exception as e:
                    print(f"消息克隆失败: {e}")

            # 步骤3: 添加sink
            print("添加sink...")
            stream.sink(manual_sink)

            print(f"手动收集完成，共 {len(collected_messages)} 条消息")

        except Exception as e:
            print(f"手动模拟失败: {e}")
            traceback.print_exc()

    if __name__ == "__main__":
        print("DataStream::collect() 调试测试")
        print("=" * 50)

        # 运行不同测试
        test_collect_step_by_step()
        test_simple_collect()
        test_manual_collect()

        print("\n调试测试完成")

except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保项目已正确构建且Python绑定可用。")
except Exception as e:
    print(f"测试过程中发生未知错误: {e}")
    import traceback
    traceback.print_exc()