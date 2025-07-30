#!/usr/bin/env python3
"""
直接模拟的QA批处理 - 完全跳过memory service
"""
import time
from dotenv import load_dotenv
from sage.utils.custom_logger import CustomLogger
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.batch_function import BatchFunction
from sage.core.function.map_function import MapFunction
from sage.lib.io.sink import TerminalSink
from sage.lib.rag.generator import OpenAIGenerator
from sage.lib.rag.promptor import QAPromptor
from sage.utils.config_loader import load_config

class WorkingQABatch(BatchFunction):
    """
    工作版QA批处理数据源
    """
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.data_path = config["data_path"]
        self.counter = 0
        self.questions = []
        self._load_questions()

    def _load_questions(self):
        """从文件加载问题"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as file:
                self.questions = [line.strip() for line in file.readlines() if line.strip()]
            print(f"WorkingQABatch: 成功加载 {len(self.questions)} 个问题")
        except Exception as e:
            print(f"WorkingQABatch: Error loading file {self.data_path}: {e}")
            self.questions = []

    def execute(self):
        """返回下一个问题，如果没有更多问题则返回None"""
        if self.counter >= len(self.questions):
            print(f"WorkingQABatch: 完成处理，共处理 {self.counter} 个问题")
            return None  # 返回None表示批处理完成

        question = self.questions[self.counter]
        self.counter += 1
        print(f"WorkingQABatch: 生成问题 #{self.counter}: {question}")
        return question

class MockBiologyRetriever(MapFunction):
    """模拟生物学知识检索器 - 不使用memory service"""
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        print("MockBiologyRetriever: 初始化完成（使用模拟数据）")

    def execute(self, data):
        if not data:
            return None

        query = data
        print(f"MockBiologyRetriever: 处理查询: {query}")

        # 返回模拟的生物学知识
        retrieved_texts = [
            "减数分裂产生的四个子细胞在基因上是不同的，这是因为交叉互换和独立分配的结果。",
            "减数分裂通过两次连续的细胞分裂，将二倍体细胞转变为四个单倍体配子。",
            "减数分裂的关键特征是同源染色体配对和分离，这与有丝分裂不同。"
        ]
        
        result = (query, retrieved_texts)
        print(f"MockBiologyRetriever: 返回检索结果")
        return result

def pipeline_run(config: dict) -> None:
    """
    创建并运行数据处理管道
    """
    env = LocalEnvironment("working_qa_batch")

    print("开始构建处理管道...")
    
    # 构建数据处理流程 - 使用模拟检索器
    (env
        .from_batch(WorkingQABatch, config["source"])
        .map(MockBiologyRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )

    print("提交处理管道...")
    env.submit()
    print("等待处理完成...")
    time.sleep(10)  # 等待处理完成
    print("关闭环境...")
    env.close()

if __name__ == '__main__':
    print("=== 工作版QA批处理测试 ===")
    CustomLogger.disable_global_console_debug()
    load_dotenv(override=False)
    
    try:
        config = load_config("config_batch.yaml")
        print("成功加载配置文件")
        pipeline_run(config)
    except Exception as e:
        print(f"运行时错误: {e}")
        import traceback
        traceback.print_exc()
