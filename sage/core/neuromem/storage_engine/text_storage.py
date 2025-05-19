# file sage/core/neuromem/storage_engine/text_storage.py
# python sage/core/neuromem/storage_engine/text_storage.py

from typing import Dict

class TextStorage:
    """
    Simple raw text storage based on externally provided IDs.

    简单的原始文本存储器，由外部提供稳定 ID（不生成哈希）。
    """

    def __init__(self):
        # 存储结构：{external_id: raw_text}
        self._store: Dict[str, str] = {}

    def store(self, item_id: str, text: str):
        """
        Store text under a given item_id.

        使用外部提供的 ID 存储原始文本。
        """
        self._store[item_id] = text

    def get(self, item_id: str) -> str:
        """
        Retrieve text using item_id.

        使用 ID 获取文本内容。
        """
        return self._store.get(item_id, "")

    def clear(self):
        """
        Clear all stored text.

        清空所有存储内容。
        """
        self._store.clear()

"""测试预期输出
Retrieved: hello world
After clear: 
"""

if __name__ == "__main__":
    import hashlib
    ts = TextStorage()
    text = "hello world"
    text_id = hashlib.sha256(text.encode()).hexdigest()

    ts.store(text_id, text)
    print("Retrieved:", ts.get(text_id))

    ts.clear()
    print("After clear:", ts.get(text_id))  # 应为空字符串
