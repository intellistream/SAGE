from __future__ import annotations

import threading
from typing import Any

import numpy as np

from sage.common.core.functions.map_function import MapFunction


class _VLLMEmbedderSingleton:
    _model = None
    _lock = threading.Lock()

    @classmethod
    def get_model(
        cls,
        *,
        model: str,
        enforce_eager: bool = True,
        **kwargs,
    ):
        """进程内 vLLM embedding 模型单例。

        注意：
        - 这是“同一 Python 进程”级别的单例。
        - 如果 SAGE runtime 在多进程/多 worker 下执行，每个进程仍会各自加载一份模型。
        """
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    from vllm import LLM

                    cls._model = LLM(
                        model=model,
                        task="embed",
                        enforce_eager=enforce_eager,
                        **kwargs,
                    )
        return cls._model


class VLLMEmbeddingMap(MapFunction):
    """在本地进程内使用 vLLM 直接生成 embedding 的 MapFunction。

    输入：dict（默认取 title 字段）
    输出：dict + embedding(np.ndarray)

    依赖：需要安装 vllm，并且本机具备相应运行环境（通常需要 GPU / CUDA）。
    """

    def __init__(
        self,
        model: str = "intfloat/e5-mistral-7b-instruct",
        text_field: str = "title",
        normalize: bool = True,
        enforce_eager: bool = True,
        batch_size: int = 16,
        **vllm_kwargs,
    ):
        super().__init__()
        self.model_name = model
        self.text_field = text_field
        self.normalize = normalize
        self.enforce_eager = enforce_eager
        self.batch_size = batch_size
        self.vllm_kwargs = vllm_kwargs

        # 预热/初始化模型（lazy 也可以，但 demo 更希望尽早失败）
        self._model = _VLLMEmbedderSingleton.get_model(
            model=self.model_name,
            enforce_eager=self.enforce_eager,
            **self.vllm_kwargs,
        )

    def _embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        outs = self._model.embed(texts)
        # vLLM embed 返回对象结构依赖版本：示例里是 o.outputs.embedding
        vecs = []
        for o in outs:
            emb = o.outputs.embedding
            arr = np.array(emb, dtype=np.float32)
            if self.normalize:
                arr = arr / (np.linalg.norm(arr) + 1e-8)
            vecs.append(arr)
        return vecs

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text = str(data.get(self.text_field, ""))
        if not text:
            return {**data, "embedding": None}

        vec = self._embed_batch([text])[0]
        return {**data, "embedding": vec}

    def get_dim(self) -> int:
        """尽量推断 embedding 维度（首次调用 embed 后可得到）。"""
        try:
            # 尝试做一次最小 embed 来拿维度
            v = self._embed_batch(["dim_probe"])[0]
            return int(v.shape[0])
        except Exception:
            return -1
