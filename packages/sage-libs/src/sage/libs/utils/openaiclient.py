from openai import OpenAI

class OpenAIClient():
    """
    Operator for generating natural language responses 

    Alibaba Could API:
        model_name="qwen-max"
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        api_key=""

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
        self.base_url = kwargs.get("base_url")
        self.api_key = kwargs.get("api_key")
        
        self.client = OpenAI(
            base_url= self.base_url, 
            api_key=self.api_key,
        )
        self.seed=kwargs["seed"]

    def generate(self, messages, **kwargs):
        """
        Chat-completion 封装
        --------------------
        * messages 允许传 list[dict] / dict ⇒ 最终转为 list[dict]
        * 支持 stream / n / logprobs 等 OpenAI 参数
        * 失败统一抛 RuntimeError 供上层捕获
        """
        try:
            # -------- 参数清理 --------
            # OpenAI 接口使用 max_tokens，保持与 up-stream 命名一致
            max_tokens = kwargs.get("max_tokens", kwargs.get("max_new_tokens", 3000))
            temperature = kwargs.get("temperature", 1.0)
            top_p = kwargs.get("top_p", None)
            stream = bool(kwargs.get("stream", False))
            frequency_penalty = kwargs.get("frequency_penalty", 0)
            n = int(kwargs.get("n", 1))
            want_logprobs = bool(kwargs.get("logprobs", False))

            # -------- 兼容 messages 形态 --------
            # dict => 包成单元素 list
            if isinstance(messages, dict):
                messages = [messages]
            if not isinstance(messages, list):
                raise ValueError("`messages` must be list[dict]")

            # -------- 调用 OpenAI --------
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                # n=n,
                # seed=self.seed,
                # stream=stream,
                # frequency_penalty=frequency_penalty,
                # logprobs=want_logprobs,
            )

            # -------- 流式返回 --------
            if stream:
                # 直接把 StreamingResponse 生成器交给上层迭代
                return response

            # -------- 非流式：解析 choice(s) --------
            def _extract(choice):
                txt = choice.message.content
                if want_logprobs:
                    logits = [lp.logprob for lp in choice.logprobs.content]
                    return txt, logits
                return txt

            if n == 1:
                return _extract(response.choices[0])
            else:
                return [_extract(c) for c in response.choices]

        except Exception as e:
            # 统一封装异常
            raise RuntimeError(f"Response generation failed: {e}") from e

