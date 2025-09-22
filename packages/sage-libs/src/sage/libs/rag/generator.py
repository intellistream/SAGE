import json
import os
import time
from collections import deque
from typing import Any, List, Tuple

import yaml
from sage.common.config.output_paths import get_states_file
from sage.core.api.function.map_function import MapFunction
from sage.libs.utils.huggingface import HFClient
from sage.libs.utils.openaiclient import OpenAIClient


class OpenAIGenerator(MapFunction):
    """
    生成节点：调用 OpenAI-Compatible / VLLM / DashScope 等端点。

    调用方式::
        sub_conf = config["generator"]["vllm"]   # <- 单端点子配置
        gen = OpenAIGenerator(sub_conf)

    其中 `sub_conf` 结构示例::

        {
          "method":     "openai",
          "model_name": "gpt-4o-mini",
          "base_url":   "http://localhost:8000/v1",
          "api_key":    "xxx",
          "seed":       42
        }
    """

    def __init__(self, config: dict, enable_profile=False, **kwargs):
        super().__init__(**kwargs)

        # 直接持有子配置
        self.config = config
        self.enable_profile = enable_profile

        # 实例化模型
        self.model = OpenAIClient(
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config["api_key"] or os.getenv("ALIBABA_API_KEY"),
            seed=self.config.get("seed", 42),
        )
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
            "model_name": self.config["model_name"],
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

    def execute(self, data: List[Any]) -> Tuple[str, str]:
        """
        输入 : [user_query, prompt]  *或*  [prompt]
        输出 : (user_query | None, generated_text)
        """
        user_query = data[0] if len(data) > 1 else None
        prompt = data[1] if len(data) > 1 else data[0]

        response = self.model.generate(prompt)
        self.num += 1

        # 保存数据记录（只有enable_profile=True时才保存）
        if self.enable_profile:
            self._save_data_record(user_query, prompt, response)

        self.logger.info(f"[{self.__class__.__name__}] Response: {response}")
        return user_query, response

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_data_records()
            except:
                pass


class HFGenerator(MapFunction):
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

    def execute(self, data: list, **kwargs) -> Tuple[str, str]:
        """
        Executes the response generation using the configured Hugging Face model based on the input data.

        :param data: Data object containing a list of input data.
                     The expected format and the content of the data depend on the model's requirements.
        :param kwargs: Additional parameters for the model generation (e.g., temperature, max_tokens, etc.).

        :return: A Data object containing the generated response as a string.
        """
        # Generate the response from the Hugging Face model using the provided data and additional arguments
        user_query = data[0] if len(data) > 1 else None

        prompt = data[1] if len(data) > 1 else data

        response = self.model.generate(prompt, **kwargs)

        print(f"\033[32m[ {self.__class__.__name__}]: Response: {response}\033[0m ")

        # Return the generated response as a Data object
        self.logger.info(
            f"\033[32m[ {self.__class__.__name__}]: Response: {response}\033[0m "
        )

        return (user_query, response)
