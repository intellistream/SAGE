# python -m sage_examples.datastream_rag_pipeline


# 导入 Sage 中的 Environment 和相关组件
import logging
import re
from sage_core.environment.local_environment import LocalEnvironment
from sage_core.environment.base_environment import RemoteEnvironment

def init_memory_and_pipeline(job_id=None,  config=None, operators=None,use_ray=False):
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
    use_Ray = False
    for key, value in config.items():
        if isinstance(value, dict) and any("remote" in str(v).lower() for v in value.values()):
            use_Ray = True

            break

    env_name = f"env_{job_id}" if job_id else "dynamic_pipeline"
    if use_Ray:

        env = RemoteEnvironment(env_name)
    else:
        env = LocalEnvironment(env_name)
    env.set_memory(config={"collection_name":f"{env_name}_memory"})
    # 如果没有提供operators配置，使用默认配置
    if not operators:
        operators = {
            "source": {"type": "FileSource", "params": {}},
            "steps": [
                {"name": "map", "type": "SimpleRetriever", "params": {}},
                {"name": "map", "type": "QAPromptor", "params": {}},
                {"name": "map", "type": "OpenAIGenerator", "params": {}}
            ],
            "sink": {"type": "FileSink", "params": {}}
        }



    # 动态导入和创建operators
    # 1. 创建source
    source_type = operators["source"]["type"]
    source_class = globals()[source_type]
    current_stream = env.from_source(source_class,config['source'])

    # 2. 创建中间处理步骤
    for step in operators["steps"]:
        step_type = step["type"]
        step_name = step["name"]
        step_class = globals()[step_type]
        # 取type字段最后一个大写字母开始的单词
        def extract_last_upper_word(s: str) -> str:
            # 找出所有以大写字母开头的“单词”
            matches = list(re.finditer(r'[A-Z][a-z0-9]*', s))
            if matches:
                return matches[-1].group().lower()
            return ''
        config_field = extract_last_upper_word(step_type)
        # 根据步骤名称调用相应的方法
        if hasattr(current_stream, step_name):
            method = getattr(current_stream, step_name)
            current_stream = method(step_class,config[config_field])
        else:
            logging.warning(f"Stream does not have method {step_name}, skipping this step")

    # 3. 创建sink
    sink_type = operators["sink"]["type"]
    sink_class = globals()[sink_type]
    sink_stream = current_stream.sink(sink_class,config['sink'])

    # 提交管道到 SAGE 运行时
    try:
        env.submit(name = f"env_{job_id}" if job_id else "dynamic_pipeline")
        # env.run_streaming()
    except Exception as e:
        logging.error(f"Failed to submit pipeline: {e}")
        raise  Exception(f"Pipeline submission failed: {e}")
    return env
   