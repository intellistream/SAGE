"""
SAGE Communication Framework 使用示例

展示如何使用新的统一通信架构替代原有的同名queue通信方式
"""

import time
import asyncio
from typing import Any, Dict

from sage.core.communication.service_base import BaseService, ServiceFunction, FunctionClient
from sage.core.communication.message_bus import get_communication_bus, CommunicationPattern


# 示例：数据处理服务
class DataProcessingService(BaseService):
    """数据处理服务示例"""

    def __init__(self):
        super().__init__("data_processing", "data_proc_001")
        self.processed_count = 0

    def initialize(self):
        """服务初始化"""
        print(f"数据处理服务 {self.service_id} 初始化完成")

    def cleanup(self):
        """服务清理"""
        print(f"数据处理服务 {self.service_id} 清理完成，共处理 {self.processed_count} 条数据")

    @ServiceFunction(name="process_data", timeout=10.0)
    def process_data(self, data: Dict[str, Any], message=None) -> Dict[str, Any]:
        """处理数据"""
        self.processed_count += 1

        # 模拟数据处理
        result = {
            "original": data,
            "processed_at": time.time(),
            "processor": self.service_id,
            "result": f"Processed: {data.get('content', 'unknown')}"
        }

        print(f"[{self.service_name}] 处理数据: {data} -> {result['result']}")
        return result

    @ServiceFunction(name="get_stats")
    def get_stats(self, params: Any = None, message=None) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "service_id": self.service_id,
            "processed_count": self.processed_count,
            "uptime": time.time()
        }


# 示例：存储服务
class StorageService(BaseService):
    """存储服务示例"""

    def __init__(self):
        super().__init__("storage", "storage_001")
        self.data_store = {}
        self.store_count = 0

    def initialize(self):
        print(f"存储服务 {self.service_id} 初始化完成")

    def cleanup(self):
        print(f"存储服务 {self.service_id} 清理完成，共存储 {self.store_count} 条数据")

    @ServiceFunction(name="store_data")
    def store_data(self, data: Dict[str, Any], message=None) -> Dict[str, str]:
        """存储数据"""
        data_id = f"data_{self.store_count}"
        self.data_store[data_id] = {
            "data": data,
            "stored_at": time.time(),
            "stored_by": self.service_id
        }
        self.store_count += 1

        print(f"[{self.service_name}] 存储数据: {data_id}")
        return {"data_id": data_id, "status": "stored"}

    @ServiceFunction(name="retrieve_data")
    def retrieve_data(self, data_id: str, message=None) -> Dict[str, Any]:
        """检索数据"""
        if data_id in self.data_store:
            print(f"[{self.service_name}] 检索数据: {data_id}")
            return self.data_store[data_id]
        else:
            return {"error": f"Data {data_id} not found"}


# 示例：协调服务（使用其他服务的函数）
class CoordinatorService(BaseService):
    """协调服务示例"""

    def __init__(self):
        super().__init__("coordinator", "coord_001")
        self.pipeline_count = 0

    def initialize(self):
        print(f"协调服务 {self.service_id} 初始化完成")
        # 订阅数据事件
        self.subscribe("data_events")

    def cleanup(self):
        print(f"协调服务 {self.service_id} 清理完成，执行了 {self.pipeline_count} 个流水线")

    @ServiceFunction(name="execute_pipeline")
    def execute_pipeline(self, input_data: Dict[str, Any], message=None) -> Dict[str, Any]:
        """执行完整的数据处理流水线"""
        self.pipeline_count += 1

        try:
            # 1. 调用数据处理服务
            processed_result = self.call_function(
                target_service="data_processing",
                function="process_data",
                payload=input_data,
                timeout=10.0
            )

            if not processed_result or 'error' in processed_result:
                return {"error": "数据处理失败", "details": processed_result}

            # 2. 调用存储服务
            storage_result = self.call_function(
                target_service="storage",
                function="store_data",
                payload=processed_result,
                timeout=5.0
            )

            if not storage_result or 'error' in storage_result:
                return {"error": "数据存储失败", "details": storage_result}

            # 3. 广播处理完成事件
            self.broadcast("data_events", {
                "event": "pipeline_completed",
                "data_id": storage_result.get("data_id"),
                "processed_by": self.service_id
            })

            result = {
                "pipeline_id": f"pipeline_{self.pipeline_count}",
                "input_data": input_data,
                "processed_result": processed_result,
                "storage_result": storage_result,
                "status": "completed"
            }

            print(f"[{self.service_name}] 流水线执行完成: {result['pipeline_id']}")
            return result

        except Exception as e:
            error_result = {
                "error": f"流水线执行失败: {str(e)}",
                "pipeline_id": f"pipeline_{self.pipeline_count}"
            }
            print(f"[{self.service_name}] 流水线执行失败: {e}")
            return error_result


def run_communication_example():
    """运行通信架构示例"""
    print("=" * 60)
    print("SAGE 统一通信架构示例")
    print("=" * 60)

    # 创建服务实例
    data_service = DataProcessingService()
    storage_service = StorageService()
    coordinator_service = CoordinatorService()

    try:
        # 启动所有服务
        print("\n1. 启动服务...")
        data_service.start()
        storage_service.start()
        coordinator_service.start()

        # 初始化服务
        data_service.initialize()
        storage_service.initialize()
        coordinator_service.initialize()

        # 等待服务完全启动
        time.sleep(1)

        # 创建客户端
        client = FunctionClient("example_client")

        # 2. 列出可用服务和函数
        print("\n2. 可用服务:")
        services = client.list_services()
        for service in services:
            print(f"   - {service['service_name']} ({service['service_id']}): {service['functions']}")

        print("\n3. 可用函数:")
        functions = client.list_functions()
        for func_name, service_ids in functions.items():
            print(f"   - {func_name}: {service_ids}")

        # 3. 直接调用单个服务函数
        print("\n4. 直接调用服务函数...")

        # 调用数据处理服务
        test_data = {"content": "Hello, SAGE!", "timestamp": time.time()}
        processed = client.call("data_processing", "process_data", test_data)
        print(f"   处理结果: {processed}")

        # 调用存储服务
        stored = client.call("storage", "store_data", processed)
        print(f"   存储结果: {stored}")

        # 获取统计信息
        stats = client.call("data_processing", "get_stats")
        print(f"   统计信息: {stats}")

        # 4. 调用协调服务执行完整流水线
        print("\n5. 执行完整流水线...")

        pipeline_input = {
            "content": "Pipeline test data",
            "source": "example_client",
            "priority": "high"
        }

        pipeline_result = client.call("coordinator", "execute_pipeline", pipeline_input)
        print(f"   流水线结果: {pipeline_result}")

        # 5. 测试并发调用
        print("\n6. 测试并发调用...")
        import concurrent.futures

        def call_pipeline(data):
            return client.call("coordinator", "execute_pipeline", {
                "content": f"Concurrent data {data}",
                "batch_id": data
            })

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(call_pipeline, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        print(f"   并发调用完成，处理了 {len(results)} 个请求")

        # 6. 获取最终统计
        print("\n7. 最终统计信息:")
        bus = get_communication_bus()
        bus_stats = bus.get_stats()
        print(f"   通信总线统计: {bus_stats}")

        final_stats = client.call("data_processing", "get_stats")
        print(f"   数据处理服务: {final_stats}")

    finally:
        # 清理资源
        print("\n8. 清理资源...")
        data_service.cleanup()
        storage_service.cleanup()
        coordinator_service.cleanup()

        data_service.stop()
        storage_service.stop()
        coordinator_service.stop()
        client.close()

        print("\n示例执行完成!")


if __name__ == "__main__":
    run_communication_example()
