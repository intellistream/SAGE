from sage.core.api.function.map_function import MapFunction

from typing import Dict, Any
import requests
import json
import logging

class BochaWebSearch(MapFunction):

    def __init__(self, config: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.api_key = config.get("api_key")
        self.count = config.get("count", 10)
        self.page = config.get("page", 1)
        self.summary = config.get("summary", True)
        self.url = "https://api.bochaai.com/v1/web-search"

        if not self.api_key:
            raise ValueError("BochaWebSearch requires an 'api_key' in config.")

    def execute(self, data: str) -> Dict[str, Any]:
        query = data
        headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        payload = {
            "query": query,
            "summary": self.summary,
            "count": self.count,
            "page": self.page
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result
        except Exception as e:
            self.logger.error(f"BochaWebSearch error: {e}", exc_info=True)
