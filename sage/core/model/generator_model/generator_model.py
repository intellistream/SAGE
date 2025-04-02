from openai import OpenAI
class OpenAIClient():
    """
    Operator for generating natural language responses 

    Alibaba Could API:
        model_name="qwen-max"
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        api_key="sk-b21a67cf99d14ead9d1c5bf8c2eb90ef"

    Ollama API:
        model_name="llama3.1:8b"
        base_url="http://222.20.77.1:11434/v1"   
        api_key="empty"

    vllm API
        model_name="meta-llama/Llama-2-13b-chat-hf"
        base_url="http://localhost:8000/v1"   
        api_key="empty"
    
    """

    def __init__(self,model_name="qwen-max",**kwargs):
        """
        Initialize the generator with a specified model and base_url.
        :param model_name: The Hugging Face model to use for generation.
        :param base_url: The base url to request.
        :param api_key: Api key to validate.
        :param seed: Seed for reproducibility.
        """
        self.model_name=model_name
        self.base_url = kwargs["base_url"]
        self.api_key = kwargs["api_key"] 
        self.client = OpenAI(
            base_url= self.base_url, 
            api_key=self.api_key,
        )
        self.seed=kwargs["seed"]

    def generate(self, prompt , **kwargs):
        """
        Generate a response using the model.
        :param input_data: Preformatted QA-template input string.
        :param kwargs: Additional parameters for generation.
        :return: Generated response.
        """
        try:
            max_tokens = kwargs.get("max_new_tokens", 100)
            temperature = kwargs.get("temperature", 1.0)  # Default temperature
            top_p = kwargs.get("top_p", None)  # Disable top-p sampling by default
            stream= kwargs.get("stream", False)
            frequency_penalty= kwargs.get("frequency_penalty", 0) #The higher it is, the more it reduces repetitive wording and prevents looping responses.
            n=kwargs.get("n",1)
            # Generate output
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=prompt,
                top_p=top_p,
                temperature=temperature,
                stream=stream,
                max_tokens=max_tokens,
                n=1,
                seed=self.seed,
                frequency_penalty=frequency_penalty,
            )
            
            if stream:
                collected_response = ""
                for chunk in response:

                    if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta 
                        if hasattr(delta, "content") and delta.content:  
                            collected_response=delta.content
                        if chunk.choices[0].finish_reason:  
                            break  
            
                response = collected_response 
            else:
                response=response.choices[0].message.content

            return response

        except Exception as e:
            raise RuntimeError(f"Response generation failed: {str(e)}")

class VLLMGenerator():
    """Class for decoder-only generator, based on vllm."""

    def __init__(self, model_name="meta-llama/Llama-2-13b-chat-hf"):
        from vllm import LLM
        self.model=LLM(model="meta-llama/Llama-2-13b-chat-hf")

    def generate(self,prompt, **kwargs):

        from vllm import SamplingParams
        max_tokens = kwargs.get("max_new_tokens", 100)
        temperature = kwargs.get("temperature", 1.0)  # Default temperature
        top_p = kwargs.get("top_p", 1.0)  # Disable top-p sampling by default
        stream= kwargs.get("stream", False)
        frequency_penalty= kwargs.get("frequency_penalty", 0) #The higher it is, the more it reduces repetitive wording and prevents looping responses.
        n=kwargs.get("n",1)
    

        sampling_params = SamplingParams(
            n=n,
            frequency_penalty=frequency_penalty,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        # prompt = " | ".join([f"{p['role'].upper()}: {p['content']}" for p in prompt])
        response = self.model.generate(prompt, sampling_params)


        return response

if __name__ == '__main__':
    prompt=[{"role":"user","content":"who are you"}]
    generator=OpenAIClient(model_name="qwen-max",base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",api_key="sk-b21a67cf99d14ead9d1c5bf8c2eb90ef",seed=42)
    response=generator.generate((prompt))
    print(response)

