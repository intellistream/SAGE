"""SageLLM Generator - 统一 LLM 推理算子

通过 EngineFactory 统一创建引擎，不硬编码任何具体引擎实现。
支持 auto/mock/cuda/ascend 等多种后端类型。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass, field
from typing import Any

from sage.common.core.functions import MapFunction as MapOperator

logger = logging.getLogger(__name__)


def _normalize_input(data: Any) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """
    规范化输入数据为 (context, prompt, options) 三元组。

    支持多种输入格式：
    - str: 直接作为 prompt
    - dict: 包含 prompt 和可选的 options
    - Sequence: [context, prompt] 或 [context, prompt, options]
    """
    context: dict[str, Any] = {}
    prompt: str = ""
    options: dict[str, Any] = {}

    if isinstance(data, str):
        prompt = data
    elif isinstance(data, dict):
        prompt = data.get("prompt", "")
        options = dict(data.get("options", {}))
        # 保留其他上下文字段
        context = {k: v for k, v in data.items() if k not in ("prompt", "options")}
    elif isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
        if len(data) >= 1:
            first = data[0]
            if isinstance(first, str):
                prompt = first
            elif isinstance(first, dict):
                context = dict(first)
        if len(data) >= 2:
            second = data[1]
            if isinstance(second, str):
                prompt = second
            elif isinstance(second, dict) and "prompt" in second:
                prompt = second["prompt"]
                options.update(second.get("options", {}))
        if len(data) >= 3 and isinstance(data[2], dict):
            options.update(data[2])
    else:
        prompt = str(data)

    return context, prompt, options


@dataclass
class SageLLMGenerator(MapOperator):
    """
    SageLLM 统一生成算子 - 通过 EngineFactory 创建引擎进行文本生成

    不直接导入或硬编码任何具体引擎实现（如 HFCudaEngine, MockEngine），
    而是通过工厂模式动态创建引擎，实现后端解耦。

    Example:
        ```python
        # 自动选择后端
        generator = SageLLMGenerator(
            model_path="Qwen/Qwen2.5-7B-Instruct",
            backend_type="auto",
        )
        result = generator.execute("写一首诗")

        # 指定 mock 后端用于测试
        generator = SageLLMGenerator(
            backend_type="mock",
            model_path="mock-model",
        )

        # 流式生成
        async for chunk in generator.stream_async("讲个故事"):
            print(chunk["text"], end="", flush=True)
        ```

    Attributes:
        backend_type: 引擎后端类型，支持 "auto"/"mock"/"cuda"/"ascend" 等
        model_path: 模型路径或 HuggingFace 模型 ID
        device_map: 设备映射策略，如 "auto"/"cuda:0"/"cpu"
        dtype: 数据类型，如 "auto"/"float16"/"bfloat16"
        max_tokens: 最大生成 token 数
        temperature: 采样温度
        top_p: nucleus 采样参数
        top_k: top-k 采样参数
        default_options: 默认生成选项
    """

    # 核心配置
    backend_type: str = "auto"
    model_path: str = ""
    device_map: str = "auto"
    dtype: str = "float16"
    device: str = "cuda"

    # HFCudaEngine 必需的配置（fail-fast 设计）
    load_in_8bit: bool = False
    load_in_4bit: bool = False
    trust_remote_code: bool = False

    # 生成参数默认值
    max_tokens: int = 2048
    max_new_tokens: int = 128  # HFCudaEngine 使用此字段
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 50

    # 引擎配置
    engine_id: str = ""
    timeout: float = 120.0
    default_options: dict[str, Any] = field(default_factory=dict)

    # 内部状态
    _engine: Any = field(default=None, init=False, repr=False)
    _initialized: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        super().__init__()
        if not self.engine_id:
            self.engine_id = f"sage-llm-{id(self)}"

    def _ensure_engine(self) -> None:
        """
        确保引擎已初始化。

        延迟初始化策略：只在首次使用时创建引擎。
        通过 EngineFactory 统一创建，不直接导入具体引擎类。
        """
        if self._initialized and self._engine is not None:
            return

        try:
            # 统一通过工厂创建，不直接 import 具体引擎
            from sagellm_backend.engine.factory import EngineFactory

            config = {
                "engine_id": self.engine_id,
                "model_path": self.model_path,
                "device": self.device,
                "device_map": self.device_map,
                "dtype": self.dtype,
                "load_in_8bit": self.load_in_8bit,
                "load_in_4bit": self.load_in_4bit,
                "trust_remote_code": self.trust_remote_code,
                "max_new_tokens": self.max_new_tokens,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
                "mock_mode": self.backend_type == "mock",
            }

            logger.info(
                f"Creating engine: backend_type={self.backend_type}, "
                f"model_path={self.model_path}, engine_id={self.engine_id}"
            )

            self._engine = EngineFactory.create(
                backend_type=self.backend_type,
                config=config,
            )

            # 启动引擎（如果需要）
            if hasattr(self._engine, "start") and not self._engine.is_running:
                import asyncio

                start_coro = self._engine.start()
                if asyncio.iscoroutine(start_coro):
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None

                    if loop is not None:
                        import concurrent.futures

                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            pool.submit(asyncio.run, start_coro).result()
                    else:
                        asyncio.run(start_coro)

            self._initialized = True

            logger.info(f"Engine created successfully: {self.engine_id}")

        except ImportError as e:
            raise ImportError(
                f"Failed to import sagellm_backend. "
                f"Please install it with: pip install sagellm-backend\n"
                f"Original error: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Failed to create engine: {e}")
            raise RuntimeError(
                f"Failed to create SageLLM engine with backend_type={self.backend_type}: {e}"
            ) from e

    def _build_generation_params(self, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        """
        构建生成参数，合并默认值和用户指定的选项。
        """
        params = {
            "prompt": prompt,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
        }
        # 应用默认选项
        params.update(self.default_options)
        # 应用用户传入的选项（优先级最高）
        params.update({k: v for k, v in options.items() if v is not None})
        return params

    def execute(self, data: Any) -> dict[str, Any]:
        """
        同步执行文本生成。

        Args:
            data: 输入数据，支持 str/dict/Sequence 格式

        Returns:
            包含生成结果的字典：
            - text: 生成的文本
            - usage: token 使用统计
            - context: 原始上下文（如果有）
        """
        self._ensure_engine()

        context, prompt, options = _normalize_input(data)
        params = self._build_generation_params(prompt, options)

        if not prompt:
            logger.warning("Empty prompt received, returning empty result")
            return {"text": "", "usage": {}, "context": context}

        try:
            logger.debug(f"Generating with params: {params}")

            # 调用引擎生成（兼容 execute/generate 两种接口，支持 async）
            import asyncio
            import uuid

            if hasattr(self._engine, "execute"):
                # 需要将 params 转换为 Request 对象
                try:
                    from sagellm_protocol.types import Request as SageLLMRequest

                    request = SageLLMRequest(
                        request_id=str(uuid.uuid4()),
                        trace_id=str(uuid.uuid4()),
                        model=self.model_path or "default",
                        prompt=params.get("prompt", ""),
                        max_tokens=params.get("max_tokens", self.max_tokens),
                        stream=False,
                        temperature=params.get("temperature", self.temperature),
                        top_p=params.get("top_p", self.top_p),
                    )
                    coro_or_result = self._engine.execute(request)
                except ImportError:
                    # 如果 sagellm_protocol 不可用，直接传 dict
                    coro_or_result = self._engine.execute(params)

                # 检查是否是协程
                if asyncio.iscoroutine(coro_or_result):
                    # 在同步上下文中运行异步方法
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None

                    if loop is not None:
                        # 已有事件循环，创建新任务
                        import concurrent.futures

                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            result = pool.submit(asyncio.run, coro_or_result).result()
                    else:
                        result = asyncio.run(coro_or_result)
                else:
                    result = coro_or_result
            elif hasattr(self._engine, "generate"):
                result = self._engine.generate(**params)
            else:
                raise RuntimeError(
                    f"Engine {type(self._engine).__name__} does not support "
                    "execute() or generate() method"
                )

            # 规范化输出格式
            if isinstance(result, str):
                output = {"text": result, "usage": {}}
            elif isinstance(result, dict):
                output = {
                    "text": result.get(
                        "text", result.get("generated", result.get("output_text", ""))
                    ),
                    "usage": result.get("usage", {}),
                }
            elif hasattr(result, "output_text"):
                # sagellm_protocol.types.Response 对象
                output_tokens = getattr(result, "output_tokens", [])
                num_output_tokens = len(output_tokens) if isinstance(output_tokens, list) else 0
                output = {
                    "text": result.output_text,
                    "usage": {
                        "completion_tokens": num_output_tokens,
                    },
                }
            else:
                output = {"text": str(result), "usage": {}}

            # 附加上下文
            if context:
                output["context"] = context

            return output

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise RuntimeError(f"SageLLM generation failed: {e}") from e

    async def stream_async(self, data: Any) -> AsyncGenerator[dict[str, Any], None]:
        """
        异步流式生成文本。

        Args:
            data: 输入数据，支持 str/dict/Sequence 格式

        Yields:
            流式输出的字典：
            - text: 当前生成的文本片段
            - done: 是否完成
            - usage: token 使用统计（仅在完成时）
        """
        self._ensure_engine()

        context, prompt, options = _normalize_input(data)
        params = self._build_generation_params(prompt, options)

        if not prompt:
            logger.warning("Empty prompt received for streaming")
            yield {"text": "", "done": True, "usage": {}}
            return

        try:
            logger.debug(f"Streaming generation with params: {params}")

            # 检查引擎是否支持流式生成
            if hasattr(self._engine, "generate_stream"):
                async for chunk in self._engine.generate_stream(**params):
                    if isinstance(chunk, str):
                        yield {"text": chunk, "done": False}
                    elif isinstance(chunk, dict):
                        yield {
                            "text": chunk.get("text", ""),
                            "done": chunk.get("done", False),
                            "usage": chunk.get("usage", {}),
                        }
                    else:
                        yield {"text": str(chunk), "done": False}

                # 发送完成信号
                yield {"text": "", "done": True, "usage": {}}

            elif hasattr(self._engine, "stream"):
                # 兼容同步流式接口
                for chunk in self._engine.stream(**params):
                    if isinstance(chunk, str):
                        yield {"text": chunk, "done": False}
                    elif isinstance(chunk, dict):
                        yield {
                            "text": chunk.get("text", ""),
                            "done": chunk.get("done", False),
                        }
                    else:
                        yield {"text": str(chunk), "done": False}

                yield {"text": "", "done": True, "usage": {}}

            else:
                # 引擎不支持流式，降级为一次性返回
                logger.warning(
                    f"Engine {self.backend_type} does not support streaming, "
                    "falling back to non-streaming generation"
                )
                result = self._engine.generate(**params)
                text = result if isinstance(result, str) else result.get("text", "")
                yield {"text": text, "done": True, "usage": result.get("usage", {})}

        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            yield {"text": "", "done": True, "error": str(e)}

    def shutdown(self) -> None:
        """
        关闭引擎并释放资源。
        """
        if self._engine is not None:
            try:
                if hasattr(self._engine, "shutdown"):
                    self._engine.shutdown()
                elif hasattr(self._engine, "close"):
                    self._engine.close()
                logger.info(f"Engine {self.engine_id} shut down")
            except Exception as e:
                logger.warning(f"Error shutting down engine: {e}")
            finally:
                self._engine = None
                self._initialized = False

    def __del__(self) -> None:
        """析构时尝试清理资源。"""
        try:
            self.shutdown()
        except Exception:
            pass


__all__ = ["SageLLMGenerator"]
