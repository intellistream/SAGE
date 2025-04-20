from typing import Any, List, Tuple
from jinja2 import Template
from sage.api.operator import PromptFunction
from sage.api.operator import Data
import ray
QA_prompt_template='''Instruction:
You are an intelligent assistant with access to a knowledge base. Answer the question below with reference to the provided context.
Only give me the answer and do not output any other words.
{%- if external_corpus %}
Relevant corpus for the current question:
{{ external_corpus }}
{%- endif %}
'''
QA_prompt_template = Template(QA_prompt_template)



@ray.remote
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

    def execute(self, data: Data[Tuple[str, List[str]]]) -> Data[list]:
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
        
        # Create the system prompt using the template and the external corpus data
        system_prompt = {
            "role": "system", 
            "content": self.prompt_template.render(**base_system_prompt_data)
        }
        
        # Create the user prompt using the query
        user_prompt = {
            "role": "user", 
            "content": f"Question: {query}"
        }

        # Combine the system and user prompts into one list
        prompt = [system_prompt, user_prompt]

        # Return the prompt list wrapped in a Data object
        return Data(prompt)


