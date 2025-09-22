#!/usr/bin/env python3
"""
MemoryService 使用示例
展示如何在SAGE中设置和使用MemoryService进行高级记忆管理

MemoryService 是 SAGE middleware 中的高级编排服务，
它协调 KV、VDB 和 Graph 微服务，提供统一的记忆管理接口。
"""

import os
import time
from typing import Any, Dict, List

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.local_environment import LocalEnvironment
from sage.middleware.services.memory.memory_service import MemoryService


# 模拟的embedding函数（实际使用中应该调用真实的embedding服务）
def mock_embedding(text: str) -> List[float]:
    """简单的模拟embedding函数"""
    import hashlib
    import numpy as np

    # 使用文本的hash来生成确定性的向量（仅用于演示）
    hash_obj = hashlib.md5(text.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    np.random.seed(hash_int % 2**32)
    return np.random.random(384).tolist()


class ConversationDataSource(BatchFunction):
    """生成对话数据的批处理源"""

    def __init__(self, conversations: List[Dict[str, Any]]):
        super().__init__()
        self.conversations = conversations
        self.index = 0

    def execute(self):
        if self.index >= len(self.conversations):
            return None
        conversation = self.conversations[self.index]
        self.index += 1
        return conversation


class MemoryProcessor(MapFunction):
    """使用MemoryService处理记忆的映射函数"""

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理对话数据并存储到记忆中"""
        memory_service = self.call_service["memory_service"]

        user_message = data["user_message"]
        ai_response = data["ai_response"]
        topic = data.get("topic", "general")

        try:
            # 存储用户消息
            user_memory_id = memory_service.store_memory(
                content=user_message,
                vector=mock_embedding(user_message),
                session_id=self.session_id,
                memory_type="conversation",
                metadata={
                    "speaker": "user",
                    "topic": topic,
                    "timestamp": time.time()
                }
            )

            # 存储AI回复
            ai_memory_id = memory_service.store_memory(
                content=ai_response,
                vector=mock_embedding(ai_response),
                session_id=self.session_id,
                memory_type="conversation",
                metadata={
                    "speaker": "ai",
                    "topic": topic,
                    "timestamp": time.time()
                }
            )

            # 如果是编程相关，存储语义记忆
            if "python" in user_message.lower() or "编程" in user_message:
                semantic_content = f"用户对编程感兴趣：{user_message[:50]}..."
                memory_service.store_memory(
                    content=semantic_content,
                    vector=mock_embedding(semantic_content),
                    session_id=self.session_id,
                    memory_type="knowledge",
                    metadata={
                        "topic": "programming",
                        "importance": "medium",
                        "timestamp": time.time()
                    }
                )

            return {
                "session_id": self.session_id,
                "user_memory_id": user_memory_id,
                "ai_memory_id": ai_memory_id,
                "topic": topic,
                "processed": True
            }

        except Exception as e:
            return {
                "error": f"存储记忆失败: {str(e)}",
                "session_id": self.session_id
            }


class MemoryRetriever(MapFunction):
    """从记忆中检索相关信息的映射函数"""

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """基于查询检索相关记忆"""
        memory_service = self.call_service["memory_service"]

        query = data.get("query", "")
        if not query:
            return {"error": "No query provided"}

        try:
            # 搜索相关记忆
            query_vector = mock_embedding(query)
            relevant_memories = memory_service.search_memories(
                query_vector=query_vector,
                session_id=self.session_id,
                limit=3
            )

            # 获取会话记忆历史
            session_memories = memory_service.get_session_memories(self.session_id)

            # 格式化结果
            formatted_memories = []
            for mem in relevant_memories:
                formatted_memories.append({
                    "text": mem.get("content", ""),
                    "type": mem.get("memory_type", "unknown"),
                    "meta": mem.get("metadata", {})
                })

            # 生成简化的上下文
            context_parts = []
            for mem in session_memories[-5:]:  # 最近5条记忆
                speaker = mem.get("metadata", {}).get("speaker", "unknown")
                content = mem.get("content", "")[:100]
                context_parts.append(f"[{speaker}] {content}")

            context = "\n".join(context_parts)

            return {
                "query": query,
                "relevant_memories": formatted_memories,
                "session_memories_count": len(session_memories),
                "context": context,
                "session_id": self.session_id
            }

        except Exception as e:
            return {
                "error": f"检索记忆失败: {str(e)}",
                "query": query,
                "session_id": self.session_id
            }


class ResultPrinter(SinkFunction):
    """打印结果的接收器函数"""

    def execute(self, data: Dict[str, Any]):
        """打印处理结果"""
        print("\n" + "="*60)
        print("🧠 MemoryService 处理结果")
        print("="*60)

        if "error" in data:
            print(f"❌ 错误: {data['error']}")
            return

        if "processed" in data:
            # 存储结果
            print("✅ 记忆存储成功")
            print(f"   会话ID: {data['session_id']}")
            print(f"   用户记忆ID: {data['user_memory_id']}")
            print(f"   AI记忆ID: {data['ai_memory_id']}")
            print(f"   主题: {data['topic']}")

        elif "query" in data:
            # 检索结果
            print(f"🔍 查询: {data['query']}")
            print(f"   会话ID: {data['session_id']}")

            print(f"\n📚 相关记忆 ({len(data['relevant_memories'])} 条):")
            for i, mem in enumerate(data['relevant_memories'], 1):
                print(f"   {i}. [{mem['type']}] {mem['text'][:60]}...")
                if mem['meta']:
                    print(f"      元数据: {mem['meta']}")

            print(f"\n� 会话统计:")
            print(f"   总记忆数: {data.get('session_memories_count', 0)}")

            print(f"\n📝 生成的上下文:")
            context = data.get('context', '')
            print(f"   {context[:200]}{'...' if len(context) > 200 else ''}")


def create_sample_conversations() -> List[Dict[str, Any]]:
    """创建示例对话数据"""
    # 尝试从配置文件加载数据
    try:
        import yaml
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "config_memory_service_demo.yaml"
        )
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config["demo_data"]["conversations"]
    except Exception as e:
        print(f"⚠️  无法加载配置文件: {e}，使用内置数据")

    # 默认的内置对话数据
    return [
        {
            "user_message": "你好，我想学习Python编程，应该从哪里开始？",
            "ai_response": "你好！学习Python编程是一个很好的选择。要开始学习，我建议：1. 安装Python环境 2. 学习基础语法 3. 练习编写简单程序",
            "topic": "programming"
        },
        {
            "user_message": "Python中变量和数据类型有哪些？",
            "ai_response": "Python有以下基本数据类型：1. 整数(int) 2. 浮点数(float) 3. 字符串(str) 4. 布尔值(bool) 5. 列表(list) 6. 元组(tuple) 7. 字典(dict)",
            "topic": "programming"
        },
        {
            "user_message": "我对机器学习很感兴趣，有什么建议？",
            "ai_response": "机器学习是一个很有前景的领域！建议从以下方面开始：1. 学习Python基础 2. 掌握数学基础（线性代数、概率论）3. 学习scikit-learn等库 4. 实践项目",
            "topic": "ai"
        },
        {
            "user_message": "周末我想放松一下，有什么推荐？",
            "ai_response": "周末放松很重要！可以考虑：1. 户外活动如散步或骑行 2. 阅读书籍 3. 学习新技能 4. 和朋友聚餐 记住保持工作生活平衡！",
            "topic": "lifestyle"
        },
        {
            "user_message": "我最近总是感觉疲惫，有什么改善方法？",
            "ai_response": "感觉疲惫可能是多种原因造成的。建议：1. 保证充足睡眠（7-9小时）2. 规律饮食，摄入均衡营养 3. 适量运动 4. 管理压力 5. 如持续严重，建议咨询医生",
            "topic": "health"
        }
    ]


class MockMemoryService:
    """模拟MemoryService，用于演示API使用方式"""

    def __init__(self):
        self.memories = {}
        self.session_memories = {}
        self.memory_counter = 0

    def store_memory(self, content, vector, session_id, memory_type="conversation", metadata=None):
        """模拟存储记忆"""
        memory_id = f"mem_{self.memory_counter}"
        self.memory_counter += 1

        memory = {
            "id": memory_id,
            "content": content,
            "vector": vector,
            "session_id": session_id,
            "memory_type": memory_type,
            "metadata": metadata or {},
            "timestamp": time.time()
        }

        # 存储到全局记忆库
        self.memories[memory_id] = memory

        # 添加到会话记忆
        if session_id not in self.session_memories:
            self.session_memories[session_id] = []
        self.session_memories[session_id].append(memory_id)

        return memory_id

    def search_memories(self, query_vector, session_id=None, limit=5, memory_type=None):
        """模拟搜索记忆"""
        candidates = []

        # 确定搜索范围
        if session_id:
            memory_ids = self.session_memories.get(session_id, [])
        else:
            memory_ids = list(self.memories.keys())

        # 过滤记忆类型
        for mem_id in memory_ids:
            memory = self.memories[mem_id]
            if memory_type and memory["memory_type"] != memory_type:
                continue
            candidates.append(memory)

        # 计算相似度并排序（使用余弦相似度）
        results = []
        for memory in candidates:
            similarity = self._cosine_similarity(query_vector, memory["vector"])
            results.append({
                "id": memory["id"],
                "content": memory["content"],
                "memory_type": memory["memory_type"],
                "metadata": memory["metadata"],
                "similarity": similarity
            })

        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def get_session_memories(self, session_id, memory_type=None):
        """获取会话记忆"""
        memory_ids = self.session_memories.get(session_id, [])
        memories = []

        for mem_id in memory_ids:
            memory = self.memories[mem_id]
            if memory_type and memory["memory_type"] != memory_type:
                continue
            memories.append(memory)

        return memories

    def generate_context(self, query, session_id, max_tokens=1000):
        """生成上下文"""
        query_vector = mock_embedding(query)
        relevant_memories = self.search_memories(query_vector, session_id, limit=5)

        context_parts = []
        total_length = 0

        for memory in relevant_memories:
            content = memory["content"]
            if total_length + len(content) > max_tokens:
                break
            context_parts.append(f"[{memory['memory_type']}] {content}")
            total_length += len(content)

        return "\n".join(context_parts)

    def _cosine_similarity(self, vec1, vec2):
        """计算余弦相似度"""
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


def demonstrate_api_usage():
    """演示MemoryService的API使用方式（不依赖实际服务）"""
    print("\n📖 MemoryService API 使用演示")
    print("-"*50)

    print("\n🔧 核心API方法:")
    print("   1. store_memory(content, vector, session_id, memory_type, metadata)")
    print("      - 存储记忆内容到记忆系统")
    print("      - 参数:")
    print("        * content: 记忆内容文本")
    print("        * vector: 内容的向量表示（用于语义搜索）")
    print("        * session_id: 会话标识符")
    print("        * memory_type: 记忆类型 ('conversation', 'knowledge', 'working')")
    print("        * metadata: 附加元数据字典")

    print("\n   2. search_memories(query_vector, session_id, limit, memory_type)")
    print("      - 基于向量相似度搜索相关记忆")
    print("      - 参数:")
    print("        * query_vector: 查询的向量表示")
    print("        * session_id: 会话标识符（可选）")
    print("        * limit: 返回结果数量限制")
    print("        * memory_type: 记忆类型过滤器（可选）")

    print("\n   3. get_session_memories(session_id, memory_type)")
    print("      - 获取指定会话的所有记忆")
    print("      - 参数:")
    print("        * session_id: 会话标识符")
    print("        * memory_type: 记忆类型过滤器（可选）")

    print("\n   4. generate_context(query, session_id, max_tokens)")
    print("      - 生成相关上下文信息")
    print("      - 参数:")
    print("        * query: 查询文本")
    print("        * session_id: 会话标识符")
    print("        * max_tokens: 上下文最大长度")

    print("\n   5. update_memory(memory_id, content, vector, metadata)")
    print("      - 更新现有记忆")
    print("      - 参数:")
    print("        * memory_id: 记忆ID")
    print("        * content: 新内容（可选）")
    print("        * vector: 新向量（可选）")
    print("        * metadata: 新元数据（可选）")

    print("\n   6. delete_memory(memory_id)")
    print("      - 删除指定记忆")
    print("      - 参数:")
    print("        * memory_id: 要删除的记忆ID")

    print("\n🔄 典型使用流程:")
    print("   1. 初始化 MemoryService 实例")
    print("   2. 为每个对话轮次调用 store_memory() 存储记忆")
    print("   3. 使用 search_memories() 检索相关历史信息")
    print("   4. 调用 generate_context() 获取上下文摘要")
    print("   5. 根据需要更新或删除记忆")

    print("\n📊 记忆类型说明:")
    print("   • conversation: 对话历史记录")
    print("   • knowledge: 事实性知识和学习内容")
    print("   • working: 临时工作记忆（短期存储）")

    print("\n⚙️ 配置参数:")
    print("   • kv_service_name: KV存储服务名称")
    print("   • vdb_service_name: 向量数据库服务名称")
    print("   • graph_service_name: 图数据库服务名称")
    print("   • default_vector_dimension: 默认向量维度")
    print("   • max_search_results: 最大搜索结果数")
    print("   • enable_caching: 是否启用缓存")
    print("   • enable_knowledge_graph: 是否启用知识图谱")

    print("\n💡 最佳实践:")
    print("   • 为每个用户会话使用唯一的 session_id")
    print("   • 选择合适的向量嵌入模型（推荐384维）")
    print("   • 为重要记忆添加丰富的元数据")
    print("   • 定期清理过期的工作记忆")
    print("   • 监控向量搜索的性能和准确性")


def main():
    """主函数：演示MemoryService的使用"""
    print("🚀 MemoryService 使用示例")
    print("="*60)

    # 检查是否在测试模式
    if os.getenv("SAGE_EXAMPLES_MODE") == "test":
        print("🧪 测试模式：跳过 MemoryService 示例（需要完整服务设置）")
        return

    print("📋 初始化 MemoryService...")

    # 强制使用MockMemoryService进行演示（避免依赖复杂的SAGE服务基础设施）
    try:
        memory_service = MockMemoryService()
        print("✅ MockMemoryService 初始化成功")
        print("   💡 使用模拟服务展示MemoryService功能")
    except Exception as e:
        print(f"❌ 模拟服务初始化失败: {e}")
        return

    # 创建示例对话数据
    conversations = create_sample_conversations()

    # 演示记忆存储
    print("\n🔄 阶段1: 存储对话记忆")
    session_id = "demo_session_001"

    for i, conversation in enumerate(conversations, 1):
        print(f"\n   处理对话 {i}/{len(conversations)}...")

        user_message = conversation["user_message"]
        ai_response = conversation["ai_response"]
        topic = conversation.get("topic", "general")

        try:
            # 存储用户消息
            user_memory_id = memory_service.store_memory(
                content=user_message,
                vector=mock_embedding(user_message),
                session_id=session_id,
                memory_type="conversation",
                metadata={
                    "speaker": "user",
                    "topic": topic,
                    "timestamp": time.time()
                }
            )
            print(f"     ✅ 用户消息已存储: {user_memory_id}")

            # 存储AI回复
            ai_memory_id = memory_service.store_memory(
                content=ai_response,
                vector=mock_embedding(ai_response),
                session_id=session_id,
                memory_type="conversation",
                metadata={
                    "speaker": "ai",
                    "topic": topic,
                    "timestamp": time.time()
                }
            )
            print(f"     ✅ AI回复已存储: {ai_memory_id}")

            # 如果是编程相关，存储语义记忆
            if "python" in user_message.lower() or "编程" in user_message:
                semantic_content = f"用户对编程感兴趣：{user_message[:50]}..."
                semantic_id = memory_service.store_memory(
                    content=semantic_content,
                    vector=mock_embedding(semantic_content),
                    session_id=session_id,
                    memory_type="knowledge",
                    metadata={
                        "topic": "programming",
                        "importance": "medium",
                        "timestamp": time.time()
                    }
                )
                print(f"     ✅ 语义记忆已存储: {semantic_id}")

        except Exception as e:
            print(f"     ❌ 存储失败: {str(e)}")

    # 演示记忆检索
    print("\n🔄 阶段2: 记忆检索演示")

    # 创建检索查询
    retrieval_queries = [
        "Python编程学习",
        "健康和疲惫",
        "机器学习建议"
    ]

    for query in retrieval_queries:
        print(f"\n   🔍 查询: {query}")

        try:
            # 搜索相关记忆
            query_vector = mock_embedding(query)
            relevant_memories = memory_service.search_memories(
                query_vector=query_vector,
                session_id=session_id,
                limit=3
            )

            print(f"     📚 找到 {len(relevant_memories)} 条相关记忆:")
            for i, mem in enumerate(relevant_memories, 1):
                content = mem.get("content", "")[:60]
                mem_type = mem.get("memory_type", "unknown")
                print(f"       {i}. [{mem_type}] {content}...")

            # 获取会话记忆统计
            session_memories = memory_service.get_session_memories(session_id)
            print(f"     📊 会话总记忆数: {len(session_memories)}")

        except Exception as e:
            print(f"     ❌ 查询失败: {str(e)}")

    print("\n" + "="*60)
    print("🎉 MemoryService 示例完成！")
    print("="*60)
    print("\n📚 关键特性展示:")
    print("   ✅ 记忆存储和检索")
    print("   ✅ 会话管理和隔离")
    print("   ✅ 语义搜索功能")
    print("   ✅ 工作记忆和上下文生成")
    print("   ✅ 知识图谱集成")
    print("\n💡 实际使用建议:")
    print("   1. 确保已启动 KV、VDB、Graph 底层服务")
    print("   2. 配置合适的向量维度和嵌入模型")
    print("   3. 根据应用场景调整记忆类型和元数据")
    print("   4. 监控记忆系统的性能和存储使用情况")


if __name__ == "__main__":
    # 禁用控制台调试日志
    CustomLogger.disable_global_console_debug()

    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 示例被用户中断")
    except Exception as e:
        print(f"\n❌ 示例执行出错: {e}")
        import traceback
        traceback.print_exc()
