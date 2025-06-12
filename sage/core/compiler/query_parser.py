import random
from typing import List, Dict

class QueryParser:
    def __init__(self, generate_func):
        """
        :param generate_func: A function that sends prompt to LLM and returns raw string response.
        """
        self.generate = generate_func
        self.examples_pool: Dict[str, List[Dict[str, str]]] = {
            "question-answering": [
                {"query": "How tall is the Eiffel Tower?"},
                {"query": "What is the main therapeutic approach described?"},
                {"query": "What is the backstory of the main character, Zara?"},
                {"query": "How can I turn off push notifications?"},
                {"query": "How do I redeem cashback rewards?"}
            ],
            "summarization": [
                {"query": "What are the key takeaways from this section?"},
                {"query": "What did the guests mainly discuss?"},
                {"query": "Give me the main points so I can present them."}
            ],
            "generation": [
                {"query": "Suggest a product name that feels modern and chill."},
                {"query": "Generate a marketing tagline in under 10 words."},
                {"query": "Give me 3 playful app names for this product."}
            ],
            "classification": [
                {"query": "Label each log as high, medium, or low latency."},
                {"query": "Categorize responses based on satisfaction level."}
            ],
            "transformation": [
                {"query": "Rewrite this review in formal business language."},
                {"query": "Simplify this for a non-lawyer audience."}
            ],
            "other": [
                {"query": "What’s your favorite color in the design?"},
                {"query": "Do you think this conversation is going somewhere?"}
            ]
        }

    def get_few_shot_examples(self, n_per_intent=1) -> List[Dict[str, str]]:
        selected = []
        for intent, pool in self.examples_pool.items():
            sampled = random.sample(pool, min(n_per_intent, len(pool)))
            for item in sampled:
                selected.append({
                    "query": item["query"],
                    "intent": intent
                })
        return selected

    def format_examples_for_prompt(self, examples: List[Dict[str, str]]) -> str:
        formatted = []
        for ex in examples:
            formatted.append(
                f"Query: {ex['query']}\nIntent: {ex['intent']}"
            )
        return "\n".join(formatted)

    def parse_query(self, natural_query: str, n_per_intent: int = 1) -> str:
        few_shots = self.get_few_shot_examples(n_per_intent=n_per_intent)
        examples_block = self.format_examples_for_prompt(few_shots)

        parse_prompt = f"""
Classify the intent of the given query into one of the following categories:
- question-answering: Asking a specific or factual question.
- summarization: Requesting a summary or key points.
- generation: Creating new content, names, or ideas.
- classification: Labeling or categorizing data.
- transformation: Rephrasing, simplifying, or translating text.
- other: None of the above.

Instructions:
1. Read the query carefully.
2. Select the most appropriate intent from the list.
3. Output only the intent label in the format: Intent: <label>
4. Do not include explanations or additional text.

Examples:
{examples_block}

Query: {natural_query}
Intent:
"""

        system_prompt = {
            "role": "system",
            "content": "You are a precise intent classifier. Output only 'Intent: <label>' with the intent label."
        }
        user_prompt = {
            "role": "user",
            "content": parse_prompt
        }

        prompt = [system_prompt, user_prompt]
        raw_response = self.generate(prompt=prompt, temperature=0.0)
        parsed_intent = "question_answering" if "question-answering" in raw_response else \
                        "summarization" if "summarization" in raw_response else \
                        "generation" if "generation" in raw_response else \
                        "classification" if "classification" in raw_response else \
                        "transformation" if "transformation" in raw_response else \
                        "other"
        return parsed_intent