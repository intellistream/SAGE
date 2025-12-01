"""
SAGE Function适配器
==================

将Refiner适配为SAGE的MapFunction，方便集成到数据流管道中。

注意: 此适配器需要SAGE核心依赖。如果没有SAGE环境，请直接使用RefinerService。
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.common.core import MapFunction
else:
    try:
        from sage.common.core import MapFunction

        SAGE_CORE_AVAILABLE = True
    except ImportError:
        SAGE_CORE_AVAILABLE = False

        # 创建dummy基类
        class MapFunction:
            """Dummy MapFunction for non-SAGE environments"""

            pass


# Use sage_refiner submodule service
from sage.middleware.components.sage_refiner.python.service import RefinerService


class RefinerAdapter(MapFunction):
    """
    Refiner适配器

    将RefinerService适配为SAGE MapFunction，可以直接在管道中使用。

    配置示例:
        config = {
            "algorithm": "long_refiner",
            "budget": 2048,
            "enable_cache": True,
            "base_model_path": "Qwen/Qwen2.5-3B-Instruct",
            # ... 其他LongRefiner配置
        }

    使用示例:
        env.from_batch(...)
           .map(ChromaRetriever, retriever_config)
           .map(RefinerAdapter, refiner_config)  # 添加压缩
           .map(QAPromptor, promptor_config)
           .sink(...)
    """

    def __init__(self, config: dict[str, Any] | None = None, **kwargs):
        """
        初始化适配器

        Args:
            config: Refiner配置字典
            **kwargs: 其他参数（兼容SAGE）
        """
        super().__init__(**kwargs)
        self.config = config or {}

        # 创建RefinerService
        self.service = RefinerService(self.config)

        # 启用性能分析（可选）
        self.enable_profile = self.config.get("enable_profile", False)

        if self.enable_profile:
            self.logger.info("Refiner profiling enabled")

    def execute(self, data: Any) -> Any:
        """
        执行精炼

        期望输入格式:
            {
                "query" or "question": "用户问题",
                "retrieval_results" or "retrieval_docs" or "results": [...],  # 检索到的文档
                ... # 其他字段会保留
            }

        输出格式:
            {
                ... # 原始字段
                "refining_results": [...],  # 精炼后的文档（字符串列表）
            }
        """
        # 标准化输入
        if isinstance(data, dict):
            query = data.get("query") or data.get("question", "")
            # 优先读取新字段，兼容旧字段
            documents = (
                data.get("retrieval_results")
                or data.get("retrieval_docs")
                or data.get("retrieved_docs")
                or data.get("results", [])
            )
        else:
            self.logger.warning(f"Unexpected data format: {type(data)}")
            return data

        if not documents:
            self.logger.debug("No documents to refine, skipping")
            # 保留原始数据，添加空的精炼结果
            if isinstance(data, dict):
                data["refining_results"] = []
            return data

        # 执行精炼
        try:
            budget = self.config.get("budget")
            result = self.service.refine(
                query=query,
                documents=documents,
                budget=budget,
                use_cache=self.config.get("enable_cache", True),
            )

            # 组装输出 - 使用统一的字段格式
            output = data.copy() if isinstance(data, dict) else {}
            output["refining_results"] = result.refined_content  # 压缩后的文档文本列表

            # 性能日志
            if self.enable_profile:
                self.logger.info(
                    f"[Refiner] Compression: {result.metrics.compression_rate:.2f}x, "
                    f"Time: {result.metrics.refine_time:.2f}s, "
                    f"Tokens: {result.metrics.original_tokens} -> {result.metrics.refined_tokens}"
                )

            return output

        except Exception as e:
            self.logger.error(f"Refiner execution failed: {e}", exc_info=True)
            # 失败时返回原始数据
            if isinstance(data, dict):
                data["refining_results"] = documents
            return data

    def __del__(self):
        """清理资源"""
        if hasattr(self, "service"):
            self.service.shutdown()
