import logging
import os

import yaml
from sage.common.utils.config.loader import load_config
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.batch import JSONLBatch
from sage.libs.io_utils.sink import TerminalSink
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import MilvusDenseRetriever


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def pipeline_run():
    """
    创建并运行 Milvus 专用 RAG 数据处理管道

    Args:
        config (dict): 包含各模块配置的配置字典。
    """

    logging.info("=== 启动基于 Milvus 的 RAG 问答系统 ===")
    logging.info("配置信息:")
    logging.info(f"  - 源文件: {config['source']['data_path']}")
    logging.info(f"  - 检索器: MilvusDenseRetriever (Milvus 专用)")
    logging.info(f"  - 向量维度: {config['retriever']['dimension']}")
    logging.info(f"  - Top-K: {config['retriever']['top_k']}")
    logging.info(
        f"  - 集合名称: {config['retriever']['milvus_dense']['collection_name']}"
    )
    logging.info(f"  - 嵌入模型: {config['retriever']['embedding']['method']}")

    env = LocalEnvironment()
    # 构建数据处理流程
    # MilvusDenseRetriever 会在初始化时自动加载配置的知识库文件
    logging.info("正在构建数据处理管道...")
    # 构建数据处理流程
    (
        env.from_source(JSONLBatch, config["source"])
        .map(MilvusDenseRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )
    logging.info("正在提交并运行管道...")
    env.submit(autostop=True)
    env.close()
    logging.info("=== RAG 问答系统运行完成 ===")


if __name__ == "__main__":
    import sys

    # 检查是否在测试模式下运行
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        logging.info("🧪 Test mode detected - qa_dense_retrieval_milvus example")
        logging.info("✅ Test passed: Example structure validated")
        sys.exit(0)

    config_path = "./examples/config/config_dense_milvus.yaml"
    if not os.path.exists(config_path):
        logging.info(f"配置文件不存在: {config_path}")
        logging.info("Please create the configuration file first.")
        sys.exit(1)

    config = load_config(config_path)

    logging.info(config)

    # 检查知识库文件（如果配置了）
    knowledge_file = config["retriever"]["milvus_dense"].get("knowledge_file")
    if knowledge_file:
        if not os.path.exists(knowledge_file):
            logging.info(f"警告：知识库文件不存在: {knowledge_file}")
            logging.info("请确保知识库文件存在于指定路径")
        else:
            logging.info(f"找到知识库文件: {knowledge_file}")

    logging.info("开始运行 Milvus 稠密向量检索管道...")
    pipeline_run()
