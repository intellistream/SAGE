# @test:require-api
# @test:timeout=180
"""测试 Pipeline-as-Service with RAG Memory - Sequential Question Processing

此示例需要 OpenAI API 密钥，且需要较长运行时间（约 60-90 秒）。
在 CI 环境中会被自动跳过。
"""

import queue
import sys
import time
from pathlib import Path

import yaml
from rag_memory_service import RAGMemoryService

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.service.base_service import BaseService
from sage.middleware.operators.rag import OpenAIGenerator, QAPromptor


class PipelineBridge:
    def __init__(self):
        self._queue = queue.Queue()
        self._closed = False

    def submit(self, payload):
        if self._closed:
            raise RuntimeError("PipelineBridge is closed")
        response_q = queue.Queue()
        self._queue.put({"payload": payload, "response_queue": response_q})
        return response_q

    def next(self, timeout=0.1):
        if self._closed:
            return None
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        self._closed = True


# ==================== 检索服务 ====================


class RetrievalSource(SourceFunction):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def execute(self, data=None):
        # 如果 bridge 已关闭，停止生成数据
        if self.bridge._closed:
            return None
        request = self.bridge.next(timeout=0.1)
        return request if request else None


class RetrievalMap(MapFunction):
    def execute(self, data):
        if not data:
            return None
        question = data["payload"]["question"]
        # 调用 RAG Memory 服务进行检索
        results = self.call_service("rag_memory", question, method="retrieve")

        if results:
            print(f"🔍 检索到 {len(results)} 条历史记忆:")
            for i, r in enumerate(results, 1):
                hist_q = r["history_query"]
                if len(hist_q) > 50:
                    hist_q = hist_q[:50] + "..."
                print(f"   {i}. {hist_q}")
        else:
            print("🔍 未检索到历史记忆（索引为空）")

        context = results
        return {
            "payload": {"question": question, "context": context},
            "response_queue": data["response_queue"],
        }


class RetrievalSink(SinkFunction):
    def execute(self, data):
        if not data:
            return
        data["response_queue"].put(data["payload"])


class RetrievalService(BaseService):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def retrieve(self, data):
        response_q = self.bridge.submit(data)
        return response_q.get(timeout=10.0)


# ==================== 写入服务 ====================


class WritingSource(SourceFunction):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def execute(self, data=None):
        request = self.bridge.next(timeout=0.1)
        return request if request else None


class WritingMap(MapFunction):
    def __init__(self, config):
        super().__init__()
        self.config = config

    def execute(self, data):
        if not data:
            return None
        payload = data["payload"]
        question = payload["question"]
        payload.get("context", [])

        # 使用配置文件中的 promptor 配置
        promptor_config = self.config.get("promptor", {})
        if not promptor_config.get("template"):
            promptor_config["template"] = """你是一位具备长期记忆的个人健康助手。

{%- if external_corpus %}
以下是相关的历史问答：
{{ external_corpus }}
{%- endif %}"""

        promptor = QAPromptor(promptor_config)
        prompted = promptor.execute(payload)

        # 使用配置文件中的 generator 配置
        generator_config = self.config.get("generator", {}).get("vllm", {})
        generator = OpenAIGenerator(generator_config)
        generator.ctx = self.ctx
        answer = generator.execute(prompted)

        # 写入记忆
        self.call_service(
            "rag_memory",
            question,
            {"answer": answer, "topic": "健康-个性化"},
            method="insert",
        )
        print("💾 已将问答存入记忆索引")

        return {
            "payload": {"question": question, "answer": answer},
            "response_queue": data["response_queue"],
        }


class WritingSink(SinkFunction):
    def execute(self, data):
        if not data:
            return
        data["response_queue"].put(data["payload"])


class WritingService(BaseService):
    def __init__(self, bridge, config):
        super().__init__()
        self.bridge = bridge
        self.config = config

    def write(self, data):
        response_q = self.bridge.submit(data)
        return response_q.get(timeout=10.0)


# ==================== QA Pipeline Service（检索+生成+写入）====================


class QAPipelineSource(SourceFunction):
    """从 bridge 接收 QA 请求"""

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def execute(self, data=None):
        # 如果 bridge 已关闭，停止生成数据
        if self.bridge._closed:
            return None
        request = self.bridge.next(timeout=0.1)
        return request if request else None


class QAPipelineMap(MapFunction):
    """执行检索、生成答案、写入记忆的完整流程"""

    def __init__(self, config):
        super().__init__()
        self.config = config

    def execute(self, data):
        if not data:
            return None

        payload = data["payload"]
        question = payload["question"]

        # 步骤 1: 检索历史记忆
        retrieval_result = self.call_service(
            "retrieval_service", {"question": question}, method="retrieve"
        )
        context = retrieval_result["context"]

        # 步骤 2: 准备 prompt
        promptor_config = self.config.get("promptor", {})
        if not promptor_config.get("template"):
            promptor_config["template"] = """你是一位具备长期记忆的个人健康助手。

{%- if external_corpus %}
以下是相关的历史问答：
{{ external_corpus }}
{%- endif %}"""

        promptor = QAPromptor(promptor_config)
        prompted = promptor.execute({"question": question, "external_corpus": context})

        # 步骤 3: 生成答案（使用配置文件中的 generator 配置）
        generator_config = self.config.get("generator", {}).get("vllm", {})
        generator = OpenAIGenerator(generator_config)
        generator.ctx = self.ctx
        answer = generator.execute(prompted)

        # 步骤 4: 写入记忆
        self.call_service(
            "rag_memory",
            question,
            {"answer": answer, "topic": "健康-个性化"},
            method="insert",
        )

        return {
            "payload": {"question": question, "answer": answer, "context": context},
            "response_queue": data["response_queue"],
        }


class QAPipelineSink(SinkFunction):
    """将答案返回给调用者"""

    def execute(self, data):
        if not data:
            return
        data["response_queue"].put(data["payload"])


class QAPipelineService(BaseService):
    """QA Pipeline Service：接收问题，返回答案"""

    def __init__(self, bridge, config):
        super().__init__()
        self.bridge = bridge
        self.config = config

    def process(self, question_data):
        """处理单个问题"""
        response_q = self.bridge.submit(question_data)
        return response_q.get(timeout=120.0)


# ==================== Controller Pipeline（顺序发送问题）====================


class QuestionController(SourceFunction):
    """顺序发送问题，每次只发送一个"""

    def __init__(self, config):
        super().__init__()
        self.questions = config.get("questions")
        self.max = config.get("max_index", len(self.questions))
        self.index = 0

    def execute(self, data=None):
        if self.index >= self.max:
            return None

        q = self.questions[self.index]
        self.index += 1

        # 不在这里打印，让 ProcessQuestion 打印，这样才能保证一问一答
        return {"question": q, "index": self.index, "total": self.max}


class ProcessQuestion(MapFunction):
    """调用 QA Pipeline Service 处理问题"""

    def execute(self, data):
        if not data:
            return None

        question = data["question"]
        index = data["index"]
        total = data.get("total", index)

        # 在调用服务之前打印问题
        print(f"\n{'=' * 60}")
        print(f"📝 问题 {index}/{total}: {question}")
        print(f"{'=' * 60}")

        # 调用 QA Pipeline Service（阻塞等待答案）
        result = self.call_service("qa_pipeline", {"question": question}, timeout=180.0)

        result["index"] = index
        return result


class DisplayAnswer(SinkFunction):
    """显示答案"""

    def __init__(self, bridges=None, total_questions=5):
        super().__init__()
        self.bridges = bridges or []
        self.total_questions = total_questions
        self.processed_count = 0

    @staticmethod
    def _render_markdown(text):
        """简单的 Markdown 渲染，用于终端显示"""
        import re

        lines = text.split("\n")
        formatted_lines = []

        for line in lines:
            # 处理 ### 三级标题
            if line.startswith("###"):
                # 去掉 ### 并加粗整行
                title = line.replace("###", "").strip()
                line = f"\033[1m{title}\033[0m"

            # 处理 **加粗** (但跳过已经被标题处理过的行)
            elif "**" in line:
                line = re.sub(r"\*\*(.+?)\*\*", r"\033[1m\1\033[0m", line)

            # 处理数字列表项
            if re.match(r"^\d+\.\s+", line):
                # 给数字加粗
                line = re.sub(r"^(\d+)\.\s+", r"\033[1m\1.\033[0m ", line)

            # 处理缩进的破折号列表项
            elif re.match(r"^\s+-\s+", line):
                # 给破折号加粗
                line = re.sub(r"^(\s+)-\s+", r"\1\033[1m-\033[0m ", line)

            formatted_lines.append(line)

        return "\n".join(formatted_lines)

    def execute(self, data):
        if not data:
            return

        data.get("question", "")
        answer_data = data.get("answer", {})
        context = data.get("context", [])
        data.get("index", 0)

        # 显示检索到的历史
        if context:
            print(f"\n🔍 检索到 {len(context)} 条历史记忆:")
            for i, item in enumerate(context[:5], 1):  # 最多显示5条
                hist_q = item.get("history_query", "")
                if len(hist_q) > 60:
                    hist_q = hist_q[:60] + "..."
                print(f"   {i}. {hist_q}")
        else:
            print("\n🔍 未检索到历史记忆（索引为空）")

        print("💾 已将问答存入记忆索引")

        # 显示答案
        if isinstance(answer_data, dict):
            answer_text = answer_data.get("generated", str(answer_data))
            generate_time = answer_data.get("generate_time", 0)
        else:
            answer_text = str(answer_data)
            generate_time = 0

        # 渲染 Markdown
        rendered_answer = self._render_markdown(answer_text)

        print(f"\n{'=' * 60}")
        print("💡 AI 回答:")
        print(f"{'=' * 60}")
        print(rendered_answer)
        print(f"{'=' * 60}")
        if generate_time > 0:
            print(f"⏱️  生成耗时: {generate_time:.2f}秒")
        print()

        # 更新处理计数
        self.processed_count += 1

        # 如果所有问题都处理完了，关闭所有 bridges
        if self.processed_count >= self.total_questions:
            print(f"\n✅ 所有 {self.total_questions} 个问题已处理完成，关闭 bridges...")
            for bridge in self.bridges:
                bridge.close()
            print("✅ Bridges 已关闭，Pipeline 即将停止...")


def main():
    sys.stdout.flush()
    sys.stderr.flush()
    print("=== main() 第 1 行 ===", file=sys.stderr, flush=True)

    script_dir = Path(__file__).parent
    print("=== main() 第 2 行 ===", file=sys.stderr, flush=True)

    config_file = script_dir / "config" / "config_rag_memory_pipeline.yaml"
    print(f"=== 配置文件: {config_file} ===", file=sys.stderr, flush=True)

    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}", file=sys.stderr)
        sys.exit(1)

    print("=== 开始加载配置 ===", file=sys.stderr, flush=True)
    with open(config_file) as f:
        config = yaml.safe_load(f)
    print("=== 配置加载完成 ===", file=sys.stderr, flush=True)

    print("创建环境...")
    env = LocalEnvironment("rag_memory_pipeline")

    try:
        # 注册 RAG Memory 服务
        print("注册 RAG Memory 服务...")
        env.register_service("rag_memory", RAGMemoryService, config["rag_config"])

        print("创建 Pipeline Bridges...")
        retrieval_bridge = PipelineBridge()
        qa_pipeline_bridge = PipelineBridge()

        # 注册服务
        print("注册服务...")
        env.register_service("retrieval_service", RetrievalService, retrieval_bridge)
        env.register_service(
            "qa_pipeline", QAPipelineService, qa_pipeline_bridge, config
        )

        # 检索 Pipeline（为 QA Pipeline 提供检索功能）
        print("创建检索 Pipeline...")
        env.from_source(RetrievalSource, retrieval_bridge).map(RetrievalMap).sink(
            RetrievalSink
        )

        # QA Pipeline（检索 + 生成 + 写入）
        print("创建 QA Pipeline...")
        env.from_source(QAPipelineSource, qa_pipeline_bridge).map(
            QAPipelineMap, config
        ).sink(QAPipelineSink)

        # Controller Pipeline（顺序发送问题）
        print("创建 Controller Pipeline...")
        total_questions = config["source"].get("max_index", 5)
        bridges = [retrieval_bridge, qa_pipeline_bridge]
        env.from_source(QuestionController, config["source"]).map(ProcessQuestion).sink(
            DisplayAnswer, bridges, total_questions
        )

        print("🚀 启动 RAG Memory Pipeline...")
        env.submit(
            autostop=False
        )  # 使用 autostop=False，因为 Service Pipelines 会持续轮询

        # 等待足够的时间让所有问题处理完成
        # 每个问题大约需要 8-10 秒（检索 + 生成 + 写入）
        expected_time = total_questions * 10 + 5  # 给每个问题 10 秒 + 5 秒缓冲
        print(f"⏳ 等待 {expected_time} 秒让所有问题处理完成...")
        time.sleep(expected_time)

        print("✅ Pipeline 执行完成!")

    finally:
        # ============================================================
        # 【重要】清理资源 - 最佳实践
        # ============================================================
        # 在应用结束时，务必调用 env.stop() + env.close() 来优雅地关闭所有资源：
        # 1. env.stop() - 停止所有正在运行的 Pipeline
        # 2. env.close() - 关闭所有注册的 Service 并释放资源
        # 3. 防止资源泄漏和僵尸进程
        #
        # 使用 try-finally 确保即使发生异常也能清理资源。
        # 这是开发 SAGE 应用的推荐做法，可以减少 bug 和意外行为。
        # ============================================================
        print("🛑 停止 Pipeline...")
        env.stop()

        print("🧹 清理环境资源...")
        env.close()
        print("✅ 环境已清理，程序正常退出")


if __name__ == "__main__":
    print("=== 程序开始执行 ===", flush=True)
    CustomLogger.disable_global_console_debug()
    print("=== CustomLogger 已禁用 ===", flush=True)
    main()
    print("=== 程序执行完毕 ===", flush=True)
