import random
import time, os
from typing import List, Dict, Any
from jinja2 import Template
from sage.core.api.function.map_function import MapFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.libs.utils.openaiclient import OpenAIClient
from sage.libs.context.model_context import ModelContext

# 问题生成的prompt模板
QUESTION_GENERATION_PROMPT = '''You are a Question Generator that creates diverse, realistic user questions for testing AI systems. Your task is to generate {{ num_questions }} random questions that represent real-world user scenarios.

## Generation Requirements:

### Diversity Categories (randomly select from):
1. **Information Seeking**: Factual questions, explanations, how-to queries
2. **Problem Solving**: Technical issues, troubleshooting, decision making
3. **Creative Tasks**: Writing requests, brainstorming, design ideas
4. **Analysis & Opinion**: Compare, evaluate, pros/cons, recommendations
5. **Learning & Education**: Explain concepts, step-by-step tutorials
6. **Daily Life**: Practical questions, lifestyle, health, finance
7. **Professional**: Work-related, business, career advice
8. **Technology**: Software, hardware, programming, digital tools
9. **Entertainment**: Movies, books, games, hobbies, travel
10. **Current Events**: News, trends, recent developments

### Complexity Levels (mix randomly):
- **Simple**: Short, direct questions (5-15 words)
- **Medium**: Moderate complexity with some context (15-40 words)  
- **Complex**: Detailed scenarios with multiple parts (40-100+ words)

### Length Variations:
- **Short**: Quick, concise questions
- **Medium**: Questions with some background context
- **Long**: Detailed scenarios with multiple requirements

### Question Styles (vary randomly):
- Direct questions: "What is...?", "How do I...?", "Why does...?"
- Scenario-based: "I'm trying to... can you help?"
- Comparative: "What's the difference between...?"
- Open-ended: "Tell me about...", "Explain..."
- Specific requests: "Create a...", "Write a...", "Design a..."

## Response Format:
Generate exactly {{ num_questions }} questions, each on a new line, numbered 1-{{ num_questions }}.

Example format:
1. How do I reset my WiFi router?
2. I'm planning a wedding for 150 guests in autumn and need help creating a budget that includes venue, catering, flowers, and entertainment. What are the typical costs and how can I save money without compromising quality?
3. What's the best programming language to learn first?

## Guidelines:
- Make questions feel natural and realistic
- Vary complexity and length significantly
- Cover different domains and use cases
- Include both personal and professional scenarios
- Some questions should be answerable quickly, others need research
- Mix formal and casual language styles
- Include questions that might require multiple steps to answer
'''

class QuestionBot(MapFunction):
    """
    问题生成Bot - 生成多样化的用户问题场景
    输入: 任意数据（通常是触发信号）
    输出: ModelContext (包含生成的随机问题)
    """
    
    def __init__(self, config: dict, questions_per_batch: int = 5, 
                 complexity_weights: Dict[str, float] = None, **kwargs):
        """
        初始化QuestionBot
        
        Args:
            config: LLM配置
            questions_per_batch: 每批生成的问题数量
            complexity_weights: 复杂度权重分布 {"simple": 0.3, "medium": 0.5, "complex": 0.2}
        """
        super().__init__(**kwargs)
        
        self.config = config
        self.questions_per_batch = questions_per_batch
        
        # 默认复杂度权重
        self.complexity_weights = complexity_weights or {
            "simple": 0.3,
            "medium": 0.5, 
            "complex": 0.2
        }
        
        # 初始化LLM模型
        self.model = OpenAIClient(
            method=config.get("method","openai"),
            model_name=config.get("model_name","qwen-turbo"),
            base_url=config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            api_key=config.get("api_key", os.environ.get("ALIBABA_API_KEY", "")),
            seed=config.get("seed", None)  # 不固定seed以增加随机性
        )

        
        # 初始化prompt模板
        self.prompt_template = Template(QUESTION_GENERATION_PROMPT)
        
        self.generation_count = 0
        
        # 预定义的问题类别和模板（用于增加多样性）
        self.question_categories = {
            "information": [
                "What is", "How does", "Why do", "When did", "Where can I find",
                "Explain", "Tell me about", "What are the benefits of"
            ],
            "problem_solving": [
                "How do I fix", "I'm having trouble with", "What should I do when",
                "Help me solve", "I need to troubleshoot", "What's wrong with"
            ],
            "creative": [
                "Write a", "Create a", "Design a", "Generate ideas for",
                "Help me brainstorm", "Come up with", "Develop a concept for"
            ],
            "comparison": [
                "What's the difference between", "Compare", "Which is better",
                "Pros and cons of", "Should I choose", "What are alternatives to"
            ],
            "learning": [
                "Teach me", "Explain step by step", "How to learn", "What's the best way to",
                "Guide me through", "Show me how to", "What do I need to know about"
            ]
        }
        
        self.logger.info(f"QuestionBot initialized - generating {questions_per_batch} questions per batch")

    def _build_generation_prompt(self, num_questions: int) -> List[Dict[str, str]]:
        """
        构建问题生成的prompt
        
        Args:
            num_questions: 要生成的问题数量
            
        Returns:
            List[Dict[str, str]]: 构建好的prompts
        """
        # 准备模板数据
        template_data = {
            'num_questions': num_questions
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
                "content": f"Generate {num_questions} diverse, realistic user questions following the guidelines above."
            }
        ]
        
        return prompts

    def _parse_generated_questions(self, response: str) -> List[str]:
        """
        解析LLM生成的问题列表
        
        Args:
            response: LLM响应字符串
            
        Returns:
            List[str]: 解析出的问题列表
        """
        questions = []
        
        # 按行分割并处理
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 移除编号（如 "1. ", "2) ", "Question 1:", 等）
            # 使用正则表达式匹配各种编号格式
            import re
            clean_line = re.sub(r'^\d+[\.\)\:]?\s*', '', line)
            clean_line = re.sub(r'^Question\s+\d+[\.\)\:]?\s*', '', clean_line, flags=re.IGNORECASE)
            
            if clean_line and len(clean_line) > 5:  # 过滤太短的内容
                questions.append(clean_line)
        
        return questions

    def _add_manual_variations(self) -> str:
        """
        手动添加一些预定义的问题变体以增加多样性
        
        Returns:
            str: 随机选择的问题
        """
        # 随机选择类别和模板
        category = random.choice(list(self.question_categories.keys()))
        template = random.choice(self.question_categories[category])
        
        # 随机主题词汇
        topics = [
            "artificial intelligence", "climate change", "space exploration", "cryptocurrency",
            "renewable energy", "mental health", "social media", "remote work",
            "electric vehicles", "virtual reality", "blockchain", "quantum computing",
            "sustainable living", "digital privacy", "online education", "e-commerce",
            "cybersecurity", "biotechnology", "smart home", "machine learning",
            "3D printing", "solar panels", "investment strategies", "healthy eating",
            "time management", "career development", "travel planning", "photography",
            "cooking techniques", "fitness routines", "meditation", "gardening"
        ]
        
        topic = random.choice(topics)
        
        # 组合生成问题
        if category == "information":
            return f"{template} {topic}?"
        elif category == "problem_solving":
            return f"{template} my {topic} setup?"
        elif category == "creative":
            return f"{template} presentation about {topic}."
        elif category == "comparison":
            return f"{template} {topic} and traditional alternatives?"
        elif category == "learning":
            return f"{template} {topic} for beginners?"
        
        return f"Tell me about {topic}."

    def _ensure_question_diversity(self, questions: List[str]) -> List[str]:
        """
        确保问题的多样性，添加长度和复杂度变化
        
        Args:
            questions: 原始问题列表
            
        Returns:
            List[str]: 调整后的问题列表
        """
        enhanced_questions = []
        
        for i, question in enumerate(questions):
            # 随机决定是否增强这个问题
            enhancement_chance = random.random()
            
            if enhancement_chance < 0.3:  # 30%的机会添加背景信息
                contexts = [
                    f"I'm a beginner and {question.lower()}",
                    f"For my work project, {question.lower()}",
                    f"I've been wondering: {question}",
                    f"My friend asked me: {question}",
                    f"As a student, I need to know: {question}",
                    f"For my presentation, {question}"
                ]
                enhanced_questions.append(random.choice(contexts))
            
            elif enhancement_chance < 0.6:  # 30%的机会保持原样
                enhanced_questions.append(question)
            
            else:  # 40%的机会简化问题
                # 简化：移除额外的词汇，保持核心
                simplified = question.replace("Can you please", "").replace("Could you", "")
                simplified = simplified.replace("I would like to know", "").strip()
                enhanced_questions.append(simplified)
        
        return enhanced_questions

    def _create_ModelContext_from_question(self, question: str) -> ModelContext:
        """
        从问题创建ModelContext
        
        Args:
            question: 生成的问题
            
        Returns:
            ModelContext: 包含问题的模板
        """
        template = ModelContext(
            sequence=self.generation_count,
            raw_question=question
        )
        
        # 添加一些元数据到prompts（可选）
        metadata_prompt = {
            "role": "system",
            "content": f"This is a randomly generated user question for testing. "
                      f"Question category: {'mixed'}, "
                      f"Generation batch: {self.generation_count}"
        }
        
        template.prompts = [metadata_prompt]
        
        return template

    def _validate_and_select_question(self, questions: List[str]) -> str:
        """
        验证并选择一个最佳问题
        
        Args:
            questions: 候选问题列表
            
        Returns:
            str: 选择的问题
        """
        if not questions:
            # 如果没有生成问题，使用备用问题
            return self._add_manual_variations()
        
        # 过滤掉太短或太长的问题
        valid_questions = [q for q in questions if 5 <= len(q.split()) <= 100]
        
        if not valid_questions:
            return self._add_manual_variations()
        
        # 随机选择一个问题
        return random.choice(valid_questions)

    def execute(self, trigger_data: Any = None) -> ModelContext:
        """
        执行问题生成
        
        Args:
            trigger_data: 触发数据（通常被忽略）
            
        Returns:
            ModelContext: 包含生成问题的模板
        """
        try:
            self.logger.debug(f"QuestionBot generating question #{self.generation_count + 1}")
            
            # 1. 决定生成多少个候选问题
            num_candidates = max(1, self.questions_per_batch)
            
            # 2. 构建生成prompt
            generation_prompts = self._build_generation_prompt(num_candidates)
            
            # 3. 调用LLM生成问题
            response = self.model.generate(generation_prompts)
            self.generation_count += 1
            
            self.logger.debug(f"LLM question generation response: {response[:200]}...")
            
            # 4. 解析生成的问题
            generated_questions = self._parse_generated_questions(response)
            
            # 5. 增强问题多样性
            enhanced_questions = self._ensure_question_diversity(generated_questions)
            
            # 6. 选择最终问题
            final_question = self._validate_and_select_question(enhanced_questions)
            
            # 7. 创建ModelContext
            result_template = self._create_ModelContext_from_question(final_question)
            
            self.logger.info(f"Generated question #{self.generation_count}: '{final_question[:50]}...'")
            
            return result_template
            
        except Exception as e:
            self.logger.error(f"QuestionBot generation failed: {e}")
            
            # 错误处理：生成一个简单的备用问题
            fallback_question = self._add_manual_variations()
            error_template = self._create_ModelContext_from_question(fallback_question)
            
            # 在prompts中记录错误信息
            error_prompt = {
                "role": "system",
                "content": f"Fallback question due to generation error: {str(e)}"
            }
            error_template.prompts.append(error_prompt)
            
            return error_template

class EnhancedQuestionBot(QuestionBot):
    """
    增强版问题生成Bot，支持更多定制化功能
    """
    
    def __init__(self, config: dict, questions_per_batch: int = 5,
                 domain_focus: List[str] = None,
                 language_styles: List[str] = None,
                 include_multilingual: bool = False, **kwargs):
        super().__init__(config, questions_per_batch, **kwargs)
        
        self.domain_focus = domain_focus or []
        self.language_styles = language_styles or ["casual", "formal", "technical"]
        self.include_multilingual = include_multilingual
        
        # 扩展的主题域
        self.domain_specific_topics = {
            "technology": ["AI", "blockchain", "cloud computing", "IoT", "cybersecurity"],
            "business": ["marketing", "finance", "management", "entrepreneurship", "strategy"],
            "health": ["nutrition", "fitness", "mental health", "medicine", "wellness"],
            "education": ["online learning", "study techniques", "career guidance", "skills"],
            "lifestyle": ["travel", "cooking", "hobbies", "relationships", "home improvement"]
        }
        
        self.logger.info(f"EnhancedQuestionBot initialized with domain focus: {domain_focus}")

    def _generate_domain_specific_question(self) -> str:
        """生成特定领域的问题"""
        if not self.domain_focus:
            return self._add_manual_variations()
        
        domain = random.choice(self.domain_focus)
        topics = self.domain_specific_topics.get(domain, ["general topics"])
        topic = random.choice(topics)
        
        templates = [
            f"How can I improve my {topic} skills?",
            f"What are the latest trends in {topic}?",
            f"I'm having issues with {topic}, can you help?",
            f"Explain the basics of {topic} for beginners.",
            f"Compare different approaches to {topic}.",
            f"What tools are best for {topic}?"
        ]
        
        return random.choice(templates)

    def execute(self, trigger_data: Any = None) -> ModelContext:
        """增强版执行逻辑"""
        
        # 30%的机会使用领域特定生成
        if self.domain_focus and random.random() < 0.3:
            domain_question = self._generate_domain_specific_question()
            return self._create_ModelContext_from_question(domain_question)
        
        # 否则使用标准生成
        return super().execute(trigger_data)
    

'''
# config/question_bot.yaml
utils:
  method: "openai"
  model_name: "gpt-3.5-turbo"
  base_url: "https://api.openai.com/v1"
  api_key: "${OPENAI_API_KEY}"

question_generation:
  questions_per_batch: 3
  domain_focus: 
    - "technology"
    - "health" 
    - "education"
    - "business"
  language_styles:
    - "casual"
    - "formal"
    - "technical"
  complexity_weights:
    simple: 0.4
    medium: 0.4
    complex: 0.2

timer_source:
  interval: 15  # 每15秒生成一个问题

sink:
  prefix: "QuestionBot"


'''