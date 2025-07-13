import os
from typing import List, Dict, Union, Tuple
from jinja2 import Template
from sage_core.function.map_function import MapFunction
from sage_utils.custom_logger import CustomLogger
from sage_common_funs.utils.template import AI_Template
from sage_common_funs.utils.generator_model import apply_generator_model

# 搜索查询优化的prompt模板
SEARCH_QUERY_OPTIMIZATION_PROMPT = '''You are a search query optimization specialist. Your task is to analyze the user's original question and existing retrieved information, then design optimized search queries to fill information gaps.

## Original User Question:
{{ raw_question }}

{%- if retriver_chunks and retriver_chunks|length > 0 %}
## Already Retrieved Information:
{% for chunk in retriver_chunks %}
### Retrieved Content {{ loop.index }}:
{{ chunk }}

{% endfor %}
{%- else %}
## No Previous Retrieved Information Available
{%- endif %}

## Your Task:
Analyze the original question and existing retrieved content, then determine what additional information is needed. Design 1-3 optimized search queries that will help gather the missing information.

## Instructions:
1. **Gap Analysis**: Identify what information is missing or incomplete
2. **Query Design**: Create specific, targeted search queries
3. **Avoid Redundancy**: Don't search for information already well-covered
4. **Be Strategic**: Focus on the most important missing pieces

## Response Format (JSON):
{
    "analysis": "Brief analysis of information gaps",
    "search_queries": [
        {
            "query": "specific search query string",
            "purpose": "what this query aims to find",
            "priority": 1-3
        }
    ],
    "reasoning": "Why these queries were selected"
}

## Guidelines:
- If information is already complete, return empty search_queries array
- Prioritize queries that directly address the user's question
- Make queries specific and targeted
- Limit to maximum 3 queries to avoid information overload
'''

class SearchBot(MapFunction):
    """
    中游搜索Bot - 分析AI_Template并设计优化的搜索查询
    输入: AI_Template (包含raw_question和retriver_chunks)
    输出: Tuple[AI_Template, List[str]] - 原始template和搜索查询列表
    """
    
    def __init__(self, config: dict, max_queries: int = 3, **kwargs):
        super().__init__(**kwargs)
        
        self.config = config
        self.max_queries = max_queries
        
        # 初始化LLM模型用于查询优化
        self.model = apply_generator_model(
            method=config["method"],
            model_name=config["model_name"],
            base_url=config["base_url"],
            api_key=config["api_key"],
            seed=42
        )
        
        # 初始化prompt模板
        self.prompt_template = Template(SEARCH_QUERY_OPTIMIZATION_PROMPT)
        
        self.query_count = 0
        
        self.logger.info(f"SearchBot initialized with max_queries: {max_queries}")

    def _analyze_information_completeness(self, template: AI_Template) -> Dict[str, any]:
        """
        分析信息完整性，判断是否需要额外搜索
        
        Args:
            template: AI_Template对象
            
        Returns:
            Dict: 分析结果
        """
        analysis = {
            "has_question": bool(template.raw_question and template.raw_question.strip()),
            "has_retrieved_content": bool(template.retriver_chunks),
            "content_count": len(template.retriver_chunks) if template.retriver_chunks else 0,
            "needs_search": True  # 默认需要搜索，由LLM决定
        }
        
        return analysis

    def _build_optimization_prompt(self, template: AI_Template) -> List[Dict[str, str]]:
        """
        构建查询优化的prompt
        
        Args:
            template: AI_Template对象
            
        Returns:
            List[Dict[str, str]]: 构建好的prompts
        """
        # 准备模板数据
        template_data = {
            'raw_question': template.raw_question or "No question provided",
            'retriver_chunks': template.retriver_chunks or []
        }
        
        # 渲染system prompt
        system_content = self.prompt_template.render(**template_data)
        
        prompts = [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": "Please analyze the information and provide optimized search queries in JSON format."
            }
        ]
        
        return prompts

    def _parse_search_optimization(self, response: str) -> Dict[str, any]:
        """
        解析LLM返回的搜索优化结果
        
        Args:
            response: LLM响应字符串
            
        Returns:
            Dict: 解析后的结果
        """
        import json
        import re
        
        try:
            # 尝试直接解析JSON
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 尝试从Markdown代码块中提取JSON
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 如果解析失败，返回默认结构
        self.logger.warning(f"Failed to parse search optimization response: {response}")
        return {
            "analysis": "Failed to parse optimization response",
            "search_queries": [],
            "reasoning": "Error in response parsing"
        }

    def _extract_search_queries(self, optimization_result: Dict[str, any]) -> List[str]:
        """
        从优化结果中提取搜索查询字符串
        
        Args:
            optimization_result: LLM返回的优化结果
            
        Returns:
            List[str]: 搜索查询字符串列表
        """
        search_queries = []
        
        queries_data = optimization_result.get("search_queries", [])
        
        for query_info in queries_data[:self.max_queries]:  # 限制查询数量
            query_string = query_info.get("query", "").strip()
            if query_string:
                search_queries.append(query_string)
        
        return search_queries

    def _validate_template(self, template: AI_Template) -> bool:
        """
        验证AI_Template是否有效
        
        Args:
            template: AI_Template对象
            
        Returns:
            bool: 是否有效
        """
        if not template.raw_question or not template.raw_question.strip():
            self.logger.warning("AI_Template missing or empty raw_question")
            return False
        
        return True

    def _log_search_analysis(self, template: AI_Template, queries: List[str]) -> None:
        """
        记录搜索分析信息
        """
        existing_chunks = len(template.retriver_chunks) if template.retriver_chunks else 0
        
        self.logger.debug(f"Search analysis: "
                         f"Question='{template.raw_question[:50]}...', "
                         f"Existing_chunks={existing_chunks}, "
                         f"Generated_queries={len(queries)}")
        
        for i, query in enumerate(queries, 1):
            self.logger.debug(f"Search query {i}: {query}")

    def execute(self, template: AI_Template) -> Tuple[AI_Template, List[str]]:
        """
        执行搜索查询优化
        
        Args:
            template: AI_Template对象，包含原始问题和已检索内容
            
        Returns:
            Tuple[AI_Template, List[str]]: 原始template和优化的搜索查询列表
        """
        try:
            self.logger.debug(f"SearchBot processing template UUID: {template.uuid}")
            
            # 1. 验证输入
            if not self._validate_template(template):
                self.logger.warning("Invalid template, returning empty search queries")
                return template, []
            
            # 2. 分析信息完整性
            analysis = self._analyze_information_completeness(template)
            
            # 3. 构建优化prompt
            optimization_prompts = self._build_optimization_prompt(template)
            
            self.logger.debug(f"Built optimization prompts with {len(optimization_prompts)} messages")
            
            # 4. 调用LLM进行查询优化
            response = self.model.generate(optimization_prompts)
            self.query_count += 1
            
            self.logger.debug(f"LLM optimization response: {response}")
            
            # 5. 解析优化结果
            optimization_result = self._parse_search_optimization(response)
            
            # 6. 提取搜索查询
            search_queries = self._extract_search_queries(optimization_result)
            
            # 7. 记录分析结果
            self._log_search_analysis(template, search_queries)
            
            self.logger.info(f"SearchBot generated {len(search_queries)} optimized queries (#{self.query_count})")
            
            return template, search_queries
            
        except Exception as e:
            self.logger.error(f"SearchBot execution failed: {e}")
            
            # 出错时返回原始template和空查询列表
            return template, []

class EnhancedSearchBot(SearchBot):
    """
    增强版搜索Bot - 支持更多定制化功能
    """
    
    def __init__(self, config: dict, max_queries: int = 3, 
                 fallback_to_original: bool = True, 
                 min_content_threshold: int = 0, **kwargs):
        super().__init__(config, max_queries, **kwargs)
        
        self.fallback_to_original = fallback_to_original
        self.min_content_threshold = min_content_threshold
        
        self.logger.info(f"EnhancedSearchBot initialized with fallback: {fallback_to_original}")

    def _should_skip_search(self, template: AI_Template) -> bool:
        """
        判断是否应该跳过搜索（信息已足够）
        """
        if not template.retriver_chunks:
            return False
        
        # 如果已有足够的内容，可能不需要额外搜索
        total_content_length = sum(len(chunk) for chunk in template.retriver_chunks)
        
        # 这里可以设置更复杂的判断逻辑
        return total_content_length > 2000 and len(template.retriver_chunks) >= 3

    def execute(self, template: AI_Template) -> Tuple[AI_Template, List[str]]:
        """
        增强版的搜索查询优化执行
        """
        try:
            # 检查是否应该跳过搜索
            if self._should_skip_search(template):
                self.logger.info("Sufficient information available, skipping search optimization")
                return template, []
            
            # 执行标准搜索优化
            result_template, search_queries = super().execute(template)
            
            # 如果没有生成查询且设置了fallback，使用原始问题作为查询
            if not search_queries and self.fallback_to_original:
                self.logger.info("No optimized queries generated, falling back to original question")
                search_queries = [template.raw_question]
            
            return result_template, search_queries
            
        except Exception as e:
            self.logger.error(f"EnhancedSearchBot failed: {e}")
            
            # 错误处理：如果设置了fallback，至少返回原始问题
            if self.fallback_to_original:
                return template, [template.raw_question]
            else:
                return template, []