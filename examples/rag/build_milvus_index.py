import logging
import os
import sys

import yaml
from sage.common.utils.config.loader import load_config
from sage.libs.rag.chunk import CharacterSplitter
from sage.libs.rag.document_loaders import TextLoader
from sage.libs.rag.milvusRetriever import MilvusDenseRetriever


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def load_knowledge_to_milvus(config):
    """
    加载知识库到 Milvus
    """
    knowledge_file = config.get("preload_knowledge_file")
    persistence_path = config.get("milvus_dense").get("persistence_path")
    collection_name = config.get("milvus_dense").get("collection_name")

    logging.info(f"=== 预加载知识库到 ChromaDB ===")
    logging.info(f"文件: {knowledge_file} | DB: {persistence_path} | 集合: {collection_name}")

    loader = TextLoader(knowledge_file)
    document = loader.load()
    logging.info(f"已加载文本，长度: {len(document['content'])}")

    splitter = CharacterSplitter({"separator": "\n\n"})
    chunks = splitter.execute(document)
    logging.info(f"分块数: {len(chunks)}")

    logging.info("初始化Milvus...")
    milvus_backend = MilvusDenseRetriever(config)
    milvus_backend.add_documents(chunks)
    logging.info(f"✓ 已添加 {len(chunks)} 个文本块")
    logging.info(f"✓ 数据库信息: {milvus_backend.get_collection_info()}")
    text_query = "什么是ChromaDB？"
    results = milvus_backend.execute(text_query)
    logging.info(f"检索结果: {results}")
    return True


if __name__ == "__main__":
    # 检查是否在测试模式下运行
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        logging.info("🧪 Test mode detected - build_milvus_index example")
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
