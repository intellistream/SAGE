import os
import yaml
from typing import Tuple, List, Any
from collections import deque

from sage.core.function.map_function import MapFunction
from sage.core.function.base_function import StatefulFunction
from sage.utils.clients.generator_model import apply_generator_model
from sage.utils.state_persistence import load_function_state, save_function_state


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

    def __init__(self, config: dict, **kwargs):
        super().__init__(**kwargs)

        # 直接持有子配置
        self.config = config

        # 实例化模型
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config["api_key"] or os.getenv("ALIBABA_API_KEY"),
            seed=self.config.get("seed", 42),
        )
        self.num = 1

    def execute(self, data: List[Any]) -> Tuple[str, str]:
        """
        输入 : [user_query, prompt]  *或*  [prompt]
        输出 : (user_query | None, generated_text)
        """
        user_query = data[0] if len(data) > 1 else None
        prompt = data[1] if len(data) > 1 else data[0]

        response = self.model.generate(prompt)
        self.num += 1

        self.logger.info(f"[{self.__class__.__name__}] Response: {response}")
        return user_query, response


class OpenAIGeneratorWithHistory(StatefulFunction):
    """
    带滚动对话历史的生成节点。
    子配置格式与 OpenAIGenerator 相同，并可额外设置 ::

        {
          ...,
          "max_history_turns": 5
        }
    """

    def __init__(self, config: dict, **kwargs):
        super().__init__(**kwargs)

        # 子配置直接使用
        self.config = config
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config["api_key"] or os.getenv("ALIBABA_API_KEY"),
            seed=self.config.get("seed", 42),
        )

        # 对话历史
        self.dialogue_history: List[dict] = []
        self.history_turns = self.config.get("max_history_turns", 5)
        self.num = 1

        # 尝试恢复历史
        base = os.path.join(self.ctx.session_folder, ".sage_checkpoints")
        os.makedirs(base, exist_ok=True)
        self.chkpt_path = os.path.join(base, f"{self.ctx.name}.chkpt")
        load_function_state(self, self.chkpt_path)

    def execute(self, data: List[Any], **kwargs) -> Tuple[str, str]:
        """
        期望输入 : [user_query, prompt_list]
        prompt_list == [{"role": "user"/"system", "content": ...}, ...]
        """
        user_query = data[0] if len(data) > 1 else None
        prompt_info = data[1] if len(data) > 1 else data[0]

        new_turns = [e for e in prompt_info if e["role"] in ("user", "system")]
        history_to_use = self.dialogue_history[-2 * self.history_turns:]
        full_prompt = history_to_use + new_turns

        self.logger.debug(f"[Prompt with history]:\n{full_prompt}")
        response = self.model.generate(full_prompt, **kwargs)

        # 更新历史
        for entry in new_turns:
            if entry["role"] == "user":
                self.dialogue_history.append(entry)
        self.dialogue_history.append({"role": "assistant", "content": response})
        self.dialogue_history = self.dialogue_history[-2 * self.history_turns:]

        self.logger.info(f"\033[32m[{self.__class__.__name__}] Response: {response}\033[0m")

        # 自动持久化
        save_function_state(self, self.chkpt_path)
        return user_query, response

    # 手动保存接口（可选）
    def save_state(self):
        save_function_state(self, self.chkpt_path)


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
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"]
        )

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

        # Return the generated response as a Data object
        self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Response: {response}\033[0m ")

        return (user_query, response)
