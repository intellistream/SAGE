"""
SAGE 微服务架构使用示例
展示如何在应用程序中注册和使用KV、VDB、Memory服务
"""
import asyncio
import time
from typing import List
import numpy as np

# 导入SAGE环境和服务
from sage.core.api.local_environment import LocalEnvironment
from sage.middleware.services import (
    MemoryService,
    create_kv_service_factory,
    create_vdb_service_factory,
    create_memory_service_factory,
)


class SampleApplication:
    """示例应用程序，展示如何使用微服务架构"""
    
    def __init__(self):
        # 创建SAGE环境
        self.env = LocalEnvironment("microservices_demo", {})
        
    def setup_services(self):
        """在应用中注册微服务"""
        print("🔧 注册微服务到SAGE环境...")
        
        # 注册KV服务
        kv_factory = create_kv_service_factory(
            service_name="kv_service",
            backend_type="memory",  # 使用内存后端
            max_size=1000,
            ttl_seconds=3600  # 1小时过期
        )
    self.env.register_service_factory("kv_service", kv_factory)
        
        # 注册VDB服务
        vdb_factory = create_vdb_service_factory(
            service_name="vdb_service",
            embedding_dimension=384,
            index_type="IndexFlatL2",
        )
        self.env.register_service_factory("vdb_service", vdb_factory)
        
        # 注册Memory编排服务
        memory_factory = create_memory_service_factory(
            service_name="memory_service",
            kv_service_name="kv_service",
            vdb_service_name="vdb_service"
        )
    self.env.register_service_factory("memory_service", memory_factory)
        
        print("✅ 所有服务已注册")
    
    def run_demo(self):
        """运行演示"""
        print("🚀 启动微服务演示")
        print("=" * 50)
        
        # 设置服务
        self.setup_services()
        
        # 创建一个简单的数据流来演示服务使用
        data_stream = self.env.from_memory_source([
            {"id": 1, "content": "用户询问了关于Python的问题", "session": "session_1"},
            {"id": 2, "content": "AI助手回答了Python基础知识", "session": "session_1"},
            {"id": 3, "content": "用户请求更多代码示例", "session": "session_1"},
            {"id": 4, "content": "讨论了机器学习算法", "session": "session_2"},
            {"id": 5, "content": "解释了神经网络原理", "session": "session_2"}
        ])
        
        # 定义处理函数
        def process_conversation(data):
            """处理对话数据的函数"""
            # 在这里我们可以使用服务调用
            # 注意：在实际的SAGE函数中，可以通过 self.call_service 访问服务
            
            print(f"处理对话: {data['content'][:30]}...")
            
            # 模拟向量化（在实际应用中，这里会调用embedding服务）
            content_vector = np.random.random(384).tolist()
            
            # 这里展示了服务调用的概念
            # 在实际的SAGE函数中，代码会是这样：
            # 
            # # 存储到KV
            # self.call_service["kv_service"].put(f"conv:{data['id']}", {
            #     "content": data['content'],
            #     "session": data['session'],
            #     "timestamp": time.time()
            # })
            # 
            # # 存储记忆
            # memory_id = self.call_service["memory_service"].store_memory(
            #     session_id=data['session'],
            #     content=data['content'],
            #     vector=content_vector,
            #     memory_type="conversation"
            # )
            
            return {
                "processed": True,
                "memory_id": f"mock_memory_{data['id']}",
                "vector_dim": len(content_vector)
            }
        
        # 应用处理函数
        processed_stream = data_stream.map(process_conversation)
        
        # 执行并收集结果
        print("\n📊 处理结果:")
        results = processed_stream.collect()
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. ✅ 已处理 - Memory ID: {result['memory_id']}")
        
        print(f"\n🎯 总共处理了 {len(results)} 条对话记录")
        
        # 展示服务调用的概念
        self.show_service_usage_concept()
    
    def show_service_usage_concept(self):
        """展示服务使用概念"""
        print("\n" + "=" * 50)
        print("💡 在SAGE函数中使用服务的示例代码:")
        print("=" * 50)
        
        example_code = '''
# 在SAGE Function中使用微服务的示例

class ConversationProcessor(BaseFunction):
    """对话处理函数"""
    
    def process(self, conversation_data):
        session_id = conversation_data['session_id']
        content = conversation_data['content']
        
        # 1. 调用KV服务存储原始数据
        kv_success = self.call_service["kv_service"].put(
            f"raw:{session_id}", 
            conversation_data
        )
        
        # 2. 生成向量表示（假设有embedding服务）
        vector = self.call_service["embedding_service"].encode(content)
        
        # 3. 调用Memory服务存储记忆
        memory_id = self.call_service["memory_service"].store_memory(
            session_id=session_id,
            content=content,
            vector=vector,
            memory_type="conversation"
        )
        
        # 4. 搜索相关历史记忆
        related_memories = self.call_service["memory_service"].search_memories(
            query_vector=vector,
            session_id=session_id,
            limit=5
        )
        
        return {
            "memory_id": memory_id,
            "related_count": len(related_memories),
            "kv_stored": kv_success
        }

# 在DAG中注册和使用
def create_conversation_dag():
    env = LocalEnvironment("conversation_app", {})
    
    # 注册微服务
    env.register_service("kv_service", KVService, create_kv_service_factory())
    env.register_service("vdb_service", VDBService, create_vdb_service_factory())
    env.register_service("memory_service", MemoryService, create_memory_service_factory())
    
    # 创建数据流
    stream = env.from_kafka_source(...)
    
    # 应用处理函数（自动访问服务）
    processed = stream.map(ConversationProcessor())
    
    return processed
        '''
        
        print(example_code)
        print("\n" + "=" * 50)
        print("🔍 关键概念:")
        print("1. 服务作为Service Tasks在DAG中运行")
        print("2. 函数通过 self.call_service[service_name] 调用服务")
        print("3. 服务可以是本地任务或Ray分布式任务")
        print("4. 应用程序控制服务的生命周期")
        print("5. 服务间通过SAGE的队列机制通信")


def main():
    """主函数"""
    app = SampleApplication()
    
    try:
        app.run_demo()
        print("\n✅ 演示完成!")
        print("\n📖 查看更多信息:")
        print("  - 微服务代码: packages/sage-middleware/src/sage/service/")
        print("  - 使用指南: packages/sage-middleware/MICROSERVICES_GUIDE.md")
        
    except KeyboardInterrupt:
        print("\n\n👋 演示被中断")
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
