# === 基础模块导入 ===
import os
import json
from typing import Tuple, Any

# === 第三方工具包 ===
from dotenv import load_dotenv

# === Sage 工具包导入 ===
from sage_utils.config_loader import load_config
from sage_utils.embedding_methods.embedding_api import apply_embedding_model
from sage_memory.memory_manager import MemoryManager

from sage_core.api.env import LocalEnvironment
from sage_core.api.tuple import Data

from sage_common_funs.io.source import FileSource
from sage_common_funs.io.sink import TerminalSink
from sage_common_funs.rag.generator import OpenAIGenerator
from sage_common_funs.rag.retriever import DenseRetriever
from sage_common_funs.rag.promptor import QAPromptor
from sage_common_funs.agent.agent import BaseAgent

# === Prompt 模板 ===
ROUTE_PROMPT_TEMPLATE = '''Instruction:
You are an expert at routing a user question to a vectorstore or web search. 
Use the vectorstore for questions on travel to Hubei Province in China. 
You do not need to be stringent with the keywords in the question related to these topics. 
Otherwise, use web-search. Give a binary choice 'web_search' or 'vectorstore' based on the question. 
Return a JSON with a single key 'datasource' and no preamble or explanation. 
Question to route: {question}
'''

# === 辅助Lambda函数 ===

def create_route_prompt(query):
    """创建路由提示"""
    return Data([query, [{"role": "system", "content": ROUTE_PROMPT_TEMPLATE.format(question=query)}]])

def parse_route_decision(data):
    """解析路由决策"""
    query, response = data.data
    try:
        response_json = json.loads(response)
        datasource = response_json.get("datasource", "web_search")
        route = "vector" if "vectorstore" in datasource else "web"
        return Data((query, route))
    except (json.JSONDecodeError, KeyError):
        return Data((query, "web"))

def extract_query(data):
    """提取查询"""
    return data.data[0]

def is_vector_route(data):
    """判断是否为向量路由"""
    return data.data[1] == "vector"

def is_web_route(data):
    """判断是否为Web路由"""
    return data.data[1] == "web"

# === 向量库构建 ===

embedder = apply_embedding_model("hf", model="sentence-transformers/all-MiniLM-L6-v2")

manager = MemoryManager()
col = manager.create_collection(
    name="vdb_test",
    backend_type="VDB",
    embedding_model=embedder,
    dim=embedder.get_dim(),
    description="adaptive_rag vdb collection",
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

# 设置 API Key
alibaba_api_key = os.environ.get("ALIBABA_API_KEY")
bocha_api_key = os.environ.get("BOCHA_API_KEY")

if bocha_api_key:
    config.setdefault("agent", {})["search_api_key"] = bocha_api_key

if alibaba_api_key:
    config.setdefault("generator", {})["api_key"] = alibaba_api_key
    config.setdefault("agent", {})["api_key"] = alibaba_api_key

# === 构建流水线（完全使用Lambda函数） ===

# 主路由流
route_stream = (
    env.from_source(FileSource, config["source"])
       .map(create_route_prompt)  # 创建路由提示
       .map(OpenAIGenerator, config["generator"])  # LLM路由判断
       .map(parse_route_decision)  # 解析路由决策
)

# 向量检索分支
vector_stream = (
    route_stream
    .filter(is_vector_route)  # 过滤向量路由
    .map(extract_query)  # 提取查询
    .map(DenseRetriever, config["retriever"])  # 检索
    .map(QAPromptor, config["promptor"])  # 构建QA提示
    .map(OpenAIGenerator, config["generator"])  # 生成答案
    .sink(TerminalSink, config["sink"])  # 输出
)

# Web搜索分支
web_stream = (
    route_stream
    .filter(is_web_route)  # 过滤Web路由
    .map(extract_query)  # 提取查询
    .map(BaseAgent, config["agent"])  # Web搜索
    .sink(TerminalSink, config["sink"])  # 输出
)

# === 提交与执行 ===

env.submit()
env.run_once()
env.close()