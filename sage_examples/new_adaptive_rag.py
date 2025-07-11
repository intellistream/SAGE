# === 基础模块导入 ===
import os, time
import json
from typing import Tuple, Any

# === 第三方工具包 ===
from dotenv import load_dotenv

# === Sage 工具包导入 ===
from sage_utils.config_loader import load_config
from sage_utils.embedding_methods.embedding_api import apply_embedding_model
from sage_memory.memory_manager import MemoryManager

from sage_core.api.env import LocalEnvironment
from sage_core.function.base_function import BaseFunction
from sage_core.api.function_api.filter_function import FilterFunction
from sage_core.api.function_api.flatmap_function import FlatMapFunction


from sage_common_funs.io.source import FileSource
from sage_common_funs.io.chatsink import ChatTerminalSink
from sage_common_funs.map.generator import OpenAIGenerator
from sage_common_funs.map.retriever import DenseRetriever
from sage_common_funs.map.promptor import QAPromptor
from sage_common_funs.map.templater import Templater
from sage_common_funs.map.agent import BaseAgent
from sage_common_funs.utils.template import AI_Template

# === Prompt 模板 ===
ROUTE_PROMPT_TEMPLATE = '''Instruction:
You are an expert at routing a user question to a vectorstore or web search. 
Use the vectorstore for questions on travel to Hubei Province in China. 
You do not need to be stringent with the keywords in the question related to these topics. 
Otherwise, use web-search. Give a binary choice 'web_search' or 'vectorstore' based on the question. 
Return a raw word of web_search or vectorstore with no preamble or explanation. 
'''

# === 数据处理Function类 ===

class RoutePromptFunction(MapFunction):
    """创建路由提示的Function"""
    
    def execute(self, data: AI_Template) -> AI_Template:
        input_template = data
        raw_question = input_template.raw_question
        system_prompt = {"role": "system", "content": ROUTE_PROMPT_TEMPLATE.format(question=input_template.raw_question)}
        user_prompt = {
            "role": "user",
            "content": f"Question: {raw_question}",
        }
        input_template.prompts.append(system_prompt)
        input_template.prompts.append(user_prompt)
        return input_template


class RouteDecisionFunction(MapFunction):
    """解析路由决策的Function"""
    
    def execute(self, data):
        input_template:AI_Template = data
        query = input_template.raw_question
        response = input_template.response
        self.logger.debug(f"Received routing response: {response} for query: {query}")
        try:
            
            if response == "vectorstore":
                route_decision = "vector"
            else:
                route_decision = "web"
                
            self.logger.info(f"Query: '{query}' -> Route: {route_decision}")
            return (input_template, route_decision)
        except Exception as e:
            self.logger.warning(f"Failed to parse routing response: {response}, error:{e}, defaulting to web")
            return (input_template, "web")


class ExtractQueryFunction(MapFunction):
    """提取查询字符串的Function"""
    
    def execute(self, data) :
        input_template, route_decision = data
        self.logger.debug(f"Extracted query: {input_template.raw_question} with route decision: {route_decision}")
        return input_template


# === 过滤器Function类 ===

class VectorRouteFilterFunction(FilterFunction):
    """过滤向量路由的Filter"""
    
    def execute(self, data) -> bool:
        input_template, route_decision = data
        return route_decision == "vector"


class WebRouteFilterFunction(FilterFunction):
    """过滤Web路由的Filter"""
    
    def execute(self, data) -> bool:
        input_template, route_decision = data
        return route_decision == "web"


class QueryLengthFilterFunction(FilterFunction):
    """过滤查询长度的Filter"""
    
    def __init__(self, min_length: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.min_length = min_length
    
    def execute(self, data) -> bool:
        query = data.raw_question
        return len(query.strip()) >= self.min_length


# === FlatMap Function示例 ===

class QueryTokenizerFunction(FlatMapFunction):
    """查询分词的FlatMap函数"""
    
    def execute(self, data) -> list:
        query = data
        # 简单分词示例
        tokens = query.split()
        return [token for token in tokens if len(token) > 2]


def main():
    """主函数"""
    # 设置向量数据库
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
        if text.strip():
            col.insert(text.strip(), metadata={})

    col.create_index(index_name="vdb_index")
    

    # 设置环境
    env = LocalEnvironment()
    env.set_memory_collection(col)
    config = load_config("new_adaptive.yaml")
    load_dotenv(override=False)

    # 设置 API Key（如果存在）
    alibaba_api_key = os.environ.get("ALIBABA_API_KEY")
    bocha_api_key = os.environ.get("BOCHA_API_KEY")

    if bocha_api_key:
        config.setdefault("agent", {})["search_api_key"] = bocha_api_key

    if alibaba_api_key:
        config.setdefault("generator", {})["api_key"] = alibaba_api_key
        config.setdefault("agent", {})["api_key"] = alibaba_api_key

    # === 构建流水线（使用新的filter和flatmap接口） ===

    # 第一阶段：查询预处理和路由决策
    route_stream = (
        env.from_source(FileSource, config["source"], delay = 10)
            .map(Templater)
           # .filter(QueryLengthFilterFunction, min_length=3)  # 过滤短查询
           .map(RoutePromptFunction)  # 创建路由提示
           .map(OpenAIGenerator, config["generator"])  # LLM路由判断
           .map(RouteDecisionFunction)  # 解析路由决策
    )

    # 第二阶段：向量检索分支
    vector_stream = (
        route_stream
        .filter(VectorRouteFilterFunction)  # 过滤向量路由
        .map(ExtractQueryFunction)  # 提取查询
        .map(DenseRetriever, config["retriever"])  # 检索相关文档
        .map(QAPromptor, config["promptor"])  # 构建QA prompt
        .map(OpenAIGenerator, config["generator"])  # 生成答案
        .sink(ChatTerminalSink, config["sink"])  # 输出结果
    )

    # 第三阶段：Web搜索分支
    web_stream = (
        route_stream
        .filter(WebRouteFilterFunction)  # 过滤Web路由
        .map(ExtractQueryFunction)  # 提取查询
        .map(BaseAgent, config["agent"])  # 使用Agent进行Web搜索
        .sink(ChatTerminalSink, config["sink"])  # 输出结果
    )

    # 可选：演示flatmap的使用
    # token_stream = (
    #     env.from_source(FileSource, config["source"])
    #        .flatmap(QueryTokenizerFunction)  # 将查询分词
    #        .sink(TerminalSink, config["sink"])  # 输出tokens
    # )

    # === 提交与执行 ===
    env.submit()
    env.run_streaming()
    time.sleep(60)
    env.close()


if __name__ == "__main__":
    main()