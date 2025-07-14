from jinja2 import Template
from sage_core.function.map_function import MapFunction
from sage_core.function.base_function import StatefulFunction, MemoryFunction
from sage_utils.custom_logger import CustomLogger
from sage_common_funs.utils.template import AI_Template

QA_prompt_template='''Instruction:
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

    # sage_lib/functions/rag/qapromptor.py
    def execute(self, data: AI_Template) -> AI_Template:
        """
        生成 ChatGPT 风格的 prompt（system+user 两条消息）。

        支持两种输入：
        1. (query, external_corpus_list_or_str)
        2. query_str)
        """
        input_template = data
        try:
            # -------- 解析输入 --------
            raw_question = input_template.raw_question
            external_corpus = input_template.retriver_chunks or ""

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
                "content": f"Question: {raw_question}",
            }
            input_template.prompts.append(system_prompt)
            input_template.prompts.append(user_prompt)
            # prompt = [system_prompt, user_prompt]
            return input_template

        except Exception as e:
            self.logger.error(f"QAPromptor failed: {str(e)}", exc_info=True)
            return input_template
