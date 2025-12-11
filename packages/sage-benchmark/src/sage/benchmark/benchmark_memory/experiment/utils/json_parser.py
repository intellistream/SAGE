"""JSON 响应解析工具模块

提供统一的 JSON 响应解析功能，用于处理 LLM 返回的 JSON 格式响应。
"""

from __future__ import annotations

import json
from typing import Any


def parse_json_response(response: str, default: Any = None) -> Any:
    """解析 LLM 返回的 JSON 响应

    支持处理 LLM 响应中常见的格式问题：
    - 响应前后有额外文本
    - JSON 嵌套在 markdown 代码块中
    - 响应包含解释性文字

    Args:
        response: LLM 返回的文本
        default: 解析失败时的默认值，如果为 None 则返回空字典

    Returns:
        解析后的 JSON 对象（dict 或 list）

    Examples:
        >>> parse_json_response('{"key": "value"}')
        {'key': 'value'}
        >>> parse_json_response('Here is the result: {"key": "value"}')
        {'key': 'value'}
        >>> parse_json_response('invalid', default=[])
        []
    """
    if default is None:
        default = {}

    if not response:
        return default

    try:
        # 清理响应文本
        response_cleaned = response.strip()

        # 尝试找到 JSON 内容
        if not response_cleaned.startswith(("{", "[")):
            # 查找第一个 { 或 [
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
