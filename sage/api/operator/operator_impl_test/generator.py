
from typing import Any,Tuple
from sage.api.model import apply_generator_model
from sage.api.operator import GeneratorFunction
from sage.api.operator import Data
import ray



class OpenAIGenerator(GeneratorFunction):
    """
    OpenAIGenerator is a generator function that interfaces with a specified OpenAI model 
    to generate responses based on input data.
    """
    def __init__(self, config):
        """
        Initializes the OpenAIGenerator instance with configuration parameters.

        :param config: Dictionary containing configuration for the generator, including 
                       the method, model name, base URL, API key, etc.
        """
        super().__init__()
        self.config = config["generator"]
        
        # Apply the generator model with the provided configuration
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config["api_key"],
            seed=42  # Hardcoded seed for reproducibility
        )

    def execute(self, data: Data[list], **kwargs) -> Data[Tuple[str, str]]:
        """
        Executes the response generation using the configured model based on the input data.

        :param data: Data object containing a list of input data. 
                     The second item in the list is expected to be a dictionary with a "content" key that contains the user's query.
        :param kwargs: Additional parameters for the model generation (e.g., temperature, max_tokens, etc.).

        :return: A Data object containing a tuple (user_query, response), where user_query is the original input query, 
                and response is the generated response from the model.
        """
        # Extract the user query from the input data
        user_query = data.data[1]["content"]
        
        # Generate the response from the model using the provided data and additional arguments
        response = self.model.generate(data.data, **kwargs)

        # Return the generated response along with the original user query as a tuple
        return Data((user_query, response))


class HFGenerator(GeneratorFunction):
    """
    HFGenerator is a generator function that interfaces with a Hugging Face model 
    to generate responses based on input data.
    """
    def __init__(self, config):
        """
        Initializes the HFGenerator instance with configuration parameters.

        :param config: Dictionary containing configuration for the generator, including 
                       the method and model name.
        """
        super().__init__()
        self.config = config["generator"]
        
        # Apply the generator model with the provided configuration
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"]
        )

    def execute(self, data: Data[list], **kwargs) -> Data[str]:
        """
        Executes the response generation using the configured Hugging Face model based on the input data.

        :param data: Data object containing a list of input data.
                     The expected format and the content of the data depend on the model's requirements.
        :param kwargs: Additional parameters for the model generation (e.g., temperature, max_tokens, etc.).

        :return: A Data object containing the generated response as a string.
        """
        # Generate the response from the Hugging Face model using the provided data and additional arguments
        response = self.model.generate(data.data, **kwargs)

        # Return the generated response as a Data object
        return Data(response)
