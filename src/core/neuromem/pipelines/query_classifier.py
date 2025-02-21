import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


class QueryClassifier:
    """
    Uses LLaMA-1B for query classification using zero-shot or few-shot prompting.
    """

    def __init__(self, model_name="meta-llama/Llama-3.2-1B-Instruct", device=None):
        """
        Initialize the LLaMA query classifier.
        :param model_name: Pretrained LLaMA model.
        :param device: CPU or GPU.
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
        self.model.eval()  # Set model to evaluation mode

        # Labels
        self.label_map = ["simple", "moderate", "complex"]

    def classify(self, query):
        """
        Classify a query using LLaMA's language understanding.
        :param query: The user query string.
        :return: Classification label.
        """

        # Few-shot Prompt
        prompt = f"""
        Classify the complexity of the following question as 'simple', 'moderate', or 'complex':

        Examples:
        - "What is the capital of France?" → simple
        - "Explain the impact of climate change on global economies." → moderate
        - "How does quantum entanglement enable secure communication in cryptography?" → complex

        Now classify this query:
        "{query}" → 
        """

        # Tokenize and generate response
        input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            output = self.model.generate(input_ids, max_new_tokens=10)

        # Decode output
        response = self.tokenizer.decode(output[0], skip_special_tokens=True).strip()
        predicted_label = self._extract_label(response)

        return {"complexity": predicted_label, "response": response}

    def _extract_label(self, response):
        """
        Extracts classification label from LLaMA's response.
        """
        for label in self.label_map:
            if label in response.lower():
                return label
        return "unknown"


if __name__ == '__main__':
    # Example Usage
    classifier = QueryClassifier()
    query = "Explain the role of reinforcement learning in autonomous driving."
    result = classifier.classify(query)
    print(result)  # {'complexity': 'moderate', 'response': 'moderate'}