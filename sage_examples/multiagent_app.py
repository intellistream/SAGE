from dotenv import load_dotenv
import os, time
from sage_core.api.env import LocalEnvironment, RemoteEnvironment
from sage_utils.config_loader import load_config
from sage_library.agent.question_bot import QuestionBot
from sage_library.agent.chief_bot import ChiefBot
from sage_library.utils.template_sink import TemplateFileSink
from sage_library.agent.searcher_bot import SearcherBot
from sage_library.tools.searcher_tool import BochaSearchTool


def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    env.set_memory(config=None)

    query_stream = (
        env.from_source(QuestionBot, config["question_bot"])
           .sink(TemplateFileSink, config["question_bot_sink"])
           .flatmap(ChiefBot, config["chief_bot"])
           .sink(TemplateFileSink, config["chief_bot_sink"])
           .map(SearcherBot, config["searcher_bot"])
           .sink(TemplateFileSink, config["searcher_bot_sink"])
           .map(BochaSearchTool, config["searcher_tool"])
           .sink(TemplateFileSink, config["searcher_tool_sink"])
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