#!/usr/bin/env python3
"""
知识库预加载脚本（SAGE多格式+工厂版）
支持 txt / pdf / md / docx 文件，
通过 LoaderFactory 动态选择 Loader，
使用 CharacterSplitter 分块，写入 ChromaDB。
"""
import os
import sys

import chromadb
from sage.libs.rag.chunk import CharacterSplitter
from sage.libs.rag.document_loaders import LoaderFactory
from sentence_transformers import SentenceTransformer


def load_knowledge_to_chromadb():
    # 配置参数
    data_dir = "../data"
    persistence_path = "./chroma_multi_store"

    # 文件与集合对应关系
    files_and_collections = [
        (os.path.join(data_dir, "qa_knowledge_base.txt"), "txt_collection"),
        (os.path.join(data_dir, "qa_knowledge_base.pdf"), "pdf_collection"),
        (os.path.join(data_dir, "qa_knowledge_base.md"), "md_collection"),
        (os.path.join(data_dir, "qa_knowledge_base.docx"), "docx_collection"),
    ]

    print(f"=== 预加载多格式知识库到 ChromaDB ===")
    print(f"存储路径: {persistence_path}")

    # 初始化嵌入模型
    print("\n加载嵌入模型...")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    # 初始化 ChromaDB
    print("初始化ChromaDB...")
    client = chromadb.PersistentClient(path=persistence_path)

    for file_path, collection_name in files_and_collections:
        if not os.path.exists(file_path):
            print(f"⚠ 文件不存在，跳过: {file_path}")
            continue

        print(f"\n=== 处理文件: {file_path} | 集合: {collection_name} ===")

        # 使用工厂类获取 loader
        document = LoaderFactory.load(file_path)
        print(f"已加载文档，长度: {len(document['content'])}")

        # 分块
        splitter = CharacterSplitter({"separator": "\n\n"})
        chunks = splitter.execute(document)
        print(f"分块数: {len(chunks)}")
        chunk_docs = [
            {"content": chunk, "metadata": {"chunk": idx + 1, "source": file_path}}
            for idx, chunk in enumerate(chunks)
        ]

        # 删除旧集合并创建新集合
        try:
            client.delete_collection(name=collection_name)
        except:
            pass
        index_type = "flat"  # 可选: "flat", "hnsw"
        collection = client.create_collection(
            name=collection_name, metadata={"index_type": index_type}
        )
        print(f"集合已创建，索引类型: {index_type}")

        # 嵌入与写入
        texts = [c["content"] for c in chunk_docs]
        embeddings = model.encode(texts).tolist()
        ids = [f"{collection_name}_chunk_{i}" for i in range(len(chunk_docs))]
        metadatas = [c["metadata"] for c in chunk_docs]
        collection.add(
            embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids
        )
        print(f"✓ 已添加 {len(chunk_docs)} 个文本块")
        print(f"✓ 数据库文档数: {collection.count()}")

        # 测试检索
        test_query = "什么是ChromaDB"
        query_embedding = model.encode([test_query]).tolist()
        results = collection.query(query_embeddings=query_embedding, n_results=3)
        print(f"检索: {test_query}")
        for i, doc in enumerate(results["documents"][0]):
            print(f"  {i + 1}. {doc[:100]}...")
        print("=== 完成 ===")

    print("\n=== 所有文件已处理完成 ===")
    return True


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if load_knowledge_to_chromadb():
        print("知识库已成功加载，可运行检索/问答脚本")
    else:
        print("知识库加载失败")
        sys.exit(1)
