from typing import List, Tuple, Dict, Any
import json
import re
from ..utils.template import AI_Template
from sage_core.function.flatmap_function import FlatMapFunction
from sage_common_funs.utils.generator_model import apply_generator_model

class ChiefBot(FlatMapFunction):
    """
    ChiefBot Agent - 作为入口代理，分析查询并决定使用哪些下游工具
    输入: AI_Template (只包含raw_question)
    输出: List[Tuple[AI_Template, str]] - 每个元组包含增强的template和对应的tool名称
    """
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """
        获取默认配置，包括LLM设置和可用工具
        
        Returns:
            Dict[str, Any]: 默认配置字典
        """
        return {
            "llm": {
                "method": "openai",
                "model_name": "gpt-3.5-turbo",
                "base_url": "https://api.openai.com/v1",
                "api_key": "${OPENAI_API_KEY}",
                "seed": 42
            },
            "available_tools": {
                "web_search": "Search the internet for current information, news, and real-time data",
                # "knowledge_retrieval": "Retrieve information from internal knowledge base or documents",
                # "calculator": "Perform mathematical calculations and solve numerical problems",
                # "code_executor": "Execute code snippets and programming tasks",
                # "data_analyzer": "Analyze data, create charts, and generate insights from datasets",
                # "translation": "Translate text between different languages",
                # "summarizer": "Summarize long documents, articles, or content",
                # "fact_checker": "Verify facts and check information accuracy",
                # "image_analyzer": "Analyze and describe images, charts, or visual content",
                # "weather_service": "Get current weather information and forecasts",
                # "stock_market": "Retrieve stock prices, market data, and financial information",
                # "news_aggregator": "Get latest news and updates on specific topics"
            },
            "tool_selection": {
                "max_tools_per_query": 3,
                "enable_parallel_execution": True,
                "priority_threshold": 3,
                "fallback_to_direct_response": True
            },
            "reasoning": {
                "detailed_analysis": True,
                "strategy_planning": True,
                "tool_reasoning": True
            }
        }
    
    def __init__(self, config: Dict[str, Any] = None, **kwargs):
        """
        初始化Chief Agent
        
        Args:
            config: 完整配置字典，包含llm、available_tools等设置
                - llm: LLM相关配置 (method, model_name, base_url, api_key, seed)
                - available_tools: 可用工具字典 {tool_name: tool_description}
                - tool_selection: 工具选择相关配置
                - reasoning: 推理相关配置
            **kwargs: 其他参数（向后兼容）
        """
        super().__init__(**kwargs)
        
        # 合并配置
        self.config = self.get_default_config()
        if config:
            # 深度合并配置
            self._deep_merge_config(self.config, config)
        
        # 向后兼容：如果直接传递了参数，使用这些参数更新config
        legacy_params = {
            'available_tools': kwargs.get('available_tools')
        }
        
        if legacy_params['available_tools'] is not None:
            self.config['available_tools'] = legacy_params['available_tools']
        
        # 提取配置项
        self.llm_config = self.config["llm"]
        self.available_tools = self.config["available_tools"]
        self.tool_selection_config = self.config["tool_selection"]
        self.reasoning_config = self.config["reasoning"]
        
        # 初始化生成器模型
        self.model = apply_generator_model(
            method=self.llm_config["method"],
            model_name=self.llm_config["model_name"],
            base_url=self.llm_config["base_url"],
            api_key=self.llm_config["api_key"],
            seed=self.llm_config.get("seed", 42)
        )
        
        # 构建工具选择提示模板
        self.tool_selection_prompt = self._build_tool_selection_prompt()
        
        # 统计信息
        self.tool_usage_stats = {}
        self.query_count = 0
        
        self.logger.info(f"ChiefBot initialized with {len(self.available_tools)} available tools")
        self.logger.debug(f"Available tools: {list(self.available_tools.keys())}")

    def _deep_merge_config(self, base_config: Dict[str, Any], new_config: Dict[str, Any]):
        """深度合并配置字典"""
        for key, value in new_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                self._deep_merge_config(base_config[key], value)
            else:
                base_config[key] = value
    
    def _build_tool_selection_prompt(self) -> str:
        """构建工具选择的提示模板"""
        tools_description = []
        for tool_name, tool_desc in self.available_tools.items():
            tools_description.append(f"- {tool_name}: {tool_desc}")
        
        tools_text = "\n".join(tools_description)
        
        # 根据配置调整prompt内容
        max_tools = self.tool_selection_config.get("max_tools_per_query", 3)
        priority_threshold = self.tool_selection_config.get("priority_threshold", 3)
        
        analysis_instruction = ""
        if self.reasoning_config.get("detailed_analysis", True):
            analysis_instruction = "Provide a detailed analysis of the user query including:"
        else:
            analysis_instruction = "Provide a brief analysis of the user query."
        
        strategy_instruction = ""
        if self.reasoning_config.get("strategy_planning", True):
            strategy_instruction = """
    "strategy": "Overall strategy for answering the query, including execution order","""
        
        reasoning_instruction = ""
        if self.reasoning_config.get("tool_reasoning", True):
            reasoning_instruction = """
            "reasoning": "detailed explanation of why this tool is needed","""
        
        prompt = f"""You are a Chief Agent responsible for analyzing user queries and selecting appropriate tools for execution.

Available Tools:
{tools_text}

Your task is to:
1. {analysis_instruction}
2. Determine which tools are needed to answer the query (maximum {max_tools} tools)
3. For each selected tool, provide a specific sub-query or instruction
4. Assign priority levels (1-5, where 5 is highest priority)

Respond in the following JSON format:
{{
    "analysis": "Analysis of the user query including complexity, domain, and requirements",{strategy_instruction}
    "selected_tools": [
        {{
            "tool_name": "exact tool name from available tools",
            "sub_query": "specific query or instruction for this tool",{reasoning_instruction}
            "priority": 1-5
        }}
    ]
}}

Rules:
- Only select tools that are actually needed (maximum {max_tools})
- Provide clear, specific sub-queries for each tool
- Priority levels: 5=Critical, 4=Important, 3=Useful, 2=Optional, 1=Nice-to-have
- Only include tools with priority >= {priority_threshold}
- If no tools are needed, return an empty selected_tools list
- Consider execution dependencies when assigning priorities

User Query: {{query}}"""
        
        return prompt
    
    def _parse_tool_selection(self, response: str) -> Dict[str, Any]:
        """解析工具选择响应"""
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
        self.logger.warning(f"Failed to parse tool selection response: {response}")
        return {
            "analysis": "Failed to parse response",
            "selected_tools": [],
            "strategy": "Default strategy - no tools selected"
        }
    
    def _filter_tools_by_priority(self, selected_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """根据优先级和配置过滤工具"""
        priority_threshold = self.tool_selection_config.get("priority_threshold", 3)
        max_tools = self.tool_selection_config.get("max_tools_per_query", 3)
        
        # 过滤优先级
        filtered_tools = [tool for tool in selected_tools 
                         if tool.get("priority", 0) >= priority_threshold]
        
        # 按优先级排序并限制数量
        filtered_tools.sort(key=lambda x: x.get("priority", 0), reverse=True)
        return filtered_tools[:max_tools]
    
    def _create_enhanced_template(self, original_template: AI_Template, 
                                tool_info: Dict[str, Any], 
                                analysis: str, 
                                tool_name:str,
                                strategy: str = None,
                                ) -> AI_Template:
        """为特定工具创建增强的template"""
        # 创建新的template，保持原有的metadata
        enhanced_template = AI_Template(
            sequence=original_template.sequence,
            timestamp=original_template.timestamp,
            uuid=original_template.uuid,
            raw_question=original_template.raw_question,
            tool_name=tool_name
        )
        
        # 构建系统prompt内容
        system_content_parts = [
            f"You are a specialized agent using the {tool_info['tool_name']} tool.",
            f"Original Query: {original_template.raw_question}",
            f"Your Specific Task: {tool_info['sub_query']}",
            f"Priority: {tool_info['priority']}/5",
            f"Chief's Analysis: {analysis}"
        ]
        
        if tool_info.get('reasoning'):
            system_content_parts.append(f"Tool Selection Reasoning: {tool_info['reasoning']}")
        
        if strategy:
            system_content_parts.append(f"Overall Strategy: {strategy}")
        
        system_content_parts.append("Execute your task and provide a clear, focused result.")
        
        # 为特定工具构建prompt
        tool_prompt = {
            "role": "system",
            "content": "\n\n".join(system_content_parts)
        }
        
        # 添加用户查询
        user_prompt = {
            "role": "user", 
            "content": tool_info['sub_query']
        }
        
        enhanced_template.prompts = [tool_prompt, user_prompt]
        
        return enhanced_template
    
    def _update_tool_stats(self, tool_name: str):
        """更新工具使用统计"""
        if tool_name not in self.tool_usage_stats:
            self.tool_usage_stats[tool_name] = 0
        self.tool_usage_stats[tool_name] += 1
    
    def execute(self, template: AI_Template) -> List[Tuple[AI_Template, str]]:
        """
        执行Chief Agent逻辑
        
        Args:
            template: 输入的AI_Template，只包含raw_question
            
        Returns:
            List[Tuple[AI_Template, str]]: 增强的template和工具名称的元组列表
        """
        try:
            self.query_count += 1
            self.logger.debug(f"ChiefBot processing query #{self.query_count}: {template.raw_question}")
            
            # 1. 构建工具选择prompt
            prompt = self.tool_selection_prompt.format(query=template.raw_question)
            
            # 2. 调用LLM进行工具选择
            messages = [{"role": "user", "content": prompt}]
            response = self.model.generate(messages)
            
            self.logger.debug(f"ChiefBot LLM response: {response}")
            
            # 3. 解析响应
            tool_selection = self._parse_tool_selection(response)
            
            analysis = tool_selection.get("analysis", "No analysis provided")
            strategy = tool_selection.get("strategy", "No strategy provided")
            selected_tools = tool_selection.get("selected_tools", [])
            
            # 4. 过滤和排序工具
            filtered_tools = self._filter_tools_by_priority(selected_tools)
            
            self.logger.info(f"ChiefBot selected {len(filtered_tools)} tools for query (filtered from {len(selected_tools)})")
            
            # 5. 为每个选中的工具创建增强的template
            result_templates = []
            
            for tool_info in filtered_tools:
                tool_name = tool_info.get("tool_name")
                
                # 验证工具名称是否有效
                if tool_name not in self.available_tools:
                    self.logger.warning(f"Unknown tool selected: {tool_name}, skipping...")
                    continue
                
                # 创建增强的template
                enhanced_template = self._create_enhanced_template(
                    template, tool_info, analysis, strategy, tool_name
                )
                
                # 添加到结果列表
                result_templates.append(enhanced_template)
                
                # 更新统计
                self._update_tool_stats(tool_name)
                
                self.logger.debug(f"Created task for tool {tool_name}: {tool_info.get('sub_query', 'No sub-query')}")
            
            # 6. 如果没有选择任何工具，根据配置决定是否提供直接响应
            if not result_templates and self.tool_selection_config.get("fallback_to_direct_response", True):
                self.logger.info("No tools selected, creating direct response template")
                no_tool_template = AI_Template(
                    sequence=template.sequence,
                    timestamp=template.timestamp,
                    uuid=template.uuid,
                    raw_question=template.raw_question
                )
                
                no_tool_prompt = {
                    "role": "system",
                    "content": f"""No specific tools were selected for this query. 
                    Provide a direct response based on your general knowledge.
                    
                    Query: {template.raw_question}
                    Analysis: {analysis}
                    Strategy: Use general knowledge to provide a helpful response."""
                }
                
                no_tool_template.prompts = [
                    no_tool_prompt,
                    {"role": "user", "content": template.raw_question}
                ]
                
                result_templates.append((no_tool_template, "direct_response"))
                self._update_tool_stats("direct_response")
            
            self.logger.info(f"ChiefBot generated {len(result_templates)} tasks")
            return result_templates
            
        except Exception as e:
            self.logger.error(f"ChiefBot execution failed: {e}")
            
            # 返回错误处理的template
            error_template = AI_Template(
                sequence=template.sequence,
                timestamp=template.timestamp,
                uuid=template.uuid,
                raw_question=template.raw_question
            )
            
            error_template.prompts = [
                {
                    "role": "system", 
                    "content": f"Error in task planning: {str(e)}. Provide a best-effort response."
                },
                {"role": "user", "content": template.raw_question}
            ]
            
            self._update_tool_stats("error_handler")
            return [(error_template, "error_handler")]

    def get_tool_stats(self) -> Dict[str, Any]:
        """获取工具使用统计"""
        return {
            "tool_usage": self.tool_usage_stats.copy(),
            "total_queries": self.query_count,
            "available_tools_count": len(self.available_tools),
            "most_used_tool": max(self.tool_usage_stats.items(), key=lambda x: x[1])[0] if self.tool_usage_stats else None
        }
    
    def add_tool(self, tool_name: str, tool_description: str):
        """动态添加工具"""
        self.available_tools[tool_name] = tool_description
        self.config["available_tools"][tool_name] = tool_description
        # 重新构建prompt模板
        self.tool_selection_prompt = self._build_tool_selection_prompt()
        self.logger.info(f"Added new tool: {tool_name}")
    
    def remove_tool(self, tool_name: str):
        """动态移除工具"""
        if tool_name in self.available_tools:
            del self.available_tools[tool_name]
            del self.config["available_tools"][tool_name]
            # 重新构建prompt模板
            self.tool_selection_prompt = self._build_tool_selection_prompt()
            self.logger.info(f"Removed tool: {tool_name}")
        else:
            self.logger.warning(f"Tool {tool_name} not found")
    
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            "llm_config": self.llm_config.copy(),
            "available_tools": list(self.available_tools.keys()),
            "tool_selection_config": self.tool_selection_config.copy(),
            "reasoning_config": self.reasoning_config.copy(),
            "stats": self.get_tool_stats()
        }