import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

class QueryPlanner:
    """
    Uses LLaMA-1B for adaptive retrieval planning based on query reasoning.
    """

    def __init__(self, model_name="meta-llama/Llama-3.2-1B-Instruct", device=None):
        """
        Initialize the LLaMA-based query planner.
        :param model_name: Pretrained LLaMA model.
        :param device: CPU or GPU.
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
        self.model.eval()  # Set model to evaluation mode

    def plan_retrieval(self, query):
        """
        Use LLaMA to plan retrieval strategies dynamically.
        :param query: The user query string.
        :return: Retrieval plan dictionary.
        """

        # Few-shot Prompt with Retrieval Planning
        prompt = f"""
        Given the user query, determine:
        - Query complexity (simple, moderate, complex)
        - Best memory source (STM, LTM, DCM)
        - Retrieval strategy (exact match, semantic search, hybrid)
        - Summarization approach (extractive, abstractive)
        - Confidence score (0-100) indicating whether retrieval is needed.

        Examples:
        Query: "What is the capital of France?"
        Plan: Simple | STM | Exact match | Extractive | 30%

        Query: "Explain the impact of climate change on global economies."
        Plan: Moderate | LTM | Semantic search | Abstractive | 70%

        Query: "How does quantum entanglement enable secure communication in cryptography?"
        Plan: Complex | DCM | Hybrid | Abstractive | 95%

        Now generate a retrieval plan for:
        Query: "{query}"
        Plan: 
        """

        # Tokenize and generate response
        input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            output = self.model.generate(input_ids, max_new_tokens=50)

        # Decode output
        response = self.tokenizer.decode(output[0], skip_special_tokens=True).strip()

        # Parse the response
        retrieval_plan = self._parse_plan(response)
        return retrieval_plan

    def _parse_plan(self, response):
        """
        Parses LLaMA output into a structured retrieval plan.
        """
        try:
            parts = response.split(" | ")
            return {
                "complexity": parts[0].strip(),
                "memory_layer": parts[1].strip(),
                "retrieval_strategy": parts[2].strip(),
                "summarization": parts[3].strip(),
                "confidence": int(parts[4].replace("%", "").strip())
            }
        except Exception as e:
            print(f"Error parsing plan: {e}")
            return {"complexity": "unknown", "memory_layer": "STM", "retrieval_strategy": "exact", "summarization": "extractive", "confidence": 50}


if __name__ == '__main__':
    # Example Usage
    planner = QueryPlanner()
    query = "Explain the impact of AI in modern healthcare systems."
    plan = planner.plan_retrieval(query)
    print(plan)