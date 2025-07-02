from typing import Any, Tuple
from sage.api.model import apply_generator_model
from sage.api.base_function import BaseFunction
from sage.api.tuple import Data
from sage.utils.custom_logger import CustomLogger


class OpenAIGenerator(BaseFunction):
    """
    OpenAIGenerator is a generator rag that interfaces with a specified OpenAI model
    to generate responses based on input data.
    """

    def __init__(self, config:dict,*,session_folder:str = None, **kwargs):

        """
        Initializes the OpenAIGenerator instance with configuration parameters.

        :param config: Dictionary containing configuration for the generator, including 
                       the method, model name, base URL, API key, etc.
        """
        self.logger = CustomLogger(
            object_name=f"OpenAIGenerator_Function",
            log_level="DEBUG",
            session_folder=session_folder,
            console_output=False,
            file_output=True
        )
        self.config = config

        # Apply the generator model with the provided configuration
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config["api_key"],
            seed=42  # Hardcoded seed for reproducibility
        )
        self.logger = CustomLogger(
            object_name=f"OpenAIGenerator_{__name__}",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )
        self.num = 1

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
        # print(f'query {self.num}  {user_query}')
        # print(f"answer {self.num}  {response}")
        self.num += 1

        self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Response: {response }\033[0m ")
        # Return the generated response along with the original user query as a tuple
        return Data((user_query, response))


class HFGenerator(BaseFunction):
    """
    HFGenerator is a generator rag that interfaces with a Hugging Face model
    to generate responses based on input data.
    """

    def __init__(self, config):
        """
        Initializes the HFGenerator instance with configuration parameters.

        :param config: Dictionary containing configuration for the generator, including
                       the method and model name.
        """
        super().__init__()
        self.config = config

        # Apply the generator model with the provided configuration
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"]
        )

    def execute(self, data: Data[list], **kwargs) -> Data[Tuple[str, str]]:
        """
        Executes the response generation using the configured Hugging Face model based on the input data.

        :param data: Data object containing a list of input data.
                     The expected format and the content of the data depend on the model's requirements.
        :param kwargs: Additional parameters for the model generation (e.g., temperature, max_tokens, etc.).

        :return: A Data object containing the generated response as a string.
        """
        # Generate the response from the Hugging Face model using the provided data and additional arguments
        user_query = data.data
        response = self.model.generate(user_query, **kwargs)

        # Return the generated response as a Data object
        self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Response: {response}\033[0m ")

        return Data((user_query, response))
