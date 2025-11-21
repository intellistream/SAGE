"""简单的 Prompt 构建工具

提供基于模板字符串的 Prompt 构建功能，替代复杂的 QAPromptor
"""

from typing import Any


def build_prompt(template: str, **kwargs: Any) -> str:
    """根据模板和参数构建 Prompt
    
    Args:
        template: Prompt 模板字符串，使用 {key} 作为占位符
        **kwargs: 要填充到模板中的键值对
    
    Returns:
        构建好的 Prompt 字符串
    
    Examples:
        >>> template = "问题: {question}\\n历史: {history}\\n请回答:"
        >>> prompt = build_prompt(template, question="你好", history="用户: 早上好")
        >>> print(prompt)
        问题: 你好
        历史: 用户: 早上好
        请回答:
    """
    return template.format(**kwargs)
