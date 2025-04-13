from .openaiclient import OpenAIClient
from .hf import HFGenerator

# class GeneratorModel:
#     def __init__(self, method: str, model_name: str, **kwargs):
#         if method=="openai":
#             self.model=OpenAIClient(model_name,**kwargs)
#         elif method=="hf":
#             self.model=HFGenerator(model_name,**kwargs)
#         else:
#             raise ValueError("this method isn't supported")
        
#     def generate(self, prompt: str, **kwargs) :

#         response=self.model.generate(prompt, **kwargs)

#         return response


class GeneratorFactory:
    @staticmethod
    def create_generator(method: str, model_name: str, **kwargs):
        """
        根据不同的 method 创建对应的生成器
        """
        if method == "openai":
            return OpenAIClient(model_name, **kwargs)
        elif method == "hf":
            return HFGenerator(model_name, **kwargs)
        else:
            raise ValueError("This method isn't supported")

class GeneratorModel:
    def __init__(self, method: str, model_name: str, **kwargs):
        # 使用工厂方法创建模型
        self.model = GeneratorFactory.create_generator(method, model_name, **kwargs)

    def generate(self, prompt: str, **kwargs):
        # 调用生成模型的生成方法
        return self.model.generate(prompt, **kwargs)


if __name__ == '__main__':
    prompt=[{"role":"user","content":"who are you"}]
    generator=OpenAIClient(model_name="qwen-max",base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",api_key="",seed=42)
    response=generator.generate((prompt))
    print(response)

