# pyright: reportGeneralTypeIssues=false
# pyright: reportMissingImports=false
# pyright: reportMissingTypeStubs=false


import os, sys, json, time, asyncio
from datetime import datetime
from dotenv import load_dotenv
from sage.api.model import apply_generator_model, apply_embedding_model
from sage_memory.memory_manager import MemoryManager

load_dotenv()

# ---------- Embedder ----------
class SimpleEmbedder:
    def __init__(self):
        self.model = apply_embedding_model(
            "openai", model="BAAI/bge-m3",
            base_url="https://api.siliconflow.cn/v1",
            api_key=os.environ.get("SILICONCLOUD_API_KEY")
        )

    def encode(self, text: str):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.model._embed(text))

# ---------- Init memory manager ----------
manager = MemoryManager()

embedder = SimpleEmbedder()
exp_table = manager.create_collection("experiment_table", backend_type="VDB", embedding_model=embedder, dim=1024)
exp_history = manager.create_collection("experiment_table_history", backend_type="KV")

for field in ["user_id", "timestamp", "meal_type", "calorie", "activity_type", "duration_min"]:
    exp_table.add_metadata_field(field)
exp_history.add_metadata_field("timestamp")

# ---------- Load dataset ----------
def parse_timestamp(ts): return datetime.fromisoformat(ts).timestamp()

file_configs = [
    ("food.json", "caption"),
    ("sport.json", "text"),
    ("health.json", "text")
]
base_path = "/home/zrc/develop_item/SAGE/sage/core/sage_memory/operator_test/structure_mem_demo"

for fname, text_field in file_configs:
    with open(os.path.join(base_path, fname), 'r', encoding='utf-8') as f:
        items = json.load(f)
        if isinstance(items, dict): items = [items]
        for item in items:
            text = item[text_field]
            metadata = {k: v for k, v in item.items() if k != text_field}
            if 'metadata' in metadata:
                metadata.update(metadata.pop('metadata'))
            if 'timestamp' in metadata:
                metadata['timestamp'] = parse_timestamp(metadata['timestamp'])
            exp_table.insert(raw_text=text, metadata=metadata)

exp_table.create_index(index_name="user_index", user_id="u001")  # type: ignore

# ---------- Chat loop ----------

def should_create_index(user_input, current_index_names) -> bool:
    return "user_index" not in current_index_names

def get_index_filter(user_input) -> dict:
    return {"user_id": "u001"}

def should_insert_history(user_input, model_response) -> bool:
    return bool(model_response.strip())

def format_history_insert(user_input, model_response) -> str:
    return f"{user_input}\n{model_response}"

def history_to_messages(items):
    items = sorted(items or [], key=lambda x: x.get("metadata", {}).get("timestamp", 0))
    messages = []
    for item in items:
        parts = item.get("text", "").split("\n", 1)
        if len(parts) == 2:
            messages += [{"role": "user", "content": parts[0]}, {"role": "assistant", "content": parts[1]}]
        else:
            messages.append({"role": "user", "content": item.get("text", "")})
    return messages

model = apply_generator_model(
    "openai", model_name="qwen-max-2025-01-25",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.environ.get("OPENAI_API_KEY")
)

try:
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break

        current_ts = int(time.time())

        # Get the list of existing indices
        existing_indices = exp_table.list_indices() if hasattr(exp_table, "list_indices") else ["user_index"]  # type: ignore

        # Determine whether a new index needs to be created
        if should_create_index(user_input, existing_indices):
            filter_cond = get_index_filter(user_input)
            print(f"Creating index with filter: {filter_cond}")
            exp_table.create_index(index_name="user_index", **filter_cond)  # type: ignore

        # Perform retrieval
        context_items = exp_table.retrieve(user_input, index_name="user_index", with_metadata=True)  # type: ignore

        # Build context snippet
        context_snippet = "\n".join([
            f"{item.get('text', '')} | metadata: {json.dumps(item.get('metadata', {}), ensure_ascii=False)}"
            for item in context_items
        ])

        history_raw = exp_history.retrieve(with_metadata=True)
        history_msgs = history_to_messages(history_raw)

        prompt = [{"role": "system", "content": f"Here are the relevant user records:\n{context_snippet}"}]
        prompt += history_msgs + [{"role": "user", "content": user_input}]
        response = model.generate(prompt)

        print("Assistant:", response)

        # Decide whether to insert into history
        if should_insert_history(user_input, response):
            insert_text = format_history_insert(user_input, response)
            exp_history.insert(insert_text, metadata={"timestamp": current_ts})

            
except KeyboardInterrupt:
    print("\n聊天结束")
    sys.exit(0)
