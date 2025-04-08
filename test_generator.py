import sage
class LlamaGenerator(sage.operator.GeneratorFunction):
    def __init__(self):
        super().__init__()
        # Load or configure a local or remote LLM (e.g., llama_8b)
        self.model = sage.model.apply_generator_model(method="openai",name="qwen-max",base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",api_key="sk-b21a67cf99d14ead9d1c5bf8c2eb90ef",seed=42)

    # Generates the model's response given a prompt string
    def execute(self, combined_prompt, **kwargs):
        if isinstance(combined_prompt,str):
            combined_prompt=[{"role":"user","content":combined_prompt}]
        return self.model.generate(combined_prompt, **kwargs)


g=LlamaGenerator()
# prompt=[{"role":"user","content":"who are you"}]
prompt="who are you"
print(g.execute(prompt))