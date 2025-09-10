#!/usr/bin/env python3
"""
SAGE Flow 基础流处理示例

展示 sage_flow 的基础流处理功能：
- 创建数据流
- 基本的 map/filter/sink 操作
- 链式 fluent API
- execute() 触发懒惰执行

作者: Kilo Code
日期: 2025-09-06
"""

import sys
import os
import time
import json
from typing import List, Dict, Any

# 添加包路径以正确导入sageflow
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from sageflow import Environment, DataStream

class BasicStreamProcessor:
    """基础流处理器"""

    def __init__(self):
        self.processed_count = 0
        self.results = []

    def create_sample_data(self) -> List[Dict[str, Any]]:
        """创建示例数据"""
        return [
            {"id": 1, "name": "Alice", "age": 25, "score": 85.5, "active": True},
            {"id": 2, "name": "Bob", "age": 30, "score": 92.0, "active": False},
            {"id": 3, "name": "Charlie", "age": 28, "score": 78.3, "active": True},
            {"id": 4, "name": "Diana", "age": 35, "score": 88.7, "active": True},
            {"id": 5, "name": "Eve", "age": 22, "score": 95.2, "active": False},
            {"id": 6, "name": "Frank", "age": 40, "score": 76.8, "active": True},
            {"id": 7, "name": "Grace", "age": 27, "score": 89.1, "active": True},
            {"id": 8, "name": "Henry", "age": 33, "score": 82.4, "active": False},
        ]

    def process_data(self):
        """使用Stream DSL处理数据"""
        print("\n=== 使用 SAGE Flow Python DSL ===")

        # 准备数据
        sample_data = self.create_sample_data()

        # 使用链式API：filter active users, map添加处理信息和grade
        def is_active(item: Dict[str, Any]) -> bool:
            return item.get('active', False)

        def add_processing_info(item: Dict[str, Any]) -> Dict[str, Any]:
            return {
                **item,
                'processed_at': time.time(),
                'grade': self.calculate_grade(item['score']),
                'embeddings': [1.0, 2.0]
            }

        env = Environment()
        ds = env.create_datastream().from_list(sample_data)
        processed_stream = (ds
                            .filter(is_active)
                            .map(add_processing_info)
                            .filter(lambda item: len(item.get("embeddings", [])) > 0)
                            .sink("print://"))

        results = processed_stream.collect()
        print(f"✓ 流处理完成，处理了 {len(results)} 条记录")

        # 应用文件sink示例
        print("\n=== 文件 Sink 示例 ===")
        file_ds = env.create_datastream().from_list(sample_data)
        file_processed = (file_ds
                          .filter(is_active)
                          .map(add_processing_info)
                          .filter(lambda item: len(item.get("embeddings", [])) > 0)
                          .sink("file://basic_output.txt"))
        file_results = file_processed.collect()
        print(f"✓ 文件sink完成，结果写入 basic_output.txt，{len(file_results)} 条记录")

        return results

    def calculate_grade(self, score: float) -> str:
        """根据分数计算等级"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        else:
            return "D"

    def demonstrate_simple_pipeline(self):
        """演示Fluent API"""
        print("\n=== Fluent API 演示 ===")
        env = Environment()
        ds = env.create_datastream().from_list([{"text": "test"}])
        result = (ds
                  .map(lambda msg: {**msg, "embeddings": [1.0, 2.0]})
                  .filter(lambda msg: len(msg["embeddings"]) > 0)
                  .collect())
        print(f"Fluent结果: {result}")

def main():
    """主函数"""
    print("SAGE Flow 基础流处理示例")
    print("=" * 60)

    processor = BasicStreamProcessor()

    # 演示简单管道
    processor.demonstrate_simple_pipeline()

    # 执行流处理
    results = processor.process_data()

    # 显示结果
    print("\n=== 处理结果 ===")
    print(f"总共处理了 {len(results)} 条记录:")
    for i, result in enumerate(results[:5], 1):  # 只显示前5条
        print(f"{i}. {result['name']}: 分数={result['score']}, 等级={result['grade']}")

    if len(results) > 5:
        print(f"... 还有 {len(results) - 5} 条记录")

    print("\n✓ 基础流处理示例完成")

    # 使用建议
    print("\n=== 使用建议 ===")
    print("1. 使用 from sageflow import Stream 创建流")
    print("2. 链式调用 .map() .filter() .sink()")
    print("3. 调用 .execute() 触发执行")
    print("4. sink支持 'print://' 和 'file://path.txt'")

if __name__ == "__main__":
    main()