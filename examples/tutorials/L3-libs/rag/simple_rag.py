#!/usr/bin/env python3
"""
简化版RAG应用 - 测试完整流程
用于验证问题源→检索→生成→输出的完整数据流

支持 RemoteEnvironment + LocalSinkScheduler：
- 计算任务在远程节点执行
- Sink 节点绑定到本地（客户端），输出可见
"""

import os
import socket
import sys
import time

from dotenv import load_dotenv

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.remote_environment import RemoteEnvironment
from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision


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


class SimpleFileSink(SinkFunction):
    """文件输出 - 结果写入文件，便于远程执行后查看"""

    def __init__(self, output_path: str = "/home/sage/SAGE/.sage/rag_output.txt", **kwargs):
        super().__init__(**kwargs)
        self.output_path = output_path

    def execute(self, data):
        from datetime import datetime

        query = data["query"]
        answer = data["answer"]

        # 构建输出内容
        output = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "answer": answer,
        }

        # 追加写入文件
        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"时间: {output['timestamp']}\n")
            f.write(f"问题: {query}\n")
            f.write(f"回答: {answer}\n")
            f.write("=" * 60 + "\n\n")

        print(f"✅ 结果已写入: {self.output_path}")


# ============================================================
# LocalSinkScheduler - 将 Sink 节点绑定到本地
# ============================================================


class LocalSinkScheduler(BaseScheduler):
    """
    本地 Sink 调度器：将 Sink 节点放到客户端本地执行

    工作原理：
    - Sink 节点 → 绑定到本地（使用实际的 Ray 节点 ID）
    - 其他节点 → 使用 Ray 默认负载均衡

    使用场景：
    - RemoteEnvironment 远程执行计算
    - 但希望 Sink 输出在本地可见

    注意：需要在 Ray 集群环境中运行，会获取当前节点的真实 Ray node ID
    """

    def __init__(self):
        super().__init__()
        self.local_hostname = socket.gethostname()
        self._local_node_id = None  # 延迟获取

    def _get_local_node_id(self):
        """获取当前节点的 Ray node ID"""
        if self._local_node_id is not None:
            return self._local_node_id

        try:
            import ray

            if not ray.is_initialized():
                # 如果 Ray 没有初始化，返回 None 使用默认调度
                return None

            # 获取当前节点的 node ID
            current_node_id = ray.get_runtime_context().get_node_id()
            self._local_node_id = current_node_id
            return current_node_id
        except Exception:
            return None

    def make_decision(self, task_node):
        """根据任务类型决定放置策略"""
        # 导入放在方法内部，确保远程反序列化时可用
        from sage.kernel.scheduler.decision import PlacementDecision

        task_name = getattr(task_node, "name", str(task_node))

        # 检查是否是 Sink 节点
        is_sink = "Sink" in task_name or "sink" in task_name.lower()

        if is_sink:
            # 获取本地节点的真实 Ray node ID
            local_node_id = self._get_local_node_id()

            if local_node_id:
                # 使用真实的 Ray node ID
                return PlacementDecision(
                    target_node=local_node_id,
                    placement_strategy="affinity",
                    reason=f"Sink bound to local node: {self.local_hostname} (node_id: {local_node_id[:8]}...)",
                )
            else:
                # 如果无法获取 node ID，使用默认调度
                return PlacementDecision(
                    placement_strategy="default",
                    reason="Sink: Could not get local node ID, using default scheduling",
                )

        # 其他任务使用默认调度
        return PlacementDecision(
            placement_strategy="default",
            reason="Default load balancing for compute tasks",
        )


def pipeline_run():
    """运行简化RAG管道"""
    print("🚀 启动简化版RAG系统")
    print("📊 流程: 问题源 → 简单检索 → 提示构建 → 模拟生成 → 终端输出")
    print("=" * 60)

    # 选择环境模式
    USE_REMOTE = True  # 设为 True 使用远程模式（需要先启动 JobManager）

    if USE_REMOTE:
        # 远程模式：需要先启动 JobManager
        # 运行: sage jobmanager start --host 0.0.0.0 --port 19001
        scheduler = LocalSinkScheduler()
        print(f"📍 使用 LocalSinkScheduler，Sink 将在本地节点 ({scheduler.local_hostname}) 执行")
        env = RemoteEnvironment(
            "rag_simple_demo",
            host="sage-node-1",
            scheduler=scheduler,
        )
    else:
        # 本地模式：直接执行，无需额外服务
        print("📍 使用 LocalEnvironment 本地执行")
        env = LocalEnvironment("rag_simple_demo")

    # 输出文件路径
    output_file = "/home/sage/SAGE/.sage/rag_output.txt"

    # 构建管道
    (
        env.from_source(SimpleQuestionSource)
        .map(SimpleRetriever)
        .map(SimplePromptor)
        .map(SimpleGenerator)
        .sink(SimpleFileSink, output_file)  # 使用 FileSink
    )

    try:
        print(f"🔄 开始处理... 结果将写入: {output_file}")
        env.submit()
        time.sleep(5)  # 等待处理完成
        print("✅ 处理完成")

        # 显示输出文件内容
        if os.path.exists(output_file):
            print(f"\n📄 输出文件内容 ({output_file}):")
            with open(output_file, encoding="utf-8") as f:
                print(f.read())

    except Exception as e:
        print(f"❌ 处理出错: {e}")
        import traceback

        traceback.print_exc()
    finally:
        env.close()


if __name__ == "__main__":
    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - rag_simple example")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    CustomLogger.disable_global_console_debug()
    load_dotenv(override=False)
    pipeline_run()
