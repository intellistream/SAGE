from typing import Any, List, Tuple
from jinja2 import Template
from sage.api.operator import PromptFunction
from sage.api.operator import Data

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


class QAPromptor(PromptFunction):
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

    def execute(self, data: Data) -> Data[list]:
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
            self.logger.info(f"query:{query}")
            # Combine into prompt list
            prompt = [system_prompt, user_prompt]

        except Exception as e:
            # Log detailed error information
            self.logger.error(f"Error in PromptFunction: {e}\nInput data: {data.data}\n{traceback.format_exc()}")

        return Data(prompt)



