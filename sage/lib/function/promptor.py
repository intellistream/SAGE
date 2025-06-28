from typing import Any, List, Tuple
from jinja2 import Template
from sage.api.operator import BaseFunction
from sage.api.operator import Data
import logging
from sage.utils.custom_logger import CustomLogger

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
    QAPromptor is a prompt function that generates a QA-style prompt using 
    an external corpus and a user query. This class is designed to prepare 
    the necessary prompt structure for a question-answering model.

    Attributes:
        config: Configuration data for initializing the prompt function (e.g., model details, etc.).
        prompt_template: A template used for generating the system prompt, typically includes context or instructions.
    """
    
    def __init__(self, config):
        """
        Initializes the QAPromptor instance with configuration and prompt template.

        :param config: Dictionary containing configuration for the prompt function.
        """
        super().__init__()
        self.config = config  # Store the configuration for later use
        self.prompt_template = QA_prompt_template  # Load the QA prompt template
        self.logger = CustomLogger(
            object_name=f"QAPromptor_{__name__}",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )

    def execute(self, data) -> Data[list]:
        """
        Generates a QA-style prompt for the input question and optional external corpus.

        This method handles two input formats:
        1. (query, external_corpus) - A tuple with query string and corpus list
        2. query - A single query string (no external corpus)

        :param data: A Data object containing either:
                     - A tuple (query, external_corpus)
                     - A single query string
        :return: A Data object containing a list with two prompts:
                 1. system_prompt: Context and instructions (with corpus if provided)
                 2. user_prompt: The user's question
        """
        try:
            # Determine input format and extract data
            if isinstance(data.data, tuple) and len(data.data) == 2:
                # Format 1: Tuple with query and external_corpus
                query, external_corpus = data.data
                # Combine corpus items if it's a list
                if isinstance(external_corpus, list):
                    external_corpus = "".join(external_corpus)
            else:
                # Format 2: Single query without external corpus
                query = data.data
                external_corpus = ""  # Default to empty corpus

            # Handle case where external_corpus might be None
            if not external_corpus:
                external_corpus = ""

            # Prepare the base data for the system prompt
            base_system_prompt_data = {"external_corpus": external_corpus}

            # If we have non-empty corpus, create a context-based system prompt
            if external_corpus:
                system_prompt = {
                    "role": "system",
                    "content": self.prompt_template.render(**base_system_prompt_data)
                }
            else:
                
                # Fallback to general instructions when no corpus is provided
                system_prompt = {
                    "role": "system",
                    "content": "You are a helpful AI assistant. Answer the user's questions accurately."
                }

            # Create the user prompt with the query
            user_prompt = {
                "role": "user",
                "content": f"Question: {query}"
            }
            # self.logger.info(f"query:{query}")
            self.logger.info(f"\033[32m[ {self.__class__.__name__}]: prompt: {user_prompt}\033[0m ")
            prompt = [system_prompt, user_prompt]

        except Exception as e:
            # Log detailed error information
            self.logger.error(f"Error in BaseFunction: {e}\nInput data: {data.data}\n")

            # Create a minimal fallback prompt in case of errors
            prompt = [
                {"role": "system", "content": "System encountered an error"},
                {"role": "user",
                 "content": f"Question: Error occurred. Please try again. (Original query: {getattr(data, 'data', '')}"}
            ]

        return Data(prompt)



class SummarizationPromptor(BaseFunction):
    """
    QAPromptor is a prompt function that generates a QA-style prompt using
    an external corpus and a user query. This class is designed to prepare
    the necessary prompt structure for a question-answering model.

    Attributes:
        config: Configuration data for initializing the prompt function (e.g., model details, etc.).
        prompt_template: A template used for generating the system prompt, typically includes context or instructions.
    """

    def __init__(self, config):
        """
        Initializes the QAPromptor instance with configuration and prompt template.

        :param config: Dictionary containing configuration for the prompt function.
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
