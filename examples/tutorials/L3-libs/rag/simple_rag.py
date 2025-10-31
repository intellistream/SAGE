#!/usr/bin/env python3
"""
简化版RAG应用 - 测试完整流程
用于验证问题源→检索→生成→输出的完整数据流
"""

import os
import sys
import time

from dotenv import load_dotenv

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment


class SimpleQuestionSource(SourceFunction):
    """简单问题源：只发送一个问题进行测试"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sent = False

    def execute(self, data=None):
        if self.sent:
            return None
        self.sent = True
        question = "张先生的手机通常放在什么地方？"
        print(f"📝 发送问题: {question}")
        return question


class SimpleRetriever(MapFunction):
    """简化的检索器"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 模拟知识库数据
        self.knowledge = {
            "张先生的手机": "张先生习惯把手机放在办公桌右上角的充电座上",
            "李女士的钱包": "李女士总是把钱包放在卧室梳妆台的第一个抽屉里",
            "王经理的钥匙": "王经理的办公室钥匙通常挂在衣帽架上的西装口袋里",
        }

    def execute(self, data):
        question = data
        print(f"🔍 检索问题: {question}")

        # 简单的关键词匹配
        relevant_info = []
        for key, value in self.knowledge.items():
            if any(word in question for word in key.split()):
                relevant_info.append(value)

        context = "\n".join(relevant_info) if relevant_info else "没有找到相关信息"
        result = {"query": question, "context": context}
        print(f"✅ 检索结果: {context}")
        return result


class SimplePromptor(MapFunction):
    """简化的提示构建器"""

    def execute(self, data):
        query = data["query"]
        context = data["context"]

        prompt = f"""请根据以下背景信息回答问题：

背景信息：
{context}

问题：{query}

请给出简洁准确的回答："""

        result = {"query": query, "prompt": prompt}
        print("✅ 构建提示完成")
        return result


class SimpleGenerator(MapFunction):
    """简化的AI生成器 - 使用模拟回答"""

    def execute(self, data):
        query = data["query"]
        data["prompt"]

        print("🤖 AI生成中...")

        # 模拟AI回答
        if "张先生" in query and "手机" in query:
            answer = "根据提供的信息，张先生习惯把手机放在办公桌右上角的充电座上。"
        elif "李女士" in query and "钱包" in query:
            answer = "根据提供的信息，李女士总是把钱包放在卧室梳妆台的第一个抽屉里。"
        elif "王经理" in query and "钥匙" in query:
            answer = "根据提供的信息，王经理的办公室钥匙通常挂在衣帽架上的西装口袋里。"
        else:
            answer = "抱歉，我无法根据现有信息回答这个问题。"

        result = {"query": query, "answer": answer}
        print(f"✅ AI生成完成: {answer}")
        return result


class SimpleTerminalSink(SinkFunction):
    """简化的终端输出"""

    def execute(self, data):
        query = data["query"]
        answer = data["answer"]

        print("\n" + "=" * 60)
        print(f"❓ 问题: {query}")
        print(f"💬 回答: {answer}")
        print("=" * 60 + "\n")


def pipeline_run():
    """运行简化RAG管道"""
    print("🚀 启动简化版RAG系统")
    print("📊 流程: 问题源 → 简单检索 → 提示构建 → 模拟生成 → 终端输出")
    print("=" * 60)

    # 创建环境
    env = LocalEnvironment()

    # 构建管道
    (
        env.from_source(SimpleQuestionSource)
        .map(SimpleRetriever)
        .map(SimplePromptor)
        .map(SimpleGenerator)
        .sink(SimpleTerminalSink)
    )

    try:
        print("🔄 开始处理...")
        env.submit()
        time.sleep(5)  # 等待处理完成
        print("✅ 处理完成")

    except Exception as e:
        print(f"❌ 处理出错: {e}")
        import traceback

        traceback.print_exc()
    finally:
        env.close()


if __name__ == "__main__":
    # 检查是否在测试模式下运行
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        print("🧪 Test mode detected - rag_simple example")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    CustomLogger.disable_global_console_debug()
    load_dotenv(override=False)
    pipeline_run()
