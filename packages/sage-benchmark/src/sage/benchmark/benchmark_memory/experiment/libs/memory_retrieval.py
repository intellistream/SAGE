"""记忆检索模块 - 负责从记忆服务中检索对话历史"""

from sage.benchmark.benchmark_memory.experiment.utils.data_parser import DataParser
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

        # 2. 初始化数据解析器（用于提取查询参数）
        self.parser = DataParser(config)

    def execute(self, data):
        """执行记忆检索

        Args:
            data: 纯数据字典（已由 PipelineServiceSource 解包）

        Returns:
            在原始数据基础上添加 "memory_data" 字段，包含检索到的原始记忆数据
        """
        if not data:
            return None

        # 使用数据解析器提取查询参数
        # 查询结构由 memory_insert_adapter 决定（与插入时的结构一致）
        query = self.parser.extract(data)

        # 调用记忆服务检索对话（统一接口：传入 query 参数）
        memory_data = self.call_service(self.service_name, query, method="retrieve", timeout=10.0)

        # 检查返回结果
        if memory_data is None:
            print("⚠️  记忆检索失败：服务未返回数据")
            data["memory_data"] = []
            return data

        # 将检索到的原始数据添加到 data 中
        # 注意：不在这里做格式化，由 post_retrieval 处理
        data["memory_data"] = memory_data

        return data
