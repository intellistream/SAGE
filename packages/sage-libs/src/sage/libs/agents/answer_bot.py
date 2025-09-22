import os
from typing import List, Dict, Union
from jinja2 import Template

from sage.core.api.function.map_function import MapFunction
from sage.common.utils.logging.custom_logger import CustomLogger

from ..utils.OpenAIClient import OpenAIClient
from ..context.model_context import ModelContext

# 集成上下文的prompt模板
CONTEXT_INTEGRATED_PROMPT = '''You are an intelligent AI assistant with comprehensive access to multiple information sources. Your task is to provide a complete, accurate, and well-reasoned answer to the user's question using all available context and information.

## Available Information Sources:

{%- if retriever_chunks and retriever_chunks|length > 0 %}
### Retrieved Knowledge Base Content:
{% for chunk in retriever_chunks %}
**Source {{ loop.index }}:**
{{ chunk }}

{% endfor %}
{%- endif %}

{%- if previous_response %}
### Previous Response Context:
{{ previous_response }}

{%- endif %}

## Instructions:
1. **Analyze the user's original question carefully**
2. **Use ALL available information sources** - knowledge base content, previous responses, and your general knowledge
3. **Synthesize information** from multiple sources to provide a comprehensive answer
4. **Be specific and cite information** when drawing from the retrieved content
5. **If information conflicts**, explain the differences and provide your best assessment
6. **If information is insufficient**, clearly state what is missing and provide the best answer possible with available data
7. **Maintain a helpful, professional tone**

## Response Format:
- Provide a clear, direct answer to the question
- Include relevant details and context
- If using retrieved information, reference it naturally in your response
- Conclude with any important caveats or additional considerations

Now, please answer the user's question using all available context and information.'''

class AnswerBot(MapFunction):
    """
    集成上下文的AnswerBot - 使用ModelContext中的所有信息源来生成完整回答
    包括raw_question、retriever_chunks、previous_response等所有上下文
    """

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        
        self.config = config
        
        # 初始化OpenAI客户端
        self.model = OpenAIClient(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config.get("api_key", None) or os.getenv("ALIBABA_API_KEY"),
            seed=42
        )
        
        # 初始化prompt模板
        self.prompt_template = Template(CONTEXT_INTEGRATED_PROMPT)
        
        self.response_count = 0
        
        self.logger.info("AnswerBot initialized - ready to process comprehensive context")

    def _build_comprehensive_prompts(self, template: ModelContext) -> List[Dict[str, str]]:
        """
        基于ModelContext的所有上下文构建comprehensive prompts
        
        Args:
            template: ModelContext对象，包含所有上下文信息
            
        Returns:
            List[Dict[str, str]]: 构建好的prompts列表
        """
        # 收集所有可用的上下文信息
        # 优先使用search_session的内容，fallback到retriver_chunks
        retriever_content = []
        if template.search_session and template.search_session.query_results:
            # 使用新的分层搜索结构
            for query_result in template.search_session.query_results:
                for result in query_result.results:
                    formatted_result = f"[{result.title}]\n{result.content}\nSource: {result.source}"
                    retriever_content.append(formatted_result)
        elif template.retriver_chunks:
            # fallback到旧的retriver_chunks
            retriever_content = template.retriver_chunks
        
        context_data = {
            'retriever_chunks': retriever_content,
            'previous_response': template.response or None
        }
        
        # 使用模板渲染system prompt
        system_content = self.prompt_template.render(**context_data)
        
        # 构建完整的prompts
        prompts = [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user", 
                "content": f"Question: {template.raw_question}"
            }
        ]
        
        # 如果有之前的回答，加入对话历史
        if template.response:
            prompts.insert(-1, {
                "role": "assistant",
                "content": f"Previous response: {template.response}"
            })
            prompts.append({
                "role": "user",
                "content": "Please provide an updated or more comprehensive answer considering all available information."
            })
        
        return prompts

    def _validate_template(self, template: ModelContext) -> bool:
        """
        验证ModelContext是否包含必要的信息
        
        Args:
            template: ModelContext对象
            
        Returns:
            bool: 是否有效
        """
        if not template.raw_question or not template.raw_question.strip():
            self.logger.warning("ModelContext missing raw_question")
            return False
        
        return True

    def _log_context_summary(self, template: ModelContext) -> None:
        """
        记录上下文信息摘要，用于调试
        """
        chunks_count = len(template.retriver_chunks) if template.retriver_chunks else 0
        has_previous = bool(template.response)
        
        self.logger.debug(f"Processing context: "
                         f"Question='{template.raw_question[:50]}...', "
                         f"Retriever_chunks={chunks_count}, "
                         f"Previous_response={has_previous}")

    def execute(self, template: ModelContext) -> ModelContext:
        """
        执行完整的上下文集成回答生成
        
        Args:
            template: ModelContext对象，包含所有上下文信息
            
        Returns:
            ModelContext: 更新了response的ModelContext对象
        """
        try:
            self.logger.debug(f"AnswerBot processing template UUID: {template.uuid}")
            
            # 1. 验证输入
            if not self._validate_template(template):
                template.response = "Error: Invalid input template - missing required raw_question"
                return template
            
            # 2. 记录上下文摘要
            self._log_context_summary(template)
            
            # 3. 构建comprehensive prompts（替换template中的prompts字段）
            comprehensive_prompts = self._build_comprehensive_prompts(template)
            
            self.logger.debug(f"Built comprehensive prompts with {len(comprehensive_prompts)} messages")
            
            # 4. 调用API生成响应
            response = self.model.generate(comprehensive_prompts)
            self.response_count += 1
            
            # 5. 更新template
            # 注意：我们不使用template.prompts字段，而是重新构建
            template.response = response
            
            # 6. 记录结果
            self.logger.info(f"Generated comprehensive response #{self.response_count}")
            self.logger.debug(f"Response preview: {response[:200]}...")
            
            return template
            
        except Exception as e:
            self.logger.error(f"AnswerBot execution failed: {e}")
            
            # 设置错误响应
            template.response = f"Error occurred during comprehensive answer generation: {str(e)}"
            
            return template

class EnhancedContextAnswerBot(AnswerBot):
    """
    增强版本的ContextAnswerBot，支持更多定制化选项
    """
    
    def __init__(self, config, include_metadata=True, max_chunks=10, **kwargs):
        super().__init__(config, **kwargs)
        
        self.include_metadata = include_metadata
        self.max_chunks = max_chunks
        
        # 增强的prompt模板
        self.enhanced_prompt_template = Template('''
You are an advanced AI assistant with access to comprehensive information sources. 

## User's Original Question:
{{ raw_question }}

{%- if retriever_chunks and retriever_chunks|length > 0 %}

## Retrieved Knowledge Base ({{ retriever_chunks|length }} sources):
{% for chunk in retriever_chunks[:max_chunks] %}
### Source {{ loop.index }}:
{{ chunk }}
{% if not loop.last %}

{% endif %}
{% endfor %}
{%- if retriever_chunks|length > max_chunks %}
... and {{ retriever_chunks|length - max_chunks }} more sources available
{%- endif %}
{%- endif %}

{%- if previous_response %}

## Previous Analysis:
{{ previous_response }}
{%- endif %}

{%- if include_metadata %}

## Processing Context:
- Query processed at: {{ timestamp }}
- Unique identifier: {{ uuid }}
- Information sources: {{ source_count }}
{%- endif %}

## Your Task:
Provide a comprehensive, well-structured answer that:
1. Directly addresses the user's question
2. Integrates information from all available sources
3. Highlights the most relevant and reliable information
4. Identifies any gaps or limitations in the available data
5. Provides actionable insights where appropriate

Please ensure your response is clear, accurate, and helpful.
        ''')

    def _build_enhanced_prompts(self, template: ModelContext) -> List[Dict[str, str]]:
        """构建增强版的prompts"""
        
        # 优先使用search_session的内容，fallback到retriver_chunks
        retriever_content = []
        if template.search_session and template.search_session.query_results:
            # 使用新的分层搜索结构
            for query_result in template.search_session.query_results:
                for result in query_result.results:
                    formatted_result = f"[{result.title}]\n{result.content}\nSource: {result.source}"
                    retriever_content.append(formatted_result)
        elif template.retriver_chunks:
            # fallback到旧的retriver_chunks
            retriever_content = template.retriver_chunks
        
        # 计算信息源数量
        source_count = len(retriever_content)
        if template.response:
            source_count += 1
        
        # 准备模板数据
        template_data = {
            'raw_question': template.raw_question,
            'retriever_chunks': retriever_content,
            'previous_response': template.response,
            'timestamp': template.timestamp,
            'uuid': template.uuid,
            'max_chunks': self.max_chunks,
            'source_count': source_count,
            'include_metadata': self.include_metadata
        }
        
        # 渲染system prompt
        system_content = self.enhanced_prompt_template.render(**template_data)
        
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Please provide your comprehensive analysis and answer."}
        ]

    def execute(self, template: ModelContext) -> ModelContext:
        """执行增强版的上下文集成回答"""
        try:
            if not self._validate_template(template):
                template.response = "Error: Invalid input template"
                return template
            
            # 使用增强版的prompt构建
            enhanced_prompts = self._build_enhanced_prompts(template)
            
            # 生成响应
            response = self.model.generate(enhanced_prompts)
            template.response = response
            
            self.response_count += 1
            self.logger.info(f"Enhanced response #{self.response_count} generated")
            
            return template
            
        except Exception as e:
            self.logger.error(f"EnhancedContextAnswerBot failed: {e}")
            template.response = f"Enhanced processing error: {str(e)}"
            return template