"""
SAGE Services API Usage Tutorial
展示如何正确使用SAGE微服务的API接口
"""
import asyncio
import numpy as np
from typing import List, Dict, Any

# 导入API接口
from sage.service.api import KVServiceAPI, VDBServiceAPI, MemoryServiceAPI, GraphServiceAPI

# 导入具体服务实现和工厂函数
from sage.service import (
    KVService, VDBService, MemoryService, GraphService,
    create_kv_service_factory, create_vdb_service_factory, 
    create_memory_service_factory, create_graph_service_factory
)
from sage.kernel.api.local_environment import LocalEnvironment


class ServiceAPITutorial:
    """SAGE服务API使用教程"""
    
    def __init__(self):
        self.env = LocalEnvironment("api_tutorial_demo")
        self.setup_services()
    
    def setup_services(self):
        """设置所有服务"""
        print("🚀 Setting up SAGE Services for API Tutorial")
        print("=" * 60)
        
        # 注册KV服务
        kv_factory = create_kv_service_factory(
            service_name="tutorial_kv",
            backend_type="memory",
            max_size=10000
        )
        self.env.register_service_factory("tutorial_kv", kv_factory)
        
        # 注册VDB服务
        vdb_factory = create_vdb_service_factory(
            service_name="tutorial_vdb",
            embedding_dimension=384,
            max_vectors=10000
        )
        self.env.register_service_factory("tutorial_vdb", vdb_factory)
        
        # 注册Memory服务
        memory_factory = create_memory_service_factory(
            service_name="tutorial_memory",
            kv_service_name="tutorial_kv",
            vdb_service_name="tutorial_vdb"
        )
        self.env.register_service_factory("tutorial_memory", memory_factory)
        
        print("✅ All services registered successfully")
    
    def demonstrate_kv_api(self):
        """演示KV API的正确使用方式"""
        print("\n📦 KV Service API Tutorial")
        print("-" * 40)
        
        # 在实际应用中，你会从环境中获取服务代理
        # 这里我们模拟API调用的预期行为
        
        print("💡 KV Service API Interface:")
        print("   - put(key, value) -> bool")
        print("   - get(key) -> Any")
        print("   - delete(key) -> bool")
        print("   - exists(key) -> bool")
        print("   - list_keys(prefix) -> List[str]")
        print("   - size() -> int")
        print("   - clear() -> bool")
        
        print("\n📝 Expected Usage Pattern:")
        usage_example = '''
# 获取KV服务代理
kv_service = env.get_service_proxy("tutorial_kv")

# 基本操作
success = kv_service.put("user:123", {"name": "Alice", "age": 30})
user_data = kv_service.get("user:123")
exists = kv_service.exists("user:123")

# 批量操作
keys = kv_service.list_keys("user:")
total_size = kv_service.size()

# 删除操作
deleted = kv_service.delete("user:123")
'''
        print(usage_example)
        
        # 模拟执行结果
        print("🎯 Expected Results:")
        print("   put() -> True")
        print("   get() -> {'name': 'Alice', 'age': 30}")
        print("   exists() -> True")
        print("   list_keys('user:') -> ['user:123']")
        print("   size() -> 1")
        print("   delete() -> True")
    
    def demonstrate_vdb_api(self):
        """演示VDB API的正确使用方式"""
        print("\n🗂️ VDB Service API Tutorial")
        print("-" * 40)
        
        print("💡 VDB Service API Interface:")
        print("   - add_vectors(documents) -> List[str]")
        print("   - search(query_vector, top_k, threshold) -> List[Dict]")
        print("   - get_vector(doc_id) -> Dict")
        print("   - delete_vectors(doc_ids) -> bool")
        print("   - update_vector(doc_id, document) -> bool")
        print("   - count() -> int")
        print("   - save_index(path) -> bool")
        print("   - load_index(path) -> bool")
        
        print("\n📝 Expected Usage Pattern:")
        usage_example = '''
# 获取VDB服务代理
vdb_service = env.get_service_proxy("tutorial_vdb")

# 添加向量文档
documents = [{
    "id": "doc_001",
    "vector": [0.1, 0.2, 0.3, ...],  # 384维向量
    "text": "这是一个示例文档",
    "metadata": {"category": "example"}
}]
doc_ids = vdb_service.add_vectors(documents)

# 向量搜索
query_vector = [0.1, 0.2, 0.3, ...]  # 查询向量
results = vdb_service.search(
    query_vector=query_vector,
    top_k=5,
    similarity_threshold=0.8
)

# 获取特定文档
document = vdb_service.get_vector("doc_001")

# 更新和删除
updated = vdb_service.update_vector("doc_001", new_document)
deleted = vdb_service.delete_vectors(["doc_001"])
'''
        print(usage_example)
        
        print("🎯 Expected Results:")
        print("   add_vectors() -> ['doc_001']")
        print("   search() -> [{'id': 'doc_001', 'score': 0.95, ...}]")
        print("   get_vector() -> {'id': 'doc_001', 'vector': [...], ...}")
        print("   count() -> 1")
    
    def demonstrate_memory_api(self):
        """演示Memory API的正确使用方式"""
        print("\n🧠 Memory Service API Tutorial")
        print("-" * 40)
        
        print("💡 Memory Service API Interface (High-level):")
        print("   - store_memory(content, vector, session_id, ...) -> str")
        print("   - retrieve_memories(query_vector, session_id, ...) -> List[Dict]")
        print("   - get_memory(memory_id) -> Dict")
        print("   - delete_memory(memory_id) -> bool")
        print("   - search_memories(query, session_id, ...) -> List[Dict]")
        print("   - get_session_memories(session_id) -> List[Dict]")
        print("   - clear_session_memories(session_id) -> bool")
        
        print("\n📝 Expected Usage Pattern:")
        usage_example = '''
# 获取Memory服务代理（高级编排服务）
memory_service = env.get_service_proxy("tutorial_memory")

# 存储记忆（自动同时存储到KV和VDB）
memory_id = memory_service.store_memory(
    content="用户询问了关于Python的问题",
    vector=[0.1, 0.2, 0.3, ...],  # 内容的向量表示
    session_id="session_123",
    memory_type="conversation",
    metadata={"topic": "programming", "language": "python"}
)

# 检索相关记忆（基于向量相似性）
related_memories = memory_service.retrieve_memories(
    query_vector=[0.1, 0.2, 0.3, ...],
    session_id="session_123",
    top_k=5
)

# 文本搜索记忆
search_results = memory_service.search_memories(
    query="Python",
    session_id="session_123",
    top_k=10
)

# 获取会话的所有记忆
session_memories = memory_service.get_session_memories("session_123")
'''
        print(usage_example)
        
        print("🎯 Expected Results:")
        print("   store_memory() -> 'memory_uuid_123'")
        print("   retrieve_memories() -> [{'id': 'memory_uuid_123', 'score': 0.92, ...}]")
        print("   search_memories() -> [{'id': 'memory_uuid_123', 'content': '...', ...}]")
    
    def demonstrate_api_composition(self):
        """演示如何组合使用多个API"""
        print("\n🔗 API Composition Tutorial")
        print("-" * 40)
        
        print("💡 实际应用场景: 智能问答系统")
        
        composition_example = '''
class IntelligentQASystem:
    """智能问答系统 - 展示API组合使用"""
    
    def __init__(self, env):
        # 获取各种服务代理
        self.kv_service = env.get_service_proxy("tutorial_kv")
        self.vdb_service = env.get_service_proxy("tutorial_vdb")
        self.memory_service = env.get_service_proxy("tutorial_memory")
    
    async def process_question(self, user_id: str, question: str):
        """处理用户问题"""
        
        # 1. 从KV服务获取用户上下文
        user_context = self.kv_service.get(f"user_context:{user_id}")
        
        # 2. 将问题转换为向量（使用embedding工具）
        question_vector = embed_text(question)  # 假设的embedding函数
        
        # 3. 使用Memory服务检索相关记忆
        related_memories = self.memory_service.retrieve_memories(
            query_vector=question_vector,
            session_id=user_context.get("session_id"),
            top_k=5
        )
        
        # 4. 直接在VDB中搜索知识库
        knowledge_results = self.vdb_service.search(
            query_vector=question_vector,
            top_k=10,
            similarity_threshold=0.7
        )
        
        # 5. 生成回答（使用LLM）
        answer = generate_answer(question, related_memories, knowledge_results)
        
        # 6. 存储新的对话记忆
        self.memory_service.store_memory(
            content=f"Q: {question}\\nA: {answer}",
            vector=question_vector,
            session_id=user_context.get("session_id"),
            memory_type="qa_pair"
        )
        
        # 7. 更新用户上下文
        user_context["last_question"] = question
        self.kv_service.put(f"user_context:{user_id}", user_context)
        
        return answer
'''
        print(composition_example)
        
        print("\n🎯 这个例子展示了:")
        print("   ✅ KV服务用于快速的上下文存取")
        print("   ✅ VDB服务用于语义相似性搜索")
        print("   ✅ Memory服务用于高级记忆管理")
        print("   ✅ 各服务协同工作完成复杂任务")
    
    def demonstrate_error_handling(self):
        """演示API错误处理最佳实践"""
        print("\n⚠️ Error Handling Best Practices")
        print("-" * 40)
        
        error_handling_example = '''
# 正确的错误处理方式
try:
    # 尝试获取服务代理
    kv_service = env.get_service_proxy("tutorial_kv")
    
    # API调用
    result = kv_service.get("some_key")
    if result is None:
        print("Key not found")
    else:
        print(f"Retrieved: {result}")
        
except ServiceNotAvailableError:
    print("KV service is not available")
except ServiceTimeoutError:
    print("KV service call timed out")
except Exception as e:
    print(f"Unexpected error: {e}")

# 批量操作的错误处理
documents = [...]  # 大量文档
batch_size = 100

for i in range(0, len(documents), batch_size):
    batch = documents[i:i+batch_size]
    try:
        doc_ids = vdb_service.add_vectors(batch)
        print(f"Successfully added batch {i//batch_size + 1}")
    except Exception as e:
        print(f"Failed to add batch {i//batch_size + 1}: {e}")
        # 可以选择重试或跳过
'''
        print(error_handling_example)
    
    def run_tutorial(self):
        """运行完整的API教程"""
        print("🎓 SAGE Services API Complete Tutorial")
        print("=" * 60)
        
        self.demonstrate_kv_api()
        self.demonstrate_vdb_api()
        self.demonstrate_memory_api()
        self.demonstrate_api_composition()
        self.demonstrate_error_handling()
        
        print("\n🎉 Tutorial Complete!")
        print("\n📚 Next Steps:")
        print("   1. 查看具体服务的实现代码")
        print("   2. 运行真实的集成测试")
        print("   3. 在你的项目中集成SAGE服务")
        print("   4. 参考API文档了解更多细节")


def main():
    """主函数"""
    tutorial = ServiceAPITutorial()
    tutorial.run_tutorial()


if __name__ == "__main__":
    main()
