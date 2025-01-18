import logging
from src.core.query_engine.operators.base_operator import BaseOperator
from src.core.prompts.utils import generate_prompt
from transformers import AutoTokenizer

MAX_CONTEXT_REFERENCES_LENGTH = 4000

class PromptOperator(BaseOperator):
    """
    Operator for generating prompts based on input data and context.
    """

    def __init__(self, prompt_template, model_name="meta-llama/Meta-Llama-3-8B-Instruct"):
        """
        Initialize the PromptOperator.
        :param prompt_template: Path to the prompt template.
        :param model_name: The Hugging Face model to use for generation.
        """
        super().__init__()
        self.prompt_template = prompt_template
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, input_data, **kwargs):
        """
        Generate a prompt using the provided template.
        :param input_data: Input data in any format (tuple, list, dict, etc.).
        :param kwargs: Additional parameters for prompt generation.
        :return: Generated prompt.
        """
        try:
            # Convert input_data to a dictionary if needed
            query, query_time, retrieval_results = input_data[0]

            kg_results = ""
            for result in retrieval_results:
                kg_results += f"- {result.strip()}\n" 

            formatted_prompts = []
            references = ""

            with open(self.prompt_template, "r") as f:
                system_prompt = f.read()
            
            # Limit the length of references to fit the model's input size.
            kg_references = kg_results[: MAX_CONTEXT_REFERENCES_LENGTH]
            references = "### References\n" + \
                "# Knowledge Graph\n" + \
                kg_references
            
            user_message = ""
            user_message += f"{references}\n------\n\n"
            user_message 
            user_message += f"Using only the references listed above, answer the following question: \n"
            user_message += f"Current Time: {query_time}\n"
            user_message += f"Question: {query}\n"

            formatted_prompts.append(
                self.tokenizer.apply_chat_template(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    tokenize=False,
                    add_generation_prompt=True,
                )
            )

            # Emit the generated prompt
            self.emit(formatted_prompts)
            self.logger.debug("Prompt generated successfully.")
        except Exception as e:
            self.logger.error(f"Error during prompt generation: {str(e)}")
            raise RuntimeError(f"Prompt generation failed: {str(e)}")
