import os

from transformers import AutoTokenizer, AutoModelForCausalLM

import torch

# DEFAULT_MODELS = {
#     "llama": "meta-llama/Llama-2-7b-chat-hf",
#     "mistral": "mistralai/Mistral-7B-v0.1",
#     "falcon": "tiiuae/falcon-7b-instruct",
#     "gptj": "EleutherAI/gpt-j-6B"
# }


class HFGenerator:
    def __init__(self, model_name="llama", device=None):
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name=model_name
        self.model, self.tokenizer = self._initialize_model()


    def _initialize_model(self):
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, device_map="auto", trust_remote_code=True
        )
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name, device_map="auto", trust_remote_code=True
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        return model, tokenizer

    def generate(self, prompt, **kwargs):
        input_prompt = ""
        if isinstance(prompt,list):
            for message in prompt:
                input_prompt += f"<{message['role']}>{message['content']}</{message['role']}>\n"
        
        input_ids = self.tokenizer(
            input_prompt, return_tensors="pt", padding=True, truncation=True
        ).to("cuda")

        inputs = {k: v.to(self.model.device) for k, v in input_ids.items()}
        output = self.model.generate(
            **inputs,
            max_new_tokens=kwargs.get("max_new_tokens", 512),
            num_return_sequences=kwargs.get("num_return_sequences", 1),
            temperature=kwargs.get("temperature", 1.0),
            top_k=kwargs.get("top_k", 50),
            top_p=kwargs.get("top_p", 1.0),
            repetition_penalty=kwargs.get("repetition_penalty", 1.0),
            do_sample=kwargs.get("do_sample", True)
        )
        response_text = self.tokenizer.decode(
            output[0][len(inputs["input_ids"][0]) :], skip_special_tokens=True
        )
        
        return response_text


if __name__ == '__main__':
    prompt=[{"role":"user","content":"who are you"}]
    generator=HFGenerator(model_name="meta-llama/Llama-2-13b-chat-hf")
    response=generator.generate(prompt)
    print(response)