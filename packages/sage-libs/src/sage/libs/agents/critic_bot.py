import json
import re
from typing import Dict, Any, Tuple
from jinja2 import Template
from sage.core.api.function.map_function import MapFunction
from sage.libs.context.model_context import ModelContext
from sage.libs.context.quality_label import QualityLabel
from sage.libs.context.critic_evaluation import CriticEvaluation
from sage.libs.utils.openaiclient import OpenAIClient




# Critic评估的prompt模板
CRITIC_EVALUATION_PROMPT = '''You are a Critic Bot responsible for evaluating the quality and completeness of AI responses. Your task is to assess whether the AI system has adequately addressed the user's original question.

## Original User Question:
{{ raw_question }}

{%- if retriver_chunks and retriver_chunks|length > 0 %}
## Available Information Sources ({{ retriver_chunks|length }} sources):
{% for chunk in retriver_chunks %}
### Source {{ loop.index }}:
{{ chunk[:300] }}...
{% endfor %}
{%- else %}
## No Retrieved Information Available
{%- endif %}

{%- if response %}
## AI Response to Evaluate:
{{ response }}
{%- else %}
## No Response Generated Yet
{%- endif %}

## Evaluation Criteria:

### Quality Dimensions:
1. **Completeness**: Does the response fully address all aspects of the question?
2. **Accuracy**: Is the information provided correct and reliable?
3. **Relevance**: Is the response directly relevant to the user's question?
4. **Clarity**: Is the response clear, well-structured, and easy to understand?
5. **Depth**: Does the response provide sufficient detail and context?
6. **Coherence**: Is the response logically consistent and well-organized?

### Assessment Categories:
- **COMPLETE_EXCELLENT**: Perfect response, exceeds expectations
- **COMPLETE_GOOD**: Good response, meets user needs adequately
- **PARTIAL_NEEDS_IMPROVEMENT**: Addresses question but has significant gaps
- **INCOMPLETE_MISSING_INFO**: Missing critical information or context
- **FAILED_POOR_QUALITY**: Poor quality, major issues with accuracy/relevance
- **ERROR_INVALID**: Invalid, nonsensical, or error-filled response

## Your Task:
Evaluate the AI response against the original question and provide a detailed assessment.

## Response Format (JSON):
{
    "overall_assessment": "COMPLETE_EXCELLENT|COMPLETE_GOOD|PARTIAL_NEEDS_IMPROVEMENT|INCOMPLETE_MISSING_INFO|FAILED_POOR_QUALITY|ERROR_INVALID",
    "confidence": 0.85,
    "reasoning": "Detailed explanation of the evaluation",
    "quality_scores": {
        "completeness": 8.5,
        "accuracy": 9.0,
        "relevance": 8.0,
        "clarity": 7.5,
        "depth": 8.0,
        "coherence": 9.0
    },
    "specific_issues": [
        "Issue 1: Specific problem identified",
        "Issue 2: Another specific problem"
    ],
    "missing_elements": [
        "Missing element 1",
        "Missing element 2"
    ],
    "suggestions_for_improvement": [
        "Suggestion 1: Specific improvement recommendation",
        "Suggestion 2: Another improvement"
    ],
    "decision": {
        "should_return_to_chief": true/false,
        "ready_for_output": true/false,
        "priority_for_reprocessing": "high|medium|low"
    }
}

## Guidelines:
- Be objective and thorough in your evaluation
- Consider the complexity and scope of the original question
- Identify specific areas for improvement
- Provide actionable suggestions
- Score quality dimensions on a 1-10 scale
- Make clear decisions about next steps
'''

class CriticBot(MapFunction):
    """
    Critic Bot - 评估AI响应质量并决定下一步处理
    输入: ModelContext (包含完整的处理结果)
    输出: ModelContext - 带评估标签
    """
    
    def __init__(self, config: dict, quality_threshold: float = 7.0, 
                 strict_mode: bool = False, **kwargs):
        """
        初始化Critic Bot
        
        Args:
            config: LLM配置
            quality_threshold: 质量阈值，低于此值需要重新处理
            strict_mode: 严格模式，提高评估标准
        """
        super().__init__(**kwargs)
        
        self.config = config
        self.quality_threshold = quality_threshold
        self.strict_mode = strict_mode
        
        # 初始化LLM模型
        self.model = OpenAIClient(
            model_name=config["model_name"],
            base_url=config["base_url"],
            api_key=config["api_key"],
            seed=42  # 使用固定seed保证评估一致性
        )
        
        # 初始化prompt模板
        self.prompt_template = Template(CRITIC_EVALUATION_PROMPT)
        
        self.evaluation_count = 0
        
        # 质量标准映射
        self.quality_standards = {
            QualityLabel.COMPLETE_EXCELLENT: 9.0,
            QualityLabel.COMPLETE_GOOD: 7.5,
            QualityLabel.PARTIAL_NEEDS_IMPROVEMENT: 6.0,
            QualityLabel.INCOMPLETE_MISSING_INFO: 4.5,
            QualityLabel.FAILED_POOR_QUALITY: 3.0,
            QualityLabel.ERROR_INVALID: 1.0
        }
        
        self.logger.info(f"CriticBot initialized with threshold: {quality_threshold}, strict_mode: {strict_mode}")

    def _build_evaluation_prompt(self, template: ModelContext) -> list:
        """
        构建评估prompt
        
        Args:
            template: 要评估的ModelContext
            
        Returns:
            list: 构建好的prompts
        """
        # 准备模板数据
        template_data = {
            'raw_question': template.raw_question or "No question provided",
            'retriver_chunks': template.retriver_chunks or [],
            'response': template.response or "No response available"
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
                "content": "Please provide a comprehensive evaluation in JSON format."
            }
        ]
        
        return prompts

    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """
        解析LLM返回的评估结果
        
        Args:
            response: LLM响应字符串
            
        Returns:
            Dict: 解析后的评估结果
        """
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
        
        # 如果解析失败，返回默认的低质量评估
        self.logger.warning(f"Failed to parse evaluation response: {response}")
        return {
            "overall_assessment": "ERROR_INVALID",
            "confidence": 0.5,
            "reasoning": "Failed to parse evaluation response",
            "quality_scores": {
                "completeness": 1.0,
                "accuracy": 1.0,
                "relevance": 1.0,
                "clarity": 1.0,
                "depth": 1.0,
                "coherence": 1.0
            },
            "specific_issues": ["Evaluation parsing failed"],
            "missing_elements": ["Valid evaluation"],
            "suggestions_for_improvement": ["Retry evaluation process"],
            "decision": {
                "should_return_to_chief": True,
                "ready_for_output": False,
                "priority_for_reprocessing": "high"
            }
        }

    def _create_critic_evaluation(self, eval_data: Dict[str, Any]) -> CriticEvaluation:
        """
        从解析的数据创建CriticEvaluation对象
        
        Args:
            eval_data: 解析后的评估数据
            
        Returns:
            CriticEvaluation: 评估结果对象
        """
        # 解析质量标签
        assessment_str = eval_data.get("overall_assessment", "ERROR_INVALID")
        try:
            quality_label = QualityLabel(assessment_str.lower())
        except ValueError:
            quality_label = QualityLabel.ERROR_INVALID
        
        # 获取决策信息
        decision = eval_data.get("decision", {})
        
        # 计算平均质量分数
        quality_scores = eval_data.get("quality_scores", {})
        avg_score = sum(quality_scores.values()) / len(quality_scores) if quality_scores else 1.0
        
        # 应用严格模式调整
        if self.strict_mode:
            avg_score *= 0.8  # 在严格模式下降低分数
        
        # 创建评估结果
        evaluation = CriticEvaluation(
            label=quality_label,
            confidence=float(eval_data.get("confidence", 0.5)),
            reasoning=eval_data.get("reasoning", "No reasoning provided"),
            specific_issues=eval_data.get("specific_issues", []) + eval_data.get("missing_elements", []),
            suggestions=eval_data.get("suggestions_for_improvement", []),
            should_return_to_chief=decision.get("should_return_to_chief", True),
            ready_for_output=decision.get("ready_for_output", False)
        )
        
        # 基于质量阈值调整决策
        if avg_score < self.quality_threshold:
            evaluation.should_return_to_chief = True
            evaluation.ready_for_output = False
        
        return evaluation

    def _validate_template(self, template: ModelContext) -> bool:
        """
        验证ModelContext是否可以被评估
        
        Args:
            template: ModelContext对象
            
        Returns:
            bool: 是否可以评估
        """
        if not template.raw_question or not template.raw_question.strip():
            self.logger.warning("ModelContext missing raw_question")
            return False
        
        # 检查是否有任何形式的处理结果
        has_response = bool(template.response and template.response.strip())
        has_chunks = bool(template.retriver_chunks)
        
        if not has_response and not has_chunks:
            self.logger.warning("ModelContext has no content to evaluate")
            return False
        
        return True

    def _add_evaluation_metadata(self, template: ModelContext, evaluation: CriticEvaluation) -> None:
        """
        将评估元数据添加到template中
        
        Args:
            template: ModelContext对象
            evaluation: 评估结果
        """
        template.evaluation = evaluation
        # 创建评估元数据
        eval_metadata = {
            "critic_evaluation": {
                "label": evaluation.label.value,
                "confidence": evaluation.confidence,
                "reasoning": evaluation.reasoning,
                "issues_count": len(evaluation.specific_issues),
                "should_return_to_chief": evaluation.should_return_to_chief,
                "ready_for_output": evaluation.ready_for_output,
                "evaluation_timestamp": template.timestamp,
                "evaluator": "CriticBot"
            }
        }
        
        # 添加到prompts作为系统信息
        eval_prompt = {
            "role": "system",
            "content": f"Critic Bot Evaluation: {json.dumps(eval_metadata, indent=2)}"
        }
        
        if not template.prompts:
            template.prompts = []
        template.prompts.append(eval_prompt)

    def _log_evaluation_summary(self, template: ModelContext, evaluation: CriticEvaluation):
        """记录评估摘要"""
        self.logger.info(f"Critic evaluation #{self.evaluation_count}: "
                        f"Label={evaluation.label.value}, "
                        f"Confidence={evaluation.confidence:.2f}, "
                        f"Return_to_chief={evaluation.should_return_to_chief}, "
                        f"Ready_for_output={evaluation.ready_for_output}")
        
        if evaluation.specific_issues:
            self.logger.debug(f"Issues identified: {len(evaluation.specific_issues)}")
            for issue in evaluation.specific_issues[:3]:  # 只记录前3个问题
                self.logger.debug(f"  - {issue}")

    def execute(self, template: ModelContext) -> ModelContext:
        """
        执行质量评估
        
        Args:
            template: 包含完整处理结果的ModelContext
            
        Returns:
            Tuple[ModelContext, CriticEvaluation]: 带评估标签的template和评估结果
        """
        try:
            self.logger.debug(f"CriticBot evaluating template UUID: {template.uuid}")
            
            # 1. 验证输入
            if not self._validate_template(template):
                # 创建错误评估
                error_evaluation = CriticEvaluation(
                    label=QualityLabel.ERROR_INVALID,
                    confidence=1.0,
                    reasoning="Invalid template - missing required content",
                    specific_issues=["Template validation failed"],
                    suggestions=["Provide valid template with question and response"],
                    should_return_to_chief=True,
                    ready_for_output=False
                )
                # 6. 添加评估元数据到template
                self._add_evaluation_metadata(template, error_evaluation)
                
                # 7. 记录评估摘要
                self._log_evaluation_summary(template, error_evaluation)
                return template
            
            # 2. 构建评估prompt
            evaluation_prompts = self._build_evaluation_prompt(template)
            
            self.logger.debug(f"Built evaluation prompts with {len(evaluation_prompts)} messages")
            
            # 3. 调用LLM进行评估
            response = self.model.generate(evaluation_prompts)
            self.evaluation_count += 1
            
            self.logger.debug(f"LLM evaluation response: {response[:300]}...")
            
            # 4. 解析评估结果
            eval_data = self._parse_evaluation_response(response)
            
            # 5. 创建评估对象
            evaluation = self._create_critic_evaluation(eval_data)
            
            # 6. 添加评估元数据到template
            self._add_evaluation_metadata(template, evaluation)
            
            # 7. 记录评估摘要
            self._log_evaluation_summary(template, evaluation)
            
            return template
            
        except Exception as e:
            self.logger.error(f"CriticBot evaluation failed: {e}")
            
            # 创建错误评估
            error_evaluation = CriticEvaluation(
                label=QualityLabel.ERROR_INVALID,
                confidence=0.5,
                reasoning=f"Evaluation process failed: {str(e)}",
                specific_issues=[f"System error: {str(e)}"],
                suggestions=["Retry evaluation with fixed system"],
                should_return_to_chief=True,
                ready_for_output=False
            )
            
            return template

class EnhancedCriticBot(CriticBot):
    """
    增强版Critic Bot，支持更多评估维度和定制化
    """
    
    def __init__(self, config: dict, quality_threshold: float = 7.0,
                 strict_mode: bool = False,
                 domain_specific_criteria: Dict[str, list] = None,
                 enable_iterative_feedback: bool = True, **kwargs):
        super().__init__(config, quality_threshold, strict_mode, **kwargs)
        
        self.domain_specific_criteria = domain_specific_criteria or {}
        self.enable_iterative_feedback = enable_iterative_feedback
        
        # 跟踪评估历史
        self.evaluation_history = {}
        
        self.logger.info(f"EnhancedCriticBot initialized with iterative feedback: {enable_iterative_feedback}")

    def _analyze_improvement_over_iterations(self, template: ModelContext) -> Dict[str, Any]:
        """分析多轮迭代中的质量改善"""
        template_id = template.uuid
        
        if template_id not in self.evaluation_history:
            self.evaluation_history[template_id] = []
        
        # 这里可以添加更复杂的历史分析逻辑
        iteration_count = len(self.evaluation_history[template_id])
        
        return {
            "iteration_count": iteration_count,
            "is_repeat_processing": iteration_count > 0,
            "improvement_trend": "unknown"  # 可以基于历史评分计算趋势
        }

    def execute(self, template: ModelContext) -> Tuple[ModelContext, CriticEvaluation]:
        """增强版评估执行"""
        
        # 分析迭代历史
        if self.enable_iterative_feedback:
            iteration_analysis = self._analyze_improvement_over_iterations(template)
            self.logger.debug(f"Iteration analysis: {iteration_analysis}")
        
        # 执行标准评估
        result_template, evaluation = super().execute(template)
        
        # 记录评估历史
        if self.enable_iterative_feedback:
            template_id = template.uuid
            if template_id not in self.evaluation_history:
                self.evaluation_history[template_id] = []
            self.evaluation_history[template_id].append(evaluation)
        
        return result_template, evaluation