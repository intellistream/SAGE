"""LLM 生成工具

提供直接调用 OpenAI-compatible API 的功能，内置响应解析能力：
- generate(): 基础文本生成
- generate_json(): 生成并解析 JSON 响应
- generate_triples(): 生成并解析三元组（HippoRAG 风格）
"""

from __future__ import annotations

import json
import logging
import re
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

    @classmethod
    def from_config(cls, config, prefix: str = "runtime") -> LLMGenerator:
        """从配置对象创建 LLMGenerator

        Args:
            config: RuntimeConfig 对象
            prefix: 配置前缀，默认为 "runtime"

        Returns:
            LLMGenerator 实例

        Raises:
            ValueError: 缺少必需的配置参数
        """
        api_key = config.get(f"{prefix}.api_key")
        base_url = config.get(f"{prefix}.base_url")
        model_name = config.get(f"{prefix}.model_name")
        max_tokens = config.get(f"{prefix}.max_tokens", 512)
        temperature = config.get(f"{prefix}.temperature", 0.7)
        seed = config.get(f"{prefix}.seed")

        # 验证必需参数
        if not all([api_key, base_url, model_name]):
            raise ValueError("缺少必需的 LLM 配置: api_key, base_url, model_name")

        return cls(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )

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

    def generate_json(
        self, prompt: str, default: Any = None, **override_params: Any
    ) -> dict | list | Any:
        """生成并解析 JSON 响应

        支持处理 LLM 响应中常见的格式问题：
        - 响应前后有额外文本
        - JSON 嵌套在 markdown 代码块中
        - 响应包含解释性文字

        Args:
            prompt: 输入的 Prompt
            default: 解析失败时的默认值，如果为 None 则返回空字典
            **override_params: 覆盖默认参数的临时参数

        Returns:
            解析后的 JSON 对象（dict 或 list）

        Examples:
            >>> result = generator.generate_json("返回 JSON 格式的用户信息")
            >>> print(result)
            {'name': 'Alice', 'age': 25}
        """
        response = self.generate(prompt, **override_params)
        return self._parse_json(response, default)

    def generate_triples(
        self, prompt: str, **override_params: Any
    ) -> tuple[list[tuple[str, str, str]], list[str]]:
        """生成并解析三元组（HippoRAG 风格）

        Args:
            prompt: 输入的 Prompt，应该是三元组提取的 prompt
            **override_params: 覆盖默认参数的临时参数

        Returns:
            (triples, refactors) 元组：
            - triples: 三元组列表 [(subject, predicate, object), ...]
            - refactors: 重构后的自然语言描述列表

        Examples:
            >>> triples, refactors = generator.generate_triples(prompt)
            >>> print(triples)
            [('Alice', 'knows', 'Bob')]
            >>> print(refactors)
            ['Alice knows Bob']
        """
        response = self.generate(prompt, **override_params)
        triples = self._parse_triples(response)
        refactors = self._refactor_triples(triples)
        return triples, refactors

    # =========================================================================
    # 私有解析方法
    # =========================================================================

    def _parse_json(self, response: str, default: Any = None) -> Any:
        """解析 LLM 返回的 JSON 响应

        Args:
            response: LLM 返回的文本
            default: 解析失败时的默认值

        Returns:
            解析后的 JSON 对象
        """
        if default is None:
            default = {}

        if not response:
            return default

        try:
            response_cleaned = response.strip()

            # 尝试找到 JSON 内容
            if not response_cleaned.startswith(("{", "[")):
                start_brace = response_cleaned.find("{")
                start_bracket = response_cleaned.find("[")

                if start_brace == -1 and start_bracket == -1:
                    return default

                if start_brace == -1:
                    start_idx = start_bracket
                elif start_bracket == -1:
                    start_idx = start_brace
                else:
                    start_idx = min(start_brace, start_bracket)

                response_cleaned = response_cleaned[start_idx:]

            # 找到匹配的结束符
            if response_cleaned.startswith("{"):
                end_idx = response_cleaned.rfind("}") + 1
            else:
                end_idx = response_cleaned.rfind("]") + 1

            if end_idx > 0:
                response_cleaned = response_cleaned[:end_idx]

            return json.loads(response_cleaned)

        except json.JSONDecodeError as e:
            print(f"[WARNING] JSON parsing error: {e}")
            return default

    def _parse_triples(self, triples_text: str) -> list[tuple[str, str, str]]:
        """解析 LLM 输出的三元组文本

        Args:
            triples_text: LLM 生成的三元组文本，格式如：
                (Subject, Predicate, Object)
                或者 "None"

        Returns:
            三元组列表 [(subject, predicate, object), ...]
        """
        triples = []

        if triples_text.strip().lower() == "none":
            return triples

        lines = triples_text.strip().split("\n")
        for line in lines:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            # 移除行首编号格式
            line = re.sub(r"^\(\d+\)\s*", "", line)
            line = re.sub(r"^\d+\.\s*", "", line)
            line = re.sub(r"^\d+\)\s*", "", line)
            line = line.strip()

            # 解析 (Subject, Predicate, Object) 格式
            if line.startswith("(") and line.endswith(")"):
                content = line[1:-1]
                parts = [part.strip() for part in content.split(",")]
                if len(parts) == 3:
                    triples.append((parts[0], parts[1], parts[2]))

        return triples

    def _refactor_triples(self, triples: list[tuple[str, str, str]]) -> list[str]:
        """将三元组重构为自然语言描述

        Args:
            triples: 三元组列表

        Returns:
            重构后的描述列表
        """
        return [f"{s} {p} {o}" for s, p, o in triples]

    def deduplicate_triples(
        self,
        triples: list[tuple[str, str, str]],
        refactors: list[str],
    ) -> tuple[list[tuple[str, str, str]], list[str]]:
        """基于描述去重三元组

        Args:
            triples: 三元组列表
            refactors: 对应的描述列表

        Returns:
            (unique_triples, unique_refactors) 去重后的结果
        """
        seen: set[str] = set()
        unique_triples = []
        unique_refactors = []

        for triple, refactor in zip(triples, refactors):
            if refactor not in seen:
                seen.add(refactor)
                unique_triples.append(triple)
                unique_refactors.append(refactor)

        return unique_triples, unique_refactors
