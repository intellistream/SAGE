# import unittest
# import logging
# import time
# import io
# from contextlib import redirect_stdout
# from pathlib import Path
# import os
# import yaml
# from dotenv import load_dotenv
#
# from sage_core.api.env import LocalEnvironment
# from sage_common_funs.io.sink import TerminalSink
# from sage_common_funs.io.source import FileSource
# from sage_common_funs.rag.generator import OpenAIGenerator
# from sage_common_funs.rag.promptor import QAPromptor
# from sage_common_funs.rag.retriever import DenseRetriever
# from sage_utils.config_loader import load_config
# from sage_utils.logging_utils import configure_logging
#
#
# class TestFullLocalPipeline(unittest.TestCase):
#     def setUp(self):
#         configure_logging(level=logging.INFO)
#         load_dotenv(override=False)
#         self.config = load_config('config_mixed.yaml')
#         api_key = os.environ.get("ALIBABA_API_KEY")
#         if api_key:
#             self.config.setdefault("generator", {})["api_key"] = api_key
#
#     def test_local_pipeline_run(self):
#         """测试 Remote pipeline 执行，并验证是否输出至少 5 次 Q/A"""
#         env = LocalEnvironment()
#         env.set_memory(config=None)
#
#         query_stream = (env
#             .from_source(FileSource, self.config["source"])
#             .map(DenseRetriever, self.config["retriever"])
#             .map(QAPromptor, self.config["promptor"])
#             .map(OpenAIGenerator, self.config["generator"])
#             .sink(TerminalSink, self.config["sink"])
#         )
#
#         env.submit()
#
#         with io.StringIO() as buf, redirect_stdout(buf):
#             env.run_once()
#             env.run_once()
#             env.run_once()
#             time.sleep(15)
#             output = buf.getvalue()
#
#         q_count = output.count("[Q] Question :")
#         a_count = output.count("[A] Answer :")
#
#         self.assertGreaterEqual(q_count, 3, f"Question 输出不足 3 次，实际为 {q_count}")
#         self.assertGreaterEqual(a_count, 3, f"Answer 输出不足 3 次，实际为 {a_count}")
#
#
#
# if __name__ == '__main__':
#     unittest.main()

import logging
import time
import io
import pytest
from contextlib import redirect_stdout
from dotenv import load_dotenv
import os

from sage_core.api.env import LocalEnvironment
from sage_common_funs.io.sink import TerminalSink
from sage_common_funs.io.source import FileSource
from sage_common_funs.rag.generator import OpenAIGenerator
from sage_common_funs.rag.promptor import QAPromptor
from sage_common_funs.rag.retriever import DenseRetriever
from sage_utils.config_loader import load_config
from sage_utils.logging_utils import configure_logging


@pytest.fixture(scope="function")
def config():
    configure_logging(level=logging.INFO)
    load_dotenv(override=False)
    cfg = load_config("config_mixed.yaml")
    api_key = os.environ.get("ALIBABA_API_KEY")
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


def test_remote_pipeline_run(env, config):
    """测试 Remote pipeline 执行，并验证是否输出至少 5 次 Q/A"""

    query_stream = (env
        .from_source(FileSource, config["source"])
        .map(DenseRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"])
        .sink(TerminalSink, config["sink"])
    )

    env.submit()

    with io.StringIO() as buf, redirect_stdout(buf):
        env.run_once()
        env.run_once()
        env.run_once()
        time.sleep(5)
        output = buf.getvalue()

    assert output.count("[Q] Question :") >= 3, "Question 输出不足 3 次"
    assert output.count("[A] Answer :") >= 3, "Answer 输出不足 3 次"
    env.close()
