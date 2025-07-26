"""
测试Memory Service的集成测试用例
"""
import os
import shutil
import traceback
from sage.service.memory.memory_service import MemoryService
from sage.utils.embedding_methods.embedding_api import apply_embedding_model

def test_memory_service():
    """测试Memory Service的主要功能（直接测试，不使用服务框架）"""
    print("🚀 Starting Memory Service test...")
    
    try:
        # 1. 直接创建MemoryService实例
        # 使用默认的embedding model
        embedding_model = apply_embedding_model("default")
        dim = embedding_model.get_dim()
        # 指定临时测试目录
        test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(test_data_dir, exist_ok=True)
        memory_service = MemoryService(data_dir=test_data_dir)
        
        print("✅ Memory service created, testing operations...")
        
        # 2. 测试创建collection
        result1 = memory_service.create_collection(
            name="test_collection",
            backend_type="VDB",
            description="Test collection",
            embedding_model=embedding_model,
            dim=dim
        )
        print(f"Create collection result: {result1}")
        assert result1["status"] == "success", f"Create collection failed: {result1}"
        
        # 3. 测试插入数据
        result2 = memory_service.insert_data(
            collection_name="test_collection",
            text="This is a test document",
            metadata={"type": "test", "date": "2025-07-26"}
        )
        print(f"Insert data result: {result2}")
        assert result2["status"] == "success", f"Insert data failed: {result2}"
        
        # 4. 测试创建索引
        result3 = memory_service.create_index(
            collection_name="test_collection",
            index_name="test_index",
            description="Test index"
        )
        print(f"Create index result: {result3}")
        assert result3["status"] == "success", f"Create index failed: {result3}"
        
        # 5. 测试检索数据
        result4 = memory_service.retrieve_data(
            collection_name="test_collection",
            query_text="test document",
            topk=5,
            index_name="test_index",
            with_metadata=True
        )
        print(f"Retrieve data result: {result4}")
        assert result4["status"] == "success", f"Retrieve data failed: {result4}"
        
        # 6. 测试插入更多数据
        for i in range(3):
            result = memory_service.insert_data(
                collection_name="test_collection",
                text=f"Test document {i}",
                metadata={"type": "test", "index": i}
            )
            print(f"Insert data {i} result: {result}")
            assert result["status"] == "success", f"Insert data {i} failed: {result}"
        
        # 7. 测试列出collections
        final_result = memory_service.list_collections()
        print(f"Collections list: {final_result}")
        assert final_result["status"] == "success", f"List collections failed: {final_result}"
        assert len(final_result["collections"]) == 1, "Should have exactly 1 collection"
        
        # 8. 测试获取collection信息
        info_result = memory_service.get_collection_info("test_collection")
        print(f"Collection info: {info_result}")
        assert info_result["status"] == "success", f"Get collection info failed: {info_result}"
        
        # 9. 测试列出索引
        index_result = memory_service.list_indexes("test_collection")
        print(f"Indexes list: {index_result}")
        assert index_result["status"] == "success", f"List indexes failed: {index_result}"
        
        print("✅ All operations completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        traceback.print_exc()
        return False
        
    finally:
        # 清理资源
        try:
            # 清理测试数据目录
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
    
    success = test_memory_service()
    
    if success:
        print("\n🎉 All tests passed! Memory service system is working correctly.")
    else:
        print("\n💥 Tests failed! Please check the logs above.")
        exit(1)
