"""
基于服务框架的Memory Service集成测试
"""
import os
import time
import queue
from sage.runtime.runtime_context import RuntimeContext
from sage.runtime.service.local_service_task import LocalServiceTask
from sage.runtime.service.service_caller import ServiceManager
from sage.core.function.base_function import BaseFunction
from sage.jobmanager.factory.service_factory import ServiceFactory
from sage.service.memory.memory_service import MemoryService
from sage.utils.embedding_methods.embedding_api import apply_embedding_model
from sage.utils.custom_logger import CustomLogger


# 创建Mock对象来初始化RuntimeContext
class MockGraphNode:
    def __init__(self, name: str):
        self.name = name
        self.parallel_index = 0
        self.parallelism = 1
        self.stop_signal_num = 1


class MockTransformation:
    def __init__(self):
        self.is_spout = False
        self.memory_collection = None


class MockEnvironment:
    def __init__(self, name: str):
        self.name = name
        self.env_base_dir = "/tmp/sage_test"
        self.uuid = "test-uuid"
        self.console_log_level = "INFO"


class TestFunction(BaseFunction):
    def execute(self, data):
        return data


def test_memory_service_integrated():
    """测试Memory Service在服务框架下的功能"""
    print("🚀 Starting Memory Service integration test...")
    
    try:
        # 1. 创建运行时上下文
        memory_graph_node = MockGraphNode("memory_service")
        memory_transformation = MockTransformation()
        memory_env = MockEnvironment("test_env")
        memory_ctx = RuntimeContext(memory_graph_node, memory_transformation, memory_env)
        
        test_graph_node = MockGraphNode("test_function")
        test_transformation = MockTransformation()
        test_env = MockEnvironment("test_env")
        test_ctx = RuntimeContext(test_graph_node, test_transformation, test_env)
        
        # 2. 创建Memory Service实例和工厂
        # 指定临时测试目录
        test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(test_data_dir, exist_ok=True)
        
        def service_factory():
            # 在服务进程中创建embedding model
            embedding_model = apply_embedding_model("default")
            memory_service = MemoryService(data_dir=test_data_dir)
            return memory_service
            
        memory_factory = ServiceFactory("memory_service", service_factory)
        
        # 3. 创建服务任务
        memory_task = LocalServiceTask(memory_factory, memory_ctx)
        
        # 4. 启动服务任务
        memory_task.start_running()
        
        # 等待服务启动
        time.sleep(2.0)
        
        # 5. 创建测试函数并设置上下文
        test_func = TestFunction()
        test_func.ctx = test_ctx
        
        print("✅ Service started, testing operations...")
        
        # 6. 测试创建collection
        result1 = test_func.call_service["memory_service"].create_collection(
            name="test_collection",
            backend_type="VDB",
            description="Test collection"
        )
        print(f"Create collection result: {result1}")
        assert result1["status"] == "success", f"Create collection failed: {result1}"
        
        # 7. 测试插入数据
        result2 = test_func.call_service["memory_service"].insert_data(
            collection_name="test_collection",
            text="This is a test document",
            metadata={"type": "test", "date": "2025-07-26"}
        )
        print(f"Insert data result: {result2}")
        assert result2["status"] == "success", f"Insert data failed: {result2}"
        
        # 8. 测试创建索引
        result3 = test_func.call_service["memory_service"].create_index(
            collection_name="test_collection",
            index_name="test_index",
            description="Test index"
        )
        print(f"Create index result: {result3}")
        assert result3["status"] == "success", f"Create index failed: {result3}"
        
        # 9. 测试检索数据
        result4 = test_func.call_service["memory_service"].retrieve_data(
            collection_name="test_collection",
            query_text="test document",
            topk=5,
            index_name="test_index",
            with_metadata=True
        )
        print(f"Retrieve data result: {result4}")
        assert result4["status"] == "success", f"Retrieve data failed: {result4}"
        
        # 10. 测试插入更多数据
        for i in range(3):
            result = test_func.call_service["memory_service"].insert_data(
                collection_name="test_collection",
                text=f"Test document {i}",
                metadata={"type": "test", "index": i}
            )
            print(f"Insert data {i} result: {result}")
            assert result["status"] == "success", f"Insert data {i} failed: {result}"
        
        # 11. 测试列出collections
        final_result = test_func.call_service["memory_service"].list_collections()
        print(f"Collections list: {final_result}")
        assert final_result["status"] == "success", f"List collections failed: {final_result}"
        assert len(final_result["collections"]) == 1, "Should have exactly 1 collection"
        
        # 12. 测试获取collection信息
        info_result = test_func.call_service["memory_service"].get_collection_info("test_collection")
        print(f"Collection info: {info_result}")
        assert info_result["status"] == "success", f"Get collection info failed: {info_result}"
        
        # 13. 测试列出索引
        index_result = test_func.call_service["memory_service"].list_indexes("test_collection")
        print(f"Indexes list: {index_result}")
        assert index_result["status"] == "success", f"List indexes failed: {index_result}"
        
        print("✅ All operations completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理资源
        try:
            if 'memory_task' in locals():
                memory_task.stop()
            # 清理测试数据目录
            import shutil
            test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
            if os.path.exists(test_data_dir):
                shutil.rmtree(test_data_dir)
            print("🧹 Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("SAGE Memory Service Integration Test")
    print("=" * 60)
    
    success = test_memory_service_integrated()
    
    if success:
        print("\n🎉 All tests passed! Memory service system is working correctly.")
    else:
        print("\n💥 Tests failed! Please check the logs above.")
        exit(1)
