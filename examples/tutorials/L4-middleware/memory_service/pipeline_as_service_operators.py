"""Pipeline-as-Service 架构组件

本模块实现了完整的 Pipeline-as-Service 模式，包含：

【核心组件】
1. PipelineBridge - 桥梁
   - 连接 Service 调用方和 Pipeline 实现
   - 使用双队列实现请求-响应模式
   - 通过 StopSignal 优雅关闭

2. QA Pipeline (服务 Pipeline)
   - QAPipelineSource: 从 Bridge 拉取请求
   - QAPipelineMap: 调用 Memory Service 处理
   - QAPipelineSink: 将结果返回给调用方

3. QAPipelineService (Pipeline 即服务)
   - 将 QA Pipeline 包装成可调用的 Service
   - process() 方法阻塞直到 Pipeline 完成
   - 实现背压机制的关键

4. Controller Pipeline (主 Pipeline)
   - QuestionBatch: 批量问题源
   - ProcessQuestion: 调用 QA Pipeline Service
   - DisplayAnswer: 显示最终结果

5. MockMemoryService (纯服务)
   - 模拟记忆检索和写入
   - 被 QA Pipeline 调用

【架构图】
```
主 Pipeline:
  QuestionBatch → ProcessQuestion → DisplayAnswer
                       ↓ call_service()
                  QA Pipeline Service
                       ↓ PipelineBridge
服务 Pipeline:
  QAPipelineSource → QAPipelineMap → QAPipelineSink
                          ↓ call_service()
                    Memory Service
```

【使用场景】
- RAG 系统：将检索-生成流程封装为服务
- 微服务架构：Pipeline 之间相互调用
- 背压控制：通过阻塞调用实现流量控制
"""

from __future__ import annotations

import queue
import time
from dataclasses import dataclass
from typing import Any, Dict, List

from sage.common.core.functions.batch_function import BatchFunction
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.api.service.base_service import BaseService
from sage.kernel.runtime.communication.router.packet import StopSignal


# ============================================================
# 组件 1: PipelineBridge - 实现 Service 和 Pipeline 的双向通信
# ============================================================


@dataclass
class PipelineRequest:
    """Pipeline 请求的数据结构

    Attributes:
        payload: 请求的实际数据（如问题、订单等）
        response_queue: 用于返回结果的队列（每个请求独立）
    """

    payload: Dict[str, Any]
    response_queue: "queue.Queue[Dict[str, Any]]"


class PipelineBridge:
    """PipelineBridge - Pipeline-as-Service 的核心桥梁

    【职责】：
    - 接收来自 Service 的请求（submit）
    - 将请求传递给 Pipeline（next）
    - 携带 response_queue 实现结果返回

    【工作流程】：
    调用方                    PipelineBridge                Pipeline
       │                          │                          │
       ├─ submit(payload) ─────→ │ 创建 response_queue        │
       │                          ├─────────────────────────→ │ Source.next()
       │                          │                          │
       │                          │                          ├─ Map 处理
       │                          │                          │
       │                          │ ←────────────────────────┤ Sink 返回
       ├─ response_queue.get() ←─┤                          │
       │                          │                          │

    【关闭流程】：
    - close() 发送 StopSignal 到请求队列
    - Pipeline 收到 StopSignal 后自然停止
    - 避免了轮询导致的资源浪费
    """

    def __init__(self):
        self._requests: "queue.Queue[PipelineRequest | StopSignal]" = queue.Queue()
        self._closed = False

    def submit(self, payload: Dict[str, Any]) -> "queue.Queue[Dict[str, Any]]":
        """提交请求到 Pipeline"""
        if self._closed:
            raise RuntimeError("Pipeline bridge is closed")
        response_q: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=1)
        req = PipelineRequest(payload=payload, response_queue=response_q)
        self._requests.put(req)
        return response_q

    def next(self, timeout: float = 0.1):
        """获取下一个请求（Pipeline Source 调用）

        返回：
        - PipelineRequest: 正常请求
        - StopSignal: 停止信号（bridge 已关闭且队列已空）
        - None: 暂时没有请求（超时）
        """
        if self._closed and self._requests.empty():
            return StopSignal("pipeline-service-shutdown")

        try:
            return self._requests.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        """关闭 Bridge，并主动发送 StopSignal"""
        if not self._closed:
            self._closed = True
            # 关键：主动放入 StopSignal，让 Pipeline 能够正常停止
            self._requests.put(StopSignal("pipeline-service-shutdown"))


# ============================================================
# 组件 2: MockMemoryService - 纯服务（被 Pipeline 调用）
# ============================================================


class MockMemoryService(BaseService):
    """模拟的记忆服务 - 纯服务角色

    【职责】：
    - 提供 retrieve() 方法：检索历史记录
    - 提供 insert() 方法：写入新记录

    【调用方】：
    - 被 QA Pipeline 的 Map 算子调用
    - 通过 self.call_service('mock_memory', ...) 调用

    【特点】：
    - 纯粹的服务，没有 Pipeline 身份
    - 使用 sleep 模拟 I/O 延迟
    - 在实际应用中，这会是真正的向量数据库或知识库
    """

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
# 组件 3: QA Pipeline 算子 - 服务 Pipeline 的实现
# ============================================================
# 这是一条完整的 Pipeline，但它被包装成 Service 供主 Pipeline 调用
# 三个算子：Source（拉取请求）→ Map（处理）→ Sink（返回结果）
# ============================================================


class QAPipelineSource(SourceFunction):
    """QA Pipeline 的 Source - 从 PipelineBridge 拉取请求

    【职责】：
    - 轮询 PipelineBridge 获取请求
    - 识别并传递 StopSignal 以触发 Pipeline 停止
    - 返回 PipelineRequest 给下游处理

    【关键点】：
    - 这是服务 Pipeline 的入口
    - 通过 bridge.next() 实现阻塞轮询
    - StopSignal 必须透传才能停止 Pipeline
    """

    def __init__(self, bridge: PipelineBridge):
        super().__init__()
        self._bridge = bridge

    def execute(self, data=None):
        """轮询 bridge，获取请求

        返回：
        - PipelineRequest: 正常请求，继续处理
        - StopSignal: 停止信号，触发 Pipeline 停止
        - None: 暂时没有数据，继续轮询
        """
        req = self._bridge.next(timeout=0.1)

        if req is None:
            return None

        # 关键：识别并传递 StopSignal
        if isinstance(req, StopSignal):
            print(f"  [QAPipelineSource] 收到停止信号: {req}")
            return req

        return req


class QAPipelineMap(MapFunction):
    """QA Pipeline 的 Map - 核心处理逻辑

    【职责】：
    - 调用 MockMemoryService 检索历史
    - 模拟 LLM 生成答案（实际中这里会调用真实的 LLM）
    - 调用 MockMemoryService 写入记忆

    【调用链】：
    - self.call_service('mock_memory', ..., method='retrieve')
    - sleep(1.0) 模拟 LLM 生成
    - self.call_service('mock_memory', ..., method='insert')

    【关键点】：
    - 透传 StopSignal（不处理）
    - 处理正常请求并返回结果 + response_queue
    """

    def execute(self, data):
        if not data:
            return None

        # 透传 StopSignal
        if isinstance(data, StopSignal):
            print(f"  [QAPipelineMap] 透传停止信号: {data}")
            return data

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
    """QA Pipeline 的 Sink - 将结果返回给调用方

    【职责】：
    - 将处理结果放入 response_queue
    - QAPipelineService 会从这个队列获取结果
    - 识别 StopSignal 但不需要特殊处理

    【关键点】：
    - 这是服务 Pipeline 的出口
    - response_queue 实现了结果的异步返回
    - StopSignal 到达后 Pipeline 自然停止
    """

    def execute(self, data):
        if not data:
            return

        # StopSignal 不需要处理，只是让它通过即可触发停止
        if isinstance(data, StopSignal):
            print("  [QAPipelineSink] 收到停止信号，Pipeline 即将停止")
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
# 组件 4: QAPipelineService - 将 QA Pipeline 包装为 Service
# ============================================================
# 这是 Pipeline-as-Service 的关键：Pipeline 同时也是 Service
# ============================================================


class QAPipelineService(BaseService):
    """QA Pipeline Service - Pipeline 即服务的包装器

    【双重身份】：
    - 对外：是一个 Service，提供 process() 接口
    - 对内：通过 PipelineBridge 连接到真实的 Pipeline

    【工作流程】：
    1. 主 Pipeline 调用 call_service('qa_pipeline', data)
    2. 进入 process() 方法
    3. bridge.submit(data) 提交到 QA Pipeline
    4. **阻塞等待** response_queue.get()
    5. QA Pipeline 完成后，结果从 response_queue 返回
    6. 返回给主 Pipeline

    【背压机制】：
    - process() 方法会阻塞！
    - 主 Pipeline 必须等待 QA Pipeline 完成
    - 这就是背压的实现原理
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
# 组件 5: 主 Pipeline 算子 - Controller Pipeline 的实现
# ============================================================
# 这是驱动整个流程的主 Pipeline
# 三个算子：Batch（批量问题）→ Map（调用服务）→ Sink（显示结果）
# ============================================================


class QuestionBatch(BatchFunction):
    """主 Pipeline 的 Batch Source - 批量问题源

    【职责】：
    - 提供批量问题数据
    - 在末尾自动添加 shutdown 命令
    - 控制整个处理流程的节奏

    【关键点】：
    - BatchFunction 需要实现 execute() 方法
    - 返回 None 时自动停止
    - shutdown 命令触发 QA Pipeline 关闭
    """

    def __init__(self, questions: List[str], include_shutdown: bool = True):
        super().__init__()
        self.questions: List[str | Dict[str, str]] = list(questions)
        if include_shutdown:
            # 添加 shutdown 命令
            self.questions.append({"command": "shutdown"})
        self.total = len(self.questions)
        self.index = 0

    def execute(self):
        """每次调用返回一个问题，返回 None 时结束"""
        if self.index >= self.total:
            return None

        item = self.questions[self.index]
        self.index += 1

        # 如果是 shutdown 命令，直接返回
        if isinstance(item, dict) and item.get("command") == "shutdown":
            return item

        # 否则是正常问题
        return {
            "question": item,
            "index": self.index,  # index 已经+1了
            "total": self.total - 1,  # 减去 shutdown 命令
        }


class ProcessQuestion(MapFunction):
    """主 Pipeline 的 Map - 调用 QA Pipeline Service 处理问题

    【职责】：
    - 调用 QA Pipeline Service 处理每个问题
    - 处理 shutdown 命令
    - 记录时间戳验证背压机制

    【背压机制的体现】：
    - self.call_service('qa_pipeline', data) **会阻塞**
    - 必须等待 QA Pipeline 完成才返回
    - 因此第二个问题必须等第一个问题完成

    【关键点】：
    - 这是背压机制的触发点
    - shutdown 命令也通过正常流程传递
    """

    def __init__(self, qa_service_name: str = "qa_pipeline", timeout: float = 60.0):
        super().__init__()
        self.qa_service_name = qa_service_name
        self.timeout = timeout

    def execute(self, data):
        if not data:
            return None

        # 处理 shutdown 命令
        if data.get("command") == "shutdown":
            print(f"\n{'=' * 60}")
            print("[Controller] 🛑 发送 shutdown 命令到 QA Pipeline")
            print(f"{'=' * 60}")
            result = self.call_service(self.qa_service_name, data, timeout=self.timeout)
            return {"type": "shutdown", "ack": result}

        # 处理正常问题
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
    """主 Pipeline 的 Sink - 显示最终结果

    【职责】：
    - 接收 QA Pipeline 返回的答案
    - 打印格式化的结果
    - 处理 shutdown 响应

    【输出信息】：
    - 问题和答案
    - 检索到的历史记录数量
    - 总耗时（验证背压效果）
    - 完成时间戳
    """

    def __init__(self):
        super().__init__()

    def execute(self, data):
        if not data:
            return

        # 处理 shutdown 响应
        if data.get("type") == "shutdown":
            print(f"\n{'=' * 60}")
            print("[Result] ✅ QA Pipeline 已关闭")
            print(f"[Result] 响应: {data.get('ack')}")
            print(f"{'=' * 60}\n")
            return

        # 处理正常答案
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
