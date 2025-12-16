"""ValidateAction - 查询验证策略

使用记忆体：
- SCM: short_term_memory，验证查询是否需要激活记忆

特点：
- 验证查询合法性和安全性
- 支持多种验证规则（长度、安全词、格式）
- 可配置失败时的行为（跳过、使用默认查询、抛出异常）
"""

import re
from typing import Any

from ..base import BasePreRetrievalAction, PreRetrievalInput, PreRetrievalOutput


class ValidateAction(BasePreRetrievalAction):
    """查询验证Action

    验证查询是否符合预期规则，并在验证失败时采取相应措施。
    """

    def _init_action(self) -> None:
        """初始化查询验证配置"""
        self.validation_rules = self._get_config_value(
            "rules", required=True, context="action=validate"
        )

        self.on_fail = self._get_config_value("on_fail", default="default")

        self.default_query = self._get_config_value("default_query", default="Hello")

        self.preprocessing = self._get_config_value(
            "preprocessing",
            default={
                "strip_whitespace": True,
                "lowercase": False,
                "remove_punctuation": False,
            },
        )

        # 收集所有阻止模式（blocked_patterns）
        self.blocked_patterns = []
        for rule in self.validation_rules:
            if rule.get("type") == "safety":
                self.blocked_patterns.extend(rule.get("blocked_patterns", []))

    def execute(self, input_data: PreRetrievalInput) -> PreRetrievalOutput:
        """验证查询

        Args:
            input_data: 输入数据

        Returns:
            验证后的输出数据

        Raises:
            ValueError: 验证失败且on_fail="raise"
        """
        question = input_data.question

        # 预处理查询
        processed_query = self._preprocess(question)

        # 执行验证规则
        validation_result = self._validate(processed_query)

        if not validation_result["valid"]:
            # 验证失败，根据on_fail配置处理
            if self.on_fail == "raise":
                raise ValueError(f"Query validation failed: {validation_result['reason']}")
            elif self.on_fail == "default":
                final_query = self.default_query
            else:  # skip
                final_query = ""
        else:
            final_query = processed_query

        return PreRetrievalOutput(
            query=final_query,
            query_embedding=None,  # 由外部统一生成
            metadata={
                "original_query": question,
                "validation_result": validation_result,
                "needs_embedding": bool(final_query),
            },
            retrieve_mode="passive",
        )

    def _preprocess(self, text: str) -> str:
        """预处理查询文本"""
        result = text

        if self.preprocessing.get("strip_whitespace", True):
            result = result.strip()

        if self.preprocessing.get("lowercase", False):
            result = result.lower()

        if self.preprocessing.get("remove_punctuation", False):
            result = re.sub(r"[^\w\s]", "", result)

        return result

    def _validate(self, text: str) -> dict[str, Any]:
        """执行验证规则

        Returns:
            验证结果字典，包含valid和reason字段
        """
        for rule in self.validation_rules:
            rule_type = rule.get("type")

            if rule_type == "length":
                min_length = rule.get("min_length", 0)
                max_length = rule.get("max_length", float("inf"))

                if not (min_length <= len(text) <= max_length):
                    return {
                        "valid": False,
                        "reason": f"Length {len(text)} not in range [{min_length}, {max_length}]",
                        "rule": rule,
                    }

            elif rule_type == "safety":
                # 检查阻止模式
                for pattern in rule.get("blocked_patterns", []):
                    if re.search(pattern, text, re.IGNORECASE):
                        return {
                            "valid": False,
                            "reason": f"Matched blocked pattern: {pattern}",
                            "rule": rule,
                        }

            elif rule_type == "format":
                # 检查格式模式
                pattern = rule.get("pattern")
                if pattern and not re.match(pattern, text):
                    return {
                        "valid": False,
                        "reason": f"Does not match format pattern: {pattern}",
                        "rule": rule,
                    }

            elif rule_type == "custom":
                # 自定义验证逻辑（通过lambda或函数）
                validator = rule.get("validator")
                if validator and not validator(text):
                    return {
                        "valid": False,
                        "reason": "Failed custom validation",
                        "rule": rule,
                    }

        return {"valid": True, "reason": "All validations passed"}
