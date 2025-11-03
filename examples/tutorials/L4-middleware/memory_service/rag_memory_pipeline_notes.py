"""简化的 Pipeline-as-Service 示例 - 用于理解背压机制

这是一个最小化的示例，展示核心架构：
- Controller Pipeline (顺序发送请求，提供背压)
- QA Pipeline Service (Pipeline 注册为 Service)
- Mock Memory Service (模拟服务，使用 sleep)

所有实际业务逻辑都用 sleep 模拟，方便调试和理解：
- Mock Memory Service: sleep 0.5秒 模拟检索/写入
- QA Pipeline: sleep 1秒 模拟生成答案

运行: python3 examples/tutorials/memory/rag_memory_pipeline_notes.py

核心要点：
1. 背压机制：Controller 调用 self.call_service("qa_pipeline", ...) 会阻塞
2. 阻塞直到：QA Pipeline 完成处理并通过 response_queue 返回结果
3. 效果：第二个问题必须等第一个问题完全处理完才开始处理

观察输出中的时间戳来验证顺序执行。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.service.base_service import BaseService

# ============================================================
# 1. PipelineBridge - 将 Pipeline 包装成可调用的 Service
# ============================================================
import queue
from dataclasses import dataclass


@dataclass
class PipelineRequest:
    payload: Dict[str, Any]
    response_queue: "queue.Queue[Dict[str, Any]]"


class PipelineBridge:
    """连接 Service 和 Pipeline 的桥梁

    工作原理：
    1. Service.process() 调用 bridge.submit(data) 创建 response_queue
    2. Pipeline Source 通过 bridge.next() 获取请求
    3. Pipeline 处理完后，Sink 将结果放入 response_queue
    4. Service.process() 从 response_queue 获取结果并返回
    """

    def __init__(self):
        self._requests: "queue.Queue[PipelineRequest]" = queue.Queue()
        self._closed = False

    def submit(self, payload: Dict[str, Any]) -> "queue.Queue[Dict[str, Any]]":
        if self._closed:
            raise RuntimeError("Pipeline bridge is closed")
        response_q: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=1)
        req = PipelineRequest(payload=payload, response_queue=response_q)
        self._requests.put(req)
        return response_q

    def next(self, timeout: float = 0.1):
        if self._closed and self._requests.empty():
            return None
        try:
            return self._requests.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        self._closed = True


# ============================================================
# 2. Mock Memory Service - 模拟记忆服务（用 sleep 代替实际操作）
# ============================================================
class MockMemoryService(BaseService):
    """模拟的记忆服务，使用 sleep 模拟检索和写入延迟"""

    def __init__(self):
        super().__init__()
        self._memory = {}  # 简单的内存存储
        self._counter = 0

    def retrieve(self, question: str) -> List[Dict[str, Any]]:
        """模拟检索历史记忆"""
        print(f"  [MockMemoryService] 开始检索: {question}")
        time.sleep(0.5)  # 模拟检索延迟

        # 返回一些模拟数据
        results = []
        if self._counter > 0:
            results = [
                {"history_query": f"历史问题 {i}", "answer": f"历史答案 {i}"}
                for i in range(min(2, self._counter))
            ]
        print(f"  [MockMemoryService] 检索完成，找到 {len(results)} 条记录")
        return results

    def insert(self, question: str, metadata: Dict[str, Any]) -> bool:
        """模拟写入记忆"""
        print(f"  [MockMemoryService] 写入记忆: {question}")
        time.sleep(0.3)  # 模拟写入延迟
        self._memory[question] = metadata
        self._counter += 1
        print("  [MockMemoryService] 写入完成")
        return True


# ============================================================
# 3. QA Pipeline - 完整的问答处理流程（Pipeline 形式）
# ============================================================
class QAPipelineSource(SourceFunction):
    """从 Bridge 获取请求"""

    def __init__(self, bridge: PipelineBridge):
        super().__init__()
        self._bridge = bridge

    def execute(self, data=None):
        # 轮询 bridge，获取请求
        req = self._bridge.next(timeout=0.1)
        return req if req else None


class QAPipelineMap(MapFunction):
    """核心处理逻辑 - 检索、生成、写入"""

    def execute(self, data):
        if not data:
            return None

        # 从请求中提取数据
        payload = data.payload if hasattr(data, "payload") else data["payload"]
        question = payload["question"]

        print(f"  [QAPipelineMap] 开始处理问题: {question}")

        # 步骤 1: 调用 MockMemoryService 检索历史
        context = self.call_service("mock_memory", question, method="retrieve")

        # 步骤 2: 模拟生成答案（用 sleep 代替实际的 LLM 调用）
        print("  [QAPipelineMap] 模拟生成答案...")
        time.sleep(1.0)  # 模拟 LLM 生成延迟
        answer = f"这是针对「{question}」的回答（模拟生成）"

        # 步骤 3: 写入记忆
        self.call_service(
            "mock_memory",
            question,
            {"answer": answer, "topic": "测试"},
            method="insert",
        )

        print("  [QAPipelineMap] 处理完成")

        # 构造返回结果
        out = {"question": question, "answer": answer, "context": context}

        # 获取响应队列
        resp_q = (
            data.response_queue
            if hasattr(data, "response_queue")
            else data["response_queue"]
        )
        return {"payload": out, "response_queue": resp_q}


class QAPipelineSink(SinkFunction):
    """将结果放入响应队列，返回给调用者"""

    def execute(self, data):
        if not data:
            return
        resp = data["payload"] if isinstance(data, dict) and "payload" in data else data
        resp_q = (
            data["response_queue"]
            if isinstance(data, dict) and "response_queue" in data
            else getattr(data, "response_queue", None)
        )
        if resp_q:
            resp_q.put(resp)
            print("  [QAPipelineSink] 结果已返回")


# ============================================================
# 4. QA Pipeline Service - 将 Pipeline 注册为 Service
# ============================================================
class QAPipelineService(BaseService):
    """将 QA Pipeline 包装成 Service，提供同步调用接口

    关键：这里的 process() 方法会阻塞，直到 Pipeline 完成处理
    这就是背压机制的核心实现！
    """

    def __init__(self, bridge: PipelineBridge, request_timeout: float = 30.0):
        super().__init__()
        self._bridge = bridge
        self._request_timeout = request_timeout

    def process(self, message: Dict[str, Any]):
        """处理请求 - 阻塞直到 Pipeline 返回结果"""
        if message is None:
            raise ValueError("Empty message")

        if message.get("command") == "shutdown":
            self._bridge.close()
            return {"status": "shutdown_ack"}

        # 提交到 Pipeline 并等待结果（阻塞！）
        response_q = self._bridge.submit(message)
        try:
            return response_q.get(timeout=self._request_timeout)
        except queue.Empty:
            raise TimeoutError("Pipeline service timed out")


# ============================================================
# 5. Controller Pipeline - 顺序发送问题，观察背压效果
# ============================================================
class QuestionController(SourceFunction):
    """顺序发送问题"""

    def __init__(self, questions: List[str], max_index: int | None = None):
        super().__init__()
        self.questions = questions
        self.max = max_index if max_index is not None else len(questions)
        self.index = 0

    def execute(self, data=None):
        if self.index >= self.max:
            return None
        q = self.questions[self.index]
        self.index += 1
        return {"question": q, "index": self.index, "total": self.max}


class ProcessQuestion(MapFunction):
    """调用 QA Pipeline Service 处理问题

    关键：self.call_service() 会阻塞直到 QA Pipeline 完成
    这保证了一个问题处理完才会处理下一个（背压）
    """

    def __init__(self, qa_service_name: str = "qa_pipeline", timeout: float = 60.0):
        super().__init__()
        self.qa_service_name = qa_service_name
        self.timeout = timeout

    def execute(self, data):
        if not data:
            return None

        question = data["question"]
        index = data["index"]
        total = data.get("total", index)

        print(f"\n{'=' * 60}")
        print(f"[Controller] 📝 问题 {index}/{total}: {question}")
        print(f"[Controller] ⏰ 开始时间: {time.strftime('%H:%M:%S')}")
        print(f"{'=' * 60}")

        start_time = time.time()

        # 🔑 关键：这里会阻塞，直到 QA Pipeline Service 完成处理
        result = self.call_service(
            self.qa_service_name, {"question": question}, timeout=self.timeout
        )

        elapsed = time.time() - start_time
        result["index"] = index
        result["elapsed"] = elapsed
        return result


class DisplayAnswer(SinkFunction):
    """显示答案"""

    def __init__(self, total_questions: int = 5, bridges: list | None = None):
        super().__init__()
        self.total_questions = total_questions
        self.processed = 0
        self.bridges = bridges or []

    def execute(self, data):
        if not data:
            return

        q = data.get("question")
        ans = data.get("answer")
        ctx = data.get("context", [])
        idx = data.get("index", 0)
        elapsed = data.get("elapsed", 0)

        print(f"\n{'=' * 60}")
        print(f"[Result] ✅ 问题 {idx} 处理完成")
        print(f"[Result] Q: {q}")
        print(f"[Result] A: {ans}")
        print(f"[Result] 检索到 {len(ctx)} 条历史记录")
        print(f"[Result] ⏱️  总耗时: {elapsed:.2f}秒")
        print(f"[Result] ⏰ 完成时间: {time.strftime('%H:%M:%S')}")
        print(f"{'=' * 60}\n")

        self.processed += 1

        # 所有问题处理完后，关闭 bridges
        if self.processed >= self.total_questions:
            print(f"\n✅ 所有 {self.total_questions} 个问题已处理完成")
            for b in self.bridges:
                b.close()


# ============================================================
# 6. Main - 组装并运行
# ============================================================


def main():
    """主函数 - 演示背压机制"""

    print("=" * 60)
    print("简化的 Pipeline-as-Service 示例")
    print("演示：Controller Pipeline + QA Pipeline Service + Mock Memory")
    print("=" * 60)

    CustomLogger.disable_global_console_debug()

    # 简单的配置
    questions = [
        "问题1：什么是背压机制？",
        "问题2：SAGE 如何实现 Pipeline-as-Service？",
        "问题3：PipelineBridge 的作用是什么？",
    ]

    total_q = len(questions)

    print(f"\n将依次处理 {total_q} 个问题")
    print("观察输出中的时间戳，验证是顺序执行（一个问题完成后才开始下一个）\n")

    # 创建环境
    env = LocalEnvironment("simple_backpressure_demo")

    try:
        # 1. 注册 Mock Memory Service（模拟记忆服务）
        print("✓ 注册 Mock Memory Service")
        env.register_service("mock_memory", MockMemoryService)

        # 2. 创建 PipelineBridge
        print("✓ 创建 PipelineBridge")
        qa_bridge = PipelineBridge()

        # 3. 注册 QA Pipeline Service
        print("✓ 注册 QA Pipeline Service")
        env.register_service("qa_pipeline", QAPipelineService, qa_bridge)

        # 4. 创建 QA Pipeline（实际处理逻辑）
        print("✓ 创建 QA Pipeline")
        env.from_source(QAPipelineSource, qa_bridge).map(QAPipelineMap).sink(
            QAPipelineSink
        )

        # 5. 创建 Controller Pipeline（顺序发送问题）
        print("✓ 创建 Controller Pipeline")
        env.from_source(QuestionController, questions, total_q).map(
            ProcessQuestion
        ).sink(DisplayAnswer, total_q, [qa_bridge])

        print("\n" + "=" * 60)
        print("🚀 启动 Pipeline...")
        print("=" * 60)

        # 启动
        env.submit(autostop=False)

        # 等待足够的时间让所有问题处理完成
        # 每个问题大约需要 2秒（检索0.5秒 + 生成1秒 + 写入0.3秒）
        wait_time = total_q * 3 + 2
        print(f"\n⏳ 等待 {wait_time} 秒让所有问题处理完成...\n")
        time.sleep(wait_time)

        print("\n" + "=" * 60)
        print("✅ Pipeline 执行完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n🛑 停止 Pipeline...")
        env.stop()

        print("🧹 清理环境资源...")
        env.close()
        print("✅ 环境已清理，程序正常退出\n")


if __name__ == "__main__":
    main()
