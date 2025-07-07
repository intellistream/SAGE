# === 基础模块导入 ===
import os
from typing import Tuple

# === 第三方工具包 ===
from dotenv import load_dotenv

# === Sage 工具包导入 ===
from sage_utils.config_loader import load_config
from sage_utils.logging_utils import configure_logging
from sage_utils.custom_logger import CustomLogger
from sage_utils.embedding_methods.embedding_api import apply_embedding_model
from sage_memory.memory_manager import MemoryManager

from sage_core.api.env import LocalEnvironment
from sage_core.api.base_function import BaseFunction
from sage_core.api.tuple import Data

from sage_common_funs.io.source import FileSource
from sage_common_funs.io.sink import TerminalSink
from sage_common_funs.rag.generator import OpenAIGenerator
from sage_common_funs.rag.retriever import DenseRetriever
from sage_common_funs.rag.promptor import QAPromptor
from sage_common_funs.agent.agent import BaseAgent
from typing import Tuple, List, Union, Type, Any

# === Prompt 模板 ===
ROUTE_PROMPT_TEMPLATE = '''Instruction:
You are an expert at routing a user question to a vectorstore or web search. 
Use the vectorstore for questions on travel to Hubei Province in China. 
You do not need to be stringent with the keywords in the question related to these topics. 
Otherwise, use web-search. Give a binary choice 'web_search' or 'vectorstore' based on the question. 
Return a JSON with a single key 'datasource' and no preamble or explanation. 
Question to route: {question}
'''


# === Operator 类定义 ===

class RoutePromptFunction(BaseFunction):
    """
    构造路由 prompt，用于判断使用向量库还是 Web 搜索。
    """
    def __init__(self, config: dict = None, *args, **kwargs):
        super.__init__(**kwargs)
        self.config = config
        self.prompt = ROUTE_PROMPT_TEMPLATE
        self.logger.set_console_level("DEBUG")
        self.logger.set_file_level("DEBUG")
        self.logger.set_global_level("DEBUG")

    def execute(self, data: Data) -> Data[list]:
        query = data.data
        system_prompt = {
            "role": "system",
            "content": self.prompt.format(question=query)
        }
        return Data([query, [system_prompt]])


class RouteSplitter(BaseFunction):
    """
    根据 OpenAI 输出结果判断是走 vectorstore 还是 web search 路径。
    """
    def __init__(self, config: dict = None, *args, **kwargs):
        super.__init__(**kwargs)
        self.config = config
        self.logger.set_console_level("DEBUG")
        self.logger.set_file_level("DEBUG")
        self.logger.set_global_level("DEBUG")
        
    @classmethod 
    def declare_outputs(cls):
        return [("vector", Any), ("web", Any)]
    
    def execute(self, data: Data[Tuple[str, str]]):
        print(f"RouteSplitter received data: {data.data}")
        if "vectorstore" in data.data[1]:
            self.collector.collect("vector", data)
        else:
            self.collector.collect("web", data)


# === 向量库构建 ===

embedder = apply_embedding_model("hf", model="sentence-transformers/all-MiniLM-L6-v2")

manager = MemoryManager()
col = manager.create_collection(
    name="vdb_test",
    backend_type="VDB",
    embedding_model=embedder,
    dim=embedder.get_dim(),
    description="operator_test vdb collection",
    as_ray_actor=False
)

# 加载数据并入库
with open("./data/hubei.txt", "r", encoding="utf-8") as f:
    texts = f.read().split("##")

for text in texts:
    col.insert(text.strip(), metadata={})

col.create_index(index_name="vdb_index")


# === 环境与配置 ===

env = LocalEnvironment()
env.set_memory_collection(col)

config = load_config("config_adaptive.yaml")
load_dotenv(override=False)

# 设置 API Key（如果存在）
alibaba_api_key = os.environ.get("ALIBABA_API_KEY")
bocha_api_key = os.environ.get("BOCHA_API_KEY")

if bocha_api_key:
    config.setdefault("agent", {})["search_api_key"] = bocha_api_key

if alibaba_api_key:
    config.setdefault("generator", {})["api_key"] = alibaba_api_key
    config.setdefault("agent", {})["api_key"] = alibaba_api_key


# === 构建主流程与分支 ===

# 主 Query 路由流程
query_stream = (
    env.from_source(FileSource, config["source"])
       .map(RoutePromptFunction, config["route_promptor"])
       .map(OpenAIGenerator, config["generator"])
       .map(RouteSplitter, config["route_splitter"])
)

# 向量流分支
vector_stream = (
    query_stream.side_output("vector")
                .map(DenseRetriever, config["retriever"])
                .map(QAPromptor, config["promptor"])
                .map(OpenAIGenerator, config["generator"])
                .sink(TerminalSink, config["sink"])
)

# Web 搜索流分支
web_stream = (
    query_stream.side_output("web")
                .map(BaseAgent, config["agent"])
                .map(TerminalSink, config)
)


# === 提交与执行 ===

env.submit()
env.run_once()
