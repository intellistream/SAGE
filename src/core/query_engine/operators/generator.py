import logging
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from src.core.query_engine.operators.base_operator import BaseOperator

class Generator(BaseOperator):
    """
    Operator for generating natural language responses using Hugging Face's Transformers.
    """

    def __init__(self, model_name="google/flan-t5-small"):
        """
        Initialize the generator with a specified T5 model.
        :param model_name: The Hugging Face model to use for generation.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Loading model and tokenizer for {model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.logger.info("Model and tokenizer loaded successfully.")

    def execute(self, input_data, **kwargs):
        """
        Generate a response using the T5 model.
        :param input_data: Input query or context formatted via a Jinja2 template.
        :param kwargs: Additional parameters for generation.
        :return: Generated response.
        """
        try:
            # Log the received input
            self.logger.debug(f"Generating response for input data:\n{input_data}")

            # Tokenize input_data
            inputs = self.tokenizer(
                input_data, return_tensors="pt", padding=True, truncation=True
            )

            # Default generation parameters
            max_new_tokens = kwargs.get("max_new_tokens", 100)
            temperature = kwargs.get("temperature", 0.7)
            top_p = kwargs.get("top_p", 0.92)

            # Generate output
            outputs = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
            )

            # Decode and return the response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            self.logger.info(f"Generated response: {response}")
            return response

        except Exception as e:
            self.logger.error(f"Error during response generation: {str(e)}")
            raise RuntimeError(f"Response generation failed: {str(e)}")

