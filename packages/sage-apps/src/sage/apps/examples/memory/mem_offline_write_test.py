"""
流处理RAG测试：使用流处理框架测试RAG知识库的写入和检索
"""
import time
from sage.kernel.utils.logging.custom_logger import CustomLogger
from sage.core.api.local_environment import LocalEnvironment
from sage.middleware.services.memory.memory_service import MemoryService
from sage.kernel.utils.embedding_methods.embedding_api import apply_embedding_model
from sage.core.api.function.map_function import MapFunction
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.sink_function import SinkFunction

class RAGQuerySource(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.test_queries = [
            "什么是深度学习？",
            "监督学习是怎么工作的？", 
            "Transformer有什么特点？",
            "强化学习的核心机制是什么？",
            "卷积神经网络用来做什么？",
            "机器学习的基本原理是什么？",
            "自然语言处理的应用场景有哪些？",
            "无监督学习和监督学习的区别？"
        ]

    def execute(self):
        if self.counter >= len(self.test_queries):
            return None

        query = self.test_queries[self.counter]
        doc = {
            "query": query,
            "query_id": self.counter + 1,
            "timestamp": "2025-07-27"
        }
        
        self.counter += 1
        return doc

class RetrieveRAGKnowledge(MapFunction):  
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.collection_name = "rag_knowledge"

    def execute(self, data):
        if not data:
            return None
        
        query = data['query']
        print(f"🔍 正在检索查询: '{query}'")
        
        # 从知识库检索相关知识
        try:
            result = self.call_service["memory_service"].retrieve_data(
                collection_name=self.collection_name,
                query_text=query,
                topk=2,  # 获取最相关的2条知识
                index_name="knowledge_index",
                with_metadata=True
            )
            
            if result['status'] == 'success':
                print(f"✅ 检索成功，找到 {len(result['results'])} 条相关知识")
                data['retrieved_knowledge'] = result['results']
                return data
            else:
                print(f"⚠️ 检索失败: {result.get('message', '未知错误')}")
                data['retrieved_knowledge'] = []
                return data
                
        except Exception as e:
            print(f"❌ 检索过程出错: {str(e)}")
            data['retrieved_knowledge'] = []
            return data

class RAGTestSink(SinkFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def execute(self, data):
        if not data:
            return None
        
        print("\n" + "="*70)
        print(f"� 查询 {data['query_id']}: {data['query']}")
        
        if data['retrieved_knowledge']:
            print(f"\n📖 检索到的相关知识 ({len(data['retrieved_knowledge'])} 条):")
            for i, knowledge in enumerate(data['retrieved_knowledge'], 1):
                text = knowledge.get('text', 'N/A')
                metadata = knowledge.get('metadata', {})
                knowledge_id = metadata.get('id', '未知')
                
                print(f"\n  {i}. [知识点 {knowledge_id}]")
                print(f"     内容: {text}")
        else:
            print("\n❌ 未检索到相关知识")
        
        print("="*70 + "\n")
        return data

def pipeline_run():
    """创建并运行RAG知识库的流处理测试管道"""
    # 创建本地环境
    env = LocalEnvironment()
    
    # 注册memory service并连接到现有的RAG知识库
    def memory_service_factory():
        # 创建memory service实例
        embedding_model = apply_embedding_model("default")
        memory_service = MemoryService()
        
        # 检查知识库是否存在，如果不存在则直接退出
        try:
            collections = memory_service.list_collections()
            if collections["status"] != "success":
                print("❌ 无法获取集合列表，测试退出")
                exit(1)
                
            collection_names = [c["name"] for c in collections["collections"]]
            if "rag_knowledge" not in collection_names:
                print("❌ 知识库 'rag_knowledge' 不存在，请先运行 mem_offline_write.py")
                print("测试退出")
                exit(1)
                
            print("✅ 找到现有的RAG知识库")
            
            # 连接到现有的知识库
            collection = memory_service.manager.connect_collection("rag_knowledge", embedding_model)
            if not collection:
                print("❌ 连接到RAG知识库失败，测试退出")
                exit(1)
                
            print("✅ 成功连接到RAG知识库")
                
        except Exception as e:
            print(f"❌ 连接知识库时出错: {str(e)}")
            print("测试退出")
            exit(1)
            
        return memory_service
    
    # 注册服务到环境中
    env.register_service("memory_service", memory_service_factory)

    print("\n🚀 启动RAG知识库流处理测试...")
    print("这个测试将:")
    print("1. 生成测试查询")
    print("2. 连接到现有的RAG知识库")
    print("3. 对每个查询进行检索测试")
    print("4. 显示检索结果\n")

    # 创建简化的RAG测试流处理管道
    env.from_source(RAGQuerySource).map(RetrieveRAGKnowledge).sink(RAGTestSink)
    
    try:
        env.submit()
        # 让主线程等待批处理完成
        print("等待流处理批次完成...")
        time.sleep(8)  # 等待足够时间让所有知识点处理完成
        
    except KeyboardInterrupt:
        print("测试被用户中断")
    finally:
        print("\n🎉 RAG知识库流处理测试完成")

if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    # 运行流处理RAG测试
    pipeline_run()
