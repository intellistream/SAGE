"""简单的 LLM Pipeline 示例 - 使用本地 vLLM 服务

这个示例展示如何：
1. 使用本地启动的 vLLM 服务（Qwen/Qwen3-8B-AWQ）
2. 创建一个简单的问答 Pipeline
3. 顺序处理多个问题并显示答案
"""

import queue
import sys
import time
from pathlib import Path

import yaml
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.middleware.operators.rag import OpenAIGenerator, QAPromptor
from sage.platform.service import BaseService


class PipelineBridge:
    """Pipeline 之间的通信桥梁"""

    def __init__(self):
        self._queue = queue.Queue()
        self._closed = False

    def submit(self, payload):
        """提交请求到 Pipeline"""
        if self._closed:
            raise RuntimeError("PipelineBridge is closed")
        response_q = queue.Queue()
        self._queue.put({"payload": payload, "response_queue": response_q})
        return response_q

    def next(self, timeout=0.1):
        """从 Pipeline 获取下一个请求"""
        if self._closed:
            return None
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        """关闭 Bridge"""
        self._closed = True


# ==================== LLM 问答服务 Pipeline ====================


class LLMSource(SourceFunction):
    """从 bridge 接收问答请求"""

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def execute(self, data=None):
        if self.bridge._closed:
            return None
        request = self.bridge.next(timeout=0.1)
        return request if request else None


class LLMMap(MapFunction):
    """使用 LLM 生成答案"""

    def __init__(self, config):
        super().__init__()
        self.config = config

    def execute(self, data):
        if not data:
            return None

        payload = data["payload"]
        question = payload["question"]

        print("🔧 LLMMap: 开始处理问题...")

        # 使用配置文件中的 promptor 配置
        promptor_config = self.config.get("promptor", {})
        if not promptor_config.get("template"):
            promptor_config[
                "template"
            ] = """你是一位友好的健康助手。请简洁、准确地回答用户的问题。

用户问题: {{ question }}

请提供有帮助的建议："""

        promptor = QAPromptor(promptor_config)
        prompted = promptor.execute({"question": question})

        print("📝 Prompt 准备完成，开始调用 LLM...")

        # 使用配置文件中的 generator 配置
        generator_config = self.config.get("generator", {}).get("vllm", {})
        generator = OpenAIGenerator(generator_config)
        generator.ctx = self.ctx

        # 生成答案
        answer = generator.execute(prompted)

        print("✅ LLM 生成完成")

        return {
            "payload": {"question": question, "answer": answer},
            "response_queue": data["response_queue"],
        }


class LLMSink(SinkFunction):
    """将答案返回给调用者"""

    def execute(self, data):
        if not data:
            return
        data["response_queue"].put(data["payload"])


class LLMService(BaseService):
    """LLM 服务：接收问题，返回答案"""

    def __init__(self, bridge, config):
        super().__init__()
        self.bridge = bridge
        self.config = config

    def ask(self, question_data):
        """处理单个问题"""
        response_q = self.bridge.submit(question_data)
        return response_q.get(timeout=60.0)


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

        return {"question": q, "index": self.index, "total": self.max}


class ProcessQuestion(MapFunction):
    """调用 LLM Service 处理问题"""

    def execute(self, data):
        if not data:
            return None

        question = data["question"]
        index = data["index"]
        total = data.get("total", index)

        # 打印问题
        print(f"\n{'='*60}")
        print(f"📝 问题 {index}/{total}: {question}")
        print(f"{'='*60}")

        print("🔄 调用 LLM Service...")

        # 调用 LLM Service（阻塞等待答案）
        result = self.call_service(
            "llm_service", {"question": question}, method="ask", timeout=120.0
        )

        print("✅ 收到 LLM Service 的回答")

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
                title = line.replace("###", "").strip()
                line = f"\033[1m{title}\033[0m"

            # 处理 **加粗**
            elif "**" in line:
                line = re.sub(r"\*\*(.+?)\*\*", r"\033[1m\1\033[0m", line)

            # 处理数字列表项
            if re.match(r"^\d+\.\s+", line):
                line = re.sub(r"^(\d+)\.\s+", r"\033[1m\1.\033[0m ", line)

            # 处理缩进的破折号列表项
            elif re.match(r"^\s+-\s+", line):
                line = re.sub(r"^(\s+)-\s+", r"\1\033[1m-\033[0m ", line)

            formatted_lines.append(line)

        return "\n".join(formatted_lines)

    def execute(self, data):
        if not data:
            return

        answer_data = data.get("answer", {})

        # 显示答案
        if isinstance(answer_data, dict):
            answer_text = answer_data.get("generated", str(answer_data))
            generate_time = answer_data.get("generate_time", 0)
        else:
            answer_text = str(answer_data)
            generate_time = 0

        # 渲染 Markdown
        rendered_answer = self._render_markdown(answer_text)

        print(f"\n{'='*60}")
        print("💡 AI 回答:")
        print(f"{'='*60}")
        print(rendered_answer)
        print(f"{'='*60}")
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
    """主函数"""
    print("=== 启动简单 LLM Pipeline 示例 ===\n")

    script_dir = Path(__file__).parent
    config_file = script_dir / "config" / "short_term_memory_pipeline.yaml"

    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}")
        sys.exit(1)

    print(f"📄 加载配置文件: {config_file}")
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    print("🔧 创建环境...")
    env = LocalEnvironment("simple_llm_pipeline")

    try:
        print("🌉 创建 Pipeline Bridge...")
        llm_bridge = PipelineBridge()

        print("📝 注册 LLM 服务...")
        env.register_service("llm_service", LLMService, llm_bridge, config)

        print("🔗 创建 LLM Pipeline（生成答案）...")
        env.from_source(LLMSource, llm_bridge).map(LLMMap, config).sink(LLMSink)

        print("🎮 创建 Controller Pipeline（顺序发送问题）...")
        total_questions = config["source"].get("max_index", 5)
        bridges = [llm_bridge]
        env.from_source(QuestionController, config["source"]).map(ProcessQuestion).sink(
            DisplayAnswer, bridges, total_questions
        )

        print("\n" + "=" * 60)
        print("🚀 启动 LLM Pipeline...")
        print("=" * 60 + "\n")

        env.submit(autostop=False)

        # 等待足够的时间让所有问题处理完成
        expected_time = total_questions * 30 + 10  # 每个问题预计 30 秒
        print(f"⏳ 等待最多 {expected_time} 秒让所有问题处理完成...")

        # 分段等待，每 5 秒检查一次
        for i in range(0, expected_time, 5):
            time.sleep(5)
            elapsed = i + 5
            print(f"⏱️  已等待 {elapsed}/{expected_time} 秒...")

        print("\n" + "=" * 60)
        print("✅ Pipeline 执行完成!")
        print("=" * 60)

    finally:
        print("\n🛑 停止 Pipeline...")
        env.stop()

        print("🧹 清理环境资源...")
        env.close()
        print("✅ 环境已清理，程序正常退出\n")


if __name__ == "__main__":
    print("=== 程序开始执行 ===\n")
    CustomLogger.disable_global_console_debug()
    main()
    print("\n=== 程序执行完毕 ===")
