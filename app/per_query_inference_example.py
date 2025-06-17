import time
import sage
import logging
import yaml
from sage.core.neuromem.memory_manager import MemoryManager
from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder


logging.basicConfig(level=logging.DEBUG)
def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

config = load_config('./app/config.yaml')
logging.basicConfig(level=logging.ERROR)

manager = sage.memory.init_default_manager()
config["memory_manager"]=manager
memory = sage.memory.create_table("long_term_memory", manager=manager)

while(True):
    user_input = input("\n>>> ").strip()
    if user_input.lower() == "exit":
        logging.info("Exiting SAGE Interactive Console")
        print("Goodbye!")
        break
    time1 = time.time()
    sage.query.run_query(user_input,config)
    time2 = time.time()
    logging.info(f"Query executed in {time2 - time1:.4f} seconds")