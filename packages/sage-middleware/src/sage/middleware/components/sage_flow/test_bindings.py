#!/usr/bin/env python3
"""
测试 SAGE Flow Python 绑定
验证新添加的绑定是否符合示例需求
"""

import sys
import os
import json
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/sage-middleware/src'))

# 导入 C++ 扩展模块
import importlib.util
spec = importlib.util.spec_from_file_location(
    "sage_flow_datastream",
    os.path.join(os.path.dirname(__file__), 'build/src/python/sage_flow_datastream.cpython-313-x86_64-linux-gnu.so')
)
sfd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sfd)
print("✓ SAGE Flow C++ 模块导入成功")

def test_environment_constructor():
    """测试 sf.Environment() 构造函数"""
    print("\n=== 测试 sf.Environment() 构造函数 ===")

    try:
        # 测试字符串构造函数
        env = sfd.Environment("test_environment")
        print("✓ Environment 字符串构造函数成功")

        # 测试配置构造函数
        config = sfd.EnvironmentConfig()
        config.job_name = "test_config"
        env2 = sfd.Environment(config)
        print("✓ Environment 配置构造函数成功")

        return True
    except Exception as e:
        print(f"✗ Environment 构造函数测试失败: {e}")
        return False

def test_from_list_function():
    """测试 sf.from_list() 函数"""
    print("\n=== 测试 sf.from_list() 函数 ===")

    try:
        # 创建测试数据
        test_data = [
            {"id": 1, "name": "Alice", "value": 100},
            {"id": 2, "name": "Bob", "value": 200},
            {"id": 3, "name": "Charlie", "value": 300}
        ]

        # 测试 from_list 函数
        stream = sfd.from_list(test_data)
        print("✓ from_list 函数调用成功")

        return True
    except Exception as e:
        print(f"✗ from_list 函数测试失败: {e}")
        return False

def test_custom_function_processing():
    """测试自定义函数的数据流处理"""
    print("\n=== 测试自定义函数的数据流处理 ===")

    try:
        # 创建环境和数据流
        env = sfd.Environment("custom_function_test")
        stream = env.create_datastream()

        # 创建测试数据
        test_data = [
            {"id": 1, "name": "Alice", "value": 100, "active": True},
            {"id": 2, "name": "Bob", "value": 200, "active": False},
            {"id": 3, "name": "Charlie", "value": 300, "active": True}
        ]

        # 从列表创建数据流
        stream = sfd.from_list(test_data)

        results = []

        # 定义自定义过滤函数
        def filter_active(item):
            """过滤活跃项目"""
            data = json.loads(item.get_content_as_string())
            return data.get("active", False)

        # 定义自定义映射函数
        def map_add_timestamp(item):
            """添加时间戳"""
            data = json.loads(item.get_content_as_string())
            data["processed_at"] = "2025-01-01T00:00:00Z"
            data["processed"] = True

            # 创建新消息
            new_content = json.dumps(data)
            return sfd.create_text_message(item.get_uid(), new_content)

        # 定义自定义 sink 函数
        def collect_results(item):
            """收集结果"""
            content = item.get_content_as_string()
            data = json.loads(content)
            results.append(data)

        # 测试链式调用
        print("  测试链式调用: filter -> map -> sink")
        stream.filter(filter_active).map(map_add_timestamp).sink(collect_results)

        print(f"✓ 自定义函数处理完成，处理了 {len(results)} 条记录")

        # 验证结果
        if len(results) == 2:  # Alice 和 Charlie
            print("✓ 过滤函数工作正常")
            if all(r.get("processed") for r in results):
                print("✓ 映射函数工作正常")
                return True
            else:
                print("✗ 映射函数未正确添加 processed 字段")
                return False
        else:
            print(f"✗ 过滤函数返回了 {len(results)} 条记录，期望 2 条")
            return False

    except Exception as e:
        print(f"✗ 自定义函数处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("SAGE Flow Python 绑定测试")
    print("=" * 50)

    tests = [
        ("Environment 构造函数", test_environment_constructor),
        ("from_list 函数", test_from_list_function),
        ("自定义函数数据流处理", test_custom_function_processing)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n执行测试: {test_name}")
        if test_func():
            passed += 1
            print(f"✓ {test_name} 测试通过")
        else:
            print(f"✗ {test_name} 测试失败")

    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！Python 绑定符合示例需求。")
        return True
    else:
        print("❌ 部分测试失败，需要进一步调试。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)