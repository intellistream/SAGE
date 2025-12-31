"""RouteAction - 检索路由策略

使用场景：
- 根据查询类型选择不同的检索策略
- 多源记忆系统的智能路由
- 条件分支检索

特点：
- 支持关键词、分类器、LLM三种路由策略
- 可输出多个路由目标（并行检索）
- 生成retrieval_hints供服务层使用
"""

import json
import re
from typing import Any

from sage.benchmark.benchmark_memory.experiment.utils import LLMGenerator

from ..base import BasePreRetrievalAction, PreRetrievalInput, PreRetrievalOutput


class RouteAction(BasePreRetrievalAction):
    """检索路由Action

    根据查询内容智能选择检索策略或目标。
    """

    def _init_action(self) -> None:
        """初始化检索路由配置"""
        self.route_strategy = self._get_config_value(
            "route_strategy", required=True, context="action=enhancement.route"
        )

        self.allow_multi_route = self._get_config_value("allow_multi_route", default=True)

        self.max_routes = self._get_config_value("max_routes", default=2)

        self.default_route = self._get_config_value(
            "default_route", default="long_term_memory", context="action=enhancement.route"
        )

        # 关键词路由配置
        if self.route_strategy == "keyword":
            self.keyword_rules = self._get_config_value(
                "keyword_rules", required=True, context="route_strategy=keyword"
            )

        # 分类器路由配置
        elif self.route_strategy == "classifier":
            self.classifier_model = self._get_config_value(
                "classifier_model", required=True, context="route_strategy=classifier"
            )
            self.route_mapping = self._get_config_value(
                "route_mapping", required=True, context="route_strategy=classifier"
            )

        # LLM路由配置
        elif self.route_strategy == "llm":
            self.route_prompt = self._get_config_value(
                "route_prompt",
                default="""Determine which memory source(s) should be queried for this question.
Available sources:
- short_term_memory: Recent conversations and events
- long_term_memory: Historical memories and past experiences
- knowledge_base: Factual information and general knowledge

Question: {query}

Return a JSON array of source names to query. Example: ["long_term_memory", "knowledge_base"]
Sources:""",
            )

        # LLM生成器将由PreRetrieval主类提供
        self._llm_generator = None

    def set_llm_generator(self, generator: LLMGenerator) -> None:
        """设置LLM生成器（由PreRetrieval主类调用）"""
        self._llm_generator = generator

    def execute(self, input_data: PreRetrievalInput) -> PreRetrievalOutput:
        """执行路由选择

        Args:
            input_data: 输入数据

        Returns:
            包含路由信息的输出数据
        """
        question = input_data.question

        if not question:
            return PreRetrievalOutput(
                query=question,
                metadata={"routes": [self.default_route], "route_strategy": self.route_strategy},
            )

        # 根据策略选择路由
        routes, route_params = self._select_routes(question)

        # 限制路由数量
        if not self.allow_multi_route:
            routes = routes[:1]
        else:
            routes = routes[: self.max_routes]

        # 如果没有路由，使用默认路由
        if not routes:
            routes = [self.default_route]

        # 构建元数据
        metadata: dict[str, Any] = {
            "original_query": question,
            "routes": routes,
            "route_params": route_params,
            "route_strategy": self.route_strategy,
            "needs_embedding": True,
        }

        # 构建retrieval_hints
        retrieval_hints = {
            "strategies": routes,
            "params": route_params,
            "route_strategy": self.route_strategy,
        }

        return PreRetrievalOutput(
            query=question,
            query_embedding=None,
            metadata=metadata,
            retrieve_mode="active",
            retrieve_params={"retrieval_hints": retrieval_hints},
        )

    def _select_routes(self, question: str) -> tuple[list[str], dict[str, Any]]:
        """选择路由目标

        Returns:
            (routes, route_params) - 路由列表和路由参数
        """
        if self.route_strategy == "keyword":
            return self._route_keyword(question)
        elif self.route_strategy == "classifier":
            return self._route_classifier(question)
        elif self.route_strategy == "llm":
            return self._route_llm(question)
        else:
            return [self.default_route], {}

    def _route_keyword(self, question: str) -> tuple[list[str], dict[str, Any]]:
        """关键词路由"""
        question_lower = question.lower()
        matched_routes: list[str] = []
        merged_params: dict[str, Any] = {}

        for rule in self.keyword_rules:
            keywords = rule.get("keywords", [])
            target = rule.get("target")
            rule_params = rule.get("params", {})

            for keyword in keywords:
                if keyword.lower() in question_lower:
                    if target and target not in matched_routes:
                        matched_routes.append(target)
                        merged_params.update(rule_params)
                    break

        return matched_routes if matched_routes else [self.default_route], merged_params

    def _route_classifier(self, question: str) -> tuple[list[str], dict[str, Any]]:
        """分类器路由

        使用简单的基于规则的意图分类。
        可扩展为：使用真实的文本分类模型（如transformers）
        """
        question_lower = question.lower()

        # 简单的意图分类规则
        intent = self._classify_intent(question_lower)

        # 根据意图映射到路由
        if intent in self.route_mapping:
            target = self.route_mapping[intent]
            return [target], {"intent": intent}
        else:
            return [self.default_route], {"intent": "unknown"}

    def _classify_intent(self, question: str) -> str:
        """简单的意图分类

        分类类型：
        - factual: 事实性问题 (what is, who is, define)
        - personal: 个人记忆相关 (I, me, my)
        - recent: 近期事件 (recently, just now, today)
        - historical: 历史事件 (last week, before, previously)
        """
        # 事实性问题特征
        factual_patterns = [
            "what is",
            "what are",
            "who is",
            "who are",
            "define",
            "explain",
            "how does",
            "why does",
            "meaning of",
            "definition of",
        ]

        # 个人记忆特征
        personal_patterns = ["i ", "my ", "me ", "mine", "remember when i", "did i", "have i"]

        # 近期事件特征
        recent_patterns = [
            "just",
            "now",
            "recently",
            "today",
            "this morning",
            "this afternoon",
            "moment ago",
        ]

        # 历史事件特征
        historical_patterns = [
            "last week",
            "last month",
            "last year",
            "before",
            "previously",
            "ago",
            "past",
        ]

        # 按优先级分类
        if any(pattern in question for pattern in factual_patterns):
            return "factual"

        if any(pattern in question for pattern in recent_patterns):
            return "recent"

        if any(pattern in question for pattern in historical_patterns):
            return "historical"

        if any(pattern in question for pattern in personal_patterns):
            return "personal"

        # 默认返回personal（因为大多数查询都与用户相关）
        return "personal"

    def _route_llm(self, question: str) -> tuple[list[str], dict[str, Any]]:
        """LLM路由"""
        if self._llm_generator is None:
            return [self.default_route], {}

        prompt = self.route_prompt.format(query=question)

        try:
            result = self._llm_generator.generate(prompt, max_tokens=100, temperature=0.3)

            # 尝试解析JSON对象
            try:
                match = re.search(r"\{.*?\}", result, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    if isinstance(parsed, dict):
                        routes = parsed.get("strategies", [])
                        params = parsed.get("params", {})
                        if routes:
                            return routes, params
            except json.JSONDecodeError:
                pass

            # 尝试解析JSON数组
            try:
                match = re.search(r"\[.*?\]", result, re.DOTALL)
                if match:
                    parsed_array = json.loads(match.group())
                    if isinstance(parsed_array, list):
                        routes = [r for r in parsed_array if isinstance(r, str)]
                        if routes:
                            return routes, {}
            except json.JSONDecodeError:
                pass

            # 如果不是JSON，尝试解析文本中的策略关键词
            known_strategies = [
                "short_term_memory",
                "long_term_memory",
                "knowledge_base",
                "semantic_search",
                "temporal_search",
            ]

            found_strategies = []
            for strategy in known_strategies:
                if strategy in result.lower():
                    found_strategies.append(strategy)

            if found_strategies:
                return found_strategies, {}

            return [self.default_route], {}

        except Exception as e:
            print(f"[WARNING] LLM routing failed: {e}")
            return [self.default_route], {}
