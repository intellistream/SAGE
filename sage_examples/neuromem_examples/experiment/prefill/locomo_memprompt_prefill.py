# file sage_examples/neuromem_examples/experiment/prefill/locomo_memprompt_prefill.py
# python -m sage_examples.neuromem_examples.experiment.prefill.locomo_memprompt_prefill
# export HF_ENDPOINT=https://hf-mirror.com
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from data.neuromem_datasets.locomo_dataloader import LocomoDataLoader

from sage_memory.api import get_memory

from sage_utils.config_loader import load_config

# ==== 记忆实体创建 memprompt(VDB) ====
config = load_config("config_locomo_memprompt.yaml").get("memory")
memprompt_collection = get_memory(config=config.get("memprompt_collection"))


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
    
# print(all_session_qa[0][0])
for i in range(3):
    # print(all_session_qa[0][i].get("q"))
    # print(all_session_qa[0][i])
    memprompt_collection.insert(
        all_session_qa[0][i].get("q"),
        metadata={"raw_qa": all_session_qa[0][i]}
    )
    
memprompt_collection.create_index(index_name="vdb_index")

print(memprompt_collection.retrieve("LGBTQ", index_name="vdb_index", topk=1))


# memprompt_collection.insert("")
# # 遍历问题
# for session_idx, qa_list in enumerate(all_session_qa):
#     print(f"Session {session_idx} 的 QA:")
#     for qa in qa_list:
#         print(f"Q: {qa['q']}")
#         print(f"A: {qa['a']}")
#     print('-' * 30)


# loader = LocomoDataLoader()
# sid = loader.get_sample_id()[0]   # 先获取第一个 sample_id
# sessions = loader.iter_session(sid)   # 再用 sid
# first_session = sessions[0]
# first_two = first_session['session_content'][:2]
# for entry in first_two:
#     print(f"speaker: {entry.get('speaker')}, text: {entry.get('text')}, session_type: {entry.get('session_type')}")




            # col.add_metadata_field("owner")
            # col.add_metadata_field("show_type")
            # texts = [
            #     ("hello world", {"owner": "ruicheng", "show_type": "text"}),
            #     ("你好，世界", {"owner": "Jun", "show_type": "text"}),
            #     ("こんにちは、世界", {"owner": "Lei", "show_type": "img"}),
            # ]
            # for text, metadata in texts:
            #     col.insert(text, metadata)
            # col.create_index(index_name="vdb_index")
            
# # ==== 使用示例 ====
# if __name__ == "__main__":
#     loader = LocomoDataLoader()

#     print("所有 sample_id:")
#     print(loader.get_sample_id())

#     sid = loader.get_sample_id()[0]
    
#     print(f"\nsample_id={sid} 下的两个 speaker:")
#     print(loader.get_speaker(sid))
    
#     print(f"\n遍历 sample_id={sid} 下所有 QA:")
#     for qa in loader.iter_qa(sid):
#         print(qa)

#     print(f"\n遍历 sample_id={sid} 下所有 session:")
#     for session in loader.iter_session(sid):
#         print(f"Session {session['session_id']} | 时间: {session['date_time']} | 条数: {len(session['session_content'])}")
#         # 打印前2条session_content做示例
#         for i, entry in enumerate(session['session_content'][:2]):
#             print(f"  [{i}] speaker: {entry.get('speaker')}, text: {entry.get('text')}, session_type: {entry.get('session_type')}")
#         if len(session['session_content']) > 2:
#             print("  ...")