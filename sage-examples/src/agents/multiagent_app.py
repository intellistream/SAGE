import time
from sage.lib.utils.tool_filter import ToolFilter
from sage.core.api.local_environment import LocalEnvironment
from sage.lib.tools.searcher_tool import BochaSearchTool
from sage.lib.utils.context_sink import ContextFileSink
from sage.utils.config_loader import load_config
from sage.lib.agents.question_bot import QuestionBot
from sage.lib.agents.chief_bot import ChiefBot
from sage.lib.agents.searcher_bot import SearcherBot
from sage.lib.agents.answer_bot import AnswerBot
from sage.lib.agents.critic_bot import CriticBot


def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
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
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 收到中断信号，正在关闭...")
    env.stop()
    env.close()

if __name__ == '__main__':
    config = load_config("../../resources/config/multiagent_config.yaml")
    pipeline_run()