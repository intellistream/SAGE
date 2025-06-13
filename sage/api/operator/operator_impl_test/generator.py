
from tempfile import tempdir
from typing import Any,Tuple
from urllib import response

from h11 import Response
from sage.api.model import apply_generator_model
from sage.api.operator import GeneratorFunction
from sage.api.operator import Data
import re
import json
from collections import Counter
from scipy.stats import entropy
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
    

class OpenAIGeneratorWithPerplexity(OpenAIGenerator):
    """
    OpenAIGeneratorWithPerplexity is a subclass of OpenAIGenerator that calculates and outputs the perplexity 
    of the generated responses in addition to the responses themselves.
    """
    def __init__(self, config):
        """
        Initializes the OpenAIGeneratorWithPerplexity instance with configuration parameters.
        
        :param config: Dictionary containing configuration for the generator, including 
                       the method, model name, base URL, API key, etc.
        """
        super().__init__(config)

    def parse_json_output(self, output):
        """
        Try to load the entire output as JSON.
        """
        try:
            json_match = re.search(r"```json(.*?)```", output, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON code block found.")

            json_str = json_match.group(1).strip()
            data = json.loads(json_str)
            return data
        except Exception as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        
    def generate_rewritten_questions(self, user_query: str, n: int = 5) -> list:
        """
        Generate n different rewrites of the original user query using the model.

        :param user_query: The original user query to be rewritten.
        :param n: The number of rewritten queries to generate.

        :return: A list of rewritten questions.
        """
        rewritten_queries = []
        rewrite_template = """
            Rewrite the following question into {n} different ways. Provide the result in a JSON format where the key is 'questions' 
            and the value is a list of rewritten questions. For example: {{"questions": ["rewritten question 1", "rewritten question 2", ...]}}
            The question to rewrite is: {user_query}
        """
        user_query= rewrite_template.format(user_query=user_query,n=n)
        prompt = [{"role":"user","content":user_query}]
        response = self.model.generate(prompt,temperature=0.9,top_p=0.9)   
        print(response) 
        try:
            # Parse the response to extract the questions from the JSON format
            json_response = self.parse_json_output(response)  # Assuming the model's response is valid JSON
            if "questions" in json_response:
                return json_response["questions"]
            else:
                raise ValueError("JSON response doesn't contain the 'questions' key")
        
        except json.JSONDecodeError:
            raise ValueError("Failed to decode JSON from model response")
        

    def calculate_semantic_entropy(self, responses: list) -> float:
        """
        Calculate the semantic entropy of the given list of responses.

        :param responses: A list of responses to analyze.

        :return: The semantic entropy of the responses.
        """
        # Flatten responses into a list of words (tokens)
        words = [word for response in responses for word in response.split()]
        
        # Calculate frequency distribution of the words
        word_counts = Counter(words)
        
        # Normalize the counts to get probabilities
        total_words = len(words)
        word_probabilities = [count / total_words for count in word_counts.values()]
        
        # Calculate the entropy using scipy's entropy function
        return entropy(word_probabilities)
    
    def execute(self, data: Data[list], **kwargs) -> Data[Tuple[str, str, float]]:
        """
        Executes the response generation using the configured model and calculates the perplexity of the generated response.
        
        :param data: Data object containing a list of input data. 
                     The second item in the list is expected to be a dictionary with a "content" key that contains the user's query.
        :param kwargs: Additional parameters for the model generation (e.g., temperature, max_tokens, etc.).
        
        :return: A Data object containing a tuple (user_query, response, perplexity), where:
                - user_query is the original input query,
                - response is the generated response from the model,
                - perplexity is the perplexity of the response.
        """
        # Extract the user query from the input data
        user_query = data.data
        
        questions=self.generate_rewritten_questions(user_query)
        print(questions)
        
        responses = []

        for question in questions:
            response=self.model.generate([{"role":"user","content":question}],tempdirature=0.9,top_p=0.9)
            responses.append(response)
        
        entropy=self.calculate_semantic_entropy(responses)
        print(entropy)
        return Data((user_query, responses, entropy))
    

# import yaml
# def load_config(path: str) -> dict:
#     with open(path, 'r') as f:
#         return yaml.safe_load(f)

# config=load_config("/home/zsl/workspace/sage/api/operator/test/config_qa.yaml")
# g=OpenAIGeneratorWithPerplexity(config)
# output=g.execute(Data([{"role":"user","content":"世界上最小的动物是？"}]),temperature=0.7,top_p=0.9,max_tokens=1000)
# print(output.data)