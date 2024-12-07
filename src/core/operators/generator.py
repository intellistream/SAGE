import logging
from transformers import AutoTokenizer, AutoModelForCausalLM
from src.core.operators.base_operator import BaseOperator

class Generator(BaseOperator):
    """
    Operator for generating natural language responses using Hugging Face's Transformers.
    """

    def __init__(self, model_name="gpt2"):
        """
        Initialize the generator with a specified model.
        :param model_name: The Hugging Face model to use for generation (default: "gpt2").
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Loading model and tokenizer for {model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.logger.info("Model and tokenizer loaded successfully.")

    def execute(self, input_data, **kwargs):
        """
        Generate a response using the Hugging Face model.
        :param input_data: Input query or context.
        :param kwargs: Additional parameters for generation.
        :return: Generated response.
        """
        try:
            # Default generation parameters
            temperature = kwargs.get("temperature", 0.7)
            max_length = kwargs.get("max_length", 50)
            top_p = kwargs.get("top_p", 0.9)

            # Encode input and generate response
            self.logger.info(f"Generating response for input: {input_data}")
            input_ids = self.tokenizer.encode(input_data, return_tensors="pt")

            output = self.model.generate(
                input_ids,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )

            # Decode the generated output
            response = self.tokenizer.decode(output[0], skip_special_tokens=True)
            self.logger.info(f"Generated response: {response}")
            return response

        except Exception as e:
            self.logger.error(f"Error during response generation: {str(e)}")
            raise RuntimeError(f"Response generation failed: {str(e)}")
