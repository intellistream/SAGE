"""记忆检索模块 - 负责从记忆服务中检索对话历史"""

from sage.common.core import MapFunction


class MemoryRetrieval(MapFunction):
    """从记忆服务检索对话历史

    职责：
    1. 初始化时明确服务后端和数据解析器
    2. 使用解析器提取查询参数
    3. 调用配置的记忆服务检索对话
    4. 返回检索到的原始数据（由 post_retrieval 处理格式化）
    """

    def __init__(self, config=None):
        """初始化 MemoryRetrieval

        Args:
            config: RuntimeConfig 对象

        功能：
        1. 明确服务后端（从 config 读取 register_memory_service）
        2. 初始化数据解析器（用于提取查询参数）
        """
        super().__init__()
        self.config = config

        # 1. 明确服务后端
        self.service_name = config.get("services.register_memory_service", "short_term_memory")
        print(f"[DEBUG] MemoryRetrieval.__init__: self.service_name = {self.service_name}")

        # 2. 检索参数（从服务配置读取）
        service_cfg = f"services.{self.service_name}"
        self.retrieval_top_k = config.get(f"{service_cfg}.retrieval_top_k", 10)
        self.num_start_nodes = config.get(f"{service_cfg}.num_start_nodes", 3)
        self.max_depth = config.get(f"{service_cfg}.max_depth", 2)

    def execute(self, data):
        """执行记忆检索

        Args:
            data: 纯数据字典（已由 PipelineServiceSource 解包）
                可能包含的字段：
                - question: 查询问题
                - query_embedding: 查询向量（可选，由 PreRetrieval 生成）
                - metadata: 元数据（可选）
                - retrieval_hints: 检索策略提示（可选，由 PreRetrieval route action 生成）
                    - strategies: 检索策略列表
                    - params: 传递给服务的检索参数
                    - route_strategy: 使用的路由策略

        Returns:
            在原始数据基础上添加 "memory_data" 字段，包含检索到的原始记忆数据
        """
        query = data["question"]
        vector = data.get("query_embedding", None)
        base_metadata = data.get("metadata") or {}

        # 合并检索参数到 metadata
        metadata = {
            **base_metadata,
            "num_start_nodes": self.num_start_nodes,
            "max_depth": self.max_depth,
        }

        # 提取 retrieval_hints（如有，由 PreRetrieval route action 生成）
        # hints 包含检索策略建议，服务可根据 hints 调整检索行为
        hints = data.get("retrieval_hints", None)

        # 调用记忆服务检索对话（统一接口：传入 query 参数）
        # 增加超时时间以适应复杂图检索场景
        result = self.call_service(
            self.service_name,
            query=query,
            vector=vector,
            metadata=metadata,
            hints=hints,  # 传递给服务，让服务决定如何使用
            top_k=self.retrieval_top_k,
            method="retrieve",
            timeout=60.0,
        )

        data["memory_data"] = result

        return data
