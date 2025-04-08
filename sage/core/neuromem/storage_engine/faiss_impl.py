import faiss
import torch
import os
import json
import threading
import numpy as np
from typing import Dict, Optional, List, Union
from sage.core.neuromem.storage_engine.base_physical_memory import BaseVectorPhysicalMemory, TextStorageLayer

class FaissMemory(BaseVectorPhysicalMemory):
    """Enhanced Faiss implementation with offline/online data support."""
    
    def __init__(
        self,
        vector_dim: int,
        top_k: int,
        retrieval_threshold: float,
        physical_data_path: str,
        faiss_index: str = "FlatIP",
        faiss_index_config: Optional[dict] = None,
        metric_type: int = faiss.METRIC_INNER_PRODUCT,
        load_offline_index: bool = False,
        offline_index_path: Optional[str] = None,
        offline_text_data_path: Optional[str] = None
        ):
        super().__init__()

        self.vector_dim = vector_dim
        self.top_k = top_k
        self.metric_type = metric_type

        self.faiss_index = faiss_index
        self.faiss_index_config = faiss_index_config
        self.retrieval_threshold = retrieval_threshold

        self.index = faiss.IndexIDMap2(
            self._create_base_index(
                self.faiss_index,
                self.vector_dim,
                self.faiss_index_config,
                self.metric_type
            )
        )
        
        # Initialize offline index if requested
        self.offline_index = None
        self.offline_text_data = {}
        if load_offline_index:
            self._load_offline_data(offline_index_path, offline_text_data_path)

        # Initialize text storage
        self.text_storage = TextStorageLayer(physical_data_path)

        self.logger.info("FaissMemory(Physical Memory) initialized for session storage.")

    def _load_offline_data(self, index_path: Optional[str], text_data_path: Optional[str]):
        """Load offline index and corresponding text data"""
        if not index_path or not text_data_path:
            self.logger.warning("Offline index or text data path not provided")
            return
            
        try:
            # Load offline index
            if os.path.exists(index_path):
                self.offline_index = faiss.read_index(index_path)
                self.logger.info(f"Loaded offline index from {index_path}")
            else:
                self.logger.warning(f"Offline index file not found at {index_path}")
                
            # Load offline text data
            if os.path.exists(text_data_path):
                with open(text_data_path, 'r') as f:
                    self.offline_text_data = json.load(f)
                self.logger.info(f"Loaded offline text data from {text_data_path}")
            else:
                self.logger.warning(f"Offline text data file not found at {text_data_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to load offline data: {str(e)}")
            raise RuntimeError(f"Failed to load offline data: {str(e)}")

    def _create_base_index(
        self,
        index_type,
        vector_dim,
        faiss_index_config, 
        metric_type
    ):
        """
        Create a basic index
        """
        if faiss_index_config is None:
            self.logger.info(f"No faiss_index_config provided for {index_type}, using default parameters.")
            faiss_index_config = {}  

        if index_type == "FlatIP":
            return faiss.IndexFlatIP(vector_dim)
        elif index_type == "FlatL2":
            return faiss.IndexFlatL2(vector_dim)
        elif index_type == "IVFFlat":
            quantizer = faiss.IndexFlatL2(vector_dim)  
            nlist = faiss_index_config.get("nlist", 100)  
            self.logger.info(f"Creating IVFFlat index with nlist={nlist}")
            return faiss.IndexIVFFlat(quantizer, vector_dim, nlist, metric_type)
        elif index_type == "HNSW":
            M = faiss_index_config.get("M", 16)  
            ef_construction = faiss_index_config.get("ef_construction", 200)  
            self.logger.info(
                f"Creating HNSW index with M={M}, ef_construction={ef_construction}"
            )
            index = faiss.IndexHNSWFlat(vector_dim, M, metric_type)
            index.hnsw.efConstruction = ef_construction
            return index
        else:
            raise ValueError(f"Unsupported index type: {index_type}")


    def _search_index(self, index, embedding_np, k, is_offline=False):
        """Helper function to search an index"""
        try:
            distances, indices = index.search(embedding_np, k)
            results = []

            for i in range(len(indices[0])):
                text_id = indices[0][i]
                score = distances[0][i]
                # print(score)
                # if text_id < 0 or score < self.retrieval_threshold:
                #     continue
                    
                if is_offline:
                    text = self.offline_text_data.get(str(text_id))
                else:
                    text = self.text_storage.get_text(int(text_id))
                    
                if text is not None:
                    results.append((text, float(score)))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed in {'offline' if is_offline else 'online'} index: {str(e)}")
            return []

    def store(self, embedding=None, raw_data=None):
        """
        Store vector embedding and raw text data
        """
        if raw_data is None:
            raise ValueError("Raw data must be provided for Storage.")
        elif embedding is None:
            raise ValueError("Embedding must be provided for Storage.")

        # Convert embedding to numpy array
        embedding_np = embedding.cpu().numpy()
        
        # Reshape to 2D array if needed
        if len(embedding_np.shape) == 1:
            embedding_np = embedding_np.reshape(1, -1)

        # Store text data and get ID
        raw_id = self.text_storage.add_text(raw_data)
        
        try:
            # Add to Faiss index
            self.index.add_with_ids(embedding_np, np.array([raw_id], dtype=np.int64)) # type: ignore 
            
            self.logger.info(f"Storage successful, Raw ID: {raw_id}")
            return raw_id
        except Exception as e:
            if raw_id is not None:
                self.text_storage.delete_text(raw_id)
            self.logger.error(f"Storage failed: {str(e)}")
            raise RuntimeError(f"Storage failed: {str(e)}")

    def retrieve(self, embedding=None, k=None):
        """
        Retrieve similar content from both online and offline indices in parallel.
        If offline index is not loaded, only search online index.
        """
        if embedding is None:
            raise ValueError("Embedding must be provided for Retrieve.")

        # Set number of results to return
        k = k if k is not None else self.top_k

        # Convert embedding to numpy array
        embedding_np = embedding.cpu().numpy()
        
        # Reshape to 2D array if needed
        if len(embedding_np.shape) == 1:
            embedding_np = embedding_np.reshape(1, -1)

        # Prepare threads for parallel search
        online_results = []
        offline_results = []
        
        def online_search():
            nonlocal online_results
            online_results = self._search_index(self.index, embedding_np, k, False)
   
        def offline_search():
            nonlocal offline_results
            offline_results = self._search_index(self.offline_index, embedding_np, k, True)

        # Create and start online search thread (always needed)
        online_thread = threading.Thread(target=online_search)
        online_thread.start()
        
        # Only create offline thread if offline index exists
        offline_thread = None
        if self.offline_index is not None:
            offline_thread = threading.Thread(target=offline_search)
            offline_thread.start()

        # Wait for online thread to complete
        online_thread.join()
        
        # Wait for offline thread if it was started
        if offline_thread is not None:
            offline_thread.join()

        # Combine and sort results by score
        combined_results = online_results + offline_results
        combined_results.sort(key=lambda x: x[1], reverse=True)
        
        # Return only the text content (without scores)
        final_results = [result[0] for result in combined_results[:k]]
        
        self.logger.info(f"Successfully retrieved {len(final_results)} results "
                        f"({len(online_results)} online, {len(offline_results)} offline)")
        
        # Log number of duplicates found
        duplicate_count = len(final_results) - len(set(final_results))
        if duplicate_count > 0:
            self.logger.info(f"Found {duplicate_count} duplicate results in the combined set")

        return list(dict.fromkeys(final_results))

    def delete(self):
        pass 

    def clean(self):
        self.text_storage.delete_all_data()



if __name__ == "__main__":

    def online_test():

        import json
        # from src.utils.file_path import RAW_FILE_LTM
        from pathlib import Path

        current_dir = Path(__file__).parent
        config_path = current_dir.parent / "default_memroy" / "default_memory_config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
            config = config.get("neuromem").get("FaissMemory_LTM")
        test = FaissMemory(vector_dim = config.get("ltm_vector_dim")
                , top_k = config.get("ltm_top_k")
                , retrieval_threshold = config.get("ltm_retrieval_threshold")
                , physical_data_path=config.get("ltm_physical_data_path")
                , faiss_index="FlatIP"
                )

        # Create tensors and store the sentences
        id1 = torch.FloatTensor(128)
        test.store(id1, "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. It was named after the engineer Gustave Eiffel.")

        id2 = torch.FloatTensor(128)
        test.store(id2, "Python is a high-level, interpreted programming language known for its simplicity and versatility.")

        id3 = torch.FloatTensor(128)
        test.store(id3, "The Great Wall of China is a series of fortifications built to protect China from northern invasions.")

        id4 = torch.FloatTensor(128)
        test.store(id4, "Albert Einstein was a theoretical physicist best known for developing the theory of relativity.")

        id5 = torch.FloatTensor(128)
        test.store(id5, "The Pacific Ocean is the largest and deepest of Earth's oceanic divisions.")

        id6 = torch.FloatTensor(128)
        test.store(id6, "Barack Obama served as the 44th president of the United States from 2009 to 2017.")

        id7 = torch.FloatTensor(128)
        test.store(id7, "The Mona Lisa is a famous portrait painted by Leonardo da Vinci during the Renaissance.")

        id8 = torch.FloatTensor(128)
        test.store(id8, "Mount Everest, located in the Himalayas, is the tallest mountain in the world.")

        id9 = torch.FloatTensor(128)
        test.store(id9, "The Roman Colosseum is an ancient amphitheater in Rome, Italy, used for gladiatorial contests and public spectacles.")

        id10 = torch.FloatTensor(128)
        test.store(id10, "Renewable energy sources include solar power, wind energy, and hydroelectric energy, which are sustainable alternatives to fossil fuels.")
        
        # Search for the first tensor
        print(test.retrieve(id1))

        test.clean()


    """
    create offline_index firstly!!!

    def test():    
        import numpy as np
        import faiss
        import torch
        import json

        # 1. 准备原始数据
        data = [
            {"id": 0, "title": "test1", "contents": "苹果"},
            {"id": 1, "title": "test2", "contents": "梨子"},
            {"id": 2, "title": "test3", "contents": "香蕉"},
            {"id": 3, "title": "test4", "contents": "西瓜"},
            {"id": 4, "title": "test5", "contents": "桃子"}
        ]

        # 2. 创建模拟的embedding向量 (维度=128)
        torch.manual_seed(42)
        embeddings = torch.randn(5, 128)  # 5个样本，每个768维
        embeddings = embeddings / torch.norm(embeddings, dim=1, keepdim=True)  # 归一化
        embeddings_np = embeddings.numpy()

        # 3. 创建FAISS索引 (使用内积相似度)
        dim = 128
        base_index = faiss.IndexFlatIP(dim)  # 基础索引
        index = faiss.IndexIDMap2(base_index)  # 包装基础索引以支持ID映射

        # 添加向量到索引 (使用原始id作为索引id)
        ids = np.array([item["id"] for item in data], dtype=np.int64)
        index.add_with_ids(embeddings_np, ids)

        # 4. 保存FAISS索引
        faiss.write_index(index, "toy_fruit.index")
        print("FAISS索引已保存到 toy_fruit.index")

        # 5. 准备并保存文本数据 (格式: {id: text})
        text_data = {item["id"]: item["contents"] for item in data}
        with open("toy_fruit_text.json", "w", encoding="utf-8") as f:
            json.dump(text_data, f, ensure_ascii=False, indent=2)
        print("文本数据已保存到 toy_fruit_text.json")

        # 6. 验证索引是否正确
        query = embeddings_np[0:1]  # 查询第一个水果(苹果)的embedding
        k = 3  # 返回top3结果
        D, I = index.search(query, k)  # D是距离/相似度分数，I是索引id

        print("\n测试查询结果:")
        print(f"查询文本: '{data[0]['contents']}'")
        print(f"Top {k} 相似结果:")
        for i in range(k):
            idx = I[0][i]
            print(f"{i+1}. ID:{idx} 文本:'{text_data[idx]}' 相似度:{D[0][i]:.4f}")

    if __name__ == "__main__":
        test()
    """    
    
    def offline_test():
        # Configuration for offline testing
        config = {
            "vector_dim": 128,
            "top_k": 3,
            "retrieval_threshold": 0.5,
            "physical_data_path": "./data/raw_docs/raw_dcm",
            "faiss_index": "FlatIP",
            "load_offline_index": True,
            "offline_index_path": "toy_fruit.index",  # Path to the pre-built offline index
            "offline_text_data_path": "toy_fruit_text.json"  # Path to the offline text data
        }

        # Initialize FaissMemory with offline data
        test = FaissMemory(
            vector_dim=config["vector_dim"],
            top_k=config["top_k"],
            retrieval_threshold=config["retrieval_threshold"],
            physical_data_path=config["physical_data_path"],
            faiss_index=config["faiss_index"],
            load_offline_index=config["load_offline_index"],
            offline_index_path=config["offline_index_path"],
            offline_text_data_path=config["offline_text_data_path"]
        )

        # Create a test query vector (same dimension as offline data)
        torch.manual_seed(42)  # For reproducibility
        embeddings = torch.randn(5, 128)  # 5 samples, each 768-dim
        embeddings = embeddings / torch.norm(embeddings, dim=1, keepdim=True)  # normalize
        query_vector = embeddings[2]  # Using the banana vector as query

        # First retrieval - should only find offline fruits
        print("\nInitial retrieval (offline only):")
        results = test.retrieve(query_vector, 3)
        print(f"Retrieved {len(results)} items:")
        for i, res in enumerate(results):
            print(f"{i+1}. {res}")

        # Store some new fruits with special embeddings
        # 1. "哈密瓜" with all zeros vector (should have low similarity with everything)
        hamimelon_vec = torch.zeros(128)
        hamimelon_id = test.store(hamimelon_vec, "哈密瓜")
        print(f"\nStored '哈密瓜' with ID {hamimelon_id} (all zeros vector)")

        # 2. "西红柿" with all ones vector (normalized)
        tomato_vec = torch.ones(128)
        tomato_vec = tomato_vec / torch.norm(tomato_vec)  # normalize
        tomato_id = test.store(tomato_vec, "西红柿")
        print(f"Stored '西红柿' with ID {tomato_id} (normalized ones vector)")

        # Second retrieval - should combine offline and online fruits
        print("\nCombined retrieval (offline + online):")
        results = test.retrieve(query_vector, 3)  # Get more results to see both types
        print(f"Retrieved {len(results)} items:")
        for i, res in enumerate(results):
            print(f"{i+1}. {res}")

        # Test query with the tomato vector - should find "西红柿" first
        print("\nQuery with tomato vector:")
        results = test.retrieve(tomato_vec, 3)
        print(f"Retrieved {len(results)} items:")
        for i, res in enumerate(results):
            print(f"{i+1}. {res}")

        # Clean up
        test.clean()
    
    # online_test()

    offline_test()
    # python -m sage.core.neuromem.storage_engine.faiss_impl
