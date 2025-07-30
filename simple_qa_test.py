#!/usr/bin/env python3
"""
简化版QA批处理测试 - 不使用memory service
"""
import time
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.batch_function import BatchFunction
from sage.core.function.map_function import MapFunction
from sage.core.function.sink_function import SinkFunction
from sage.utils.custom_logger import CustomLogger

class SimpleQABatch(BatchFunction):
    """
    简化的QA批处理数据源
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
        except Exception as e:
            print(f"Error loading file {self.data_path}: {e}")
            self.questions = []

    def execute(self):
        """返回下一个问题，如果没有更多问题则返回None"""
        if self.counter >= len(self.questions):
            print(f"SimpleQABatch: 完成，已处理 {self.counter} 个问题")
            return None  # 返回None表示批处理完成

        question = self.questions[self.counter]
        self.counter += 1
        print(f"SimpleQABatch: 生成问题 #{self.counter}: {question}")
        return question

class DummyRetriever(MapFunction):
    """模拟检索器"""
    def execute(self, data):
        if not data:
            return None
        
        print(f"DummyRetriever: 处理问题: {data}")
        # 模拟检索结果
        mock_results = ["模拟检索结果1", "模拟检索结果2"]
        result = (data, mock_results)
        print(f"DummyRetriever: 返回结果: {result}")
        return result

class DummyGenerator(MapFunction):
    """模拟生成器"""
    def execute(self, data):
        if not data:
            return None
        
        query, retrieved_texts = data
        print(f"DummyGenerator: 处理查询: {query}")
        
        # 模拟生成答案
        answer = f"基于检索到的信息：{retrieved_texts}，回答是：False"
        print(f"DummyGenerator: 生成答案: {answer}")
        return answer

class TerminalSink(SinkFunction):
    """终端输出"""
    def execute(self, data):
        print(f"=== 最终答案 ===")
        print(data)
        print("================")
        return data

def main():
    print("=== 简化QA批处理测试 ===")
    
    env = LocalEnvironment("simple_qa_test")
    
    # 配置
    config = {
        "source": {"data_path": "data/sample/one_question.txt"},
        "retriever": {"collection_name": "dummy"},
        "generator": {"model": "dummy"},
        "sink": {"output": "terminal"}
    }
    
    # 构建处理管道
    (env
        .from_batch(SimpleQABatch, config["source"])
        .map(DummyRetriever, config["retriever"])
        .map(DummyGenerator, config["generator"])
        .sink(TerminalSink, config["sink"])
    )
    
    try:
        print("开始QA处理...")
        env.submit()
        time.sleep(10)  # 等待处理完成
    except KeyboardInterrupt:
        print("测试中断")
    finally:
        print("测试结束")
        env.close()

if __name__ == '__main__':
    CustomLogger.disable_global_console_debug()
    main()
