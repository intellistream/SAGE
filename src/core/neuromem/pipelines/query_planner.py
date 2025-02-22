import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from src.utils.text_processing import process_text_to_embedding


class QueryPlanner:
    """
    LLaMA-based query planner for adaptive retrieval and summarization.
    """

    def __init__(self, model_name="meta-llama/Llama-3.2-1B-Instruct", device=None):
        """
        Initialize the query planner with a language model for classification.
        :param model_name: LLaMA model used for query classification.
        :param device: Compute device (CUDA or CPU).
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        # Select device
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        # Load model and tokenizer
        self.logger.info(f"Loading LLaMA model {model_name} for query classification...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
        self.logger.info("LLaMA model loaded successfully.")

    def plan_retrieval(self, query):
        """
        Plan the retrieval process based on the query's complexity and intent.
        :param query: The user query string.
        :return: A retrieval plan dict containing memory layer, retrieval method, and summarization strategy.
        """
        # Step 1: Classify query complexity
        query_complexity = self.classify_query_complexity(query)

        # Step 2: Decide memory layer(s) to retrieve from
        memory_layers = self.decide_memory_layers(query_complexity)

        # Step 3: Choose retrieval strategy
        retrieval_strategy = self.decide_retrieval_strategy(query_complexity)

        # Step 4: Determine number of results (k)
        k = self.determine_k(query_complexity)

        # Step 5: Decide summarization method (if needed)
        summarization = self.decide_summarization(query_complexity)

        # Build and return retrieval plan
        retrieval_plan = {
            "memory_layers": memory_layers,
            "retrieval_strategy": retrieval_strategy,
            "k": k,
            "summarization": summarization
        }

        self.logger.info(f"Generated retrieval plan: {retrieval_plan}")
        return retrieval_plan

    def classify_query_complexity(self, query):
        """
        Uses LLaMA to classify query complexity.
        :param query: User query string.
        :return: Complexity level (simple, moderate, complex).
        """
        prompt = f"Classify the complexity of this query: '{query}'. Respond with one of [simple, moderate, complex]."

        input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            output = self.model.generate(input_ids, max_new_tokens=5)
        response = self.tokenizer.decode(output[0], skip_special_tokens=True).strip().lower()

        if "simple" in response:
            return "simple"
        elif "moderate" in response:
            return "moderate"
        elif "complex" in response:
            return "complex"
        else:
            return "moderate"  # Default if classification is unclear

    def decide_memory_layers(self, query_complexity):
        """
        Decide which memory layers (STM, LTM, DCM) to retrieve from.
        :param query_complexity: Query classification.
        :return: List of memory layers.
        """
        if query_complexity == "simple":
            return ["short_term", "dynamic_contextual"]  # Recent memory is enough
        elif query_complexity == "moderate":
            return ["short_term", "long_term", "dynamic_contextual"]  # Need broader knowledge
        else:
            return ["short_term", "long_term", "dynamic_contextual"]  # Complex requires deep knowledge

    def decide_retrieval_strategy(self, query_complexity):
        """
        Choose the retrieval method based on query complexity.
        :param query_complexity: Query classification.
        :return: Retrieval strategy (exact, semantic, hybrid).
        """
        if query_complexity == "simple":
            return "exact match"
        elif query_complexity == "moderate":
            return "semantic search"
        else:
            return "hybrid"  # Mix of exact + semantic

    def determine_k(self, query_complexity):
        """
        Dynamically decide the number of retrieved documents (k).
        :param query_complexity: Query classification.
        :return: Number of results to retrieve.
        """
        if query_complexity == "simple":
            return 2
        elif query_complexity == "moderate":
            return 4
        else:
            return 6  # Complex queries need more context

    def decide_summarization(self, query_complexity):
        """
        Determine if and how to summarize retrieved data.
        :param query_complexity: Query classification.
        :return: Summarization method (none, extractive, abstractive).
        """
        if query_complexity == "simple":
            return "none"
        elif query_complexity == "moderate":
            return "extractive"
        else:
            return "abstractive"  # Complex queries need deeper summarization


if __name__ == '__main__':
    query_planner = QueryPlanner()
    query = "Who invented the light bulb?"
    plan = query_planner.plan_retrieval(query)
    print(plan)

    query = "What are the main causes of climate change?"
    plan = query_planner.plan_retrieval(query)
    print(plan)

    query = "How do quantum computers leverage superposition to perform parallel computations?"
    plan = query_planner.plan_retrieval(query)
    print(plan)