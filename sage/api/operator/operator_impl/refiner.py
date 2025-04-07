from sage.api.operator import RefinerFuction
from sage.api.operator import Data
from sage.api.model import apply_generator_model
from typing import Tuple,List
import logging
class AbstractiveRecompRefiner(RefinerFuction):
    """Abstractive refiner using RECOMP approach"""

    def __init__(self, config):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config=config["refiner"]
        self.model=apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config["api_key"],
            seed=42
        )

    def execute(self, data:Data[Tuple[str, List[str]]]) -> Data[Tuple[str, List[str]]]:
        try:
            # Prepare input
            query,doc_set=data.data
            emit_docs = []
            for retrieval_docs in doc_set:
                query,processed_docs=self._format_input(query, retrieval_docs)
                input_prompt=self.build_prompt(query, processed_docs)
                summary=self.model.generate(input_prompt)
                # print("summary:",summary)
                summary=[summary]
                emit_docs.append(summary)
        except Exception as e:
            self.logger.error(f"Refining failed: {str(e)}")
            raise RuntimeError(f"Refining error: {str(e)}")
        
        return Data((query,emit_docs[0]))

    def _format_input(self, question, retrieval_result):
        processed_docs = [
            "\n".join(doc.split("\n")[:])
            for doc in retrieval_result
        ]
        processed_docs = '\n'.join(processed_docs)
        return question, processed_docs

    def build_prompt(self,question, docs):
        user_content=f"""
        Generate a concise, factual summary from the document below that specifically answers the question. Follow these requirements:
        1. Extract ONLY information directly related to the question
        2. Present results using bullet points or short structured paragraphs
        3. Include critical elements: 
        - Numerical data/percentages 
        - Time periods/dates 
        - Definitive conclusions
        - Named entities (people/organizations/locations)
        4. Exclude speculative statements and irrelevant details

        Question:
        {question}

        Document:
        {docs}
        Summery:
        """
        return [{"role":"user","content":user_content}]
