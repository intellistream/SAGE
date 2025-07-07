from jinja2 import Template
from sage_core.api.base_function import BaseFunction, StatefulFunction, MemoryFunction
from sage_core.api.tuple import Data
from sage_utils.custom_logger import CustomLogger

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


class QAPromptor(BaseFunction):
    """
    QAPromptor is a prompt rag that generates a QA-style prompt using
    an external corpus and a user query. This class is designed to prepare 
    the necessary prompt structure for a question-answering model.

    Attributes:
        config: Configuration data for initializing the prompt rag (e.g., model details, etc.).
        prompt_template: A template used for generating the system prompt, typically includes context or instructions.
    """
    
    def __init__(self, config:dict,*,session_folder:str = None, **kwargs):

        """
        Initializes the QAPromptor instance with configuration and prompt template.

        :param config: Dictionary containing configuration for the prompt rag.
        """
        self.logger = CustomLogger(
            object_name=f"QAPromptor_Function",
            log_level="DEBUG",
            session_folder=session_folder,
            console_output=False,
            file_output=True
        )
        self.config = config  # Store the configuration for later use
        self.prompt_template = QA_prompt_template  # Load the QA prompt template

    # sage_lib/functions/rag/qapromptor.py
    def execute(self, data) -> Data[list]:
        """
        生成 ChatGPT 风格的 prompt（system+user 两条消息）。

        支持两种输入：
        1. Data((query, external_corpus_list_or_str))
        2. Data(query_str)
        """
        try:
            # -------- 解析输入 --------
            raw = data.data
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
            self.logger.info(
                "\033[32m[%s] prompt generated for query: %s\033[0m",
                self.__class__.__name__,
                query,
            )
            return Data(prompt)

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
            return Data(fallback)


class SummarizationPromptor(BaseFunction):
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

    def execute(self, data) -> Data[list]:
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
        query, external_corpus = data.data

        # Combine the external corpus list into a single string (in case it's split into multiple parts)
        external_corpus = "".join(external_corpus)

        # Prepare the base data for the system prompt, which includes the external corpus
        base_system_prompt_data = {
            "external_corpus": external_corpus
        }

        # query = data.data
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
        return Data(prompt)
