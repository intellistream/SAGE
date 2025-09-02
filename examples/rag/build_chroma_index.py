#!/usr/bin/env python3
"""
知识库预加载脚本（支持 txt / pdf / md / docx）
使用不同 Loader 解析文件，分块后写入 ChromaDB。
"""
import os
import sys
import chromadb
from sentence_transformers import SentenceTransformer
from sage.libs.rag.document_loaders import LoaderFactory
from sage.libs.rag.chunk import CharacterSplitter

def build_and_load_collection(file_path: str, loader_cls, collection_name: str, persistence_path: str):
    print(f"\n=== 处理文件: {file_path} | 集合名: {collection_name} ===")
    loader = loader_cls(file_path)
    document = loader.load()
    print(f"已加载文档，长度: {len(document['content'])}")

    splitter = CharacterSplitter({"separator": "\n\n"})
    chunks = splitter.execute(document)
    print(f"分块数: {len(chunks)}")

    chunk_docs = [
        {"content": chunk, "metadata": {"chunk": idx + 1, "source": file_path}}
        for idx, chunk in enumerate(chunks)
    ]

    # 初始化 ChromaDB
    client = chromadb.PersistentClient(path=persistence_path)
    try:
        client.delete_collection(name=collection_name)
    except:
        pass
    collection = client.create_collection(name=collection_name, metadata={"index_type": "flat"})
    print(f"集合已创建: {collection_name}")

    # 嵌入
    texts = [c["content"] for c in chunk_docs]
    embeddings = model.encode(texts).tolist()
    ids = [f"{collection_name}_chunk_{i}" for i in range(len(chunk_docs))]
    metadatas = [c["metadata"] for c in chunk_docs]

    collection.add(
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
        ids=ids
    )
    print(f"✓ 已添加 {len(chunk_docs)} 个文本块")
    print(f"✓ 数据库文档数: {collection.count()}")

    # 测试检索
    test_query = "什么是ChromaDB"
    query_embedding = model.encode([test_query]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=2)
    print(f"检索: {test_query}")
    for i, doc in enumerate(results['documents'][0]):
        print(f"  {i+1}. {doc[:80]}...")
    print("=== 处理完成 ===")

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    persistence_path = "./chroma_multi_store"

    print("\n加载嵌入模型...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    # 示例文件路径（你需要准备这些文件放到 ../data/ 下）
    txt_file = "examples/data/qa_knowledge_base.txt"
    pdf_file = "examples/data/qa_knowledge_base.pdf"
    md_file = "examples/data/qa_knowledge_base.md"
    docx_file = "examples/data/qa_knowledge_base.docx"

    # 依次处理不同格式的文件
    build_and_load_collection(txt_file, TextLoader, "txt_collection", persistence_path)
    build_and_load_collection(pdf_file, PDFLoader, "pdf_collection", persistence_path)
    build_and_load_collection(md_file, MarkdownLoader, "md_collection", persistence_path)
    build_and_load_collection(docx_file, DocxLoader, "docx_collection", persistence_path)

    print("\n=== 所有文件已处理完成 ===")
