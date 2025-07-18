# file sage_examples/neuromem_examples/experiment/prefill/locomo_memprompt_prefill.py
# python -m sage_examples.neuromem_examples.experiment.prefill.locomo_memprompt_prefill
# export HF_ENDPOINT=https://hf-mirror.com
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from tqdm import tqdm
from sage_memory.api import get_memory, get_manager
from sage_utils.config_loader import load_config
from data.neuromem_datasets.locomo_dataloader import LocomoDataLoader

# ==== 记忆实体创建 memprompt(VDB) ====
config = load_config("config_locomo_memprompt.yaml").get("memory")
memprompt_collection = get_memory(config=config.get("memprompt_collection_session1"))

# ==== 记忆实体填充 memprompt(VDB) ====
memprompt_collection.add_metadata_field("raw_qa")

loader = LocomoDataLoader()
sid = loader.get_sample_id()[0]
all_session_qa = []  
for session in loader.iter_session(sid):
    qa_list = []
    session_content = session['session_content']
    for i in range(0, len(session_content) - 1, 2):
        q = session_content[i]['text']
        a = session_content[i + 1]['text']
        qa_list.append({'q': q, 'a': a})
    all_session_qa.append(qa_list)  
    
for session_qa in tqdm(all_session_qa, desc="Session Progress"):
    for qa in tqdm(session_qa, desc="QA Progress", leave=False):
        memprompt_collection.insert(
            qa["q"],
            metadata={"raw_qa": qa}
        )

memprompt_collection.create_index(index_name="global_index")

manager = get_manager()
manager.store_collection()


# print(memprompt_collection.retrieve("LGBTQ", index_name="global_index", topk=3, with_metadata=True))


# print(memprompt_collection.retrieve("LGBTQ", index_name="vdb_index", topk=1))
         
# # print(all_session_qa)
# for i in range(len(all_session_qa[0])):
#     memprompt_collection.insert(
#         all_session_qa[0][i].get("q"),
#         metadata={"raw_qa": all_session_qa[0][i]}
#     )
    
# memprompt_collection.create_index(index_name="vdb_index")

# print(memprompt_collection.retrieve("LGBTQ", index_name="vdb_index", topk=1))



# import logging

# from sage_core.api.env import LocalEnvironment
# from sage_common_funs.io.sink import TerminalSink
# from sage_common_funs.io.source import FileSource
# from sage_common_funs.rag.generator import OpenAIGenerator
# from sage_common_funs.rag.promptor import QAPromptor
# from sage_common_funs.rag.retriever import BM25sRetriever
# from sage_utils.config_loader import load_config
# from sage_utils.logging_utils import configure_logging


# def pipeline_run():
#     """创建并运行数据处理管道"""
#     env = LocalEnvironment()
#     env.set_memory(config=None)
#     # 构建数据处理流程
#     query_stream = env.from_source(FileSource, config["source"])
#     query_and_chunks_stream = query_stream.map(BM25sRetriever, config["retriever"])
#     prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
#     response_stream = prompt_stream.map(OpenAIGenerator, config["generator"])
#     response_stream.sink(TerminalSink, config["sink"])
#     # 提交管道并运行
#     env.submit()
#     env.run_streaming()  # 启动管道

#     # time.sleep(100)  # 等待管道运行

# if __name__ == '__main__':
#     # 加载配置并初始化日志
#     config = load_config('config_bm25s.yaml')
#     configure_logging(level=logging.INFO)
#     # 初始化内存并运行管道
#     pipeline_run()