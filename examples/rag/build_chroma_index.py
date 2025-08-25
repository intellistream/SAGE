#!/usr/bin/env python3
"""
知识库预加载脚本（SAGE版）
使用 TextLoader 加载文本，CharacterSplitter 分块，写入 ChromaDB。
"""
import os
import sys
import chromadb
from sentence_transformers import SentenceTransformer
from sage.libs.rag.document_loaders import TextLoader
from sage.libs.rag.chunk import CharacterSplitter

def load_knowledge_to_chromadb():
    # 配置参数
    knowledge_file = "../../data/qa_knowledge_base.txt"
    persistence_path = "./chroma_qa_database"
    collection_name = "qa_knowledge_base"

    print(f"=== 预加载知识库到 ChromaDB ===")
    print(f"文件: {knowledge_file} | DB: {persistence_path} | 集合: {collection_name}")

    loader = TextLoader(knowledge_file)
    document = loader.load()
    print(f"已加载文本，长度: {len(document['content'])}")

    splitter = CharacterSplitter({"separator": "\n\n"})
    chunks = splitter.execute(document)
    print(f"分块数: {len(chunks)}")
    chunk_docs = [
        {"content": chunk, "metadata": {"chunk": idx+1, "source": knowledge_file}}
        for idx, chunk in enumerate(chunks)
    ]

    # 初始化嵌入模型
    print("\n加载嵌入模型...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print("初始化ChromaDB...")
    client = chromadb.PersistentClient(path=persistence_path)
    try:
        client.delete_collection(name=collection_name)
    except:
        pass
    # 支持索引类型设置（如 flat, hnsw），默认 flat
    index_type = "flat"  # 可选: "flat", "hnsw"，如需更改可修改此处
    collection = client.create_collection(name=collection_name, metadata={"index_type": index_type})
    print(f"集合已创建，索引类型: {index_type}")
    texts = [c["content"] for c in chunk_docs]
    embeddings = model.encode(texts).tolist()
    ids = [f"chunk_{i}" for i in range(len(chunk_docs))]
    metadatas = [c["metadata"] for c in chunk_docs]
    collection.add(
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
        ids=ids
    )
    print(f"✓ 已添加 {len(chunk_docs)} 个文本块")
    print(f"✓ 数据库文档数: {collection.count()}")
    test_query = "什么是ChromaDB"
    query_embedding = model.encode([test_query]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=3)
    print(f"检索: {test_query}")
    for i, doc in enumerate(results['documents'][0]):
        print(f"  {i+1}. {doc[:100]}...")
    print("=== 预加载完成 ===")
    return True

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if load_knowledge_to_chromadb():
        print("知识库已成功加载，可运行检索/问答脚本")
    else:
        print("知识库加载失败")
        sys.exit(1)
