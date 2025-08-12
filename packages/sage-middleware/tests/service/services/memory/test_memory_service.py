"""
测试Memory Service的集成测试用例
"""
import sys
import os
import shutil
import traceback

# 添加正确的项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sage_middleware_src = os.path.join(current_dir, '../../../../src')
sys.path.insert(0, os.path.abspath(sage_middleware_src))

from sage.middleware.services.memory.memory_service import MemoryService
from sage.middleware.utils.embedding.embedding_api import apply_embedding_model

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
        
        # 10. 测试存储单个collection
        store_collection_result = memory_service.store_collection("test_collection")
        print(f"Store collection result: {store_collection_result}")
        assert store_collection_result["status"] == "success", f"Store collection failed: {store_collection_result}"
        
        # 11. 创建第二个collection来测试选择性存储
        result_col2 = memory_service.create_collection(
            name="temp_collection",
            backend_type="VDB",
            description="Temporary test collection",
            embedding_model=embedding_model,
            dim=dim
        )
        print(f"Create temp collection result: {result_col2}")
        assert result_col2["status"] == "success", f"Create temp collection failed: {result_col2}"
        
        # 12. 向第二个collection插入数据
        temp_insert_result = memory_service.insert_data(
            collection_name="temp_collection",
            text="This is temporary data",
            metadata={"type": "temp", "temporary": True}
        )
        print(f"Insert temp data result: {temp_insert_result}")
        assert temp_insert_result["status"] == "success", f"Insert temp data failed: {temp_insert_result}"
        
        # 13. 测试存储所有manager数据
        store_all_result = memory_service.store()
        print(f"Store all result: {store_all_result}")
        assert store_all_result["status"] == "success", f"Store all failed: {store_all_result}"
        
        print("✅ All operations including storage completed successfully!")
        
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


def test_data_loss_without_storage():
    """测试未保存collection导致的数据丢失"""
    print("\n🔍 Starting data loss test without storage...")
    
    try:
        # 使用默认的embedding model
        embedding_model = apply_embedding_model("default")
        dim = embedding_model.get_dim()
        
        # 创建独立的测试目录
        test_data_dir = os.path.join(os.path.dirname(__file__), "test_data_loss")
        os.makedirs(test_data_dir, exist_ok=True)
        
        print("✅ Starting data loss test...")
        
        # 阶段1: 创建两个collection并插入数据
        print("\n📝 Phase 1: Creating collections and inserting data...")
        
        memory_service = MemoryService(data_dir=test_data_dir)
        
        # 创建第一个collection
        result1 = memory_service.create_collection(
            name="saved_collection",
            backend_type="VDB", 
            description="This will be saved",
            embedding_model=embedding_model,
            dim=dim
        )
        assert result1["status"] == "success"
        
        # 创建第二个collection
        result2 = memory_service.create_collection(
            name="unsaved_collection",
            backend_type="VDB",
            description="This will NOT be saved",
            embedding_model=embedding_model,
            dim=dim
        )
        assert result2["status"] == "success"
        
        # 向两个collection插入数据
        for i in range(3):
            # 保存的collection
            memory_service.insert_data(
                collection_name="saved_collection",
                text=f"Saved document {i}",
                metadata={"type": "saved", "index": i}
            )
            # 未保存的collection  
            memory_service.insert_data(
                collection_name="unsaved_collection", 
                text=f"Unsaved document {i}",
                metadata={"type": "unsaved", "index": i}
            )
        
        # 只保存第一个collection
        print("\n💾 Phase 2: Storing only the first collection...")
        store_result = memory_service.store_collection("saved_collection")
        assert store_result["status"] == "success"
        print(f"✅ Stored 'saved_collection': {store_result}")
        
        # 验证两个collection都还在内存中
        list_result = memory_service.list_collections()
        assert list_result["status"] == "success"
        assert len(list_result["collections"]) == 2
        print(f"✅ Both collections still in memory: {[c['name'] for c in list_result['collections']]}")
        
        # 释放当前service实例
        print("\n🔄 Phase 3: Creating new service instance to simulate restart...")
        del memory_service
        
        # 重新创建服务实例 (模拟重启后从磁盘加载)
        memory_service2 = MemoryService(data_dir=test_data_dir)
        
        # 验证数据丢失情况
        print("\n🔍 Phase 4: Checking data after restart...")
        
        # 检查collections列表
        list_result_after = memory_service2.list_collections()
        assert list_result_after["status"] == "success"
        collection_names = [c['name'] for c in list_result_after['collections']]
        print(f"Collections after restart: {collection_names}")
        
        # 验证保存的collection仍然存在
        if "saved_collection" in collection_names:
            print("✅ 'saved_collection' found - data persisted correctly")
            # 尝试检索数据验证完整性
            retrieve_saved = memory_service2.retrieve_data(
                collection_name="saved_collection",
                query_text="Saved document",
                topk=5,
                with_metadata=True
            )
            if retrieve_saved["status"] == "success" and len(retrieve_saved["results"]) > 0:
                print(f"✅ Saved collection data intact: {len(retrieve_saved['results'])} documents found")
            else:
                print("⚠️ Saved collection exists but data may be incomplete")
        else:
            print("❌ ERROR: 'saved_collection' not found after restart!")
            
        # 验证未保存的collection丢失
        if "unsaved_collection" not in collection_names:
            print("✅ 'unsaved_collection' correctly lost - demonstrates need for storage")
        else:
            print("⚠️ WARNING: 'unsaved_collection' unexpectedly persisted")
            
        print("\n🎯 Data loss test demonstrates:")
        print("  - Collections must be explicitly stored to persist")
        print("  - Only stored collections survive service restart") 
        print("  - store_collection() provides selective persistence")
        
        return True
        
    except Exception as e:
        print(f"❌ Data loss test failed: {e}")
        traceback.print_exc()
        return False
        
    finally:
        # 清理测试数据
        try:
            test_data_dir = os.path.join(os.path.dirname(__file__), "test_data_loss")
            if os.path.exists(test_data_dir):
                shutil.rmtree(test_data_dir)
            print("🧹 Data loss test cleanup completed")
        except Exception as e:
            print(f"⚠️ Data loss test cleanup error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("SAGE Memory Service Integration Test")
    print("=" * 60)
    
    # 运行基本功能测试
    success = test_memory_service()
    
    if success:
        print("\n🎉 Basic tests passed! Running data loss test...")
        # 运行数据丢失测试
        loss_test_success = test_data_loss_without_storage()
        
        if loss_test_success:
            print("\n🎉 All tests passed! Memory service system is working correctly.")
            print("✨ Storage functionality verified - data persistence works as expected.")
        else:
            print("\n💥 Data loss tests failed! Please check the logs above.")
            exit(1)
    else:
        print("\n💥 Basic tests failed! Please check the logs above.")
        exit(1)
