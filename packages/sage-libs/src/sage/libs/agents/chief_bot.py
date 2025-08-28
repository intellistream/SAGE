from typing import List, Tuple, Dict, Any
import json
import re
from ..context.model_context import ModelContext
from sage.core.api.function.flatmap_function import FlatMapFunction
from sage.libs.utils.openaiclient import OpenAIClient

class ChiefBot(FlatMapFunction):
    """
    ChiefBot Agent - 作为入口代理，分析查询并决定使用哪些下游工具
    输入: ModelContext (只包含raw_question)
    输出: List[ModelContext] - 每个template包含增强信息和正确的tool_name
    """
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """获取默认配置，包括LLM设置和可用工具"""
        return {
            "utils": {
                "method": "openai",
                "model_name": "gpt-3.5-turbo",
                "base_url": "https://api.openai.com/v1",
                "api_key": "${OPENAI_API_KEY}",
                "seed": 42,
                "temperature": 0.1,
                "max_tokens": 1000
            },
            "available_tools": {
                "web_search": "Search the internet for current information, news, and real-time data",
                "direct_response": "Provide direct response using general knowledge without external tools"
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
        """初始化Chief Agent"""
        super().__init__(**kwargs)
        
        # 合并配置
        self.config = self.get_default_config()
        if config:
            self._deep_merge_config(self.config, config)
        
        # 向后兼容
        if kwargs.get('available_tools'):
            self.config['available_tools'] = kwargs['available_tools']
        
        # 提取配置项
        self.llm_config = self.config["utils"]
        self.available_tools = self.config["available_tools"]
        self.tool_selection_config = self.config["tool_selection"]
        self.reasoning_config = self.config["reasoning"]
        
        # 初始化生成器模型
        try:
            self.model = OpenAIClient(
                method=self.llm_config["method"],
                model_name=self.llm_config["model_name"],
                base_url=self.llm_config["base_url"],
                api_key=self.llm_config["api_key"],
                seed=self.llm_config.get("seed", 42),
                temperature=self.llm_config.get("temperature", 0.1),
                max_tokens=self.llm_config.get("max_tokens", 1000)
            )
            self.logger.info("OpenAI client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
        
        # 构建工具选择提示模板
        self.tool_selection_prompt = self._build_tool_selection_prompt()
        
        # 统计信息
        self.tool_usage_stats = {}
        self.query_count = 0
        
        self.logger.info(f"ChiefBot initialized with {len(self.available_tools)} available tools")

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
        max_tools = self.tool_selection_config.get("max_tools_per_query", 3)
        
        prompt = f"""You are a Chief Agent that analyzes user queries and selects appropriate tools.

Available Tools:
{tools_text}

Analyze the user query and respond with ONLY a valid JSON object in this exact format:

{{{{
    "analysis": "Brief analysis of the user query",
    "selected_tools": [
        {{{{
            "tool_name": "exact_tool_name",
            "sub_query": "specific instruction for this tool",
            "priority": 4
        }}}}
    ]
}}}}

Rules:
- Return ONLY valid JSON, no other text
- Maximum {max_tools} tools
- Use exact tool names from the list above
- Priority: 1-5 (5=highest)
- If no tools needed, use empty array for selected_tools

User Query: {{query}}"""
        
        return prompt
    
    def _parse_tool_selection(self, response: str) -> Dict[str, Any]:
        """增强的工具选择响应解析"""
        if not response or not response.strip():
            self.logger.error("Empty response from LLM")
            return self._get_fallback_response()
        
        # 清理响应
        cleaned_response = response.strip()
        
        # 记录原始响应用于调试
        self.logger.debug(f"Raw LLM response: {repr(cleaned_response)}")
        
        # 尝试多种解析方法
        parsing_methods = [
            self._parse_direct_json,
            self._parse_markdown_json,
            self._parse_partial_json,
            self._parse_with_regex
        ]
        
        for method in parsing_methods:
            try:
                result = method(cleaned_response)
                if result and self._validate_parsed_result(result):
                    self.logger.debug(f"Successfully parsed using {method.__name__}")
                    return result
            except Exception as e:
                self.logger.debug(f"{method.__name__} failed: {e}")
                continue
        
        # 所有解析方法都失败
        self.logger.error(f"All parsing methods failed for response: {repr(cleaned_response[:200])}")
        return self._get_fallback_response()
    
    def _parse_direct_json(self, response: str) -> Dict[str, Any]:
        """直接JSON解析"""
        return json.loads(response)
    
    def _parse_markdown_json(self, response: str) -> Dict[str, Any]:
        """从Markdown代码块提取JSON"""
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        raise ValueError("No JSON found in markdown")
    
    def _parse_partial_json(self, response: str) -> Dict[str, Any]:
        """尝试修复不完整的JSON"""
        # 查找JSON对象的开始
        start_idx = response.find('{')
        if start_idx == -1:
            raise ValueError("No JSON object start found")
        
        # 查找最后一个}
        end_idx = response.rfind('}')
        if end_idx == -1 or end_idx <= start_idx:
            raise ValueError("No JSON object end found")
        
        json_str = response[start_idx:end_idx + 1]
        
        # 尝试解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # 尝试修复常见问题
            fixed_json = self._fix_common_json_issues(json_str)
            return json.loads(fixed_json)
    
    def _parse_with_regex(self, response: str) -> Dict[str, Any]:
        """使用正则表达式提取关键信息并构建JSON"""
        # 提取analysis
        analysis_match = re.search(r'"analysis"\s*:\s*"([^"]*)"', response)
        analysis = analysis_match.group(1) if analysis_match else "Query analysis"
        
        # 提取tools信息
        tools = []
        tool_pattern = r'"tool_name"\s*:\s*"([^"]*)".*?"sub_query"\s*:\s*"([^"]*)".*?"priority"\s*:\s*(\d+)'
        
        for match in re.finditer(tool_pattern, response, re.DOTALL):
            tool_name, sub_query, priority = match.groups()
            if tool_name in self.available_tools:
                tools.append({
                    "tool_name": tool_name,
                    "sub_query": sub_query,
                    "priority": int(priority)
                })
        
        return {
            "analysis": analysis,
            "selected_tools": tools
        }
    
    def _fix_common_json_issues(self, json_str: str) -> str:
        """修复常见的JSON格式问题"""
        # 移除尾随逗号
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # 确保字符串被正确引用
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
        
        return json_str
    
    def _validate_parsed_result(self, result: Dict[str, Any]) -> bool:
        """验证解析结果的有效性"""
        if not isinstance(result, dict):
            return False
        
        # 检查必需字段
        if "analysis" not in result:
            result["analysis"] = "Default analysis"
        
        if "selected_tools" not in result:
            result["selected_tools"] = []
        
        # 验证selected_tools格式
        if not isinstance(result["selected_tools"], list):
            result["selected_tools"] = []
            return True
        
        # 验证每个工具的格式
        valid_tools = []
        for tool in result["selected_tools"]:
            if isinstance(tool, dict) and "tool_name" in tool:
                # 确保工具名称有效
                if tool["tool_name"] in self.available_tools:
                    # 设置默认值
                    tool.setdefault("sub_query", tool["tool_name"] + " query")
                    tool.setdefault("priority", 3)
                    valid_tools.append(tool)
        
        result["selected_tools"] = valid_tools
        return True
    
    def _get_fallback_response(self) -> Dict[str, Any]:
        """获取后备响应"""
        return {
            "analysis": "Failed to parse LLM response, using direct response",
            "selected_tools": [
                {
                    "tool_name": "direct_response",
                    "sub_query": "Provide a helpful response using general knowledge",
                    "priority": 3
                }
            ]
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
    
    def _create_enhanced_template(self, original_template: ModelContext, 
                                tool_info: Dict[str, Any], 
                                analysis: str) -> ModelContext:
        """为特定工具创建增强的template"""
        tool_name = tool_info.get("tool_name")
        
        # 创建新的template - 修复这里的问题
        enhanced_template = ModelContext(
            sequence=original_template.sequence,
            timestamp=original_template.timestamp,
            uuid=original_template.uuid,
            raw_question=original_template.raw_question,
            tool_name=tool_name  # 确保这里是字符串
        )
        
        # 构建prompts
        system_content = f"""You are a specialized agent using the {tool_name} tool.

Original Query: {original_template.raw_question}
Your Specific Task: {tool_info.get('sub_query', 'Process the query')}
Priority: {tool_info.get('priority', 3)}/5
Chief's Analysis: {analysis}

Execute your task and provide a clear, focused result."""
        
        enhanced_template.prompts = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": tool_info.get('sub_query', original_template.raw_question)}
        ]
        
        return enhanced_template
    
    def _update_tool_stats(self, tool_name: str):
        """更新工具使用统计"""
        if tool_name not in self.tool_usage_stats:
            self.tool_usage_stats[tool_name] = 0
        self.tool_usage_stats[tool_name] += 1
    
    def execute(self, template: ModelContext) -> List[ModelContext]:
        """执行Chief Agent逻辑"""
        try:
            self.query_count += 1
            self.logger.debug(f"ChiefBot processing query #{self.query_count}: {template.raw_question}")
            
            # 1. 构建工具选择prompt
            prompt = self.tool_selection_prompt.format(query=template.raw_question)
            self.logger.debug(f"ChiefBot prompt length: {len(prompt)} chars")
            
            # 2. 调用LLM进行工具选择
            messages = [{"role": "user", "content": prompt}]
            
            try:
                self.logger.debug("Calling LLM for tool selection...")
                response = self.model.generate(messages)
                self.logger.debug(f"LLM response received, length: {len(response)} chars")
                self.logger.debug(f"LLM response preview: {response[:200]}...")
                
            except Exception as e:
                self.logger.error(f"LLM generation failed: {e}", exc_info=True)
                # 使用后备响应
                response = '{"analysis": "LLM call failed", "selected_tools": [{"tool_name": "direct_response", "sub_query": "Provide helpful response", "priority": 3}]}'
            
            # 3. 解析响应
            self.logger.debug("Parsing tool selection response...")
            tool_selection = self._parse_tool_selection(response)
            
            analysis = tool_selection.get("analysis", "No analysis provided")
            selected_tools = tool_selection.get("selected_tools", [])
            
            self.logger.info(f"Parsed {len(selected_tools)} tools from LLM response")
            
            # 4. 过滤和排序工具
            filtered_tools = self._filter_tools_by_priority(selected_tools)
            self.logger.info(f"ChiefBot selected {len(filtered_tools)} tools after filtering")
            
            # 5. 为每个选中的工具创建增强的template
            result_templates = []
            
            for tool_info in filtered_tools:
                tool_name = tool_info.get("tool_name")
                
                # 验证工具名称
                if tool_name not in self.available_tools:
                    self.logger.warning(f"Unknown tool selected: {tool_name}, skipping...")
                    continue
                
                # 创建增强的template
                enhanced_template = self._create_enhanced_template(
                    template, tool_info, analysis
                )
                
                result_templates.append(enhanced_template)
                self._update_tool_stats(tool_name)
                
                self.logger.debug(f"Created task for tool {tool_name}")
            
            # 6. 如果没有工具，提供直接响应
            if not result_templates and self.tool_selection_config.get("fallback_to_direct_response", True):
                self.logger.info("No tools selected, creating direct response template")
                
                direct_template = ModelContext(
                    sequence=template.sequence,
                    timestamp=template.timestamp,
                    uuid=template.uuid,
                    raw_question=template.raw_question,
                    tool_name="direct_response"
                )
                
                direct_template.prompts = [
                    {
                        "role": "system",
                        "content": f"Provide a direct response using general knowledge.\n\nQuery: {template.raw_question}\nAnalysis: {analysis}"
                    },
                    {"role": "user", "content": template.raw_question}
                ]
                
                result_templates.append(direct_template)
                self._update_tool_stats("direct_response")
            
            self.logger.info(f"ChiefBot generated {len(result_templates)} tasks")
            return result_templates
            
        except Exception as e:
            self.logger.error(f"ChiefBot execution failed: {e}", exc_info=True)
            
            # 返回错误处理的template
            error_template = ModelContext(
                sequence=template.sequence,
                timestamp=template.timestamp,
                uuid=template.uuid,
                raw_question=template.raw_question,
                tool_name="error_handler"
            )
            
            error_template.prompts = [
                {
                    "role": "system", 
                    "content": f"Error in task planning: {str(e)}. Provide a best-effort response."
                },
                {"role": "user", "content": template.raw_question}
            ]
            
            self._update_tool_stats("error_handler")
            return [error_template]

    # 其余方法保持不变...
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
        self.tool_selection_prompt = self._build_tool_selection_prompt()
        self.logger.info(f"Added new tool: {tool_name}")
    
    def remove_tool(self, tool_name: str):
        """动态移除工具"""
        if tool_name in self.available_tools:
            del self.available_tools[tool_name]
            del self.config["available_tools"][tool_name]
            self.tool_selection_prompt = self._build_tool_selection_prompt()
            self.logger.info(f"Removed tool: {tool_name}")
        else:
            self.logger.warning(f"Tool {tool_name} not found")