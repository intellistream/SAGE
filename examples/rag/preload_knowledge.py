#!/usr/bin/env python3
"""
预加载知识库脚本
将知识库文件加载到ChromaDB数据库中
"""

import os
import sys
import chromadb
from sentence_transformers import SentenceTransformer

def load_knowledge_to_chromadb():
    """加载知识库到ChromaDB"""
    
    # 配置参数
    knowledge_file = "/home/zsl/workspace1/SAGE/data/qa_knowledge_base.txt"
    persistence_path = "./chroma_qa_database"
    collection_name = "qa_knowledge_base"
    
    print(f"=== 预加载知识库到 ChromaDB ===")
    print(f"知识库文件: {knowledge_file}")
    print(f"数据库路径: {persistence_path}")
    print(f"集合名称: {collection_name}")
    
    # 检查知识库文件是否存在
    if not os.path.exists(knowledge_file):
        print(f"错误：知识库文件不存在: {knowledge_file}")
        return False
    
    # 读取知识库内容
    print("\n正在读取知识库文件...")
    with open(knowledge_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按段落分割文档
    documents = [doc.strip() for doc in content.split('\n\n') if doc.strip()]
    print(f"共解析出 {len(documents)} 个文档段落")
    
    # 初始化嵌入模型
    print("\n正在加载嵌入模型...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    # 初始化ChromaDB客户端
    print("\n正在初始化ChromaDB...")
    client = chromadb.PersistentClient(path=persistence_path)
    
    # 创建或获取集合
    try:
        # 尝试删除现有集合
        try:
            client.delete_collection(name=collection_name)
            print(f"已删除现有集合: {collection_name}")
        except:
            pass  # 集合不存在，忽略错误
        
        # 创建新集合
        collection = client.create_collection(name=collection_name)
        print(f"已创建新集合: {collection_name}")
    except Exception as e:
        print(f"创建集合时出错: {e}")
        return False
    
    # 生成嵌入向量
    print("\n正在生成文档嵌入向量...")
    embeddings = model.encode(documents).tolist()
    
    # 准备文档ID和元数据
    ids = [f"doc_{i}" for i in range(len(documents))]
    metadatas = [{"source": "knowledge_base", "doc_id": i} for i in range(len(documents))]
    
    # 添加文档到集合
    print("正在添加文档到ChromaDB...")
    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"\n✓ 成功添加 {len(documents)} 个文档到ChromaDB")
    
    # 验证数据
    count = collection.count()
    print(f"✓ 数据库中共有 {count} 个文档")
    
    # 测试检索
    print("\n正在测试检索功能...")
    test_query = "什么是ChromaDB"
    query_embedding = model.encode([test_query]).tolist()
    
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
    )
    
    print(f"测试查询: {test_query}")
    print(f"检索到 {len(results['documents'][0])} 个相关文档")
    for i, doc in enumerate(results['documents'][0]):
        print(f"  {i+1}. {doc[:100]}...")
    
    print("\n=== 知识库预加载完成 ===")
    return True

if __name__ == '__main__':
    # 切换到正确的工作目录
    os.chdir('/home/zsl/workspace1/SAGE/examples/rag')
    
    success = load_knowledge_to_chromadb()
    if success:
        print("\n知识库已成功加载，现在可以运行qa_openai.py")
    else:
        print("\n知识库加载失败")
        sys.exit(1)
