import logging
from transformers import AutoTokenizer, AutoModelForCausalLM
from src.core.query_engine.operators.base_operator import BaseOperator


class Generator(BaseOperator):
    """
    Operator for generating natural language responses using Hugging Face's Transformers.
    """

    def __init__(self, model_name="meta-llama/Llama-3.2-1B", device="cuda"):
        """
        Initialize the generator with a specified model.
        :param model_name: The Hugging Face model to use for generation.
        :param device: The device to load the model on ("cuda" for GPU or "cpu").
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Loading model and tokenizer for {model_name}...")

        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Ensure padding token is set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")
        self.device = device

        self.logger.info("Model and tokenizer loaded successfully.")

    def execute(self, input_data, **kwargs):
        """
        Generate a response using the model.
        :param input_data: Input query or context.
        :param kwargs: Additional parameters for generation.
        :return: Generated response.
        """
        try:
            # Log the received input
            self.logger.info(f"Generating response for input data:\n{input_data}")

            # Tokenize input_data
            inputs = self.tokenizer(
                input_data, return_tensors="pt", padding=True, truncation=True
            ).to(self.device)

            # Default generation parameters
            max_new_tokens = kwargs.get("max_new_tokens", 100)
            temperature = kwargs.get("temperature", 0.7)
            top_p = kwargs.get("top_p", 0.9)

            # Generate output
            outputs = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
            )

            # Decode and return the response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            self.logger.info(f"Decoded output: {response}")
            return response

        except Exception as e:
            self.logger.error(f"Error during response generation: {str(e)}")
            raise RuntimeError(f"Response generation failed: {str(e)}")
