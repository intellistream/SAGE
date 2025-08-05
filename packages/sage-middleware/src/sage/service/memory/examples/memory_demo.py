"""
Memory Service 使用示例
展示如何使用Memory微服务进行高级记忆管理，协调KV、VDB和Graph服务
"""
import numpy as np
import time
from sage.core.api.local_environment import LocalEnvironment
from sage.service import (
    create_kv_service_factory,
    create_vdb_service_factory, 
    create_graph_service_factory,
    create_memory_service_factory
)


def test_memory_service():
    """测试Memory编排服务"""
    print("🚀 Memory Service Demo")
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
    env.register_service("demo_memory", memory_factory)
    print("   ✅ Memory Service registered")
    
    print("\n📝 Memory Operations Demo:")
    
    # 模拟会话记忆存储
    session_id = "conversation_001"
    memories = [
        {
            "content": "用户询问了关于Python编程的问题",
            "vector": np.random.random(384).tolist(),
            "memory_type": "question",
            "metadata": {"topic": "programming", "language": "python"}
        },
        {
            "content": "AI助手提供了Python基础语法的详细解释",
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
    test_memory_service()
    test_memory_use_cases()
    test_memory_advantages()
    print("\n🎯 Memory Service demo completed!")
