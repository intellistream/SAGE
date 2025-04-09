from sage.api.memory.memory_api import create_table, connect, retrieve_func, write_func, init_default_manager, get_default_manager
import logging

def configure_logging(level=logging.INFO, log_file=None):
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file)) # type: ignore 

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

if __name__ == "__main__":

    configure_logging(level=logging.INFO)

    manager_test = init_default_manager()
    manager = get_default_manager()

    stm = create_table("short_term_memory", manager)
    ltm = create_table("long_term_memory", manager)
    dcm = create_table("dynamic_contextual_memory", manager)

    print("=" * 30)

    # STM-TEST
    stm.store("This is STM data")
    print("STM retrieval test(store): This is STM data")
    stm_retrieval_results = str(stm.retrieve())
    print("STM retrieval test:(retrieve): " + stm_retrieval_results)
    if stm_retrieval_results == "['This is STM data']":
        print("\033[92mSTM retrieval test pass!\033[0m")
    else:
        print("\033[91mSTM retrieval test error!\033[0m")
    print("=" * 30)

    # LTM-TEST
    ltm.store("This is LTM data")
    print("LTM retrieval test(store): This is LTM data")
    ltm_retrieval_results = str(ltm.retrieve("This is LTM data"))
    print("LTM retrieval test(retrieve): " + ltm_retrieval_results)
    if ltm_retrieval_results == "['This is LTM data']":
        print("\033[92mLTM retrieval test pass!\033[0m")
    else:
        print("\033[91mLTM retrieval test error!\033[0m")
    print("=" * 30)

    # DCM-TEST
    dcm.store("This is DCM data")
    print("DCM retrieval test(store): This is DCM data")
    dcm_retrieval_results = str(dcm.retrieve("This is DCM data"))
    print("DCM retrieval test(retrieve): " + dcm_retrieval_results)
    if dcm_retrieval_results == "['This is DCM data', '苹果', '香蕉']":
        print("\033[92mDCM retrieval test pass!\033[0m")
    else:
        print("\033[91mDCM retrieval test error!\033[0m")
    print("=" * 30)

    # CONNECT-TEST
    composite = connect(manager, "short_term_memory", "long_term_memory")
    composite.store("This is Composite data.")
    composite_retrieval_results = str(composite.retrieve("This is composite data"))
    print("composite retrieval test: " + composite_retrieval_results)
    if composite_retrieval_results == "['This is Composite data.', 'This is LTM data']":
        print("\033[92mComposite retrieval test pass!\033[0m")
    else:
        print("\033[91mComposite retrieval test error!\033[0m")
    print("=" * 30)

    # CONNECT-FUNC-TEST
    import torch

    def test_write_func(raw_data, embedding, memory):
        embedding = torch.full((128,), 0.5)
        print("Custom store function called with embedding: [0.5,,,0.5] x 128")
        memory.store(raw_data, embedding)

    def test_retrieve_func(embedding, memory):
        embedding = torch.full((128,), 0.5)
        print("Custom retrieve function called with embedding: [0.5,,,0.5] x 128")
        return memory.retrieve(embedding, k=1)

    composite.store("This is a Storage & Retrieval Test.", write_func=test_write_func)

    composite_func_results = str(composite.retrieve("This is a Storage & Retrieval Test.", retrieve_func=test_retrieve_func))
    print("composite func results: " + composite_func_results)
    if composite_func_results == "['This is a Storage & Retrieval Test.']":
        print("\033[92mComposite func test pass!\033[0m")
    else:
        print("\033[91mComposite func test error!\033[0m")
    print("=" * 30)

    # CONNECT-FLUSH-TEST
    composite.flush_kv_to_vdb(stm, ltm)
    if len(stm.retrieve("test")) == 0 and len(ltm.retrieve("")) == 4:
        print("\033[92mComposite flush test pass!\033[0m")
    else:
        print("\033[91mComposite flush test error!\033[0m") 

    # MANAGER-TEST
    print(manager.list_collections())

    ltm.clean()
    dcm.clean()
      
