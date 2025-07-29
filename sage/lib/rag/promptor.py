from jinja2 import Template
from sage.core.function.base_function import StatefulFunction, MemoryFunction

from sage.core.function.map_function import MapFunction

from sage.utils.custom_logger import CustomLogger

import os
import time
import json

QA_prompt_template = '''Instruction:
You are an intelligent assistant with access to a knowledge base. Answer the question below with reference to the provided context.
Only give me the answer and do not output any other words.
{%- if external_corpus %}
Relevant corpus for the current question:
{{ external_corpus }}
{%- endif %}
'''

summarization_prompt_template = '''Instruction:
You are an intelligent assistant. Summarize the content provided below in a concise and clear manner.
Only provide the summary and do not include any additional information.
{%- if external_corpus %}
Content to summarize:
{{ external_corpus }}
{%- endif %}
'''
QA_prompt_template = Template(QA_prompt_template)
summarization_prompt_template = Template(summarization_prompt_template)

query_profiler_prompt_template = '''
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
'''
query_profiler_prompt_template = Template(query_profiler_prompt_template)


class QAPromptor(MapFunction):
    """
    QAPromptor is a prompt rag that generates a QA-style prompt using
    an external corpus and a user query. This class is designed to prepare
    the necessary prompt structure for a question-answering model.

    Attributes:
        config: Configuration data for initializing the prompt rag (e.g., model details, etc.).
        prompt_template: A template used for generating the system prompt, typically includes context or instructions.
    """

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)

        """
        Initializes the QAPromptor instance with configuration and prompt template.

        :param config: Dictionary containing configuration for the prompt rag.
        """
        self.config = config  # Store the configuration for later use
        self.prompt_template = QA_prompt_template  # Load the QA prompt template

        # 设置数据存储路径
        if hasattr(self.ctx, 'env_base_dir') and self.ctx.env_base_dir:
            self.data_base_path = os.path.join(self.ctx.env_base_dir, ".sage_states", "promptor_data")
        else:
            # 使用默认路径
            self.data_base_path = os.path.join(os.getcwd(), ".sage_states", "promptor_data")

        os.makedirs(self.data_base_path, exist_ok=True)
        self.data_records = []

    def _save_data_record(self, query, external_corpus, prompt):
        """保存提示词数据记录"""
        record = {
            'timestamp': time.time(),
            'query': query,
            'external_corpus': external_corpus,
            'prompt': prompt
        }
        self.data_records.append(record)
        self._persist_data_records()

    def _persist_data_records(self):
        """将数据记录持久化到文件"""
        if not self.data_records:
            return

        timestamp = int(time.time())
        filename = f"promptor_data_{timestamp}.json"
        path = os.path.join(self.data_base_path, filename)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    # sage_lib/functions/rag/qapromptor.py
    def execute(self, data) -> list:
        """
        生成 ChatGPT 风格的 prompt（system+user 两条消息）。

        支持两种输入：
        1. (query, external_corpus_list_or_str))
        2. query_str)
        """
        try:
            # -------- 解析输入 --------
            raw = data
            if isinstance(raw, tuple) and len(raw) == 2:
                query, external_corpus = raw
                if isinstance(external_corpus, list):
                    external_corpus = "\n".join(external_corpus)
            else:
                query = raw
                external_corpus = ""

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
                        "You are a helpful AI assistant. "
                        "Answer the user's questions accurately."
                    ),
                }

            # -------- user prompt --------
            user_prompt = {
                "role": "user",
                "content": f"Question: {query}",
            }

            prompt = [system_prompt, user_prompt]

            # 保存数据记录
            self._save_data_record(query, external_corpus, prompt)

            return [query, prompt]

        except Exception as e:
            self.logger.error(
                "QAPromptor error: %s | input=%s", e, getattr(data, "data", "")
            )
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
        try:
            self._persist_data_records()
        except:
            pass


class SummarizationPromptor(MapFunction):
    """
    QAPromptor is a prompt rag that generates a QA-style prompt using
    an external corpus and a user query. This class is designed to prepare
    the necessary prompt structure for a question-answering model.

    Attributes:
        config: Configuration data for initializing the prompt rag (e.g., model details, etc.).
        prompt_template: A template used for generating the system prompt, typically includes context or instructions.
    """

    def __init__(self, config):
        """
        Initializes the QAPromptor instance with configuration and prompt template.

        :param config: Dictionary containing configuration for the prompt rag.
        """
        super().__init__()
        self.config = config  # Store the configuration for later use
        self.prompt_template = summarization_prompt_template  # Load the summarization prompt template

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
        base_system_prompt_data = {
            "external_corpus": external_corpus
        }

        # query = data
        # Create the system prompt using the template and the external corpus data
        system_prompt = {
            "role": "system",
            "content": self.prompt_template.render(**base_system_prompt_data)
        }
        # system_prompt = {
        #     "role": "system",
        #     "content": ""
        # }
        # Create the user prompt using the query
        user_prompt = {
            "role": "user",
            "content": f"Question: {query}"
        }

        # Combine the system and user prompts into one list
        prompt = [system_prompt, user_prompt]

        # Return the prompt list wrapped in a Data object
        return prompt


class QueryProfilerPromptor(MapFunction):
    """
    QueryProfilerPromptor provides a prompt for profiling queries.

    """

    def __init__(self, config):
        """
        Initializes the QueryProfilerPromptor instance with configuration and prompt template.

        :param config: Dictionary containing configuration for the prompt rag.
        """
        super().__init__()
        self.config = config  # Store the configuration for later use
        self.prompt_template = query_profiler_prompt_template  # Load the query profiler prompt template

    def execute(self, data) -> list:
        """
        Generates a profiling prompt for the input query.

        :param data: A string representing the query to be profiled.

        :return: A list containing the profiling prompt.
        """
        query = data
        prompt = {
            "role": "user",
            "content": self.prompt_template.render(query=query, metadata=self.config.get("metadata", {}),
                                                   chunk_size=self.config.get("chunk_size", 1024))
        }
        return [prompt]