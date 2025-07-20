import logging
import pytest
from dotenv import load_dotenv
import os

from sage_core.environment.base_environment import LocalEnvironment
from sage_common_funs.io.sink import TerminalSink
from sage_common_funs.io.source import FileSource
from sage_libs.rag.generator import OpenAIGenerator
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.retriever import DenseRetriever
from sage_utils.config_loader import load_config
from sage_utils.logging_utils import configure_logging


@pytest.fixture(scope="function")
def config():
    configure_logging(level=logging.INFO)
    load_dotenv(override=False)
    cfg = load_config("config_mixed.yaml")
    api_key = os.environ.get("VLLM_API_KEY")
    if api_key:
        cfg.setdefault("generator", {})["api_key"] = api_key
    return cfg


@pytest.fixture(scope="function")
def env():
    env = LocalEnvironment()
    env.set_memory(config=None)
    yield env
    # teardown: 主动清理资源
    try:
        if hasattr(env, "executor"):
            env.executor.shutdown(wait=False)
        if hasattr(env, "actors"):
            for a in env.actors:
                a.kill()
    except Exception as e:
        logging.warning(f"env teardown failed: {e}")


def test_pipeline_execution(env, config):
    """验证 pipeline 是否正确运行"""

    query_stream = (env
        .from_source(FileSource, config["source"])
        .map(DenseRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"])
        .sink(TerminalSink, config["sink"])
    )

    env.submit()

    # 运行 pipeline 并检查是否成功执行
    for i in range(3):
        try:
            env.run_once()
            logging.info(f"Pipeline run {i + 1} executed successfully.")
            env.stop()
        except Exception as e:
            pytest.fail(f"Pipeline run {i + 1} failed: {e}")


    env.close()
