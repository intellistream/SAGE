import json

from sage_plugins.longrefiner_fn.longrefiner.refiner import LongRefiner

# Initialize
query_analysis_module_lora_path = "jinjiajie/Query-Analysis-Qwen2.5-3B-Instruct"
doc_structuring_module_lora_path = "jinjiajie/Doc-Structuring-Qwen2.5-3B-Instruct"
selection_module_lora_path = "jinjiajie/Global-Selection-Qwen2.5-3B-Instruct"

refiner = LongRefiner(
    base_model_path="Qwen/Qwen2.5-3B-Instruct",
    query_analysis_module_lora_path=query_analysis_module_lora_path,
    doc_structuring_module_lora_path=doc_structuring_module_lora_path,
    global_selection_module_lora_path=selection_module_lora_path,
    score_model_name="bge-reranker-v2-m3",
    score_model_path="BAAI/bge-reranker-v2-m3",
    max_model_len=25000,
)

# Load sample data
with open("assets/sample_data.json", "r") as f:
    data = json.load(f)
question = list(data.keys())[0]
document_list = list(data.values())[0]

# Process documents
refined_result = refiner.run(question, document_list, budget=2048)
print(refined_result)