import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer, util

from src.utils.text_processing import process_text_to_embedding
from src.core.neuromem.pipelines.query_planner import QueryPlanner

class IntegrationPipeline:
    """
    Adaptive retrieval and integration pipeline that dynamically selects retrieval sources,
    strategies, and applies intelligent summarization to reduce context size.
    """

    def __init__(self, memory_manager, model_name="meta-llama/Llama-3.2-1B-Instruct", device="cuda"):
        """
        Initialize the integration pipeline.
        :param memory_manager: Instance of NeuronMemManager to access STM, LTM, and DCM.
        :param model_name: LLaMA model for structured summarization.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.memory_manager = memory_manager
        self.query_planner = QueryPlanner()  # LLaMA-based retrieval planner

        # Load LLaMA for summarization
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(device)

        # Sentence Embedding Model for Relevance Filtering
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def execute(self, query):
        """
        Process the query by dynamically planning retrieval and summarization.
        :param query: The user input query.
        :return: Retrieved and summarized data.
        """
        # Step 1: Generate retrieval plan
        retrieval_plan = self.query_planner.plan_retrieval(query)
        self.logger.info(f"Generated Retrieval Plan: {retrieval_plan}")

        layers = retrieval_plan["memory_layers"]  # ["STM", "LTM", "DCM"]
        retrieval_strategy = retrieval_plan["retrieval_strategy"]
        k = retrieval_plan["k"]  # Number of results
        summarization = retrieval_plan["summarization"]

        # Step 2: Convert query to embedding if needed
        # query_embedding = None # TODO: Can be optimized if LTM DCM not queried
        # if retrieval_strategy in ["semantic search", "hybrid"]:
        query_embedding = process_text_to_embedding(query)
        key = None

        # Step 3: Retrieve from selected memory layers
        retrieved_data = []
        for layer in layers:
            data = self.memory_manager.retrieve_from_memory(
                memory_layer=layer,
                query_embedding=query_embedding,
                key = key,
                k=k)
            retrieved_data.extend(data)

        # # Step 4: Adaptive Summarization Strategy
        # total_tokens = sum(len(self.tokenizer.encode(text)) for text in retrieved_data)
        # max_tokens = self.model.config.max_position_embeddings * 0.8  # 80% of token limit

        summarized_data = retrieved_data
        # if total_tokens < max_tokens:
        #     summarized_data = retrieved_data  # No need for summarization
        # elif total_tokens < max_tokens * 1.5:
        #     summarized_data = self.extractive_summary(retrieved_data)
        # else:
        #     summarized_data = self.hierarchical_summary(query, retrieved_data)

        self.logger.info(f"Final Summarized Data: {summarized_data}")
        return summarized_data

    def relevance_filter(self, query, retrieved_data, threshold=0.6):
        """
        Filter out irrelevant retrieved results using sentence embedding similarity.
        """
        query_embedding = self.embedder.encode(query, convert_to_tensor=True)
        filtered_data = []

        for doc in retrieved_data:
            doc_embedding = self.embedder.encode(doc, convert_to_tensor=True)
            similarity = util.pytorch_cos_sim(query_embedding, doc_embedding).item()
            if similarity > threshold:
                filtered_data.append(doc)

        return filtered_data

    def extractive_summary(self, retrieved_data):
        """
        Extractive summarization: Return only the most relevant sentences.
        """
        return retrieved_data[:2]  # Top-k relevant results

    def hierarchical_summary(self, query, retrieved_data):
        """
        Hierarchical summarization to iteratively reduce context size.
        """
        batch_size = 3  # Summarize in groups of 3
        batched_summaries = []

        # Step 1: Summarize each batch separately
        for i in range(0, len(retrieved_data), batch_size):
            chunk = retrieved_data[i:i+batch_size]
            summary = self.llama_summarization(query, chunk)
            batched_summaries.append(summary)

        # Step 2: Summarize the summaries
        final_summary = self.llama_summarization(query, batched_summaries)
        return final_summary

    def llama_summarization(self, query, retrieved_data):
        """
        Generate structured summary using LLaMA.
        """
        formatted_context = "\n\n".join(f"- {data}" for data in retrieved_data)

        prompt = f"""
        Given the retrieved information below, generate a structured and logically coherent summary
        that directly answers the query:

        Query: "{query}"

        Retrieved Context:
        {formatted_context}

        Summary:
        """

        input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.model.device)
        output = self.model.generate(input_ids, max_new_tokens=150)
        summary = self.tokenizer.decode(output[0], skip_special_tokens=True)

        return summary


# import logging
#
# from src.core.neuromem.pipelines.query_classifier import QueryClassifier
# from src.core.neuromem.pipelines.retrieval_tuner import RetrievalTuner
# from src.utils.text_processing import process_text_to_embedding
#
# class IntegrationPipeline:
#     """
#     Adaptive pipeline for dynamic retrieval and summarization.
#     """
#
#     def __init__(self, memory_layers, classifier_model="meta-llama/Llama-3.2-1B-Instruct"):
#         """
#         Initialize memory layers and internal query classifier.
#         """
#         self.logger = logging.getLogger(self.__class__.__name__)
#         self.memory_layers = memory_layers
#
#         # Initialize components
#         self.query_classifier = QueryClassifier(model_name=classifier_model)
#         self.retrieval_tuner = RetrievalTuner()  # Determines retrieval & summarization strategy
#
#     def plan(self, query):
#         """
#         Creates an adaptive retrieval plan.
#         """
#         query_complexity = self.query_classifier.classify(query)  # Classify query
#         retrieval_plan = self.retrieval_tuner.tune(query, complexity=query_complexity)  # Tune strategy
#
#         self.logger.info(f"Generated retrieval plan: {retrieval_plan}")
#         return retrieval_plan
#
#     def retrieve(self, query, plan, k=3):
#         """
#         Retrieves data based on the generated retrieval plan.
#         """
#         query_embedding = process_text_to_embedding(query)
#         retrieved_data = []
#
#         for source in plan["retrieval_sources"]:
#             memory = self.memory_layers.get(source)
#             if not memory:
#                 continue
#
#             if plan["retrieval_method"] == "exact_match":
#                 retrieved_data.extend(memory.retrieve(key=query, k=k))
#             elif plan["retrieval_method"] == "semantic_search":
#                 retrieved_data.extend(memory.retrieve(query_embedding=query_embedding, k=k))
#             elif plan["retrieval_method"] == "hybrid":
#                 exact_results = memory.retrieve(key=query, k=k//2)
#                 semantic_results = memory.retrieve(query_embedding=query_embedding, k=k//2)
#                 retrieved_data.extend(exact_results + semantic_results)
#
#         return retrieved_data
#
#     def summarize(self, context, plan):
#         """
#         Summarizes retrieved context dynamically.
#         """
#         if not plan["needs_summarization"]:
#             return context
#
#         summary_method = plan["summary_method"]
#
#         if summary_method == "extractive":
#             return " ".join([str(item) for item in context])[:512]  # Truncate
#         elif summary_method == "abstractive":
#             return self._abstractive_summarize(context)
#         elif summary_method == "chain_of_thought":
#             return self._chain_of_thought_summarize(context)
#
#     def _abstractive_summarize(self, context):
#         """
#         Abstractive summarization (stub).
#         """
#         return f"Summarized context (abstractive): {context[:512]}"
#
#     def _chain_of_thought_summarize(self, context):
#         """
#         Chain-of-thought summarization (stub).
#         """
#         return f"Step-by-step reasoning summary: {context[:512]}"