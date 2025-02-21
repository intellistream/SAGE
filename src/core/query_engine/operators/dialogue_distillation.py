import os
import logging
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForCausalLM
from src.core.query_engine.operators.base_operator import BaseOperator


class DialogueDistillation(BaseOperator):
    """
    Operator for distilling dialogue history into a concise summary.
    """

    def __init__(self, model_name="google/flan-t5-base", device=None, seed=42):
        """
        Initialize the distillation model.
        :param model_name: The Hugging Face model to use for summarization.
        :param device: The device to load the model on ("cpu" or "cuda").
        :param seed: Seed for reproducibility.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Initializing DialogueDistillation with model: {model_name}...")

        # Set random seed for reproducibility
        torch.manual_seed(seed)

        # Automatically detect device if not provided
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.logger.info(f"Selected device: {self.device}")

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Ensure padding token is set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Load model
        if "flan-t5" in model_name or "t5" in model_name:
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name, trust_remote_code=True
            ).to(self.device)
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name, trust_remote_code=True
            ).to(self.device)

        self.logger.info("Model and tokenizer loaded successfully.")

    def execute(self, input_data, **kwargs):
        """
        Distill dialogue by separately summarizing question and answer, then update input_data.
        :param input_data: List containing dialogue data.
        :return: Updated distilled question and answer.
        """
        try:
            # Validate input structure
            if not isinstance(input_data[0], dict) or "raw_data" not in input_data[0] \
                    or "question" not in input_data[0]["raw_data"] or "answer" not in input_data[0]:
                raise ValueError("input_data must contain a dictionary with 'raw_data', 'question', and 'answer'.")

            input_data = input_data[0]  # Extract first data
            raw_data = input_data["raw_data"]
            question = raw_data["question"]
            answer = input_data["answer"]

            # Separate distillation: First distill question
            distilled_question = self._distill_text(f"Summarize the question: '{question}'")

            # Then distill answer
            distilled_answer = self._distill_text(f"Summarize the answer: '{answer}'")

            # Update input_data with distilled versions
            input_data["raw_data"]["question"] = distilled_question
            input_data["answer"] = distilled_answer

            # Emit processed data
            self.emit({"raw_data": input_data["raw_data"], "answer": input_data["answer"]})

            return distilled_answer  # or return both distilled_question and distilled_answer if needed

        except Exception as e:
            self.logger.error(f"Error distilling dialogue: {str(e)}")
            raise RuntimeError(f"Failed to distill dialogue: {str(e)}")

    def _distill_text(self, text):
        """
        Distill the provided text (either question or answer).
        :param text: The text to distill.
        :return: The distilled (summarized) version of the text.
        """
        try:
            # Tokenize input text
            inputs = self.tokenizer(
                text, return_tensors="pt", padding=True, truncation=True
            ).to(self.device)

            # Generate distilled version (summary)
            outputs = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=50,  # Adjust based on desired length
                num_beams=4,
                do_sample=False,
                temperature=0.7,
                top_p=None,
                pad_token_id=self.tokenizer.pad_token_id,
                num_return_sequences=1,
            )

            # Decode and return distilled text
            distilled_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return distilled_text.strip()

        except Exception as e:
            self.logger.error(f"Error during text distillation: {str(e)}")
            raise RuntimeError(f"Text distillation failed: {str(e)}")

