# python -m sage_examples.datastream_rag_pipeline


# 导入 Sage 中的 Environment 和相关组件
import logging
from sage_core.api.environment import Environment
from sage_common_funs.function.retriever import SimpleRetriever


async def init_memory_and_pipeline(job_id=None,  config=None, operators=None):
    """
    动态构建并初始化数据处理管道

    参数:
        job_id: 作业ID
        manager_handle: 内存管理器句柄
        config: 配置参数字典
        operators: 字典，包含需要构建的operators及其配置
                   格式: {
                       "source": {"type": "FileSource", "params": {}},
                       "steps": [
                           {"name": "retrieve", "type": "SimpleRetriever", "params": {}},
                           {"name": "construct_prompt", "type": "QAPromptor", "params": {}},
                           ...
                       ],
                       "sink": {"type": "FileSink", "params": {}}
                   }
    """

    # 创建一个新的管道实例
    pipeline_name = f"pipeline_{job_id}" if job_id else "dynamic_pipeline"
    pipeline = Environment(pipeline_name)

    # 如果没有提供operators配置，使用默认配置
    if not operators:
        operators = {
            "source": {"type": "FileSource", "params": {}},
            "steps": [
                {"name": "retrieve", "type": "SimpleRetriever", "params": {}},
                {"name": "construct_prompt", "type": "QAPromptor", "params": {}},
                {"name": "generate_response", "type": "OpenAIGenerator", "params": {}}
            ],
            "sink": {"type": "FileSink", "params": {}}
        }

    # 动态导入和创建operators
    # 1. 创建source
    source_type = operators["source"]["type"]
    source_class = globals()[source_type]
    current_stream = pipeline.from_source(source_class,config)

    # 2. 创建中间处理步骤
    for step in operators["steps"]:
        step_type = step["type"]
        step_name = step["name"]
        step_class = globals()[step_type]

        # 根据步骤名称调用相应的方法
        if hasattr(current_stream, step_name):
            method = getattr(current_stream, step_name)
            current_stream = method(step_class,config)
        else:
            logging.warning(f"Stream does not have method {step_name}, skipping this step")

    # 3. 创建sink
    sink_type = operators["sink"]["type"]
    sink_class = globals()[sink_type]
    sink_stream = current_stream.sink(sink_class,config)

    # 提交管道到 SAGE 运行时
    pipeline.submit(config={"is_long_running": True})
    return pipeline
   