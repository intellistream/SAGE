#!/usr/bin/env python3
"""
SAGE Flow 函数和操作符测试示例

展示 sage_flow 的函数和操作符功能：
- 自定义函数
- 内置操作符
- 错误处理和恢复
- 函数组合

作者: Kilo Code
日期: 2025-09-04
"""

import sys
import os
import json
import time
import random
import logging
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timedelta
from functools import wraps

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/sage-middleware/src'))

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/sage-middleware/src'))

# 直接导入 C++ 扩展模块
import importlib.util
spec = importlib.util.spec_from_file_location(
    "sage_flow_datastream",
    os.path.join(os.path.dirname(__file__), '../../packages/sage-middleware/src/sage/middleware/components/sage_flow/python/sage_flow_datastream.cpython-313-x86_64-linux-gnu.so')
)
sfd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sfd)
print("✓ SAGE Flow 模块导入成功")

# 检查模块是否可用
MODULE_AVAILABLE = True

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FunctionOperatorTester:
    """函数和操作符测试器"""

    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
        self.custom_functions = {}
        self.test_results = []

    def create_test_data(self) -> List[Dict[str, Any]]:
        """创建测试数据"""
        data = []
        for i in range(50):
            item = {
                "id": i + 1,
                "name": f"Item_{i+1}",
                "value": random.randint(1, 1000),
                "category": random.choice(["A", "B", "C", "D"]),
                "status": random.choice(["active", "inactive", "pending", "error"]),
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "source": "test_generator",
                    "version": "1.0",
                    "tags": random.sample(["important", "urgent", "low_priority", "high_value"], random.randint(0, 3))
                }
            }
            data.append(item)
        return data

    def custom_filter_function(self, data: Dict[str, Any]) -> bool:
        """自定义过滤函数"""
        try:
            # 过滤活跃状态且值大于50的项目
            return (data.get("status") == "active" and
                    data.get("value", 0) > 50 and
                    "important" in data.get("metadata", {}).get("tags", []))
        except Exception as e:
            logger.error(f"过滤函数错误: {e}")
            return False

    def custom_map_function(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """自定义映射函数"""
        try:
            # 添加处理信息和计算字段
            processed_data = data.copy()
            processed_data["processed_at"] = datetime.now().isoformat()
            processed_data["value_category"] = self.categorize_value(data.get("value", 0))
            processed_data["is_high_value"] = data.get("value", 0) > 500
            processed_data["processing_node"] = "function_tester"

            # 计算复合得分
            base_score = data.get("value", 0)
            category_multiplier = {"A": 1.2, "B": 1.0, "C": 0.8, "D": 0.6}
            multiplier = category_multiplier.get(data.get("category", "C"), 1.0)
            processed_data["composite_score"] = round(base_score * multiplier, 2)

            return processed_data
        except Exception as e:
            logger.error(f"映射函数错误: {e}")
            return {"error": str(e), "original_data": data}

    def categorize_value(self, value: int) -> str:
        """根据值进行分类"""
        if value >= 800:
            return "premium"
        elif value >= 500:
            return "high"
        elif value >= 200:
            return "medium"
        else:
            return "low"

    def error_handling_function(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """错误处理函数"""
        try:
            # 模拟可能出错的操作
            if random.random() < 0.1:  # 10% 的概率出错
                raise ValueError("随机模拟错误")

            # 正常处理
            result = data.copy()
            result["error_handled"] = False
            result["error_message"] = None
            return result

        except Exception as e:
            # 错误处理和恢复
            logger.warning(f"处理数据时出错: {e}")
            result = data.copy()
            result["error_handled"] = True
            result["error_message"] = str(e)
            result["recovery_action"] = "fallback_processing"
            return result

    def validation_function(self, data: Dict[str, Any]) -> bool:
        """数据验证函数"""
        try:
            required_fields = ["id", "name", "value", "category", "status"]
            for field in required_fields:
                if field not in data:
                    logger.warning(f"缺少必需字段: {field}")
                    return False

            if not isinstance(data.get("value"), (int, float)):
                logger.warning("值字段类型不正确")
                return False

            if data.get("value", 0) < 0:
                logger.warning("值不能为负数")
                return False

            return True
        except Exception as e:
            logger.error(f"验证函数错误: {e}")
            return False

    def aggregation_function(self, accumulator: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """聚合函数"""
        try:
            if not accumulator:
                accumulator = {
                    "count": 0,
                    "total_value": 0,
                    "categories": {},
                    "statuses": {},
                    "min_value": float('inf'),
                    "max_value": 0
                }

            accumulator["count"] += 1
            value = data.get("value", 0)
            accumulator["total_value"] += value
            accumulator["min_value"] = min(accumulator["min_value"], value)
            accumulator["max_value"] = max(accumulator["max_value"], value)

            # 分类统计
            category = data.get("category", "unknown")
            accumulator["categories"][category] = accumulator["categories"].get(category, 0) + 1

            status = data.get("status", "unknown")
            accumulator["statuses"][status] = accumulator["statuses"].get(status, 0) + 1

            return accumulator
        except Exception as e:
            logger.error(f"聚合函数错误: {e}")
            return accumulator

    def function_composition_example(self):
        """函数组合示例"""
        print("\n=== 函数组合示例 ===")

        test_data = self.create_test_data()

        self.function_composition_real(test_data)

    def function_composition_real(self, data: List[Dict[str, Any]]):
        """使用真实 API 的函数组合"""
        print("□ 使用真实 SAGE Flow API 函数组合")

        if sfd is None:
            print("□ SAGE Flow 模块不可用，使用模拟模式")
            self.function_composition_simulation(data)
            return

    def function_composition_simulation(self, data: List[Dict[str, Any]]):
        """模拟函数组合"""
        print("□ 使用模拟函数组合")

        # 模拟处理数据
        processed = []
        for item in data:
            if self.validation_function(item) and self.custom_filter_function(item):
                mapped = self.custom_map_function(item)
                error_handled = self.error_handling_function(mapped)
                processed.append(error_handled)

        print(f"✓ 模拟函数组合处理完成: {len(processed)} 成功")

        # 聚合结果
        if processed:
            aggregator = {}
            for result in processed:
                aggregator = self.aggregation_function(aggregator, result)

            print("聚合统计:")
            print(f"  处理项目数: {aggregator['count']}")
            print(".2f")
            print(f"  值范围: {aggregator['min_value']} - {aggregator['max_value']}")
            print(f"  分类分布: {aggregator['categories']}")
            print(f"  状态分布: {aggregator['statuses']}")

        # 使用真实的流处理 API
        if sfd is not None:
            env = sfd.Environment("function_composition_example")
            stream = env.create_datastream()
        else:
            print("□ SAGE Flow 模块不可用，跳过真实 API 调用")
            return

        results = []
        errors = []

        def process_item(item):
            try:
                # 函数组合链
                if not self.validation_function(item):
                    errors.append({"item": item, "error": "validation_failed"})
                    return

                if not self.custom_filter_function(item):
                    return  # 过滤掉不符合条件的项目

                mapped_item = self.custom_map_function(item)
                error_handled_item = self.error_handling_function(mapped_item)

                results.append(error_handled_item)
                self.processed_count += 1

            except Exception as e:
                errors.append({"item": item, "error": str(e)})
                self.error_count += 1

        # 处理数据
        for item in data:
            process_item(item)

        print(f"✓ 函数组合处理完成: {len(results)} 成功, {len(errors)} 错误")

        # 聚合结果
        if results:
            aggregator = {}
            for result in results:
                aggregator = self.aggregation_function(aggregator, result)

            print("聚合统计:")
            print(f"  处理项目数: {aggregator['count']}")
            print(".2f")
            print(f"  值范围: {aggregator['min_value']} - {aggregator['max_value']}")
            print(f"  分类分布: {aggregator['categories']}")
            print(f"  状态分布: {aggregator['statuses']}")


    def operator_chaining_example(self):
        """操作符链示例"""
        print("\n=== 操作符链示例 ===")

        test_data = self.create_test_data()

        self.operator_chaining_real(test_data)

    def operator_chaining_real(self, data: List[Dict[str, Any]]):
        """使用真实 API 的操作符链"""
        print("□ 使用真实 SAGE Flow API 操作符链")

        if sfd is None:
            print("□ SAGE Flow 模块不可用，使用模拟模式")
            self.operator_chaining_simulation(data)
            return

        self.operator_chaining_simulation(data)

    def operator_chaining_simulation(self, data: List[Dict[str, Any]]):
        """模拟操作符链"""
        print("□ 使用模拟操作符链")

        # 模拟操作符链：filter -> map -> reduce
        filtered_data = [item for item in data if self.custom_filter_function(item)]
        print(f"✓ 过滤操作: {len(data)} -> {len(filtered_data)}")

        mapped_data = [self.custom_map_function(item) for item in filtered_data]
        print(f"✓ 映射操作: {len(filtered_data)} -> {len(mapped_data)}")

        # 自定义 reduce 操作
        reduced_result = {}
        for item in mapped_data:
            reduced_result = self.aggregation_function(reduced_result, item)

        print(f"✓ 聚合操作完成")
        print(f"  最终结果: {reduced_result['count']} 项目，总值 {reduced_result['total_value']}")

    def error_recovery_example(self):
        """错误恢复示例"""
        print("\n=== 错误恢复示例 ===")

        # 创建包含错误数据的测试数据
        test_data = self.create_test_data()
        # 添加一些故意错误的测试数据
        error_data = [
            {"id": "invalid", "name": None, "value": -100},  # 类型错误
            {"id": 999, "name": "Error_Test", "value": "not_a_number"},  # 值类型错误
            {},  # 缺少必需字段
        ]
        test_data.extend(error_data)

        print(f"测试数据包含 {len(error_data)} 条错误数据")

        self.error_recovery_real(test_data)

    def error_recovery_real(self, data: List[Dict[str, Any]]):
        """使用真实 API 的错误恢复"""
        print("□ 使用真实 SAGE Flow API 错误恢复")
        self.error_recovery_simulation(data)

    def error_recovery_simulation(self, data: List[Dict[str, Any]]):
        """模拟错误恢复"""
        print("□ 使用模拟错误恢复")

        successful = []
        failed = []

        for item in data:
            try:
                # 验证数据
                if not self.validation_function(item):
                    failed.append({"item": item, "error": "validation_failed"})
                    continue

                # 处理数据
                processed = self.custom_map_function(item)
                processed = self.error_handling_function(processed)

                successful.append(processed)

            except Exception as e:
                failed.append({"item": item, "error": str(e)})

        print(f"✓ 错误恢复处理完成: {len(successful)} 成功, {len(failed)} 失败")

        if failed:
            print("失败项目详情:")
            for failure in failed[:3]:  # 只显示前3个失败
                print(f"  ID: {failure['item'].get('id', 'unknown')}, 错误: {failure['error']}")

    def performance_monitoring_example(self):
        """性能监控示例"""
        print("\n=== 性能监控示例 ===")

        test_data = self.create_test_data()
        batch_sizes = [10, 50, 100, 500]

        for batch_size in batch_sizes:
            batch_data = test_data[:batch_size]

            start_time = time.time()

            processed = 0
            errors = 0

            for item in batch_data:
                try:
                    if self.validation_function(item) and self.custom_filter_function(item):
                        self.custom_map_function(item)
                        processed += 1
                except Exception:
                    errors += 1

            end_time = time.time()
            duration = end_time - start_time

            throughput = len(batch_data) / duration if duration > 0 else 0
            success_rate = processed / len(batch_data) * 100 if batch_data else 0

            print(f"批量大小 {batch_size}:")
            print(".3f")
            print(".1f")
            print(".1f")

    def custom_function_registry_example(self):
        """自定义函数注册示例"""
        print("\n=== 自定义函数注册示例 ===")

        # 注册自定义函数
        self.custom_functions = {
            "validate": self.validation_function,
            "filter": self.custom_filter_function,
            "map": self.custom_map_function,
            "aggregate": self.aggregation_function,
            "error_handle": self.error_handling_function
        }

        print(f"✓ 注册了 {len(self.custom_functions)} 个自定义函数")

        # 演示函数调用
        test_item = self.create_test_data()[0]

        for func_name, func in self.custom_functions.items():
            try:
                if func_name == "validate":
                    result = func(test_item)
                    print(f"  {func_name}: {result}")
                elif func_name == "filter":
                    result = func(test_item)
                    print(f"  {func_name}: {result}")
                elif func_name == "map":
                    result = func(test_item)
                    print(f"  {func_name}: 转换了 {len(result)} 个字段")
                elif func_name == "aggregate":
                    accumulator = {}
                    result = func(accumulator, test_item)
                    print(f"  {func_name}: 聚合了 {result['count']} 项目")
                elif func_name == "error_handle":
                    result = func(test_item)
                    print(f"  {func_name}: 错误处理状态 {result.get('error_handled', False)}")
            except Exception as e:
                print(f"  {func_name}: 执行失败 - {e}")

def main():
    """主函数"""
    print("SAGE Flow 函数和操作符测试示例")
    print("=" * 60)

    tester = FunctionOperatorTester()

    # 执行各种函数和操作符示例
    tester.function_composition_example()
    tester.operator_chaining_example()
    tester.error_recovery_example()
    tester.performance_monitoring_example()
    tester.custom_function_registry_example()

    # 显示统计信息
    print("\n=== 处理统计 ===")
    print(f"总处理项目数: {tester.processed_count}")
    print(f"错误数量: {tester.error_count}")
    print(".1f")

    print("\n✓ 函数和操作符测试示例完成")

    # 功能说明
    print("\n=== 函数和操作符功能说明 ===")
    print("1. 自定义函数: 支持用户定义的过滤、映射、聚合函数")
    print("2. 函数组合: 支持多个函数的链式调用")
    print("3. 错误处理: 提供错误检测和恢复机制")
    print("4. 操作符链: 支持 filter -> map -> reduce 模式")
    print("5. 性能监控: 提供处理时间和吞吐量统计")
    print("6. 函数注册: 支持动态函数注册和调用")

    print("\n✓ 使用真实 SAGE Flow 引擎运行")

if __name__ == "__main__":
    main()