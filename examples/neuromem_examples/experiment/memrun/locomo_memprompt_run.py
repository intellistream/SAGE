# file sage_examples/neuromem_examples/experiment/memrun/locomo_memprompt_run.py
# python -m sage_examples.neuromem_examples.experiment.memrun.locomo_memprompt_run
# export HF_ENDPOINT=https://hf-mirror.com

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from tqdm import tqdm
from data.neuromem_datasets.locomo_dataloader import LocomoDataLoader

# manager = get_manager()
# config = load_config("config_locomo_memprompt.yaml").get("memory").get("memprompt_collection_session1")
# memprompt_collection = manager.connect_collection(name=config.get("collection_name"), embedding_model=apply_embedding_model(name=config["embedding_model_name"]))

# print(memprompt_collection.retrieve("LGBTQ", index_name="global_index", topk=3, with_metadata=True))

loader = LocomoDataLoader()
sid = loader.get_sample_id()[0]

qa_list = list(loader.iter_qa(sid))
for qa in tqdm(qa_list, desc="QA Progress"):
    print(qa.get("question"))
