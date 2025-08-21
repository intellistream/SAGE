import time
import os
from dotenv import load_dotenv

from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.sink import TerminalSink
from sage.libs.io_utils.batch import JSONLBatch
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import ChromaRetriever
from sage.common.utils.config.loader import load_config


def pipeline_run(config: dict) -> None:
    """
    创建并运行 ChromaDB 专用 RAG 数据处理管道

    Args:
        config (dict): 包含各模块配置的配置字典。
    """
    
    print("=== 启动基于 ChromaDB 的 RAG 问答系统 ===")
    print("配置信息:")
    print(f"  - 源文件: {config['source']['data_path']}")
    print(f"  - 检索器: DenseRetriever (ChromaDB 专用)")
    print(f"  - 向量维度: {config['retriever']['dimension']}")
    print(f"  - Top-K: {config['retriever']['top_k']}")
    print(f"  - 集合名称: {config['retriever']['chroma']['collection_name']}")
    print(f"  - 嵌入模型: {config['retriever']['embedding']['method']}")


    env = LocalEnvironment()
    #env.set_memory(config=None)

    # 构建数据处理流程
    # DenseRetriever 会在初始化时自动加载配置的知识库文件
    print("正在构建数据处理管道...")
    
    (env
        .from_batch(JSONLBatch, config["source"])
        .map(ChromaRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )

    print("正在提交并运行管道...")
    env.submit()
    time.sleep(5)  # 等待管道运行5秒
    env.close()
    print("=== RAG 问答系统运行完成 ===")


if __name__ == '__main__':
    load_dotenv(override=False)
    from sage.common.utils.logging.custom_logger import CustomLogger
    CustomLogger.disable_global_console_debug()
    load_dotenv(override=False)
    
    config_file = os.environ.get('SAGE_CONFIG', 'config_chroma_only.yaml')
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", config_file)
    
    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
        print("可用的 ChromaDB 配置文件：")
        print("  - config_chroma_only.yaml ")
        print()
        print("使用方法:")
        print("  SAGE_CONFIG=config_chroma_only.yaml python qa_openai.py")
        exit(1)
    
    config = load_config(config_path)
    
    print(f"使用配置文件: {config_file}")

    
    # 检查知识库文件（如果配置了）
    knowledge_file = config["retriever"]["chroma"].get("knowledge_file")
    if knowledge_file:
        if not os.path.exists(knowledge_file):
            print(f"警告：知识库文件不存在: {knowledge_file}")
            print("请确保知识库文件存在于指定路径")
        else:
            print(f"找到知识库文件: {knowledge_file}")

    pipeline_run(config)
