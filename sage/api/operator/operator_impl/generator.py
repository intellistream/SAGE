
from typing import Any,Tuple
from sage.api.model import apply_generator_model
from sage.api.operator import GeneratorFunction
from sage.api.operator import Data
class OpenAIGenerator(GeneratorFunction):
    def __init__(self,config):
        super().__init__()
        self.config=config["generator"]
        self.model=apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config["api_key"],
            seed=42
        )
    def execute(self, data: Data[list], **kwargs) -> Data[Tuple[str,str]]:

        # if isinstance(combined_prompt,str):
        #     combined_prompt=[{"role":"user","content":combined_prompt}]
        user_query=data.data[1]["content"]
        response=self.model.generate(data.data,**kwargs)

        return Data((user_query,response))
        
class HFGenerator(GeneratorFunction):
    def __init__(self,config):
        super().__init__()
        self.config=config["generator"]
        self.model=apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"]
        )
    def execute(self, data: Data[list], **kwargs) -> Data[str]:

        # if isinstance(combined_prompt,str):
        #     combined_prompt=[{"role":"user","content":combined_prompt}]
        
        response=self.model.generate(data.data,**kwargs)

        return Data(response)