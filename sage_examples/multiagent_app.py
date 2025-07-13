from dotenv import load_dotenv
import os, time
from sage_core.api.env import LocalEnvironment, RemoteEnvironment
from sage_utils.config_loader import load_config
from sage_library.agent.question_bot import QuestionBot
from sage_library.utils.template_sink import TemplateFileSink


def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    env.set_memory(config=None)

    query_stream = (
        env.from_source(QuestionBot, config["question_bot"])
           .sink(TemplateFileSink)
           .print("Result")
    )

    try:
        env.submit()
        env.run_streaming()
        print("🌱 管道已启动，按 Ctrl+C 中断")
        while True:
            time.sleep(1)  # 持续运行直到被打断
    except KeyboardInterrupt:
        print("\n🛑 收到中断信号，正在关闭...")
        env.stop()
    finally:
        env.close()
        print("✅ 管道已安全关闭")

if __name__ == '__main__':
    config = load_config("multiagent_config.yaml")
    pipeline_run()