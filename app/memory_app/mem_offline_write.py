"""
离线写入示例：Naive RAG知识库构建
将10句关于AI/ML的知识保存到memory service中
"""
from sage.utils.custom_logger import CustomLogger
from sage.service.memory.memory_service import MemoryService
from sage.utils.embedding_methods.embedding_api import apply_embedding_model

def create_naive_rag_knowledge_base():
    """创建简单的RAG知识库"""
    print("🚀 创建 Naive RAG 知识库...")
    
    # 准备10句AI/ML相关的知识
    knowledge_sentences = [
        "机器学习是人工智能的一个分支，通过算法让计算机从数据中自动学习模式。",
        "深度学习使用多层神经网络来模拟人脑的学习过程，特别擅长处理图像和语音。",
        "自然语言处理帮助计算机理解和生成人类语言，包括文本分析和语音识别。",
        "监督学习需要标注好的训练数据，算法通过输入输出对来学习预测规律。",
        "无监督学习不需要标签，主要用于发现数据中的隐藏结构和模式。",
        "强化学习通过奖励机制让智能体在环境中学习最优策略。",
        "卷积神经网络特别适合处理图像数据，能够自动提取图像特征。",
        "循环神经网络擅长处理序列数据，如时间序列和文本数据。",
        "Transformer架构通过注意力机制革命性地改进了自然语言处理任务。",
        "大语言模型通过大规模预训练学习语言知识，然后通过微调适应特定任务。"
    ]
    
    try:
        # 1. 创建 MemoryService 实例
        embedding_model = apply_embedding_model("default")
        dim = embedding_model.get_dim()
        memory_service = MemoryService()
        col_name = "rag_knowledge"
        # 2. 创建知识库 collection
        collection_result = memory_service.create_collection(
            name=col_name,
            backend_type="VDB",
            description="Naive RAG knowledge base",
            embedding_model=embedding_model,
            dim=dim
        )
        
        if collection_result["status"] != "success":
            print(f"❌ 创建集合失败: {collection_result['message']}")
            return False
            
        print("✅ 知识库集合创建成功")
        
        # 3. 逐句插入知识
        print("\n📚 开始插入知识句子...")
        for i, sentence in enumerate(knowledge_sentences):
            result = memory_service.insert_data(
                collection_name=col_name,
                text=sentence,
                metadata={
                    "id": i + 1,
                    "topic": "AI/ML",
                    "type": "knowledge",
                    "source": "manual"
                }
            )
            
            if result["status"] == "success":
                print(f"  ✅ 句子 {i+1}: {sentence} 已保存")
            else:
                print(f"  ❌ 句子 {i+1}: 保存失败 - {result['message']}")
        
        # 4. 创建默认索引用于检索
        index_result = memory_service.create_index(
            collection_name=col_name,
            index_name="knowledge_index",
            description="知识检索索引"
        )
        
        if index_result["status"] == "success":
            print("✅ 检索索引创建成功")
        else:
            print(f"❌ 索引创建失败: {index_result['message']}")
        
        # 5. 保存到磁盘
        store_result = memory_service.store()
        if store_result["status"] == "success":
            print("✅ 知识库已保存到磁盘")
        else:
            print(f"❌ 保存失败: {store_result['message']}")
        
        # 6. 显示统计信息
        info_result = memory_service.get_collection_info(col_name)
        if info_result["status"] == "success":
            print(f"\n📊 知识库统计:")
            print(f"  - 集合名称: {info_result['collection_info']['name']}")
            print(f"  - 描述: {info_result['collection_info']['description']}")
            print(f"  - 状态: {info_result['collection_info']['status']}")
        
        print(f"\n🎉 Naive RAG 知识库构建完成！共保存 {len(knowledge_sentences)} 句知识")
        return True
        
    except Exception as e:
        print(f"❌ 构建知识库失败: {str(e)}")
        return False

if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    create_naive_rag_knowledge_base()
