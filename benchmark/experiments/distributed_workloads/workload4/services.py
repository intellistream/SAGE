"""
Workload 4 Service Implementations

所有 Service classes 放在独立模块中，避免 Ray 序列化问题。
"""

print("[services.py] Module imported successfully - verifying Service extraction")  # 验证

from sage.kernel.api.service.base_service import BaseService


class EmbeddingService(BaseService):
    """Embedding 服务包装器（延迟初始化避免序列化问题）"""

    def __init__(self, base_url: str, model: str, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = None  # 延迟初始化

    def __getstate__(self):
        """排除 httpx client（序列化时）"""
        state = self.__dict__.copy()
        state["_client"] = None
        return state

    def __setstate__(self, state):
        """恢复状态（反序列化时）"""
        self.__dict__.update(state)

    def _get_client(self):
        """延迟创建 httpx 客户端（避免 SSLContext pickle 问题）"""
        if self._client is None:
            import httpx

            self._client = httpx.Client(timeout=120.0)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量 embedding"""
        client = self._get_client()

        response = client.post(
            f"{self.base_url}/embeddings",
            json={"input": texts, "model": self.model},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]
        return embeddings

    def embed_single(self, text: str) -> list[float]:
        """单文本 embedding"""
        return self.embed([text])[0]


class FAISSVDBService(BaseService):
    """FAISS VDB 服务包装器（使用真实 FiQA 数据集）"""

    def __init__(self, vdb_name: str, dimension: int, index_dir: str, dataset_name: str, **kwargs):
        super().__init__(**kwargs)
        self.vdb_name = vdb_name
        self.dimension = dimension
        self.index_dir = index_dir
        self._dataset_name = dataset_name
        self._faiss_index = None
        self._documents: list[dict] = []
        self._initialized = False

    def __getstate__(self):
        """排除 FAISS 索引和文档（序列化时）"""
        state = self.__dict__.copy()
        state["_faiss_index"] = None
        state["_documents"] = []
        state["_initialized"] = False
        return state

    def __setstate__(self, state):
        """恢复状态（反序列化时），延迟加载索引"""
        self.__dict__.update(state)

    def _ensure_index(self):
        """延迟加载真实的 FiQA 数据集（vdb1 和 vdb2 共享）"""
        if self._initialized:
            return

        import json
        from pathlib import Path

        import faiss

        # 使用真实数据集路径
        index_path = Path(self.index_dir) / f"{self._dataset_name}_faiss.index"
        docs_path = Path(self.index_dir) / f"{self._dataset_name}_documents.jsonl"

        # 检查文件是否存在
        if not index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {index_path}\nPlease ensure FiQA dataset is prepared."
            )
        if not docs_path.exists():
            raise FileNotFoundError(
                f"Documents file not found: {docs_path}\nPlease ensure FiQA dataset is prepared."
            )

        # 加载真实的 FAISS 索引
        print(f"[{self.vdb_name}] Loading FiQA index from {index_path}")
        self._faiss_index = faiss.read_index(str(index_path))

        # 加载真实的文档数据
        print(f"[{self.vdb_name}] Loading FiQA documents from {docs_path}")
        self._documents = []
        with open(docs_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    doc = json.loads(line)
                    self._documents.append(doc)

        print(
            f"[{self.vdb_name}] Loaded FiQA dataset: "
            f"{self._faiss_index.ntotal} vectors, "
            f"{len(self._documents)} documents, "
            f"dimension={self._faiss_index.d}"
        )
        self._initialized = True

    def search(
        self, query_embedding: list[float], top_k: int = 20, filter_threshold: float = 0.0
    ) -> list[tuple[str, str, float]]:
        """搜索相似文档（FiQA 数据集）"""
        self._ensure_index()

        import numpy as np

        # 归一化查询向量（FiQA 使用归一化的 Inner Product）
        query_vec = np.array(query_embedding, dtype=np.float32)
        query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        query_vec = query_vec.reshape(1, -1)

        # FAISS 搜索
        scores, indices = self._faiss_index.search(query_vec, top_k)

        # 组装结果（使用 FiQA 文档格式）
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(self._documents) and score >= filter_threshold:
                doc = self._documents[idx]
                # FiQA 文档格式：{"id", "text", "title"}
                text = doc.get("text", "") or doc.get("content", "")
                results.append(
                    (
                        str(doc.get("id", idx)),
                        text,
                        float(score),
                    )
                )

        return results


class GraphMemoryService(BaseService):
    """图内存服务包装器"""

    def __init__(self, max_depth: int, max_nodes: int, **kwargs):
        super().__init__(**kwargs)
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self._graph = None  # 延迟初始化

    def __getstate__(self):
        """排除 networkx 图（序列化时）"""
        state = self.__dict__.copy()
        state["_graph"] = None
        return state

    def __setstate__(self, state):
        """恢复状态（反序列化时），延迟初始化图"""
        self.__dict__.update(state)

    def _ensure_graph(self):
        """确保图已创建"""
        if self._graph is None:
            import networkx as nx
            import numpy as np

            # 创建 Mock 知识图
            self._graph = nx.DiGraph()

            # 添加节点和边
            num_nodes = 200
            for i in range(num_nodes):
                node_id = f"node_{i}"
                self._graph.add_node(
                    node_id,
                    content=f"Memory node {i}: Knowledge about topic {i}",
                    embedding=np.random.randn(1024).tolist(),
                )

            # 添加边（随机连接）
            np.random.seed(42)
            for i in range(num_nodes):
                # 每个节点连接 2-5 个其他节点
                num_edges = np.random.randint(2, 6)
                targets = np.random.choice(num_nodes, num_edges, replace=False)
                for j in targets:
                    if i != j:
                        weight = np.random.uniform(0.5, 1.0)
                        self._graph.add_edge(f"node_{i}", f"node_{j}", weight=weight)

    def search(
        self,
        query_embedding: list[float],
        max_depth: int | None = None,
        max_nodes: int | None = None,
        beam_width: int = 10,
    ) -> list[dict[str, any]]:
        """
        BFS 图遍历搜索（标准接口）。

        Args:
            query_embedding: 查询向量
            max_depth: 最大遍历深度（None 使用服务默认值）
            max_nodes: 最大返回节点数（None 使用服务默认值）
            beam_width: Beam search 宽度

        Returns:
            List of dict with keys: node_id, content, depth, path, relevance_score, node_type
        """
        # 使用默认值如果未提供
        if max_depth is None:
            max_depth = self.max_depth
        if max_nodes is None:
            max_nodes = self.max_nodes

        self._ensure_graph()

        from collections import deque

        import numpy as np

        # 计算所有节点与 query 的相似度
        query_vec = np.array(query_embedding)
        query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-8)

        node_scores = {}
        for node_id in self._graph.nodes():
            node_embedding = self._graph.nodes[node_id]["embedding"]
            node_vec = np.array(node_embedding)
            node_vec = node_vec / (np.linalg.norm(node_vec) + 1e-8)
            score = float(query_vec @ node_vec)
            node_scores[node_id] = score

        # 选择起始节点（最相似的 beam_width 个）
        sorted_nodes = sorted(node_scores.items(), key=lambda x: -x[1])
        start_nodes = [node_id for node_id, _ in sorted_nodes[:beam_width]]

        # BFS 遍历
        visited = set()
        results = []
        queue = deque()

        for start_node in start_nodes:
            queue.append((start_node, 0, [start_node]))
            visited.add(start_node)

        while queue and len(results) < max_nodes:
            node_id, depth, path = queue.popleft()

            # 添加到结果（返回字典格式）
            content = self._graph.nodes[node_id]["content"]
            score = node_scores[node_id]
            results.append(
                {
                    "node_id": node_id,
                    "content": content,
                    "depth": depth,
                    "path": path,
                    "relevance_score": score,
                    "node_type": "memory",  # Mock 数据都是 memory 类型
                }
            )

            # 继续遍历
            if depth < max_depth:
                neighbors = list(self._graph.successors(node_id))
                # 按相似度排序邻居
                neighbor_scores = [(n, node_scores[n]) for n in neighbors if n not in visited]
                neighbor_scores.sort(key=lambda x: -x[1])

                for neighbor, _ in neighbor_scores[:beam_width]:
                    if neighbor not in visited and len(results) < max_nodes:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1, path + [neighbor]))

        return results


class LLMService(BaseService):
    """LLM 服务包装器"""

    def __init__(self, base_url: str, model: str, max_tokens: int, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self._client = None  # 延迟初始化

    def __getstate__(self):
        """排除 httpx client（序列化时）"""
        state = self.__dict__.copy()
        state["_client"] = None
        return state

    def __setstate__(self, state):
        """恢复状态（反序列化时）"""
        self.__dict__.update(state)

    def _get_client(self):
        """延迟创建 httpx 客户端"""
        if self._client is None:
            import httpx

            self._client = httpx.Client(timeout=180.0)
        return self._client

    def generate(self, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        """生成响应"""
        client = self._get_client()

        response = client.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": temperature,
            },
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def generate_batch(
        self, batch_messages: list[list[dict[str, str]]], temperature: float = 0.7
    ) -> list[str]:
        """批量生成响应"""
        # 简化版：顺序调用（真实场景应该用并发）
        results = []
        for messages in batch_messages:
            try:
                response = self.generate(messages, temperature)
                results.append(response)
            except Exception as e:
                results.append(f"[Error: {e}]")
        return results
