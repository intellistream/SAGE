import os
from typing import Tuple,List
from sage_common_funs.utils.generator_model import apply_generator_model
from sage_core.function.base_function import BaseFunction,StatefulFunction

from sage_utils.custom_logger import CustomLogger
from sage_common_funs.utils.template import AI_Template

class OpenAIGenerator(BaseFunction):
    """
    OpenAIGenerator is a generator rag that interfaces with a specified OpenAI model
    to generate responses based on input data.
    """

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)

        """
        Initializes the OpenAIGenerator instance with configuration parameters.

        :param config: Dictionary containing configuration for the generator, including 
                       the method, model name, base URL, API key, etc.
        """
        self.config = config
        # Apply the generator model with the provided configuration
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.api_key,
            seed=42  # Hardcoded seed for reproducibility
        )
        self.num = 1

    def execute(self, data: AI_Template) -> AI_Template:
        """
        Executes the response generation using the configured model based on the input data.

        :param data: Data object containing a list of input data.
                     The second item in the list is expected to be a dictionary with a "content" key that contains the user's query.
        :param kwargs: Additional param eters for the model generation (e.g., temperature, max_tokens, etc.).

        :return: A Data object containing a tuple (user_query, response), where user_query is the original input query,
                and response is the generated response from the model.
        """
        # Extract the user query from the input data
        input_template = data
 
        prompts = input_template.prompts
        # self.logger.debug(prompts)
        # 可以在上边的generator.logger中配置logger.console_output= True
        # Generate the response from the model using the provided data and additional arguments
        response:str = self.model.generate(prompts)
        self.num += 1
        input_template.response = response
        self.logger.info(f"Response: {response }")
        # Return the generated response along with the original user query as a tuple
        return input_template