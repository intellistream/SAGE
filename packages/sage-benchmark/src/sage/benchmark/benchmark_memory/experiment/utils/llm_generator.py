"""简单的 LLM 生成工具

提供直接调用 OpenAI-compatible API 的功能，替代复杂的 OpenAIGenerator
"""

import logging
from typing import Any

from openai import OpenAI

# 禁用 httpx 和 openai 的 INFO 日志
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


class LLMGenerator:
    """简单的 LLM 生成器类"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        seed: int | None = None,
        **kwargs: Any,
    ):
        """初始化 LLM 生成器
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model_name: 模型名称
            max_tokens: 最大生成 token 数
            temperature: 温度参数
            seed: 随机种子（可选）
            **kwargs: 其他传递给 API 的参数
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.seed = seed
        self.extra_params = kwargs

    def generate(self, prompt: str, **override_params: Any) -> str:
        """调用 OpenAI-compatible API 生成回答
        
        Args:
            prompt: 输入的 Prompt
            **override_params: 覆盖默认参数的临时参数
        
        Returns:
            生成的回答文本
        
        Raises:
            Exception: API 调用失败时抛出异常
        """
        # 构建请求参数
        request_params: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        
        # 添加可选参数
        if self.seed is not None:
            request_params["seed"] = self.seed
        
        # 添加初始化时的额外参数
        request_params.update(self.extra_params)
        
        # 添加本次调用的覆盖参数
        request_params.update(override_params)
        
        # 调用 API
        response = self.client.chat.completions.create(**request_params)
        
        # 提取回答
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content or ""
        
        return ""
