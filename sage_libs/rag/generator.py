import os
from typing import Tuple,List
from sage_common_funs.utils.generator_model import apply_generator_model
from sage_core.function.map_function import MapFunction 
from sage_core.function.base_function import StatefulFunction
from sage_utils.custom_logger import CustomLogger
from sage_runtime.state_persistence import load_function_state, save_function_state

class OpenAIGenerator(MapFunction):
    """
    OpenAIGenerator is a generator rag that interfaces with a specified OpenAI model
    to generate responses based on input data.
    """

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)

        """
        Initializes the OpenAIGenerator instance with configuration parameters.

        :param config: Dictionary containing configuration for the generator, including 
                       the method, model name, base URL, API key, etc.
        """
        self.config = config
        # Apply the generator model with the provided configuration
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config["api_key"] or os.getenv("ALIBABA_API_KEY"),
            seed=42  # Hardcoded seed for reproducibility
        )
        self.num = 1



    # 其中原有的**kwargs应该由函数内部或者data内部提供
    def execute(self, data: list) -> Tuple[str, str]:
        """
        Executes the response generation using the configured model based on the input data.

        :param data: Data object containing a list of input data.
                     The second item in the list is expected to be a dictionary with a "content" key that contains the user's query.
        :param kwargs: Additional parameters for the model generation (e.g., temperature, max_tokens, etc.).

        :return: A Data object containing a tuple (user_query, response), where user_query is the original input query,
                and response is the generated response from the model.
        """
        # Extract the user query from the input data
        user_query = data[0] if len(data) > 1  else None
 
        prompt = data[1] if len(data) > 1 else data

        response = self.model.generate(prompt)

        self.num += 1

        self.logger.info(f"[ {self.__class__.__name__}]: Response: {response}")

        # Return the generated response along with the original user query as a tuple
        return (user_query, response)

class OpenAIGeneratorWithHistory(StatefulFunction):
    """
    OpenAIGenerator with global dialogue memory.
    Maintains a rolling history of past user and assistant turns (stateful).
    """

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config

        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=os.getenv("ALIBABA_API_KEY"),
            seed=42
        )

        # 全局历史状态，按对话轮次记录字符串
        self.dialogue_history: List[str] = []
        self.history_turns = config.get("max_history_turns", 5)
        self.num = 1

        base = os.path.join(self.runtime_context.session_folder, ".sage_checkpoints")
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, f"{self.runtime_context.name}.chkpt")
        load_function_state(self, path)

    def execute(self, data: List, **kwargs) -> Tuple[str, str]:
        """
        Expects input data: [user_query, prompt_dict]
        Where prompt_dict includes {"content": ...}
        """
        # 延迟恢复：在首次执行前根据 runtime_context 恢复状态


        user_query = data[0] if len(data) > 1 else None
        prompt_info = data[1] if len(data) > 1 else data

        new_turns = [entry for entry in prompt_info if entry["role"] in ("user", "system")]

        history_to_use = self.dialogue_history[-2 * self.history_turns:]
        full_prompt = history_to_use + new_turns

        self.logger.debug(f"[Prompt with history]:\n{full_prompt}")

        response = self.model.generate(full_prompt, **kwargs)

        for entry in new_turns:
            if entry["role"] == "user":
                self.dialogue_history.append(entry)
        self.dialogue_history.append({"role": "assistant", "content": response})
        self.dialogue_history = self.dialogue_history[-2 * self.history_turns:]  # 保留最近 N 轮

        self.logger.info(f"\033[32m[{self.__class__.__name__}] Response: {response}\033[0m")

        # —— 自动持久化：每次 execute 后保存状态 —— 
        base = os.path.join(self.runtime_context.session_folder, ".sage_checkpoints")
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, f"{self.runtime_context.name}.chkpt")
        save_function_state(self, path)
        return (user_query, response)
    
    def save_state(self):
        """
        手动触发：持久化当前 dialogue_history，用于测试调用。
        """
        base = os.path.join(self.runtime_context.session_folder, ".sage_checkpoints")
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, f"{self.runtime_context.name}.chkpt")
        save_function_state(self, path)

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
        user_query = data[0] if len(data) > 1  else None
 
        prompt = data[1] if len(data) > 1 else data
        
        response = self.model.generate(prompt, **kwargs)

        # Return the generated response as a Data object
        self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Response: {response}\033[0m ")

        return (user_query, response)
