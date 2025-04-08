from .openaiclient import OpenAIClient
from .hf import HFGenerator

class GeneratorModel:
    def __init__(self, method: str, model_name: str, **kwargs):
        if method=="openai":
            self.model=OpenAIClient(model_name,**kwargs)
        elif method=="hf":
            self.model=HFGenerator(model_name,**kwargs)
        else:
            raise ValueError("this method isn't supported")
        
    def generate(self, prompt: str, **kwargs) :

        response=self.model.generate(prompt, **kwargs)

        return response


if __name__ == '__main__':
    prompt=[{"role":"user","content":"who are you"}]
    generator=OpenAIClient(model_name="qwen-max",base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",api_key="",seed=42)
    response=generator.generate((prompt))
    print(response)

