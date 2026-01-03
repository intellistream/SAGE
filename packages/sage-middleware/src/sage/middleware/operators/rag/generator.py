import json
import os
import time
from typing import Any

from openai import OpenAI

from sage.common.config.output_paths import get_states_file
from sage.common.core.functions import MapFunction as MapOperator
from sage.libs.integrations.huggingface import HFClient


class OpenAIGenerator(MapOperator):
    """
    生成节点：调用 OpenAI-Compatible / VLLM 等端点。

    调用方式::
        sub_conf = config["generator"]["vllm"]   # <- 单端点子配置
        gen = OpenAIGenerator(sub_conf)

    其中 `sub_conf` 结构示例::

        {
          "method":     "openai",
          "model_name": "gpt-4o-mini",
          "base_url":   "http://localhost:8000/v1",
          "api_key":    "xxx",  # pragma: allowlist secret
          "seed":       42
        }
    """

    def __init__(self, config: dict, enable_profile=False, **kwargs):
        super().__init__(**kwargs)

        # 直接持有子配置
        self.config = config
        self.enable_profile = enable_profile

        # 实例化模型
        # API key 优先级: 配置文件 > OPENAI_API_KEY
        api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")

        # 获取必需的配置参数（使用 .get() 提供默认值）
        model_name = self.config.get("model_name") or self.config.get("model", "gpt-3.5-turbo")
        # 展开环境变量（如果 model_name 包含环境变量）
        model_name = os.path.expandvars(model_name)
        base_url = self.config.get("base_url", "https://api.openai.com/v1")

        # 直接使用 OpenAI 客户端（支持 vLLM 等 OpenAI 兼容 API）
        self.model = OpenAI(
            base_url=base_url,
            api_key=api_key or "EMPTY",  # vLLM 本地服务可用任意 key
        )
        self.model_name = model_name
        self.num = 1

        # 只有启用profile时才设置数据存储路径
        if self.enable_profile:
            # Use unified output path system
            self.data_base_path = str(get_states_file("dummy", "generator_data").parent)
            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

    def _save_data_record(self, query, prompt, response):
        """保存生成数据记录"""
        if not self.enable_profile:
            return

        record = {
            "timestamp": time.time(),
            "query": query,
            "prompt": prompt,
            "response": response,
            "model_name": self.config.get("model_name") or self.config.get("model", "unknown"),
        }
        self.data_records.append(record)
        self._persist_data_records()

    def _persist_data_records(self):
        """将数据记录持久化到文件"""
        if not self.enable_profile or not self.data_records:
            return

        timestamp = int(time.time())
        filename = f"generator_data_{timestamp}.json"
        path = os.path.join(self.data_base_path, filename)

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    def execute(self, data: list[Any]) -> dict[str, Any]:
        """
        输入 : [original_data, prompt]  *或*  [prompt]
        输出 : 完整的数据字典，包含 generated 字段

        prompt 可以是:
        - str: 普通字符串，将转换为 [{"role": "user", "content": prompt}]
        - list[dict]: 已格式化的消息列表，直接传递给 OpenAI API
        """
        # 解析输入数据
        if len(data) > 1:
            # 来自QAPromptor: [original_data, prompt]
            original_data = data[0]
            prompt = data[1]
        else:
            # 直接prompt输入: [prompt]
            original_data = {}
            prompt = data[0]

        # 提取user_query
        if isinstance(original_data, dict):
            user_query = original_data.get("query", original_data.get("question", ""))
        else:
            user_query = None

        # 如果 prompt 是字符串，转换为标准消息格式
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list) and all(isinstance(item, dict) for item in prompt):
            # 如果已经是消息列表格式，直接使用
            messages = prompt
        else:
            # 兜底处理：转换为字符串再构造消息
            messages = [{"role": "user", "content": str(prompt)}]

        # 准备生成参数（从配置中提取）
        generate_kwargs = {}

        # 支持的参数列表
        supported_params = [
            "max_tokens",
            "temperature",
            "top_p",
            "enable_thinking",  # Qwen 特有参数：禁用思考过程输出
            "stream",
            "frequency_penalty",
            "n",
            "logprobs",
        ]

        # 从配置中提取参数并传递给 generate
        for param in supported_params:
            if param in self.config:
                generate_kwargs[param] = self.config[param]

        # 使用 OpenAI 客户端调用 chat completions API
        completion = self.model.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **generate_kwargs,
        )
        response = completion.choices[0].message.content

        self.num += 1

        # 保存数据记录（只有enable_profile=True时才保存）
        if self.enable_profile:
            self._save_data_record(user_query, prompt, response)

        self.logger.info(f"[{self.__class__.__name__}] Response: {response}")

        # 构建完整的输出数据，保持上游数据
        if isinstance(original_data, dict):
            # 保持原始数据结构，添加generated字段
            result = dict(original_data)
            result["generated"] = response
            # generate_time 由 MapOperator 自动添加
            result["question"] = result.get(
                "question",
                {"query": user_query, "references": result.get("references", [])},
            )
            return result
        else:
            # 兼容原有tuple格式输出，但符合返回类型
            return {
                "query": user_query if user_query is not None else "",
                "generated": response,
                # generate_time 由 MapOperator 自动添加
            }

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_data_records()
            except Exception:
                pass


class HFGenerator(MapOperator):
    """
    HFGenerator is a generator rag that interfaces with a Hugging Face model
    to generate responses based on input data.
    """

    def __init__(self, config, **kwargs):
        """
        Initializes the HFGenerator instance with configuration parameters.

        :param config: Dictionary containing configuration for the generator, including
                       the method and model name.
        """
        super().__init__(**kwargs)
        self.config = config
        # Apply the generator model with the provided configuration
        self.model = HFClient(model_name=self.config["model_name"])

    def execute(self, data: list, **kwargs) -> tuple[str, str]:
        """
        Executes the response generation using the configured Hugging Face model based on the input data.

        :param data: Data object containing a list of input data.
                     The expected format and the content of the data depend on the model's requirements.
        :param kwargs: Additional parameters for the model generation (e.g., temperature, max_tokens, etc.).

        :return: A Data object containing the generated response as a string.
        """
        # Generate the response from the Hugging Face model using the provided data and additional arguments
        user_query = data[0] if len(data) > 1 else None

        prompt = data[1] if len(data) > 1 else data[0]

        response = self.model.generate(prompt, **kwargs)

        print(f"\033[32m[ {self.__class__.__name__}]: Response: {response}\033[0m ")

        # Return the generated response as a Data object
        self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Response: {response}\033[0m ")

        return (
            user_query if user_query is not None else "",
            response if isinstance(response, str) else str(response),
        )
