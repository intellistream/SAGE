import random

class RetrievalTuner:
    """
    Dynamically tunes retrieval strategy based on query properties.
    """

    def tune(self, query, complexity):
        """
        Returns a dynamically generated retrieval plan based on the query.
        """
        retrieval_sources = self._select_memory_sources(complexity)
        retrieval_method = self._select_retrieval_method(complexity)
        summary_method = self._select_summarization_method(complexity)

        return {
            "retrieval_sources": retrieval_sources,
            "retrieval_method": retrieval_method,
            "needs_summarization": complexity == "complex",
            "summary_method": summary_method
        }

    def _select_memory_sources(self, complexity):
        """
        Selects which memory sources to retrieve from.
        """
        if complexity == "simple":
            return ["short_term"]
        elif complexity == "moderate":
            return ["long_term", "dynamic_contextual"]
        else:  # Complex query
            return ["short_term", "long_term", "dynamic_contextual", "external_apis"]

    def _select_retrieval_method(self, complexity):
        """
        Chooses retrieval strategy.
        """
        if complexity == "simple":
            return "exact_match"
        elif complexity == "moderate":
            return "semantic_search"
        else:
            return "hybrid"

    def _select_summarization_method(self, complexity):
        """
        Selects how to summarize the retrieved data.
        """
        if complexity == "simple":
            return None  # No summarization needed
        elif complexity == "moderate":
            return "extractive"
        else:
            return random.choice(["abstractive", "chain_of_thought"])
