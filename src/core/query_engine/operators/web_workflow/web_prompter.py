import logging
from src.core.prompts.utils import generate_prompt
from transformers import AutoTokenizer

MAX_CONTEXT_REFERENCES_LENGTH = 4000

class WebPrompter():
    """
    Operator for generating prompts based on input data, KG results and Web results.
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

    def execute(self, query, query_time, web_results, kg_results):
        """
        Generate a prompt using the provided template.
        :param query: The natural query string that initiated the search.
        :param query_time: The time at which the query was made, such as `03/10/2024, 23:19:21 PT`
        :param web_results: A list of web search results relevant to the query.
        :param kg_results: A string containing knowledge graph results relevant to the query.
        :return: Generated prompt.
        """
        try:
            # Convert input_data to a dictionary if needed
            formatted_prompts = []
            web_references = ""
            kg_references = ""
            user_message = ""
            
            if len(web_results) > 0:
                for _snippet_idx, snippet in enumerate(web_results):
                    web_references += f"- {snippet.strip()}\n"

            # Limit the length of references to fit the model's input size.
            web_references = web_references[: int(MAX_CONTEXT_REFERENCES_LENGTH / 2)]
            kg_references = kg_results[: int(MAX_CONTEXT_REFERENCES_LENGTH / 2)]
            
            with open(self.prompt_template, "r") as f:
                system_prompt = f.read()
            
            references = "### References\n" + \
                "# Web\n" + \
                web_references + \
                "# Knowledge Graph\n" + \
                kg_references

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
            self.logger.debug("Web prompt generated successfully.")
            return formatted_prompts
        except Exception as e:
            self.logger.error(f"Error during web prompt generation: {str(e)}")
            raise RuntimeError(f"Web prompt generation failed: {str(e)}")
