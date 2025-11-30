#!/usr/bin/env python3
"""
为 Gateway RAG 构建 ChromaDB 索引

从 docs-public/docs_src 读取文档并存入 ChromaDB
"""

import sys
from pathlib import Path


def build_chroma_index():
    """构建 ChromaDB 索引用于 Gateway RAG"""

    print("=" * 70)
    print("构建 ChromaDB 索引 for SAGE Gateway RAG")
    print("=" * 70)

    # 1. 查找文档源目录
    print("\n[步骤 1] 定位文档源...")

    from sage.common.config.output_paths import find_sage_project_root

    project_root = find_sage_project_root()
    if not project_root:
        print("  ❌ 找不到项目根目录")
        return False

    source_dir = project_root / "docs-public" / "docs_src"
    if not source_dir.exists():
        print(f"  ❌ 文档源目录不存在: {source_dir}")
        return False

    print(f"  ✅ 文档源目录: {source_dir}")

    # 统计文档数量
    md_files = list(source_dir.rglob("*.md"))
    print(f"  ✅ 找到 {len(md_files)} 个 Markdown 文件")

    if len(md_files) == 0:
        print("  ⚠️  没有找到任何文档")
        return False

    # 2. 初始化 ChromaDB
    print("\n[步骤 2] 初始化 ChromaDB...")

    vector_db_path = Path.home() / ".sage" / "vector_db"
    vector_db_path.mkdir(parents=True, exist_ok=True)

    from sage.middleware.operators.rag.retriever import ChromaRetriever

    retriever_config = {
        "chroma": {
            "persist_directory": str(vector_db_path),
            "persistence_path": str(vector_db_path),
            "collection_name": "sage_docs",
        },
        "top_k": 5,
        "embedding": {
            "model_name": "BAAI/bge-small-zh-v1.5",
        },
    }

    try:
        retriever = ChromaRetriever(retriever_config)
        print(f"  ✅ ChromaDB 初始化成功: {vector_db_path}")
    except Exception as e:
        print(f"  ❌ ChromaDB 初始化失败: {e}")
        return False

    # 3. 处理文档
    print("\n[步骤 3] 处理文档...")

    from sage.common.utils.document_processing import (
        parse_markdown_sections,
        slugify,
    )

    total_chunks = 0
    processed_files = 0

    # 获取 embedding 模型
    embedder = retriever.embedding_model

    # 获取 ChromaDB backend
    chroma_backend = retriever.chroma_backend

    for file_path in md_files[:10]:  # 先处理前10个文件测试
        try:
            # 读取文档
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # 解析为 sections（只传入content）
            sections = parse_markdown_sections(content)

            if not sections:
                continue

            # 准备批量数据
            documents = []
            embeddings = []
            doc_ids = []

            for idx, section in enumerate(sections):
                # 构建文档内容
                doc_content = f"{section['heading']}\n\n{section['content']}"
                documents.append(doc_content)

                # 生成 embedding
                embedding = embedder.encode(doc_content)
                embeddings.append(embedding)

                # 生成唯一 ID
                file_slug = slugify(file_path.stem)
                section_slug = slugify(section["heading"])
                doc_id = f"{file_slug}_{section_slug}_{idx}"
                doc_ids.append(doc_id)

            # 批量添加到 ChromaDB
            if documents:
                chroma_backend.add_documents(documents, embeddings, doc_ids)
                total_chunks += len(documents)
                processed_files += 1
                print(f"  ✓ 处理: {file_path.name} ({len(documents)} chunks)")

        except Exception as e:
            print(f"  ✗ 错误处理 {file_path.name}: {e}")
            continue

    print("\n✅ 索引构建完成！")
    print(f"  - 处理文件数: {processed_files}")
    print(f"  - 文档片段数: {total_chunks}")
    print(f"  - 索引路径: {vector_db_path}")

    # 4. 测试检索
    print("\n[步骤 4] 测试检索...")

    test_query = "什么是SAGE"
    result = retriever.execute(test_query)

    if result and "retrieval_results" in result:
        num_results = len(result["retrieval_results"])
        print(f"  ✅ 检索测试成功: 查询 '{test_query}' 返回 {num_results} 个结果")

        if num_results > 0:
            print("\n  示例结果:")
            first_result = result["retrieval_results"][0]
            content_preview = first_result[:200] if len(first_result) > 200 else first_result
            print(f"    {content_preview}...")
    else:
        print("  ⚠️  检索测试返回 0 个结果")

    print("\n" + "=" * 70)
    print("索引构建成功！现在可以使用 Gateway RAG 功能了")
    print("=" * 70)

    return True


if __name__ == "__main__":
    try:
        success = build_chroma_index()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n中断构建")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 构建失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
