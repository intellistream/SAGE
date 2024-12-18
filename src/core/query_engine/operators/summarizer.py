import logging
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from src.core.query_engine.operators.base_operator import BaseOperator


class Summarizer(BaseOperator):
    """
    Operator for summarizing text using Hugging Face's Transformers.
    """

    def __init__(self, model_name="facebook/bart-large-cnn"):
        """
        Initialize the summarizer with a specified model.
        :param model_name: The Hugging Face model to use for summarization (default: "facebook/bart-large-cnn").
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Loading model and tokenizer for {model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.logger.info("Model and tokenizer loaded successfully.")

    def execute(self, input_data, **kwargs):
        """
        Summarize the input text using the Hugging Face model.
        :param input_data: The text to summarize.
        :param kwargs: Additional parameters for summarization.
        :return: Summarized text.
        """
        try:
            # Default summarization parameters
            max_length = kwargs.get("max_length", 130)
            min_length = kwargs.get("min_length", 30)
            length_penalty = kwargs.get("length_penalty", 2.0)
            num_beams = kwargs.get("num_beams", 4)

            # Handle input data: join list elements if input_data is a list
            if isinstance(input_data, list):
                input_data = " ".join(map(str, input_data))

            # Encode input and generate summary
            self.logger.info(f"Summarizing input: {input_data}")
            inputs = self.tokenizer.encode(input_data, return_tensors="pt", truncation=True, max_length=1024)

            summary_ids = self.model.generate(
                inputs,
                max_length=max_length,
                min_length=min_length,
                length_penalty=length_penalty,
                num_beams=num_beams,
                early_stopping=True,
            )

            # Decode the generated summary
            summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            self.logger.info(f"Generated summary: {summary}")
            return summary

        except Exception as e:
            self.logger.error(f"Error during summarization: {str(e)}")
            raise RuntimeError(f"Summarization failed: {str(e)}")

