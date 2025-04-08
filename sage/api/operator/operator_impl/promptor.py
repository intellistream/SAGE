from typing import Any, List, Tuple
from jinja2 import Template
from sage.api.operator import PromptFunction
from sage.api.operator import Data
QA_prompt_template='''Instruction:
You are an intelligent assistant with access to a knowledge base. Answer the question below with reference to the provided context.
Only give me the answer and do not output any other words.
{%- if external_corpus %}
Relevant corpus for the current question:
{{ external_corpus }}
{%- endif %}
'''
QA_prompt_template = Template(QA_prompt_template)

class QAPromptor(PromptFunction):
    def __init__(self,config):
        super().__init__()
        self.config=config
        self.prompt_template=QA_prompt_template

    def execute(self, data: Data[Tuple[str, List[str]]]) -> Data[list]:
        query,external_corpus=data.data
        external_corpus = "".join(external_corpus) 
        base_system_prompt_data = {
                "external_corpus": external_corpus
        }
        system_prompt={"role":"system","content":self.prompt_template.render(**base_system_prompt_data)}
        user_prompt={"role":"user","content":f"Question: {query}"}

        prompt=[system_prompt,user_prompt]

        return Data(prompt)
    

