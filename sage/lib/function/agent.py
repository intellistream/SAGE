from calendar import c
from sage.api.model import apply_generator_model
from sage.api.base_function import BaseFunction
from sage.api.operator import Data
from typing import Any,Tuple
import requests
import json
import re

class Tool:
    def __init__(self, name, func, description):
        self.name = name
        self.func = func
        self.description = description

    def run(self, *args, **kwargs):
        return self.func(*args, **kwargs)
    
class BochaSearch:
    def __init__(self, url="https://api.bochaai.com/v1/web-search"):
        self.url = url
        self.headers = {
            'Authorization': 'sk-3e0704d84d954379b5c38d089ddd2b96',
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

PREFIX = """Answer the following questions as best you can. You have access to the following tools:"""
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


class BaseAgent:
    def __init__(self, config):
        self.config = config["agent"]
        print(self.config)
        search = BochaSearch()
        self.tools = [
            Tool(
                name = "Search",
                func=search.run,
                description="useful for when you need to search to answer questions about current events"
            )
        ]
        self.tool_names = ", ".join([tool.name for tool in self.tools])
        self.tools = {tool.name: tool for tool in self.tools}
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config["api_key"],
            seed=42 
        )
        self.max_steps=self.config.get("max_steps", 5)

    def get_prompt(self, input, agent_scratchpad):
        return PREFIX + FORMAT_INSTRUCTIONS.format(tool_names=self.tool_names) + SUFFIX.format(
            input=input, agent_scratchpad=agent_scratchpad
        )
    
    def parse_json_output(self, output):
        """
        Try to load the entire output as JSON.
        """
        try:
            json_match = re.search(r"```json(.*?)```", output, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON code block found.")

            json_str = json_match.group(1).strip()
            data = json.loads(json_str)
            return data
        except Exception as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        
    def execute(self, data: Data[str],*args, **kwargs) -> Data[Tuple[bool,str, str]]:
        query = data.data
        agent_scratchpad = ""
        count = 0
        while True:
            count += 1
            if count > self.max_steps:
                # raise ValueError("Max steps exceeded.")
                return Data((False,query,""))
            
            prompt = self.get_prompt(query, agent_scratchpad)
            prompt=[{"role":"user","content":prompt}]
            output = self.model.generate(prompt)
            print(output)
            output=self.parse_json_output(output)
            # print(output)
            if output.get("final_answer") is not "":
                final_answer = output["final_answer"]
                print(f"Final Answer: {final_answer}")
                return Data((True,query,final_answer))

            action, action_input = output.get("action"), output.get("action_input")

            if action is None:
                # raise ValueError("Could not parse action.")
                return Data((False,query,""))

            if action not in self.tools:
                # raise ValueError(f"Unknown tool requested: {action}")
                return Data((False,query,""))

            tool = self.tools[action]
            tool_reault = tool.run(action_input)
            tool_reault["data"]["webPages"]["value"]
            snippets =[item["snippet"] for item in tool_reault["data"]["webPages"]["value"]]
            observation = "\n".join(snippets)
            print(f"Observation: {observation}")
            agent_scratchpad += str(output) + f"\nObservation: {observation}\nThought: "

# import yaml
# def load_config(path: str) -> dict:
#     with open(path, 'r') as f:
#         return yaml.safe_load(f)

# config=load_config("/home/zsl/workspace/sage/api/operator/operator_impl/config.yaml")
# agent=BaseAgent(config)
# agent.run("你是谁")