from typing import Any
from sage.api.model import apply_generator_model
from sage.api.operator import GeneratorFunction
class OpenAIGenerator(GeneratorFunction):
    def __init__(self):
        super().__init__()
        self.model=apply_generator_model(
            method="openai",
            name="qwen-max",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="sk-b21a67cf99d14ead9d1c5bf8c2eb90ef",
            seed=42
        )
    def execute(self, combined_prompt, **kwargs) -> str:

        if isinstance(combined_prompt,str):
            combined_prompt=[{"role":"user","content":combined_prompt}]
        
        response=self.model.generate(combined_prompt,**kwargs)

        return response
        
class vllmGenerator(GeneratorFunction):
    def __init__(self):
        super().__init__()
        self.model=apply_generator_model(
            method="vllm",
            name="meta-llama/Llama-2-13b-chat-hf"
        )
    def execute(self, combined_prompt, **kwargs) -> str:

        if isinstance(combined_prompt,str):
            combined_prompt=[{"role":"user","content":combined_prompt}]
        
        response=self.model.generate(combined_prompt,**kwargs)

        return response