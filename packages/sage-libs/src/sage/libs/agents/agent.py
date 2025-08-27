from sage.core.api.function.map_function import MapFunction

from typing import Tuple
import requests
import json
import re, time

from sage.libs.utils.openaiclient import OpenAIClient


class Tool:
    def __init__(self, name, func, description):
        self.name = name
        self.func = func
        self.description = description

    def run(self, *args, **kwargs):
        return self.func(*args, **kwargs)
    
class BochaSearch:
    def __init__(self,api_key):
        self.url = "https://api.bochaai.com/v1/web-search"
        self.api_key = api_key
        self.headers = {
            'Authorization': api_key,
            'Content-Type': 'application/json'
        }

    def run(self, query):
        payload = json.dumps({
            "query": query,
            "summary": True,
            "count": 10,
            "page": 1
        })
        response = requests.request("POST", self.url, headers=self.headers, data=payload)
        return response.json()

PREFIX = """Answer the following questions as best you can. You have access to the following tools:{tool_names}"""
FORMAT_INSTRUCTIONS = """Always respond in the following JSON format:

```json
{{
  "thought": "your thought process",
  "action": "the action to take, should be one of [{tool_names}]",
  "action_input": "the input to the action",
  "observation": "Result from tool after execution",
  "final_answer": "Final answer to the original question"
}}
```
Notes:
If you are taking an action, set 'final_answer' to "" and 'observation' to "".
If you have enough information to answer, set 'action' to "", and fill in 'final_answer' directly. 
"""

SUFFIX = """Begin!
Question: {input}
Thought:{agent_scratchpad}
"""


class BaseAgent(MapFunction):
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.logger.set_console_level("DEBUG")
        self.config = config
        search = BochaSearch(api_key=self.config["search_api_key"])

        self.tools = [
            Tool(
                name = "Search",
                func=search.run,
                description="useful for when you need to search to answer questions about current events"
            )
        ]
        self.tools = {tool.name: tool for tool in self.tools}
        self.tool_names = ", ".join(self.tools.keys())  # 修复点
        self.format_instructions = FORMAT_INSTRUCTIONS.format(tool_names=self.tool_names)
        self.prefix= PREFIX.format(tool_names=self.tool_names)
        self.model = OpenAIClient(
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config["api_key"],
            seed=42 
        )
        self.max_steps=self.config.get("max_steps", 5)

    def get_prompt(self, input, agent_scratchpad):
        return self.prefix + self.format_instructions + SUFFIX.format(
            input=input, agent_scratchpad=agent_scratchpad
        )
    
    def parse_json_output(self, output: str) -> dict:
        # 尝试直接加载
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # 如果不是纯 JSON，再试图从 Markdown 中提取
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", output, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Malformed JSON inside Markdown: {str(e)}") from e

        # 兜底报错
        raise ValueError("Invalid JSON format: No valid JSON found (either plain or wrapped in Markdown)")
        
    def execute(self, data: str) -> Tuple[str, str]:
        query = data
        agent_scratchpad = ""
        count = 0
        while True:
            count += 1
            self.logger.debug(f"Step {count}: Processing query: {query}")
            if count > self.max_steps:
                # raise ValueError("Max steps exceeded.")
                return (query,"")
            
            prompt = self.get_prompt(query, agent_scratchpad)
            self.logger.debug(f"Prompt: {prompt}")
            prompt=[{"role":"user","content":prompt}]
            output = self.model.generate(prompt)
            self.logger.debug(output)
            output=self.parse_json_output(output)
            # self.logger.debug(output)
            if output.get("final_answer") != "":
                final_answer = output["final_answer"]
                
                self.logger.debug(f"Final Answer: {final_answer}")
                return (query,final_answer)

            action, action_input = output.get("action"), output.get("action_input")

            if action is None:
                # raise ValueError("Could not parse action.")
                return (query,"")

            if action not in self.tools:
                # raise ValueError(f"Unknown tool requested: {action}")
                return (query,"")

            tool = self.tools[action]
            tool_result = tool.run(action_input)
            self.logger.debug(f"Tool {action} result: {tool_result}")
            snippets =[item["snippet"] for item in tool_result["data"]["webPages"]["value"]]
            observation = "\n".join(snippets)
            self.logger.debug(f"Observation: {observation}")
            agent_scratchpad += str(output) + f"\nObservation: {observation}\nThought: "
            time.sleep(5)

# import yaml
# def load_config(path: str) -> dict:
#     with open(path, 'r') as f:
#         return yaml.safe_load(f)

# config=load_config("/home/zsl/workspace/sage/api/operator/operator_impl/config.yaml")
# agent=BaseAgent(config)
# agent.run("你是谁")