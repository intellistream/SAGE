"""
Memory Service API 使用示例
展示如何正确使用Memory微服务的API接口进行高级记忆管理
Memory服务作为编排服务，协调KV、VDB和Graph服务
"""
import numpy as np
import time
from sage.api.local_environment import LocalEnvironment
from sage.service import (
    create_kv_service_factory,
    create_vdb_service_factory, 
    create_graph_service_factory,
    create_memory_service_factory
)
from sage.service.api.memory_api import MemoryServiceAPI


def test_memory_service_api():
    """测试Memory服务API的正确使用方式"""
    print("🚀 Memory Service API Demo")
    print("=" * 60)
    
    # 创建环境
    env = LocalEnvironment("memory_service_demo")
    
    # 注册所有依赖的微服务
    print("📋 Registering microservices...")
    
    # KV服务
    kv_factory = create_kv_service_factory(
        service_name="demo_kv",
        backend_type="memory",
        max_size=10000
    )
    env.register_service("demo_kv", kv_factory)
    print("   ✅ KV Service registered")
    
    # VDB服务
    vdb_factory = create_vdb_service_factory(
        service_name="demo_vdb",
        embedding_dimension=384,
        index_type="IndexFlatL2"
    )
    env.register_service("demo_vdb", vdb_factory)
    print("   ✅ VDB Service registered")
    
    # Graph服务
    graph_factory = create_graph_service_factory(
        service_name="demo_graph",
        backend_type="memory",
        max_nodes=5000
    )
    env.register_service("demo_graph", graph_factory)
    print("   ✅ Graph Service registered")
    
    # Memory编排服务
    memory_factory = create_memory_service_factory(
        service_name="demo_memory",
        kv_service_name="demo_kv",
        vdb_service_name="demo_vdb",
        graph_service_name="demo_graph",
        enable_knowledge_graph=True
    )
    print("✅ All microservices registered successfully")
    
    # 在实际应用中，你需要启动环境并获取服务代理
    # env.submit()  # 启动环境
    # memory_service = env.get_service_proxy("demo_memory")
    
    # 这里我们演示API接口的预期使用方式
    demonstrate_memory_api_usage()


def demonstrate_memory_api_usage():
    """演示Memory服务API的标准使用模式"""
    print("\n📝 Memory Service API Usage Patterns:")
    print("-" * 50)
    
    # 展示API接口
    print("💡 Memory Service API Interface (High-level Orchestration):")
    print("   class MemoryServiceAPI:")
    print("     - store_memory(content, vector, session_id, ...) -> str")
    print("     - retrieve_memories(query_vector, session_id, ...) -> List[Dict]")
    print("     - get_memory(memory_id) -> Optional[Dict]")
    print("     - delete_memory(memory_id) -> bool")
    print("     - search_memories(query, session_id, ...) -> List[Dict]")
    print("     - get_session_memories(session_id) -> List[Dict]")
    print("     - clear_session_memories(session_id) -> bool")
    
    print("\n📋 Standard Usage Example:")
    usage_code = '''
# 1. 获取Memory服务代理（高级编排服务）
memory_service = env.get_service_proxy("demo_memory")

# 2. 存储对话记忆
session_id = "conversation_001"

# 存储用户问题
question_memory_id = memory_service.store_memory(
    content="用户询问：如何在Python中实现装饰器？",
    vector=embed_text("如何在Python中实现装饰器？"),  # 假设的embedding函数
    session_id=session_id,
    memory_type="user_question",
    metadata={
        "topic": "python",
        "difficulty": "intermediate",
        "timestamp": time.time()
    }
)

# 存储AI回答
answer_memory_id = memory_service.store_memory(
    content="AI回答：装饰器是Python中的高级特性，可以用来修改函数行为...",
    vector=embed_text("装饰器是Python中的高级特性..."),
    session_id=session_id,
    memory_type="ai_response",
    metadata={
        "topic": "python",
        "relates_to": question_memory_id,
        "code_examples": True
    }
)

# 3. 基于向量相似性检索相关记忆
query_vector = embed_text("Python函数装饰器的使用方法")
related_memories = memory_service.retrieve_memories(
    query_vector=query_vector,
    session_id=session_id,
    memory_type=None,  # 所有类型
    top_k=5
)

# 4. 基于文本搜索记忆
text_search_results = memory_service.search_memories(
    query="装饰器",
    session_id=session_id,
    memory_type="ai_response",
    top_k=10
)

# 5. 获取会话的完整记忆历史
session_history = memory_service.get_session_memories(session_id)

# 6. 获取特定记忆的详细信息
memory_detail = memory_service.get_memory(question_memory_id)
'''
    print(usage_code)
    
    # 模拟执行结果
    print("🎯 Expected Results:")
    operations = [
        ("store_memory(question)", "'mem_q_uuid_123'"),
        ("store_memory(answer)", "'mem_a_uuid_456'"),
        ("retrieve_memories(vector)", "[{'id': 'mem_q_123', 'score': 0.94, ...}]"),
        ("search_memories('装饰器')", "[{'id': 'mem_a_456', 'content': 'AI回答...', ...}]"),
        ("get_session_memories()", "[{'id': 'mem_q_123', ...}, {'id': 'mem_a_456', ...}]"),
        ("get_memory('mem_q_123')", "{'id': 'mem_q_123', 'content': '用户询问...', ...}"),
    ]
    
    for operation, result in operations:
        print(f"   {operation:<30} -> {result}")


def demonstrate_advanced_memory_patterns():
    """演示Memory服务的高级使用模式"""
    print("\n🧠 Advanced Memory Management Patterns:")
    print("-" * 50)
    
    advanced_patterns = '''
# 1. 智能对话上下文管理
class ConversationContextManager:
    def __init__(self, memory_service: MemoryServiceAPI):
        self.memory = memory_service
    
    def maintain_context(self, session_id: str, new_message: str, 
                        max_context_memories: int = 10):
        """维护对话上下文"""
        # 获取最近的记忆作为上下文
        recent_memories = self.memory.get_session_memories(session_id)
        context_memories = recent_memories[-max_context_memories:]
        
        # 基于新消息检索相关历史记忆
        message_vector = embed_text(new_message)
        relevant_memories = self.memory.retrieve_memories(
            query_vector=message_vector,
            session_id=session_id,
            top_k=5
        )
        
        # 组合上下文
        full_context = {
            "recent_memories": context_memories,
            "relevant_memories": relevant_memories,
            "current_message": new_message
        }
        
        return full_context

# 2. 知识图谱增强的记忆检索
class KnowledgeEnhancedRetrieval:
    def __init__(self, memory_service: MemoryServiceAPI):
        self.memory = memory_service
    
    def enhanced_retrieval(self, query: str, session_id: str):
        """增强的检索：结合向量相似性和知识图谱"""
        query_vector = embed_text(query)
        
        # 第一步：向量相似性检索
        vector_results = self.memory.retrieve_memories(
            query_vector=query_vector,
            session_id=session_id,
            top_k=20
        )
        
        # 第二步：文本检索
        text_results = self.memory.search_memories(
            query=query,
            session_id=session_id,
            top_k=20
        )
        
        # 第三步：知识图谱扩展（通过Memory服务的Graph集成）
        # Memory服务内部会自动利用知识图谱关系
        
        # 合并和去重结果
        all_results = self.merge_and_rank_results(vector_results, text_results)
        
        return all_results[:10]  # 返回top 10

# 3. 记忆生命周期管理
class MemoryLifecycleManager:
    def __init__(self, memory_service: MemoryServiceAPI):
        self.memory = memory_service
    
    def archive_old_memories(self, session_id: str, days_threshold: int = 30):
        """归档旧记忆"""
        cutoff_time = time.time() - (days_threshold * 24 * 3600)
        
        all_memories = self.memory.get_session_memories(session_id)
        old_memories = [
            mem for mem in all_memories 
            if mem.get("metadata", {}).get("timestamp", 0) < cutoff_time
        ]
        
        # 选择性保留重要记忆
        important_memories = self.filter_important_memories(old_memories)
        memories_to_delete = [
            mem for mem in old_memories if mem not in important_memories
        ]
        
        # 删除不重要的旧记忆
        for memory in memories_to_delete:
            self.memory.delete_memory(memory["id"])
        
        return len(memories_to_delete)
    
    def filter_important_memories(self, memories):
        """过滤重要记忆（基于metadata标记、用户反馈等）"""
        important = []
        for memory in memories:
            metadata = memory.get("metadata", {})
            if (metadata.get("importance") == "high" or 
                metadata.get("user_bookmarked") or
                metadata.get("memory_type") == "key_insight"):
                important.append(memory)
        return important

# 4. 多模态记忆存储
class MultiModalMemoryManager:
    def __init__(self, memory_service: MemoryServiceAPI):
        self.memory = memory_service
    
    def store_conversation_turn(self, session_id: str, user_message: str, 
                              ai_response: str, images=None, files=None):
        """存储多模态对话轮次"""
        turn_id = f"turn_{int(time.time())}"
        
        # 存储用户消息
        user_memory_id = self.memory.store_memory(
            content=user_message,
            vector=embed_text(user_message),
            session_id=session_id,
            memory_type="user_message",
            metadata={
                "turn_id": turn_id,
                "has_images": bool(images),
                "has_files": bool(files),
                "modalities": ["text"] + (["image"] if images else []) + (["file"] if files else [])
            }
        )
        
        # 存储AI回应
        ai_memory_id = self.memory.store_memory(
            content=ai_response,
            vector=embed_text(ai_response),
            session_id=session_id,
            memory_type="ai_response",
            metadata={
                "turn_id": turn_id,
                "responds_to": user_memory_id,
                "response_quality": "pending_evaluation"
            }
        )
        
        return turn_id, user_memory_id, ai_memory_id
'''
    print(advanced_patterns)
            "vector": np.random.random(384).tolist(),
            "memory_type": "answer",
            "metadata": {"topic": "programming", "language": "python", "complexity": "basic"}
        },
        {
            "content": "用户表示理解了，并询问更高级的主题",
            "vector": np.random.random(384).tolist(),
            "memory_type": "feedback",
            "metadata": {"sentiment": "positive", "next_topic": "advanced"}
        }
    ]
    
    print(f"\n🧠 Storing memories for session {session_id}:")
    memory_ids = []
    for i, memory in enumerate(memories):
        # memory_id = memory_service.store_memory(
        #     content=memory["content"],
        #     vector=memory["vector"],
        #     session_id=session_id,
        #     memory_type=memory["memory_type"],
        #     metadata=memory["metadata"],
        #     create_knowledge_graph=True
        # )
        memory_id = f"mem_{i+1}"  # 模拟返回的ID
        memory_ids.append(memory_id)
        print(f"   ✅ Stored {memory['memory_type']}: {memory_id}")
    
    # 模拟记忆搜索
    print(f"\n🔍 Searching memories:")
    query_vector = np.random.random(384).tolist()
    
    # search_results = memory_service.search_memories(
    #     query_vector=query_vector,
    #     session_id=session_id,
    #     limit=5,
    #     include_graph_context=True
    # )
    
    # 模拟搜索结果
    search_results = [
        {
            "id": "mem_2",
            "content": "AI助手提供了Python基础语法的详细解释",
            "similarity_score": 0.85,
            "memory_type": "answer",
            "graph_context": {
                "related_nodes": ["topic:python", "user:conversation_001"],
                "relationships": ["ABOUT", "IN_SESSION"]
            }
        },
        {
            "id": "mem_1", 
            "content": "用户询问了关于Python编程的问题",
            "similarity_score": 0.82,
            "memory_type": "question",
            "graph_context": {
                "related_nodes": ["topic:python", "user:conversation_001"],
                "relationships": ["ASKS_ABOUT", "IN_SESSION"]
            }
        }
    ]
    
    print(f"   📖 Found {len(search_results)} relevant memories:")
    for result in search_results:
        print(f"      - {result['memory_type']}: {result['content'][:50]}...")
        print(f"        相似度: {result['similarity_score']:.3f}")
        print(f"        图上下文: {len(result['graph_context']['related_nodes'])} 相关节点")
    
    # 模拟会话记忆分析
    print(f"\n📊 Session Analysis:")
    
    # session_analysis = memory_service.get_session_memories(
    #     session_id=session_id,
    #     include_graph_analysis=True
    # )
    
    session_analysis = {
        "session_id": session_id,
        "memory_count": 3,
        "memory_types": {"question": 1, "answer": 1, "feedback": 1},
        "graph_analysis": {
            "topics_discussed": ["python", "programming"],
            "conversation_flow": "question -> answer -> feedback",
            "sentiment_trend": "neutral -> positive",
            "knowledge_gaps": ["advanced topics"]
        }
    }
    
    print(f"   📈 Session Statistics:")
    print(f"      - 总记忆数: {session_analysis['memory_count']}")
    print(f"      - 记忆类型: {session_analysis['memory_types']}")
    print(f"      - 讨论主题: {', '.join(session_analysis['graph_analysis']['topics_discussed'])}")
    print(f"      - 对话流程: {session_analysis['graph_analysis']['conversation_flow']}")
    print(f"      - 情感趋势: {session_analysis['graph_analysis']['sentiment_trend']}")
    
    print("\n💡 Memory Service Features:")
    print("   - 统一记忆管理接口")
    print("   - 自动知识图谱构建")  
    print("   - 语义搜索和过滤")
    print("   - 会话上下文分析")
    print("   - 跨服务事务一致性")
    print("   - 图增强的记忆检索")


def test_memory_use_cases():
    """演示Memory服务的应用场景"""
    print("\n🎯 Memory Service Use Cases:")
    
    use_cases = [
        {
            "name": "智能客服",
            "scenario": "记住用户历史问题，提供个性化答案",
            "memory_types": ["question", "answer", "preference", "issue"],
            "features": ["上下文理解", "问题追踪", "解决方案推荐"]
        },
        {
            "name": "个人助手",
            "scenario": "学习用户习惯，提供主动建议",
            "memory_types": ["habit", "preference", "schedule", "goal"],
            "features": ["习惯分析", "日程优化", "目标跟踪"]
        },
        {
            "name": "教育系统",
            "scenario": "跟踪学习进度，个性化教学路径",
            "memory_types": ["knowledge", "skill", "progress", "difficulty"],
            "features": ["知识图谱", "学习路径", "难点识别"]
        },
        {
            "name": "内容推荐",
            "scenario": "基于用户兴趣历史推荐相关内容",
            "memory_types": ["interest", "interaction", "content", "feedback"],
            "features": ["兴趣建模", "内容关联", "反馈学习"]
        }
    ]
    
    for case in use_cases:
        print(f"  📚 {case['name']}: {case['scenario']}")
        print(f"      记忆类型: {', '.join(case['memory_types'])}")
        print(f"      核心功能: {', '.join(case['features'])}")


def test_memory_advantages():
    """展示Memory服务相比单一服务的优势"""
    print("\n🌟 Memory Service Advantages:")
    
    advantages = [
        {
            "aspect": "统一接口",
            "description": "单一API调用，自动协调KV、VDB、Graph服务",
            "benefit": "简化应用开发，减少集成复杂度"
        },
        {
            "aspect": "事务一致性", 
            "description": "确保数据在多个服务间的一致性",
            "benefit": "避免数据不一致，提高可靠性"
        },
        {
            "aspect": "图增强检索",
            "description": "结合向量相似性和图关系进行检索",
            "benefit": "更准确的上下文理解和推荐"
        },
        {
            "aspect": "自动索引",
            "description": "自动维护各服务间的关联关系",
            "benefit": "减少手动维护，提高数据质量"
        },
        {
            "aspect": "智能分析",
            "description": "提供跨服务的综合分析能力",
            "benefit": "深度洞察，支持决策"
        }
    ]
    
    for adv in advantages:
        print(f"  ⭐ {adv['aspect']}: {adv['description']}")
        print(f"      价值: {adv['benefit']}")


if __name__ == "__main__":
    test_memory_service_api()
    demonstrate_advanced_memory_patterns()
    print("\n🎯 Memory Service API demo completed!")
    print("\n📚 Next: Check the complete API tutorial for integration examples")
