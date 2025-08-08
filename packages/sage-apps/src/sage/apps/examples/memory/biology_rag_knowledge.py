"""
生物学RAG知识库构建
针对生物学问题"Answer with True or False: Meiosis produces four genetically identical daughter cells."
创建包含强相关、弱相关和无关知识的知识库
"""
from sage.kernel.utils.logging.custom_logger import CustomLogger
from sage.middleware.services.memory.memory_service import MemoryService
from sage.kernel.utils.embedding_methods.embedding_api import apply_embedding_model

def create_biology_rag_knowledge_base():
    """创建生物学RAG知识库"""
    print("🚀 创建生物学RAG知识库...")

    # 准备生物学相关知识句子
    knowledge_sentences = [
        # 强相关知识 - 直接关于减数分裂
        "减数分裂是一种特殊的细胞分裂过程，产生四个具有单倍体基因组的配子细胞。",
        "减数分裂产生的四个子细胞在基因上是不同的，这是因为交叉互换和独立分配的结果。",
        "减数分裂通过两次连续的细胞分裂，将二倍体细胞转变为四个单倍体配子。",
        "减数分裂I期中的交叉互换导致染色体片段交换，使得产生的配子具有基因多样性。",
        "减数分裂的关键特征是同源染色体配对和分离，这与有丝分裂不同。",
        "减数分裂产生的配子细胞染色体数目是体细胞的一半。",

        # 弱相关知识 - 关于细胞分裂但不是减数分裂
        "有丝分裂产生两个基因相同的二倍体子细胞，用于生长和修复组织。",
        "细胞分裂是生物体生长、发育和繁殖的基础过程。",
        "DNA复制发生在细胞分裂之前，确保遗传信息的准确传递。",
        "配子形成过程对于有性繁殖至关重要，保证了遗传多样性。",
        "细胞周期包括间期和分裂期，受到严格的检查点调控。",

        # 无关知识 - 生物学其他领域
        "光合作用是植物利用阳光、水和二氧化碳制造葡萄糖的过程。",
        "蛋白质合成包括转录和翻译两个主要步骤。",
        "生态系统中的能量流动遵循热力学第二定律，呈单向流动。",
        "酶是生物催化剂，能够降低化学反应的活化能。"
    ]

    try:
        # 1. 创建 MemoryService 实例
        embedding_model = apply_embedding_model("default")
        dim = embedding_model.get_dim()
        memory_service = MemoryService()
        col_name = "biology_rag_knowledge"

        # 2. 创建知识库 collection
        collection_result = memory_service.create_collection(
            name=col_name,
            backend_type="VDB",
            description="Biology RAG knowledge base for meiosis questions",
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
                    "topic": "biology",
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
            index_name="biology_index",
            description="生物学知识检索索引"
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

        print(f"\n🎉 生物学RAG知识库构建完成！共保存 {len(knowledge_sentences)} 句知识")
        return True

    except Exception as e:
        print(f"❌ 构建知识库失败: {str(e)}")
        return False

if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    create_biology_rag_knowledge_base()