"""记忆插入模块 - 负责将对话存储到记忆服务中"""

from sage.benchmark.benchmark_memory.experiment.utils.data_parser import DataParser
from sage.common.core import MapFunction


class MemoryInsert(MapFunction):
    """将对话插入记忆服务

    职责：
    1. 初始化时明确服务后端和数据解析器
    2. 接收对话数据并提取
    3. 调用配置的记忆服务存储对话
    4. 返回存储状态
    """

    def __init__(self, config=None):
        """初始化 MemoryInsert

        Args:
            config: RuntimeConfig 对象
        
        功能：
        1. 明确服务后端（从 config 读取 register_memory_service）
        2. 初始化数据解析器（通过 config 配置提取方法）
        """
        super().__init__()
        self.config = config
        
        # 1. 明确服务后端
        self.service_name = config.get("services.register_memory_service", "short_term_memory")
        
        # 2. 初始化数据解析器（支持通过 config 配置提取方法）
        self.parser = DataParser(config)

    def execute(self, data):
        """执行记忆插入

        Args:
            data: 纯数据字典（已由 PipelineServiceSource 解包）

        Returns:
            原始数据（透传，供后续处理使用）
        """
        if not data:
            return None

        # 使用数据解析器提取对话（内部会进行验证）
        dialogs = self.parser.extract(data)

        # 调用记忆服务存储对话
        self.call_service(
            self.service_name,
            dialogs,
            method="insert",
            timeout=10.0,
        )

        # 透传数据给下一个算子（保持原始格式）
        return data
