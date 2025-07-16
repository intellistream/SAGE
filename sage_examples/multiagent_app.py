from dotenv import load_dotenv
import os, time
from sage_core.api.env import LocalEnvironment, RemoteEnvironment
from sage_utils.config_loader import load_config
from sage_library.agent.question_bot import QuestionBot
from sage_library.agent.chief_bot import ChiefBot
from sage_library.utils.context_sink import ContextFileSink
from sage_library.agent.searcher_bot import SearcherBot
from sage_library.tools.searcher_tool import BochaSearchTool
from sage_library.agent.answer_bot import AnswerBot
from sage_library.agent.critic_bot import CriticBot
from sage_library.utils.tool_filter import ToolFilter



def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    env.set_memory(config=None)

    chief_stream = (
        env.from_source(QuestionBot, config["question_bot"])
           .sink(ContextFileSink, config["question_bot_sink"])
           .flatmap(ChiefBot, config["chief_bot"])
           .sink(ContextFileSink, config["chief_bot_sink"])
    )
    searcher_stream = (chief_stream.filter(ToolFilter, config["searcher_filter"]).
            map(SearcherBot, config["searcher_bot"]).sink(ContextFileSink, config["searcher_bot_sink"])
           .map(BochaSearchTool, config["searcher_tool"]).sink(ContextFileSink, config["searcher_tool_sink"])
           
    )
    direct_response_stream = chief_stream.filter(ToolFilter, config["direct_response_filter"])

    answer_input_stream = searcher_stream.connect(direct_response_stream)

    response_stream = (answer_input_stream
        .map(AnswerBot, config["answer_bot"]).sink(ContextFileSink, config["answer_bot_sink"])
        .map(CriticBot, config["critic_bot"]).sink(ContextFileSink, config["critic_bot_sink"]).print("Final Results"))


    env.submit()
    env.run_once()
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 收到中断信号，正在关闭...")
    env.stop()
    env.close()
    # try:
    #     env.submit()
    #     env.run_streaming() # 开销有点大，最好只润一次做测试
    #     print("🌱 管道已启动，按 Ctrl+C 中断")
    #     while True:
    #         time.sleep(1)  # 持续运行直到被打断
    # except KeyboardInterrupt:
    #     print("\n🛑 收到中断信号，正在关闭...")
    #     env.stop()
    # finally:
    #     env.close()
    #     print("✅ 管道已安全关闭")

if __name__ == '__main__':
    config = load_config("multiagent_config.yaml")
    pipeline_run()