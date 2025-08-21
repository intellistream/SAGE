import os

from transformers import AutoTokenizer, AutoModelForCausalLM

import torch

# DEFAULT_MODELS = {
#     "llama": "meta-llama/Llama-2-7b-chat-hf",
#     "mistral": "mistralai/Mistral-7B-v0.1",
#     "falcon": "tiiuae/falcon-7b-instruct",
#     "gptj": "EleutherAI/gpt-j-6B"
# }


import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

class HFClient:
    def __init__(self, model_name="llama", device=None, base_url = None, api_key=None, seed = None):
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name=model_name
        self.model, self.tokenizer = self._initialize_model()

    def _initialize_model(self):
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, trust_remote_code=True
        )
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            device_map="auto" if self.device == "cuda" else None
        )

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Ensure model on the right device if not using device_map
        if self.device != "cuda":
            model = model.to(self.device)

        return model, tokenizer

    def generate(self, prompt, **kwargs):
        # 设置生成参数
        generation_kwargs = {
            'max_new_tokens': kwargs.get('max_new_tokens', 128),  # 减少生成长度
            'temperature': kwargs.get('temperature', 0.3),        # 降低temperature
            'do_sample': True,
            'pad_token_id': self.tokenizer.eos_token_id,
            'eos_token_id': self.tokenizer.eos_token_id,
        }
        
        # Construct prompt text
        if isinstance(prompt, list):
            # 使用简单的格式化，避免复杂的chat template
            input_prompt = ""
            for message in prompt:
                role = message['role']
                content = message['content']
                if role == 'system':
                    input_prompt += f"System: {content}\n\n"
                elif role == 'user':
                    input_prompt += f"User: {content}\n\nAssistant: "
        elif isinstance(prompt, str):
            input_prompt = prompt

        print(f"Input prompt: {input_prompt[:200]}...")  # 调试信息
        
        # Tokenize input
        input_ids = self.tokenizer(
            input_prompt, 
            return_tensors="pt", 
            padding=True, 
            truncation=True,
            max_length=1024  # 限制输入长度
        ).to(self.device)
        
        print(f"Input token length: {input_ids['input_ids'].shape[1]}")  # 调试信息

        # Generate output
        try:
            with torch.no_grad():  # 节省内存
                output = self.model.generate(
                    **input_ids,
                    **generation_kwargs
                )
        except Exception as e:
            print(f"Generation error: {e}")
            return "Generation failed due to an error."

        # Decode output
        response_text = self.tokenizer.decode(
            output[0][input_ids["input_ids"].shape[1]:], 
            skip_special_tokens=True
        ).strip()

        print(f"Generated response: {response_text}")  # 调试信息
        return response_text