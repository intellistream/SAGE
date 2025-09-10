#!/usr/bin/env python3
"""
SAGE Flow 高级流处理示例

展示 sage_flow 的高级流处理功能：
- 窗口操作（模拟时间/计数窗口）
- 聚合操作（group by + aggregate）
- 流连接（join）
- 复杂数据转换（map链式）
- sink多种输出

使用纯Python DSL，无C++依赖，支持链式fluent API。

作者: Kilo Code
日期: 2025-09-06
"""

import sys
import os
import time
import json
import random
from typing import List, Dict, Any, Callable
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np  # type: ignore

# 添加包路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from sageflow import Stream, Environment, IndexFunction

class AdvancedStreamProcessor:
    """高级流处理器"""

    def __init__(self):
        self.window_results: List[Dict[str, Any]] = []
        self.aggregated_results: List[Dict[str, Any]] = []

    def create_time_series_data(self) -> List[Dict[str, Any]]:
        """创建时间序列数据"""
        base_time = datetime.now()
        data = []
        for i in range(20):  # 简化到20条
            timestamp = base_time + timedelta(seconds=i * 2)
            item = {
                "id": i + 1,
                "timestamp": timestamp.isoformat(),
                "sensor_id": f"sensor_{random.randint(1, 3)}",
                "temperature": round(random.uniform(20.0, 30.0), 2),
                "humidity": round(random.uniform(40.0, 80.0), 2),
                "pressure": round(random.uniform(980.0, 1020.0), 2)
            }
            data.append(item)
        return data

    def create_user_activity_data(self) -> List[Dict[str, Any]]:
        """创建用户活动数据"""
        users = ["alice", "bob", "charlie", "diana", "eve"]
        actions = ["login", "logout", "click", "view", "purchase"]
        data = []
        base_time = datetime.now()
        for i in range(15):  # 简化
            timestamp = base_time + timedelta(seconds=i * 3)
            item = {
                "id": i + 1,
                "timestamp": timestamp.isoformat(),
                "user_id": random.choice(users),
                "action": random.choice(actions),
                "session_id": f"session_{random.randint(1, 10)}",
                "value": random.randint(1, 100) if random.choice(actions) == "purchase" else 0
            }
            data.append(item)
        return data

    def window_operations_example(self):
        """窗口操作示例（模拟时间窗口）"""
        print("\n=== 窗口操作示例 ===")
        sensor_data = self.create_time_series_data()

        def extract_timestamp(item: Dict[str, Any]) -> datetime:
            return datetime.fromisoformat(item["timestamp"])

        def window_aggregate(window_data: List[Dict[str, Any]]) -> Dict[str, Any]:
            if not window_data:
                return {}
            avg_temp = sum(item["temperature"] for item in window_data) / len(window_data)
            return {
                "window_start": window_data[0]["timestamp"],
                "record_count": len(window_data),
                "avg_temperature": round(avg_temp, 2),
                "max_temperature": max(item["temperature"] for item in window_data),
                "sensor_count": len(set(item["sensor_id"] for item in window_data))
            }

        # 使用Stream模拟窗口：先map添加窗口键，然后aggregate
        def add_window_key(item: Dict[str, Any]) -> Dict[str, Any]:
            ts = extract_timestamp(item)
            window_start = ts.replace(second=(ts.second // 10) * 10)  # 10秒窗口
            return {**item, "window_key": window_start.isoformat()}

        stream = Stream.from_list(sensor_data)
        windowed = (stream
                    .map(add_window_key)
                    .aggregate(
                        key_func=lambda x: x["window_key"],
                        agg_func=window_aggregate
                    )
                    .sink("print://"))
        results = windowed.execute()
        self.window_results = results
        print(f"✓ 处理了 {len(results)} 个时间窗口")

    def aggregation_operations_example(self):
        """聚合操作示例"""
        print("\n=== 聚合操作示例 ===")
        activity_data = self.create_user_activity_data()

        # 模拟lookup数据
        lookup_data = [
            {"user_id": "alice", "bonus": 10},
            {"user_id": "bob", "bonus": 20},
            {"user_id": "charlie", "bonus": 5}
        ]

        def get_user_key(item: Dict[str, Any]) -> str:
            return item["user_id"]

        def join_users(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
            if right:
                return {**left, "total_value": left["value"] + right["bonus"]}
            return {**left, "total_value": left["value"]}

        # Join示例
        main_stream = Stream.from_list(activity_data)
        lookup_stream = Stream.from_list(lookup_data)
        joined_stream = main_stream.join(lookup_stream, get_user_key, join_users)

        # Aggregate示例：按user_id聚合总价值
        def aggregate_user_stats(group: List[Dict[str, Any]]) -> Dict[str, Any]:
            user_id = group[0]["user_id"] if group else "unknown"
            total_value = sum(item["total_value"] for item in group)
            action_count = len(group)
            return {"user_id": user_id, "total_value": total_value, "action_count": action_count}

        aggregated = joined_stream.aggregate(get_user_key, aggregate_user_stats)

        # NumPy示例
        values = np.array([item["value"] for item in activity_data[:5]])  # type: ignore
        numpy_stream = Stream.from_numpy(values)
        numpy_agg = numpy_stream.aggregate(
            key_func=lambda x: "all",  # 单一键聚合整个列表
            agg_func=lambda lst: {"sum": sum(lst), "mean": np.mean(lst)}  # type: ignore
        )

        # 执行
        join_results = joined_stream.sink("print://").execute()
        agg_results = aggregated.sink("file://agg_output.txt").execute()
        numpy_results = numpy_agg.execute()

        self.aggregated_results = agg_results
        print(f"✓ 聚合完成，{len(agg_results)} 个用户统计")
        print(f"NumPy结果: {numpy_results}")

    def stream_joining_example(self):
        """流连接示例"""
        print("\n=== 流连接示例 ===")
        sensor_data = self.create_time_series_data()[:10]
        activity_data = self.create_user_activity_data()[:10]

        def get_time_key(item: Dict[str, Any]) -> str:
            return item["timestamp"][:16]  # 分钟级

        def join_activity_sensor(act: Dict[str, Any], sen: Dict[str, Any]) -> Dict[str, Any]:
            if sen:
                return {
                    **act,
                    "temperature": sen["temperature"],
                    "humidity": sen["humidity"],
                    "time_match": True
                }
            return {**act, "time_match": False}

        activity_stream = Stream.from_list(activity_data)
        sensor_stream = Stream.from_list(sensor_data)
        joined = activity_stream.join(sensor_stream, get_time_key, join_activity_sensor)

        results = joined.sink("print://").execute()
        print(f"✓ 连接了 {len(results)} 条记录，匹配 {sum(1 for r in results if r['time_match'])} 条")

    def complex_transformation_example(self):
        """复杂转换示例"""
        print("\n=== 复杂转换示例 ===")
        data = self.create_time_series_data()

        def complex_transform(item: Dict[str, Any]) -> Dict[str, Any]:
            temp_c = item["temperature"]
            temp_f = temp_c * 9/5 + 32
            hum_index = temp_c * item["humidity"] / 100
            pressure_trend = "high" if item["pressure"] > 1010 else "low" if item["pressure"] < 990 else "stable"
            alert = "high" if temp_c > 28 or item["humidity"] > 75 else "normal"
            return {
                **item,
                "temperature_fahrenheit": round(temp_f, 2),
                "humidity_index": round(hum_index, 2),
                "pressure_trend": pressure_trend,
                "alert_level": alert,
                "processed_at": time.time()
            }

        stream = Stream.from_list(data)
        transformed = (stream
                       .map(complex_transform)
                       .filter(lambda x: x["alert_level"] == "normal")  # 只保留正常警报
                       .sink("file://transformed_output.txt"))
        results = transformed.execute()
        print(f"✓ 复杂转换了 {len(results)} 条记录（正常警报）")

    def demonstrate_fluent_api(self):
        """演示完整fluent API"""
        print("\n=== Fluent API 演示 ===")
        data = [{"id": 1, "val": 10}, {"id": 2, "val": 5}, {"id": 3, "val": 15}]
        env = Environment()
        ds = env.create_datastream().from_list(data)
        result = (ds
                  .config(parallelism=2)
                  .map(lambda x: {**x, "doubled": x["val"] * 2})
                  .filter(lambda x: x["doubled"] > 10)
                  .sink("print://")
                  .collect())
        print(f"Fluent结果: {result}")
    
    def demonstrate_rag_index(self):
        """演示Index RAG示例"""
        print("\n=== Index RAG 示例 ===")
        from sageflow import IndexFunction
        env = Environment()
        # 创建示例数据
        sample_vectors = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [1.5, 2.5]]
        ds = env.create_datastream().from_list(sample_vectors)
        index = IndexFunction()
        # 添加向量到index
        ds.sink(index.add_vector).execute()
        # 搜索kNN
        query = [1.0, 2.0]
        results = index.search_kNN(query, k=3)
        print(f"RAG搜索结果: {results}")
        print(f"✓ 找到了 {len(results)} 个最近邻")

def main():
    """主函数"""
    print("SAGE Flow 高级流处理示例")
    print("=" * 60)

    processor = AdvancedStreamProcessor()

    # 执行示例
    processor.window_operations_example()
    processor.aggregation_operations_example()
    processor.stream_joining_example()
    processor.complex_transformation_example()
    processor.demonstrate_fluent_api()
    processor.demonstrate_rag_index()

    # 结果摘要
    print("\n=== 结果摘要 ===")
    print(f"窗口结果: {len(processor.window_results)} 个窗口")
    print(f"聚合结果: {len(processor.aggregated_results)} 个统计")

    if processor.window_results:
        print("\n示例窗口:")
        for r in processor.window_results[:2]:
            print(f"  {r['window_start']}: {r['record_count']} 记录, 平均温度 {r['avg_temperature']}°C")

    print("\n✓ 高级流处理示例完成")

    # 说明
    print("\n=== 高级DSL功能 ===")
    print("1. 窗口: 通过map添加键 + aggregate")
    print("2. Join: .join(other, key_func, join_func)")
    print("3. Aggregate: .aggregate(key_func, agg_func)")
    print("4. Sink: 'file://path.txt' 或 'print://'")
    print("5. Fluent: 所有方法返回Stream，支持链式")

if __name__ == "__main__":
    main()