from sage_utils.clients.hf import HFGenerator
from sage_utils.clients.openaiclient import OpenAIClient
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


def apply_generator_model(method: str,**kwargs) -> GeneratorModel:
    """
    usage  参见sage/api/model/operator_test.py
    while name(method) = "hf", please set the param:model;
    while name(method) = "openai",if you need call other APIs which are compatible with openai,set the params:base_url,api_key,model;
    Example:operator_test.py
    """
    return GeneratorModel(method = method,**kwargs)
