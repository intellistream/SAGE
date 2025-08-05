# file sage_examples/neuromem_examples/experiment/prefill/locomo_memprompt_prefill.py
# python -m sage_examples.neuromem_examples.experiment.prefill.locomo_memprompt_prefill

# 国内镜像能够加快 Hugging Face 的模型下载速度
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"


from sage.utils.config_loader import load_config

from sage.core.api.local_environment import LocalEnvironment


# from tqdm import tqdm
# from sage.service.memory..api import get_memory, get_manager
# from data.neuromem_datasets.locomo_dataloader import LocomoDataLoader

from app.memory_app.experiment.function.locomo import LocomoSource, LocomoTerminalSink

def pipeline_run():
    env = LocalEnvironment()
    config = None
    env.set_memory(config=config)
    query_stream = env.from_source(LocomoSource, config)
    query_stream.sink(LocomoTerminalSink, config)
    env.submit()
    env.run_streaming()  # 启动管道
    # manager = env.get_manager()
    # manager.store_collection()  # 保存管道状态
    # env.stop()

if __name__ == '__main__':
    # 加载配置并初始化日志
    # config = load_config('config_bm25s.yaml')
    # 初始化内存并运行管道
    pipeline_run()






# from sage.lib.io.source import FileSource
# from sage.lib.rag.generator import OpenAIGenerator
# from sage.lib.rag.promptor import QAPromptor
# from sage.lib.rag.retriever import BM25sRetriever



# def pipeline_run():
#     """创建并运行数据处理管道"""
#     env = LocalEnvironment()
#     env.set_memory(config=None)
#     # 构建数据处理流程
#     query_stream = env.from_source(FileSource, config["source"])
#     query_and_chunks_stream = query_stream.map(BM25sRetriever, config["retriever"])
#     prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
#     response_stream = prompt_stream.map(OpenAIGenerator, config["generator"]["local"])
#     response_stream.sink(TerminalSink, config["sink"])
#     # 提交管道并运行
#     env.submit()
#       # 启动管道

#     # time.sleep(100)  # 等待管道运行

# if __name__ == '__main__':
#     # 加载配置并初始化日志
#     config = load_config('config_bm25s.yaml')
#     # 初始化内存并运行管道
#     pipeline_run()





# # ==== 记忆实体创建 memprompt(VDB) ====
# config = load_config("config_locomo_memprompt.yaml").get("memory")
# memprompt_collection = get_memory(config=config.get("memprompt_collection_session1"))

# # ==== 记忆实体填充 memprompt(VDB) ====
# memprompt_collection.add_metadata_field("a")
# from data.neuromem_datasets.locomo_dataloader import LocomoDataLoader
# loader = LocomoDataLoader()

# 预处理session数据的格式，使其转变为memprompt格式
#   - 索引的组成主要是embedding(q)
#   - 返回的数据是{'text': xxx, 'metadata': {'a': "xxx"}}

# sid = loader.get_sample_id()[0]
# all_session_qa = [] 
# num = 0
# for session in loader.iter_session(sid):
#     qa_list = []
#     session_content = session['session_content']
#     for i in range(0, len(session_content) - 1, 2):
#         q = session_content[i]['text']
#         a = session_content[i + 1]['text']
#         qa_list.append({'q': q, 'a': a})
#         print(q)
#     all_session_qa.append(qa_list)  

# for session_qa in tqdm(all_session_qa, desc="Session Progress"):
#     for qa in tqdm(session_qa, desc="QA Progress", leave=False):
#         memprompt_collection.insert(
#             qa["q"],
#             metadata={"a": qa["a"]}
#         )

# memprompt_collection.create_index(index_name="global_index")

# manager = get_manager()
# manager.store_collection()


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



