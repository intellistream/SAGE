import json
import os
import time

from jinja2 import Template

from sage.common.core.functions import MapFunction as MapOperator

QA_prompt_template_str = """Instruction:
You are an intelligent assistant with access to a knowledge base. Answer the question below with reference to the provided context.
Only give me the answer and do not output any other words.
{%- if external_corpus %}
Relevant corpus for the current question:
{{ external_corpus }}
{%- endif %}
"""

QA_short_answer_template_str = """Instruction:
You are an intelligent assistant with access to a knowledge base. Answer the question below with reference to the provided context.
Please provide a concise answer and conclude with 'So the final answer is: [your answer]'.
{%- if external_corpus %}
Relevant corpus for the current question:
{{ external_corpus }}
{%- endif %}
"""

summarization_prompt_template_str = """Instruction:
You are an intelligent assistant. Summarize the content provided below in a concise and clear manner.
Only provide the summary and do not include any additional information.
{%- if external_corpus %}
Content to summarize:
{{ external_corpus }}
{%- endif %}
"""
QA_prompt_template = Template(QA_prompt_template_str)
QA_short_answer_template = Template(QA_short_answer_template_str)
summarization_prompt_template = Template(summarization_prompt_template_str)

query_profiler_prompt_template_str = """
For the given query = how Trump earn his first 1 million dollars?: Analyze the language and internal structure of the query and provide the following information:

1. Does it need joint reasoning across multiple documents?
2. Provide a complexity profile for the query:
   - Complexity: High / Low
   - Joint Reasoning needed: Yes / No
3. Does this query need input chunks to be summarized? If yes, provide a range in words for the summarized chunks.
4. How many distinct pieces of information are needed to answer the query?

database_metadata = The dataset consists of multiple chunks of information from Fortune 500 companies on financial reports from every quarter of 2023.
chunk_size = 1024

Estimate the query profile along with the database_metadata and chunk_size.

Your output must be:
- **Only a valid JSON object**
- **No explanations, no formatting, no comments**
- **No markdown code blocks or prose**
- **Strictly conform to this schema:**

{
  "need_joint_reasoning": <true|false>,
  "complexity": "High" or "Low",
  "need_summarization": <true|false>,
  "summarization_length": integer (30-200),
  "n_info_items": integer (1-6)
}
"""
query_profiler_prompt_template = Template(query_profiler_prompt_template_str)


class QAPromptor(MapOperator):
    """
    QAPromptor is a prompt rag that generates a QA-style prompt using
    an external corpus and a user query. This class is designed to prepare
    the necessary prompt structure for a question-answering model.

    Attributes:
        config: Configuration data for initializing the prompt rag (e.g., model details, etc.).
        prompt_template: A template used for generating the system prompt, typically includes context or instructions.
    """

    prompt_template: Template

    def __init__(self, config, enable_profile=False, **kwargs):
        super().__init__(**kwargs)

        """
        Initializes the QAPromptor instance with configuration and prompt template.

        :param config: Dictionary containing configuration for the prompt rag.
        """
        self.config = config  # Store the configuration for later use
        self.enable_profile = enable_profile

        # 使用配置文件中的模板，如果没有则使用默认模板
        self.use_short_answer = config.get("use_short_answer", False)  # 是否使用短答案模式

        if "template" in config:
            from jinja2 import Template

            self.prompt_template = Template(config["template"])
        else:
            # 根据配置选择模板
            if self.use_short_answer:
                self.prompt_template = QA_short_answer_template
            else:
                self.prompt_template = QA_prompt_template  # Load the QA prompt template

        # 只有启用profile时才设置数据存储路径
        if self.enable_profile:
            from sage.common.config.output_paths import get_sage_paths

            try:
                sage_paths = get_sage_paths()
                self.data_base_path = str(sage_paths.states_dir / "promptor_data")
            except Exception:
                # Fallback to current working directory
                if (
                    self.ctx is not None
                    and hasattr(self.ctx, "env_base_dir")
                    and self.ctx.env_base_dir
                ):
                    self.data_base_path = os.path.join(
                        self.ctx.env_base_dir, ".sage_states", "promptor_data"
                    )
                else:
                    # 使用默认路径
                    self.data_base_path = os.path.join(os.getcwd(), ".sage_states", "promptor_data")

            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

    def _save_data_record(self, query, external_corpus, prompt):
        """保存提示词数据记录"""
        if not self.enable_profile:
            return

        record = {
            "timestamp": time.time(),
            "query": query,
            "external_corpus": external_corpus,
            "prompt": prompt,
        }
        self.data_records.append(record)
        self._persist_data_records()

    def _persist_data_records(self):
        """将数据记录持久化到文件"""
        if not self.enable_profile or not self.data_records:
            return

        timestamp = int(time.time())
        filename = f"promptor_data_{timestamp}.json"
        path = os.path.join(self.data_base_path, filename)

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    # sage_lib/functions/rag/qapromptor.py
    def execute(self, data) -> list:
        """
        生成 ChatGPT 风格的 prompt（system+user 两条消息）。

        支持多种输入格式：
        1. (query, external_corpus_list_or_str)  # 元组格式
        2. query_str  # 纯字符串
        3. {"query": ..., "results": [...]}  # 字典格式（来自检索器）
        4. {"question": ..., "context": [...]}  # 字典格式（来自测试）
        """
        self.logger.info(f"QAPromptor received data: {data}")
        try:
            # -------- 解析输入 --------
            raw = data
            original_data = data  # 保存原始数据以便返回

            if isinstance(raw, dict):
                # 字典格式输入 - 支持多种字段名
                query = raw.get("query", raw.get("question", ""))

                # 处理不同的上下文字段名
                external_corpus_list = []

                # 处理 refining_results 字段（来自 refiner - 压缩后的文档）
                if "refining_results" in raw:
                    results = raw.get("refining_results", [])
                    for result in results:
                        if isinstance(result, str):
                            external_corpus_list.append(result)
                        else:
                            external_corpus_list.append(str(result))

                # 处理 retrieval_results 字段（来自 retriever - 原始检索结果）
                elif "retrieval_results" in raw:
                    results = raw.get("retrieval_results", [])
                    for result in results:
                        if isinstance(result, dict) and "text" in result:
                            external_corpus_list.append(result["text"])
                        elif isinstance(result, str):
                            external_corpus_list.append(result)
                        else:
                            external_corpus_list.append(str(result))

                # 处理 context 字段（来自测试）
                elif "context" in raw:
                    context = raw.get("context", [])
                    if isinstance(context, list):
                        external_corpus_list.extend([str(c) for c in context])
                    else:
                        external_corpus_list.append(str(context))

                # 处理 external_corpus 字段
                elif "external_corpus" in raw:
                    external_corpus = raw.get("external_corpus", "")
                    if isinstance(external_corpus, list):
                        external_corpus_list.extend([str(c) for c in external_corpus])
                    else:
                        external_corpus_list.append(str(external_corpus))

                external_corpus = "\n".join(external_corpus_list)

            elif isinstance(raw, tuple) and len(raw) == 2:
                # 元组格式输入
                query, external_corpus = raw
                if isinstance(external_corpus, list):
                    external_corpus = "\n".join(external_corpus)
                # 对于元组输入，保持原有行为，返回query而不是原始数据
                original_data = query
            else:
                # 字符串格式输入
                query = str(raw)
                external_corpus = ""
                # 对于字符串输入，保持原有行为，返回query而不是原始数据
                original_data = query

            external_corpus = external_corpus or ""

            # -------- system prompt --------
            if external_corpus:
                system_prompt = {
                    "role": "system",
                    "content": self.prompt_template.render(external_corpus=external_corpus),
                }
            else:
                system_prompt = {
                    "role": "system",
                    "content": (
                        "You are a helpful AI assistant. Answer the user's questions accurately."
                    ),
                }

            # -------- user prompt --------
            user_prompt = {
                "role": "user",
                "content": f"Question: {query}",
            }
            self.logger.info(
                f"QAPromptor generated prompt: {system_prompt['content']} | {user_prompt['content']}"
            )
            prompt = [system_prompt, user_prompt]

            # 保存数据记录（只有enable_profile=True时才保存）
            if self.enable_profile:
                self._save_data_record(query, external_corpus, prompt)

            return [original_data, prompt]

        except Exception as e:
            self.logger.error("QAPromptor error: %s | input=%s", e, getattr(data, "data", ""))
            fallback = [
                {"role": "system", "content": "System encountered an error."},
                {
                    "role": "user",
                    "content": (
                        "Question: Error occurred. Please try again."
                        f" (Original: {getattr(data, 'data', '')})"
                    ),
                },
            ]
            return fallback

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_data_records()
            except Exception:
                pass


class SummarizationPromptor(MapOperator):
    """
    QAPromptor is a prompt rag that generates a QA-style prompt using
    an external corpus and a user query. This class is designed to prepare
    the necessary prompt structure for a question-answering model.

    Attributes:
        config: Configuration data for initializing the prompt rag (e.g., model details, etc.).
        prompt_template: A template used for generating the system prompt, typically includes context or instructions.
    """

    prompt_template: Template

    def __init__(self, config):
        """
        Initializes the QAPromptor instance with configuration and prompt template.

        :param config: Dictionary containing configuration for the prompt rag.
        """
        super().__init__()
        self.config = config  # Store the configuration for later use
        self.prompt_template = (
            summarization_prompt_template  # Load the summarization prompt template
        )

    def execute(self, data) -> list:
        """
        Generates a QA-style prompt for the input question and external corpus.

        This method takes the query and external corpus, processes the corpus
        into a single string, and creates a system prompt and user prompt based
        on a predefined template.

        :param data: A Data object containing a tuple. The first element is the query (a string),
                     and the second is a list of external corpus (contextual information for the model).

        :return: A Data object containing a list with two prompts:
                 1. system_prompt: A system prompt based on the template with external corpus data.
                 2. user_prompt: A user prompt containing the question to be answered.
        """
        # Unpack the input data into query and external_corpus
        query, external_corpus = data

        # Combine the external corpus list into a single string (in case it's split into multiple parts)
        external_corpus = "".join(external_corpus)

        # Prepare the base data for the system prompt, which includes the external corpus
        base_system_prompt_data = {"external_corpus": external_corpus}

        # query = data
        # Create the system prompt using the template and the external corpus data
        system_prompt = {
            "role": "system",
            "content": self.prompt_template.render(**base_system_prompt_data),
        }
        # system_prompt = {
        #     "role": "system",
        #     "content": ""
        # }
        # Create the user prompt using the query
        user_prompt = {"role": "user", "content": f"Question: {query}"}

        # Combine the system and user prompts into one list
        prompt = [system_prompt, user_prompt]

        # Return the prompt list wrapped in a Data object
        return prompt


class QueryProfilerPromptor(MapOperator):
    """
    QueryProfilerPromptor provides a prompt for profiling queries.

    """

    prompt_template: Template

    def __init__(self, config):
        """
        Initializes the QueryProfilerPromptor instance with configuration and prompt template.

        :param config: Dictionary containing configuration for the prompt rag.
        """
        super().__init__()
        self.config = config  # Store the configuration for later use
        self.prompt_template = (
            query_profiler_prompt_template  # Load the query profiler prompt template
        )

    def execute(self, data) -> list:
        """
        Generates a profiling prompt for the input query.

        :param data: A string representing the query to be profiled.

        :return: A list containing the profiling prompt.
        """
        query = data
        prompt = {
            "role": "user",
            "content": self.prompt_template.render(
                query=query,
                metadata=self.config.get("metadata", {}),
                chunk_size=self.config.get("chunk_size", 1024),
            ),
        }
        return [prompt]


# ============================================================================
# LongBench Promptor - 用于 LongBench 基准测试
# ============================================================================

# LongBench 数据集专用 prompt 模板（来自官方 dataset2prompt.json）
LONGBENCH_PROMPT_TEMPLATES: dict[str, str] = {
    "narrativeqa": "You are given a story, which can be either a novel or a movie script, and a question. Answer the question asconcisely as you can, using a single phrase if possible. Do not provide any explanation.\n\nStory: {context}\n\nNow, answer the question based on the story asconcisely as you can, using a single phrase if possible. Do not provide any explanation.\n\nQuestion: {input}\n\nAnswer:",
    "qasper": 'You are given a scientific article and a question. Answer the question as concisely as you can, using a single phrase or sentence if possible. If the question cannot be answered based on the information in the article, write "unanswerable". If the question is a yes/no question, answer "yes", "no", or "unanswerable". Do not provide any explanation.\n\nArticle: {context}\n\n Answer the question based on the above article as concisely as you can, using a single phrase or sentence if possible. If the question cannot be answered based on the information in the article, write "unanswerable". If the question is a yes/no question, answer "yes", "no", or "unanswerable". Do not provide any explanation.\n\nQuestion: {input}\n\nAnswer:',
    "multifieldqa_en": "Read the following text and answer briefly.\n\n{context}\n\nNow, answer the following question based on the above text, only give me the answer and do not output any other words.\n\nQuestion: {input}\nAnswer:",
    "multifieldqa_zh": "阅读以下文字并用中文简短回答：\n\n{context}\n\n现在请基于上面的文章回答下面的问题，只告诉我答案，不要输出任何其他字词。\n\n问题：{input}\n回答：",
    "hotpotqa": "Answer the question based on the given passages. Only give me the answer and do not output any other words.\n\nThe following are given passages.\n{context}\n\nAnswer the question based on the given passages. Only give me the answer and do not output any other words.\n\nQuestion: {input}\nAnswer:",
    "2wikimqa": "Answer the question based on the given passages. Only give me the answer and do not output any other words.\n\nThe following are given passages.\n{context}\n\nAnswer the question based on the given passages. Only give me the answer and do not output any other words.\n\nQuestion: {input}\nAnswer:",
    "musique": "Answer the question based on the given passages. Only give me the answer and do not output any other words.\n\nThe following are given passages.\n{context}\n\nAnswer the question based on the given passages. Only give me the answer and do not output any other words.\n\nQuestion: {input}\nAnswer:",
    "dureader": "请基于给定的文章回答下述问题。\n\n文章：{context}\n\n请基于上述文章回答下面的问题。\n\n问题：{input}\n回答：",
    "gov_report": "You are given a report by a government agency. Write a one-page summary of the report.\n\nReport:\n{context}\n\nNow, write a one-page summary of the report.\n\nSummary:",
    "qmsum": "You are given a meeting transcript and a query containing a question or instruction. Answer the query in one or more sentences.\n\nTranscript:\n{context}\n\nNow, answer the query based on the above meeting transcript in one or more sentences.\n\nQuery: {input}\nAnswer:",
    "multi_news": "You are given several news passages. Write a one-page summary of all news. \n\nNews:\n{context}\n\nNow, write a one-page summary of all the news.\n\nSummary:",
    "vcsum": "下面有一段会议记录，请你阅读后，写一段总结，总结会议的内容。\n会议记录：\n{context}\n\n会议总结：",
    "trec": "Please determine the type of the question below. Here are some examples of questions.\n\n{context}\n{input}",
    "triviaqa": "Answer the question based on the given passage. Only give me the answer and do not output any other words. The following are some examples.\n\n{context}\n\n{input}",
    "samsum": "Summarize the dialogue into a few short sentences. The following are some examples.\n\n{context}\n\n{input}",
    "lsht": "请判断给定新闻的类别，下面是一些例子。\n\n{context}\n{input}",
    "passage_count": "There are some paragraphs below sourced from Wikipedia. Some of them may be duplicates. Please carefully read these paragraphs and determine how many unique paragraphs there are after removing duplicates. In other words, how many non-repeating paragraphs are there in total?\n\n{context}\n\nPlease enter the final count of unique paragraphs after removing duplicates. The output format should only contain the number, such as 1, 2, 3, and so on.\n\nThe final answer is: ",
    "passage_retrieval_en": 'Here are 30 paragraphs from Wikipedia, along with an abstract. Please determine which paragraph the abstract is from.\n\n{context}\n\nThe following is an abstract.\n\n{input}\n\nPlease enter the number of the paragraph that the abstract is from. The answer format must be like "Paragraph 1", "Paragraph 2", etc.\n\nThe answer is: ',
    "passage_retrieval_zh": '以下是若干段落文字，以及其中一个段落的摘要。请确定给定的摘要出自哪一段。\n\n{context}\n\n下面是一个摘要\n\n{input}\n\n请输入摘要所属段落的编号。答案格式必须是"段落1"，"段落2"等格式\n\n答案是：',
    "lcc": "Please complete the code given below. \n{context}Next line of code:\n",
    "repobench-p": "Please complete the code given below. \n{context}{input}Next line of code:\n",
}

# LongBench 数据集最大生成长度（来自官方 dataset2maxlen.json）
LONGBENCH_MAX_GEN_LENGTHS: dict[str, int] = {
    "narrativeqa": 128,
    "qasper": 128,
    "multifieldqa_en": 64,
    "multifieldqa_zh": 64,
    "hotpotqa": 32,
    "2wikimqa": 32,
    "musique": 32,
    "dureader": 128,
    "gov_report": 512,
    "qmsum": 512,
    "multi_news": 512,
    "vcsum": 512,
    "trec": 64,
    "triviaqa": 32,
    "samsum": 128,
    "lsht": 64,
    "passage_count": 32,
    "passage_retrieval_en": 32,
    "passage_retrieval_zh": 32,
    "lcc": 64,
    "repobench-p": 64,
}

# 这些数据集不应该使用 chat template 包装
# 原始 pred.py 注释：chat models are better off without build prompts on these tasks
LONGBENCH_NO_CHAT_DATASETS: set[str] = {"trec", "triviaqa", "samsum", "lsht", "lcc", "repobench-p"}

# LongBench 模型最大上下文长度映射（来自官方 model2maxlen.json）
# 用于确定截断阈值，确保 prompt 不超过模型限制
LONGBENCH_MODEL_MAX_LENGTHS: dict[str, int] = {
    # GLM 系列
    "GLM-4-9B-Chat": 120000,
    "glm-4-plus": 120000,
    # Llama 系列
    "Llama-3.1-8B-Instruct": 120000,
    "Llama-3.1-70B-Instruct": 120000,
    "Llama-3.3-70B-Instruct": 120000,
    "Llama-3.1-Nemotron-70B-Instruct": 120000,
    # Qwen 系列
    "Qwen2.5-7B-Instruct": 120000,
    "Qwen2.5-72B-Instruct": 120000,
    "Qwen/Qwen2.5-7B-Instruct": 120000,
    "Qwen/Qwen2.5-14B-Instruct": 120000,
    "Qwen/Qwen2.5-72B-Instruct": 120000,
    # Mistral 系列
    "Mistral-Large-Instruct-2407": 120000,
    "Mistral-Large-Instruct-2411": 120000,
    "mistral-nemo-instruct-2407": 128000,
    # Cohere
    "c4ai-command-r-plus-08-2024": 120000,
    # OpenAI 系列
    "gpt-4o-2024-08-06": 120000,
    "gpt-4o-mini-2024-07-18": 120000,
    "o1-mini-2024-09-12": 120000,
    "o1-preview-2024-09-12": 120000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4-turbo": 128000,
    "gpt-3.5-turbo": 16385,
    # Anthropic 系列
    "claude-3.5-sonnet-20241022": 200000,
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    # 旧版模型（保留兼容）
    "llama2-7b-chat-4k": 3500,
    "longchat-v1.5-7b-32k": 31500,
    "xgen-7b-8k": 7500,
    "internlm-7b-8k": 7500,
    "chatglm2-6b": 31500,
    "chatglm2-6b-32k": 31500,
    "chatglm3-6b-32k": 31500,
    "Qwen1.5-7B-Chat": 31500,
    "vicuna-v1.5-7b-16k": 15500,
    "phi-3.5-mini-instruct": 128000,
}


class LongBenchPromptor(MapOperator):
    """
    LongBench 专用 Promptor，用于 LongBench 基准测试。

    功能：
    1. 从硬编码的 LONGBENCH_PROMPT_TEMPLATES 加载任务专用模板
    2. 使用 context 和 input (query) 填充模板
    3. Token 级中间截断（当超过 max_input_tokens 时，保留首尾）
    4. 按数据集决定是否使用 chat template（few-shot 和代码任务不使用）

    截断策略（原始 LongBench pred.py）：
        # truncate to fit max_length (we suggest truncate in the middle,
        # since the left and right side may contain crucial instructions)
        if len(tokenized_prompt) > max_length:
            half = int(max_length/2)
            prompt = tokenizer.decode(tokenized_prompt[:half], skip_special_tokens=True) +
                     tokenizer.decode(tokenized_prompt[-half:], skip_special_tokens=True)

    配置参数：
        - max_input_tokens: int | None - 最大输入 token 数，超过则中间截断
        - is_chat_model: bool - 是否使用 chat template（默认 False）
        - model_name_or_path: str | None - 模型路径，用于加载 tokenizer
    """

    def __init__(self, config: dict, **kwargs):
        """
        初始化 LongBenchPromptor。

        Args:
            config: 配置字典，支持以下参数：
                - max_input_tokens: 最大输入 token 数（可选）
                - is_chat_model: 是否使用 chat template（默认 False）
                - model_name_or_path: 模型路径，用于 tokenizer（可选）
        """
        super().__init__(**kwargs)
        self.config = config
        self.max_input_tokens: int | None = config.get("max_input_tokens", None)
        self.is_chat_model: bool = config.get("is_chat_model", False)

        # 延迟加载 tokenizer（仅当需要截断时）
        self._tokenizer = None
        self._model_name_or_path: str | None = config.get("model_name_or_path", None)

    @property
    def tokenizer(self):
        """延迟加载 tokenizer"""
        if self._tokenizer is None and self._model_name_or_path:
            try:
                from transformers import AutoTokenizer

                self._tokenizer = AutoTokenizer.from_pretrained(
                    self._model_name_or_path,
                    trust_remote_code=True,
                )
                self.logger.info(f"Loaded tokenizer from {self._model_name_or_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load tokenizer: {e}")
                self._tokenizer = None
        return self._tokenizer

    def _truncate_middle(self, prompt: str) -> str:
        """
        中间截断策略（保留首尾）。

        原始 LongBench 实现：直接拼接两个 decode 结果（不加分隔符）。

        Args:
            prompt: 原始 prompt 字符串

        Returns:
            截断后的 prompt
        """
        if not self.tokenizer or not self.max_input_tokens:
            return prompt

        tokenized = self.tokenizer(prompt, truncation=False, return_tensors="pt").input_ids[0]

        if len(tokenized) > self.max_input_tokens:
            half = self.max_input_tokens // 2
            # 原始实现：直接拼接两个 decode 结果
            prompt = self.tokenizer.decode(
                tokenized[:half], skip_special_tokens=True
            ) + self.tokenizer.decode(tokenized[-half:], skip_special_tokens=True)
            self.logger.debug(
                f"Truncated prompt from {len(tokenized)} to {self.max_input_tokens} tokens"
            )

        return prompt

    def _apply_chat_template(self, prompt: str) -> str:
        """
        应用 chat template。

        Args:
            prompt: 原始 prompt 字符串

        Returns:
            包装后的 prompt
        """
        if not self.tokenizer:
            return prompt

        try:
            # 使用 transformers 的 apply_chat_template
            messages = [{"role": "user", "content": prompt}]
            chat_prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            return chat_prompt
        except Exception as e:
            self.logger.warning(f"Failed to apply chat template: {e}")
            return prompt

    def execute(self, data: dict) -> list:
        """
        生成 LongBench 风格的 prompt。

        输入格式（来自 LongBenchBatch）：
        {
            "query": str,           # 用户问题（原 input 字段）
            "context": str,         # 长文本上下文
            "references": list,     # 标准答案
            "_dataset": str,        # 数据集名称
            ...
        }

        输出格式：
        [original_data, prompt_string]

        Args:
            data: 包含 query, context, _dataset 等字段的字典

        Returns:
            [原始数据, prompt 字符串] 列表
        """
        # 获取必要字段
        dataset = data.get("_dataset", "")
        context = data.get("context", "")
        query = data.get("query", "")

        # 1. 获取数据集专用模板
        template = LONGBENCH_PROMPT_TEMPLATES.get(
            dataset,
            "{context}\n\nQuestion: {input}\nAnswer:",  # 默认模板
        )

        # 2. 填充模板（LongBench 使用 {context} 和 {input} 占位符）
        prompt = template.format(context=context, input=query)

        # 3. Token 级中间截断（如果配置了 max_input_tokens）
        if self.max_input_tokens and self.tokenizer:
            prompt = self._truncate_middle(prompt)

        # 4. Chat template 包装（按数据集决定）
        # 原始 pred.py: if dataset not in ["trec", "triviaqa", "samsum", "lsht", "lcc", "repobench-p"]:
        #                   prompt = build_chat(tokenizer, prompt, model_name)
        if self.is_chat_model and dataset not in LONGBENCH_NO_CHAT_DATASETS:
            prompt = self._apply_chat_template(prompt)

        self.logger.info(f"LongBenchPromptor: dataset={dataset}, prompt_length={len(prompt)}")

        # 5. 将 max_gen_tokens 添加到数据中，供 Generator 使用
        data["_max_gen_tokens"] = LONGBENCH_MAX_GEN_LENGTHS.get(dataset, 128)

        # 返回 [原始数据, prompt]
        return [data, prompt]

    @staticmethod
    def get_max_gen_length(dataset: str) -> int:
        """
        获取数据集的最大生成长度。

        Args:
            dataset: 数据集名称

        Returns:
            最大生成 token 数
        """
        return LONGBENCH_MAX_GEN_LENGTHS.get(dataset, 128)

    @staticmethod
    def get_prompt_template(dataset: str) -> str:
        """
        获取数据集的 prompt 模板。

        Args:
            dataset: 数据集名称

        Returns:
            prompt 模板字符串
        """
        return LONGBENCH_PROMPT_TEMPLATES.get(dataset, "{context}\n\nQuestion: {input}\nAnswer:")

    @staticmethod
    def get_model_max_length(model_name: str, default: int = 8192) -> int:
        """
        获取模型的最大上下文长度。

        支持精确匹配和模糊匹配（模型名称包含关系）。

        Args:
            model_name: 模型名称或路径
            default: 默认最大长度（如果模型未在映射中）

        Returns:
            模型最大上下文 token 数
        """
        # 精确匹配
        if model_name in LONGBENCH_MODEL_MAX_LENGTHS:
            return LONGBENCH_MODEL_MAX_LENGTHS[model_name]

        # 模糊匹配（检查模型名称是否包含已知模型）
        model_lower = model_name.lower()
        for known_model, max_len in LONGBENCH_MODEL_MAX_LENGTHS.items():
            if known_model.lower() in model_lower or model_lower in known_model.lower():
                return max_len

        return default
