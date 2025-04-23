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
                {
                    "context": "A short article about the Eiffel Tower.",
                    "query": "How tall is the Eiffel Tower?"
                },
                {
                    "context": "A research paper abstract about Alzheimer's treatment.",
                    "query": "What is the main therapeutic approach described?"
                },
                {
                    "context": "A fictional character bio from a game design document.",
                    "query": "What is the backstory of the main character, Zara?"
                },
                {
                    "context": "Documentation on how the app handles notifications.",
                    "query": "How can I turn off push notifications?"
                },
                {
                    "context": "An FAQ about a new credit card rewards system.",
                    "query": "How do I redeem cashback rewards?"
                }
            ],
            "retrieval": [
                {
                    "context": "Wikipedia article about Ada Lovelace.",
                    "query": "What is Ada Lovelace best known for?"
                },
                {
                    "context": "FAQ page of a payment system.",
                    "query": "Is there a fee for international transfers?"
                },
                {
                    "context": "A report on carbon emissions by industry sector.",
                    "query": "Which industry has the highest emission rate?"
                }
            ],
            "summarization": [
                {
                    "context": "A report detailing quarterly financial metrics and regional differences.",
                    "query": "What are the key takeaways from this section?"
                },
                {
                    "context": "Transcript of a podcast episode on renewable energy.",
                    "query": "What did the guests mainly discuss?"
                },
                {
                    "context": "An internal memo reviewing customer satisfaction surveys.",
                    "query": "Give me the main points so I can present them."
                }
            ],
            "generation": [
                {
                    "context": "Design brief for a coffee brand targeted at Gen Z.",
                    "query": "Suggest a product name that feels modern and chill."
                },
                {
                    "context": "Product description for a smart lamp.",
                    "query": "Generate a marketing tagline in under 10 words."
                },
                {
                    "context": "User request for naming a pet tracker app.",
                    "query": "Give me 3 playful app names for this product."
                }
            ],
            "classification": [
                {
                    "context": "Log data from different network nodes.",
                    "query": "Label each log as high, medium, or low latency."
                },
                {
                    "context": "Survey results from different customer types.",
                    "query": "Categorize responses based on satisfaction level."
                }
            ],
            "transformation": [
                {
                    "context": "A negative product review in casual tone.",
                    "query": "Rewrite this review in formal business language."
                },
                {
                    "context": "A paragraph describing a complex legal clause.",
                    "query": "Simplify this for a non-lawyer audience."
                }
            ],
            "other": [
                {
                    "context": "Description of a poster about Earth Day.",
                    "query": "What’s your favorite color in the design?"
                },
                {
                    "context": "A philosophical dialogue between two AI models.",
                    "query": "Do you think this conversation is going somewhere?"
                }
            ]
        }

    def get_few_shot_examples(self, n_per_intent=1) -> List[Dict[str, str]]:
        selected = []
        for intent, pool in self.examples_pool.items():
            sampled = random.sample(pool, min(n_per_intent, len(pool)))
            for item in sampled:
                selected.append({
                    "context": item["context"],
                    "query": item["query"],
                    "intent": intent
                })
        return selected

    def format_examples_for_prompt(self, examples: List[Dict[str, str]]) -> str:
        formatted = []
        for ex in examples:
            formatted.append(
                f"Context: {ex['context']}\nQuery: {ex['query']}\nIntent: {ex['intent']}\n"
            )
        return "\n".join(formatted)

    def parse_query(self, natural_query: str, context: str = "", n_per_intent: int = 1) -> str:
        few_shots = self.get_few_shot_examples(n_per_intent=n_per_intent)
        examples_block = self.format_examples_for_prompt(few_shots)

        parse_prompt = f"""
---Goal---
Determine the intent behind a natural language query. You must classify the query into **one** of the following predefined intent types:

- question-answering: Asking a specific, contextual or precise question based on the provided text or document.
- summarization: Asking to condense or extract key points from a body of content.
- generation: Asking to create new content, ideas, names, taglines, etc.
- classification: Asking to categorize or label the input.
- transformation: Asking to rephrase, simplify, translate, or convert the input.
- retrieval: Asking for general knowledge, broad factual info, or well-known concepts.
- other: If none of the above clearly apply.

---Instructions---
1. Carefully read the query and its context.
2. Choose the most appropriate intent from the list.
3. Respond with one word only. Do not explain or comment.
Output format: <intent>

---Examples---
{examples_block}

---Query to Process---
Context: {context if context else "None"}
Query: {natural_query}
Intent:
"""

        raw_response = self.generate(parse_prompt, temperature=0.0)
        parsed_intent = "question-answering"  if "question-answering" in raw_response else \
                        "retrieval" if "retrieval" in raw_response else \
                        "summarization" if "summarization" in raw_response else \
                        "generation" if "generation" in raw_response else \
                        "classification" if "classification" in raw_response else \
                        "transformation" if "transformation" in raw_response else \
                        "other"

        return parsed_intent
