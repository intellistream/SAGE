from typing import Any

import requests

from sage.common.core.functions import MapFunction as MapOperator


class BochaWebSearch(MapOperator):
    def __init__(self, config: dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.api_key = config.get("api_key")
        self.count = config.get("count", 10)
        self.page = config.get("page", 1)
        self.summary = config.get("summary", True)
        self.url = "https://api.bochaai.com/v1/web-search"

        if not self.api_key:
            raise ValueError("BochaWebSearch requires an 'api_key' in config.")

    def execute(self, data: str) -> dict[str, Any]:
        query = data
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}
        payload = {
            "query": query,
            "summary": self.summary,
            "count": self.count,
            "page": self.page,
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result
        except Exception as e:
            self.logger.error(f"BochaWebSearch error: {e}", exc_info=True)
            return {}  # Return empty dict on error
