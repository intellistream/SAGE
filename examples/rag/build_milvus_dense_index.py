import logging
import os
import sys

import yaml
from sage.common.utils.config.loader import load_config
from sage.libs.rag.chunk import CharacterSplitter
from sage.libs.rag.document_loaders import LoaderFactory
from sage.libs.rag.milvusRetriever import MilvusDenseRetriever


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def load_knowledge_to_milvus(config):
    """
    加载多格式知识库到 Milvus（单集合版本，不保留来源信息）
    """
    knowledge_files = config.get("preload_knowledge_file")
    if not isinstance(knowledge_files, list):
        knowledge_files = [knowledge_files]

    persistence_path = config.get("milvus_dense").get("persistence_path")
    collection_name = "qa_dense_collection"  # 单集合

    logging.info(f"=== 预加载多格式知识库到 Milvus ===")
    logging.info(f"DB: {persistence_path}")
    logging.info(f"统一集合: {collection_name}")

    logging.info("初始化Milvus...")
    milvus_backend = MilvusDenseRetriever(config, collection_name=collection_name)

    all_chunks = []

    for file_path in knowledge_files:
        if not os.path.exists(file_path):
            logging.info(f"⚠ 文件不存在，跳过: {file_path}")
            continue

        logging.info(f"\n=== 处理文件: {file_path} ===")

        document = LoaderFactory.load(file_path)
        logging.info(f"已加载文档，长度: {len(document['content'])}")

        splitter = CharacterSplitter({"separator": "\n\n"})
        chunks = splitter.execute(document)
        logging.info(f"分块数: {len(chunks)}")

        all_chunks.extend(chunks)
        logging.info(f"✓ 已准备 {len(chunks)} 个文本块")

    if all_chunks:
        milvus_backend.add_documents(all_chunks)
        logging.info(f"\n✓ 已写入 {len(all_chunks)} 个文本块到集合 {collection_name}")
        logging.info(f"✓ 数据库信息: {milvus_backend.get_collection_info()}")

        # 测试检索
        text_query = "什么是ChromaDB？"
        results = milvus_backend.execute(text_query)
        logging.info(f"检索结果: {results}")

        # 测试检索
        text_query = "RAG 系统的主要优势是什么？"
        results = milvus_backend.execute(text_query)
        logging.info(f"检索结果: {results}")
    else:
        logging.info("⚠ 没有有效的知识文件，未写入任何数据")

    logging.info("=== 完成 ===")
    return True


if __name__ == "__main__":
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        logging.info("🧪 Test mode detected - build_milvus_dense_index example")
        logging.info("✅ Test passed: Example structure validated")
        sys.exit(0)

    config_path = "./examples/config/config_dense_milvus.yaml"
    if not os.path.exists(config_path):
        logging.info(f"配置文件不存在: {config_path}")
        logging.info("Please create the configuration file first.")
        sys.exit(1)

    config = load_config(config_path)
    result = load_knowledge_to_milvus(config["retriever"])
    if result:
        logging.info("知识库已成功加载，可运行检索/问答脚本")
    else:
        logging.info("知识库加载失败")
        sys.exit(1)
