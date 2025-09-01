# file sage/core/sage.middleware.services.neuromem./search_engine/kv_index/bm25s_index.py
# python -m sage.core.sage.middleware.services.neuromem..search_engine.kv_index.bm25s_index

import os
import bm25s
import shutil
import Stemmer
from typing import List, Optional, Dict, Any

from sage.middleware.components.neuromem.search_engine.kv_index.base_kv_index import BaseKVIndex


class BM25sIndex(BaseKVIndex):
    def __init__(
        self,
        config: Optional[dict] = None,
    ):
        """
        Initialize BM25sIndex.
        支持两种初始化方式：
        1. 直接通过声明来创建：传入 config，然后使用 build_index() 方法来构建索引
        2. 通过 BM25sIndex.load() 来加载：调用load方法
        
        Initialize the BM25sIndex instance with two initialization methods:
        1. Direct creation: pass config, then use build_index() method to build the index
        2. Load from disk: use load method
        """
        self.config = config or {}
        
        # 从config中获取必要参数，否则使用默认值
        self.name = self.config.get("name", None)
        if self.name is None:
            raise ValueError("索引名称(name)未在config中指定")
        
        # 初始化基本属性
        self.ids: List[str] = []
        self.texts: List[str] = []
        self.tokens: List[List[str]] = []
        self.tokenizer = None
        self.bm25 = None
        
        # BM25s 特定配置参数
        self.backend = self.config.get("backend", "numba")
        self.language = self.config.get("language", "auto")  # auto, zh, en
        self.custom_stopwords = self.config.get("custom_stopwords", None)

    def _get_tokenizer(self, texts: List[str]):
        """
        根据文本内容和配置选择合适的分词器（中文或英文）。
        Select appropriate tokenizer (Chinese or English) according to the content of texts and config.
        """
        # 优先使用配置中指定的语言
        if self.language == "zh":
            zh_flag = True
        elif self.language == "en":
            zh_flag = False
        else:  # auto
            zh_flag = self._is_chinese(texts[0]) if texts else False
        
        if zh_flag:
            return bm25s.tokenization.Tokenizer(
                stopwords=self.custom_stopwords or 'zh'
            )
        else:
            stemmer = Stemmer.Stemmer("english")
            return bm25s.tokenization.Tokenizer(
                stopwords=self.custom_stopwords or 'en', 
                stemmer=stemmer
            )

    def _build_index(self, texts: List[str], ids: List[str]):
        """
        构建BM25索引
        Build BM25 index
        """
        self.ids = list(ids)
        self.texts = list(texts)
        self.tokenizer = self._get_tokenizer(self.texts)
        self.tokens = self.tokenizer.tokenize(self.texts) # type: ignore
        self.bm25 = bm25s.BM25(corpus=self.texts, backend=self.backend)
        self.bm25.index(self.tokens)

    def build_index(self, texts: List[str], ids: List[str]):
        """
        构建BM25索引的公共方法。
        Public method to build BM25 index.
        """
        if len(texts) != len(ids):
            raise ValueError("texts and ids must have the same length.")
        self._build_index(texts, ids)

    def _rebuild(self):
        """
        重新构建分词器、分词结果和BM25索引。
        Rebuild the tokenizer, tokens, and BM25 index.
        """
        if not self.texts:
            return
        self.tokenizer = self._get_tokenizer(self.texts)
        self.tokens = self.tokenizer.tokenize(self.texts) # type: ignore
        self.bm25 = bm25s.BM25(corpus=self.texts, backend=self.backend)
        self.bm25.index(self.tokens)

    def _is_chinese(self, text: str):
        """
        判断字符串中是否包含中文字符。
        Detect whether the text contains Chinese characters.
        """
        return any('\u4e00' <= ch <= '\u9fff' for ch in text)

    def insert(self, text, doc_id):
        """
        插入新的文本和id，并重建索引。
        Insert a new text and doc_id, then rebuild the index.
        """
        self.texts.append(text)
        self.ids.append(doc_id)
        self._rebuild()

    def delete(self, id: str) -> None:
        """
        根据id删除对应的文本，并重建索引。
        Delete the text corresponding to the given id, then rebuild the index.
        """
        if id not in self.ids:
            return
        idx = self.ids.index(id)
        self.ids.pop(idx)
        self.texts.pop(idx)
        self._rebuild()

    def update(self, id: str, new_text: str) -> None:
        """
        更新指定id的文本内容，并重建索引。
        Update the text of the given id, then rebuild the index.
        """
        if id not in self.ids:
            return
        idx = self.ids.index(id)
        self.texts[idx] = new_text
        self._rebuild()

    def search(self, text: str, topk: int = 5) -> List[str]:
        """
        对输入文本进行检索，返回最相关的topk个id。
        Search for the most relevant texts and return the top-k ids.
        """
        if self.bm25 is None or len(self.ids) == 0:
            return []
        query_token = self.tokenizer.tokenize([text])[0] # type: ignore
        scores = self.bm25.get_scores(query_token) # type: ignore
        topk_idx = sorted(range(len(scores)), key=lambda i: -scores[i])[:topk]
        return [self.ids[i] for i in topk_idx]


    def store(self, dir_path: str) -> Dict[str, Any]:
        """
        将索引信息存储到指定目录，包含bm25模型、分词器、ids和texts。
        Store the index info into the specified directory, including bm25 model, tokenizer, ids, and texts.
        """
        os.makedirs(dir_path, exist_ok=True)
        
        # 保存BM25模型
        if self.bm25 is not None:
            self.bm25.vocab_dict = {str(k): v for k, v in self.bm25.vocab_dict.items()} # type: ignore
            self.bm25.save(dir_path, corpus=None)# type: ignore
        
        # 保存分词器
        if self.tokenizer is not None:
            self.tokenizer.save_vocab(dir_path) # type: ignore
            self.tokenizer.save_stopwords(dir_path) # type: ignore
        
        # 保存配置信息
        meta = {
            "name": self.name,
            "backend": self.backend,
            "language": self.language,
            "custom_stopwords": self.custom_stopwords,
            "config": self.config
        }
        with open(os.path.join(dir_path, "meta.json"), "w", encoding="utf-8") as f:
            import json
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        # 保存ids和texts
        with open(os.path.join(dir_path, "ids.txt"), "w", encoding="utf-8") as f:
            for i in self.ids:
                f.write(i + "\n")
        with open(os.path.join(dir_path, "texts.txt"), "w", encoding="utf-8") as f:
            for t in self.texts:
                f.write(t.replace("\n", " ") + "\n")
        return {"index_path": dir_path}

    def _load_data(self, dir_path: str):
        """
        从目录加载索引及相关内容，包括bm25模型、分词器、ids和texts。
        Load index and related data from directory, including bm25 model, tokenizer, ids, and texts.
        """
        # 加载配置信息
        meta_path = os.path.join(dir_path, "meta.json")
        if os.path.exists(meta_path):
            import json
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.config = meta.get("config", {})
            self.backend = meta.get("backend", "numba")
            self.language = meta.get("language", "auto")
            self.custom_stopwords = meta.get("custom_stopwords", None)
        
        # 加载BM25模型
        self.bm25 = bm25s.BM25.load(dir_path)

        # 加载分词器
        self.tokenizer = bm25s.tokenization.Tokenizer()
        self.tokenizer.load_vocab(dir_path)
        self.tokenizer.load_stopwords(dir_path)

        # 加载ids和texts
        with open(os.path.join(dir_path, "ids.txt"), "r", encoding="utf-8") as f:
            self.ids = [line.strip() for line in f.readlines()]
        with open(os.path.join(dir_path, "texts.txt"), "r", encoding="utf-8") as f:
            self.texts = [line.strip() for line in f.readlines()]
            
        # 重建tokens
        self.tokens = [self.tokenizer.tokenize([t], return_as="tuple")[0][0] for t in self.texts] # type: ignore
        self.bm25.index(self.tokens)

    @classmethod
    def load(cls, name: str, dir_path: str) -> "BM25sIndex":
        """
        通过名称和根路径加载一个BM25sIndex实例。
        Load a BM25sIndex instance by name and root path.
        """
        # 创建一个空的实例，然后加载数据
        config = {"name": name}
        instance = cls(config=config)
        instance._load_data(dir_path)
        return instance

    @staticmethod
    def clear(dir_path: str):
        """
        删除指定名称下的所有索引数据。
        Remove all index data under the specified name.
        """
        try:
            shutil.rmtree(dir_path)
            print(f"Cleared: {dir_path}")
        except FileNotFoundError:
            print(f"Directory does not exist, nothing to clear: {dir_path}")
        except Exception as e:
            print(f"Failed to clear: {e}")


if __name__ == "__main__":
    # 简单数据
    ids = ["a", "b", "c"]
    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Hello world! This is a operator_test document.",
        "Python is a great programming language."
    ]
    root_path = "./tmp_bm25_test"  # 用临时目录避免误删业务数据
    index_dir = root_path
    index_name = "demo"

    # 1. 初始化索引 - 使用新的config方式
    print("\n== 初始化并首检 ==")
    config = {
        "name": index_name,
        "backend": "numba",
        "language": "auto",  # 可以指定 "zh", "en" 或 "auto"
        "custom_stopwords": None
    }
    index = BM25sIndex(config=config)
    index.build_index(texts, ids)
    print("初始检索 'Python':", index.search("Python"))
    print("初始检索 'hello':", index.search("hello"))
    print("初始检索 'fox':", index.search("fox"))

    # 2. 插入新文档后检索
    print("\n== 插入新文档 ==")
    index.insert("This document mentions python and fox together.", "d")
    print("插入后检索 'python':", index.search("python"))
    print("插入后检索 'fox':", index.search("fox"))

    # 3. 删除文档后检索
    print("\n== 删除文档 ==")
    index.delete("b")
    print("删除 'b' 后检索 'hello':", index.search("hello"))
    print("删除 'b' 后检索 'operator_test':", index.search("operator_test"))
    print("删除 'b' 后检索 'python':", index.search("python"))

    # 4. 更新文档后检索
    print("\n== 更新文档 ==")
    index.update("c", "Hello world! Now c document talks about foxes.")
    print("更新 'c' 后检索 'fox':", index.search("fox"))
    print("更新 'c' 后检索 'python':", index.search("python"))

    # 5. 保存索引
    print("\n== 保存索引到磁盘 ==")
    store_info = index.store(index_dir)
    print("索引保存路径:", store_info["index_path"])

    # 6. 等待用户输入 'yes' 后加载索引并检索
    print("\n== 测试持久化（请手动输入 yes 继续）==")
    user_input = input("输入 'yes' 以继续测试 load 并检索：")
    if user_input.strip().lower() == "yes":
        index_loaded = BM25sIndex.load(name=index_name, dir_path=index_dir)
        print("持久化load后检索 'fox':", index_loaded.search("fox"))
        print("持久化load后检索 'python':", index_loaded.search("python"))
        print("持久化load后检索 'hello':", index_loaded.search("hello"))
        print("ids序列:", index_loaded.ids)
    else:
        print("用户未输入 'yes'，测试提前结束。")

    # 7. 清理测试目录
    print("\n== 清理测试目录 ==")
    BM25sIndex.clear(index_dir)

