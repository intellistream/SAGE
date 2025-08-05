import time
from sage.api.local_environment import LocalEnvironment
from sage.api.remote_environment import RemoteEnvironment
from sage.service.memory.memory_service import MemoryService
from sage.api.function.map_function import MapFunction
from sage.api.function.batch_function import BatchFunction
from sage.api.function.sink_function import SinkFunction

# 具体的算子里要写请求服务的逻辑，使用memory service来存储和检索数据。
class MemorySource(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_docs = 5
        self.documents = [
            {
                "text": "Python is a high-level, interpreted programming language known for its simplicity and readability. It emphasizes code readability with its notable use of significant whitespace.",
                "metadata": {"category": "programming", "topic": "python", "type": "language_description"}
            },
            {
                "text": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.",
                "metadata": {"category": "technology", "topic": "machine_learning", "type": "concept_definition"}
            },
            {
                "text": "Deep learning is part of machine learning methods based on artificial neural networks. It allows computational models to learn data representations with multiple levels of abstraction.",
                "metadata": {"category": "technology", "topic": "deep_learning", "type": "concept_definition"}
            },
            {
                "text": "Natural Language Processing (NLP) combines linguistics and machine learning to help computers understand, interpret, and manipulate human language.",
                "metadata": {"category": "technology", "topic": "nlp", "type": "concept_definition"}
            },
            {
                "text": "TensorFlow is an open-source machine learning framework developed by Google. It provides a comprehensive ecosystem of tools for machine learning and deep learning.",
                "metadata": {"category": "technology", "topic": "frameworks", "type": "tool_description"}
            }
        ]

    def execute(self):
        if self.counter >= self.max_docs:
            return None

        doc = self.documents[self.counter].copy()
        doc['metadata']['doc_id'] = self.counter
        doc['metadata']['date'] = '2025-07-26'
        
        self.counter += 1
        return doc

class WriteCollection(MapFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.collection_name = "test_collection"

    def execute(self, data) -> list:
        if not data:
            return None
        
        # 调用 memory service 插入数据
        result = self.call_service["memory_service"].insert_data(
            collection_name=self.collection_name,
            text=data['text'],
            metadata=data['metadata']
        )
        
        if result['status'] == 'success':
            print(f"✅ Successfully inserted document {data['metadata']['doc_id']}")
            return data
        else:
            print(f"❌ Failed to insert document: {result['message']}")
            return None

class RetrieveCollection(MapFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.collection_name = "test_collection"

    def execute(self, data) -> list:
        if not data:
            return None
        
        # 使用原文本作为查询来检索相似文档
        result = self.call_service["memory_service"].retrieve_data(
            collection_name=self.collection_name,
            query_text=data['text'],
            topk=3,  # 获取前3个最相似的文档
            with_metadata=True
        )
        
        if result['status'] == 'success':
            print(f"🔍 Retrieved similar documents for doc_id {data['metadata']['doc_id']}")
            # 将检索结果添加到原始数据中
            data['similar_docs'] = result['results']
            return data
        else:
            print(f"❌ Failed to retrieve documents: {result['message']}")
            return None

class MemorySink(SinkFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def execute(self, data) -> list:
        if not data:
            return None
        
        print("\n" + "="*50)
        print(f"📄 Original Document (ID: {data['metadata']['doc_id']})")
        print(f"Text: {data['text']}")
        print(f"Metadata: {data['metadata']}")
        
        if 'similar_docs' in data and data['similar_docs']:
            print("\n📑 Similar Documents:")
            for i, doc in enumerate(data['similar_docs'], 1):
                print(f"\n{i}. Similar Document:")
                print(f"Text: {doc.get('text', 'N/A')}")
                print(f"Metadata: {doc.get('metadata', 'N/A')}")
        
        print("="*50 + "\n")
        return data

def pipeline_run():
    """创建并运行使用memory service的数据处理管道"""
    # 创建本地环境
    env = LocalEnvironment("mem_examples")
    
    # 注册memory service并初始化操作的表格
    def memory_service_factory():
        # 创建memory service实例
        memory_service = MemoryService()
        
        # 创建测试集合
        result = memory_service.create_collection(
            name="test_collection",
            backend_type="VDB",
            description="Test collection for memory service example"
        )
        
        if result['status'] == 'success':
            print("✅ Collection created successfully")
            
            # 预先插入一些文档
            initial_docs = [
                {
                    "text": "Artificial Intelligence (AI) is the simulation of human intelligence by machines. It includes machine learning, neural networks, and expert systems.",
                    "metadata": {"category": "technology", "topic": "ai", "type": "concept_definition"}
                },
                {
                    "text": "PyTorch is a popular deep learning framework that provides dynamic computational graphs. It is widely used in research and production.",
                    "metadata": {"category": "technology", "topic": "frameworks", "type": "tool_description"}
                },
                {
                    "text": "Computer vision is a field of AI that enables computers to derive meaningful information from digital images and videos.",
                    "metadata": {"category": "technology", "topic": "computer_vision", "type": "concept_definition"}
                },
                {
                    "text": "Data preprocessing is a crucial step in machine learning that involves cleaning, normalizing, and transforming raw data into a suitable format.",
                    "metadata": {"category": "technology", "topic": "data_science", "type": "process_description"}
                }
            ]
            
            print("\n📚 Inserting initial documents into collection...")
            for i, doc in enumerate(initial_docs):
                doc['metadata']['doc_id'] = f'init_{i}'
                doc['metadata']['date'] = '2025-07-26'
                
                insert_result = memory_service.insert_data(
                    collection_name="test_collection",
                    text=doc['text'],
                    metadata=doc['metadata']
                )
                
                if insert_result['status'] == 'success':
                    print(f"✅ Successfully inserted initial document {i+1}")
                else:
                    print(f"❌ Failed to insert initial document {i+1}: {insert_result['message']}")
                
        else:
            print(f"❌ Failed to create collection: {result['message']}")
            
        return memory_service
    
    # 注册服务到环境中
    env.register_service("memory_service", memory_service_factory)

    print("\n🚀 Starting memory service pipeline...")
    print("This example will:")
    print("1. Generate sample documents")
    print("2. Store them in the memory service")
    print("3. Retrieve similar documents for each stored document")
    print("4. Display the results\n")

    # 创建数据处理管道
    env.from_source(MemorySource).map(WriteCollection).map(RetrieveCollection).sink(MemorySink)
    
    try:
        env.submit()
        # 让主线程睡眠，让批处理自动完成并停止
        print("Waiting for batch processing to complete...")
        time.sleep(5)  # 等待5秒
    except KeyboardInterrupt:
        print("停止运行")
    finally:
        print("Hello Memory 批处理示例结束")


if __name__ == '__main__':
    pipeline_run()
