# pyright: reportGeneralTypeIssues=false
# pyright: reportMissingImports=false
# pyright: reportMissingTypeStubs=false

from dotenv import load_dotenv
load_dotenv()

import os
import json
from datetime import datetime
import asyncio
import httpx

from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import VectorStoreRetrieverMemory
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

from langchain_core.embeddings import Embeddings
from typing import List, Callable, Optional
from langchain_core.vectorstores import VectorStore
from langchain.schema import Document
from langchain_core.retrievers import BaseRetriever
import numpy as np

class MetadataFirstRetriever(BaseRetriever):
    def __init__(
        self,
        vectorstore: VectorStore,
        embedder,
        metadata_filter_func: Optional[Callable[[dict], bool]] = None,
        k: int = 5,
    ):
        self.vectorstore = vectorstore
        self.embedder = embedder  # 实现了 embed_query
        self.metadata_filter_func = metadata_filter_func
        self.k = k

    def get_relevant_documents(self, query: str) -> List[Document]:
        # 1. 取出所有文档
        all_docs = list(self.vectorstore.docstore._dict.values())

        # 2. metadata 精确过滤
        if self.metadata_filter_func:
            filtered_docs = [doc for doc in all_docs if self.metadata_filter_func(doc.metadata)]
        else:
            filtered_docs = all_docs

        if not filtered_docs:
            return []

        # 3. 获取 query 向量
        query_embedding = self.embedder.embed_query(query)
        query_vec = np.array(query_embedding)

        # 4. 手动打分（余弦相似度）
        scored = []
        for doc in filtered_docs:
            doc_vec = self.vectorstore.index.reconstruct(doc.metadata["vector_id"])
            doc_vec = np.array(doc_vec)
            sim = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec))
            scored.append((sim, doc))

        # 5. 排序并取 top-k
        scored.sort(key=lambda x: -x[0])
        return [doc for _, doc in scored[:self.k]]


class SimpleEmbedder:
    def __init__(self):
        self.api_key = os.environ.get("SILICONCLOUD_API_KEY")
        self.base_url = "https://api.siliconflow.cn/v1"
        self.model = "BAAI/bge-m3"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _embed_async(self, text: str):
        url = f"{self.base_url}/embeddings"
        json_data = {
            "model": self.model,
            "input": text
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=json_data, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            embedding = data["data"][0]["embedding"]
            return embedding

    def encode(self, text: str):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self._embed_async(text))


class LangChainEmbedder(Embeddings):
    def __init__(self, embedder: SimpleEmbedder):
        self.embedder = embedder

    def embed_documents(self, texts):
        return [self.embedder.encode(t) for t in texts]

    def embed_query(self, text):
        return self.embedder.encode(text)


def parse_timestamp(s):
    try:
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return None


def filter_docs_by_time_window(docs, start_ts=None, end_ts=None):
    filtered = []
    for doc in docs:
        ts = doc.metadata.get("timestamp")
        if ts is None:
            continue
        if start_ts is not None and ts < start_ts:
            continue
        if end_ts is not None and ts > end_ts:
            continue
        filtered.append(doc)
    return filtered


# 继承VectorStoreRetrieverMemory，添加时间窗口过滤功能
from pydantic import Field

class TimeWindowMemory(VectorStoreRetrieverMemory):
    start_ts: float | None = Field(default=None)
    end_ts: float | None = Field(default=None)

    def _get_text(self, docs):
        # 简单拼接所有文档内容
        return "\n".join([doc.page_content for doc in docs])

    def load_memory_variables(self, inputs):
        docs = self.retriever.get_relevant_documents(inputs["input"])
        filtered_docs = filter_docs_by_time_window(docs, self.start_ts, self.end_ts)
        text = self._get_text(filtered_docs)
        return {self.memory_key: text}

from typing import Callable, Any, Optional
from pydantic import Field
from langchain.memory import VectorStoreRetrieverMemory

class FlexibleMetadataMemory(VectorStoreRetrieverMemory):
    metadata_filter_func: Optional[Callable[[dict], bool]] = Field(default=None)
    metadata_conditions: dict = Field(default_factory=dict)

    def _match_metadata(self, metadata: dict) -> bool:
        if self.metadata_conditions:
            for k, v in self.metadata_conditions.items():
                if metadata.get(k) != v:
                    return False

        if self.metadata_filter_func:
            if not self.metadata_filter_func(metadata):
                return False

        return True

    def _filter_docs(self, docs):
        return [doc for doc in docs if self._match_metadata(doc.metadata)]

    def _get_text(self, docs):
        return "\n".join([doc.page_content for doc in docs])

    def load_memory_variables(self, inputs):
        docs = self.retriever.get_relevant_documents(inputs["input"])
        filtered_docs = self._filter_docs(docs)
        return {self.memory_key: self._get_text(filtered_docs)}
def should_use_existing_index(user_input: str) -> bool:
    # If the input contains keywords like "memory", "history", etc., use existing index
    return any(keyword in user_input for keyword in ["memory", "history", "before", "past"])


def should_create_new_index(user_input: str) -> bool:
    # If the input introduces a new topic, consider creating a new index
    return any(keyword in user_input for keyword in ["new", "add", "record", "note"])


def should_store_to_index(response: str) -> bool:
    # Store the response if it's considered valuable (based on length here)
    return len(response.strip()) > 20  # Can be refined with quality/confidence metrics


def main():
    simple_embedder = SimpleEmbedder()
    embedding = LangChainEmbedder(simple_embedder)

    file_configs = [
        ("/home/zrc/develop_item/SAGE/sage/core/neuromem/test/structure_mem_demo/food.json", "caption"),
        ("/home/zrc/develop_item/SAGE/sage/core/neuromem/test/structure_mem_demo/sport.json", "text"),
        ("/home/zrc/develop_item/SAGE/sage/core/neuromem/test/structure_mem_demo/health.json", "text"),
    ]

    docs_to_add = []
    for file_path, text_field in file_configs:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                text = item[text_field]
                metadata = {k: v for k, v in item.items() if k != text_field}
                if "metadata" in metadata and isinstance(metadata["metadata"], dict):
                    metadata.update(metadata.pop("metadata"))
                if "timestamp" in metadata:
                    ts = parse_timestamp(metadata["timestamp"])
                    if ts:
                        metadata["timestamp"] = ts
                docs_to_add.append(Document(page_content=text, metadata=metadata))

    vectorstore = FAISS.from_documents(docs_to_add, embedding) if docs_to_add else FAISS.from_documents([], embedding)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 20})

    start_ts = datetime.fromisoformat("2025-05-25T00:00:00").timestamp()
    end_ts = datetime.fromisoformat("2025-05-28T23:59:59").timestamp()
    memory = TimeWindowMemory(retriever=retriever, start_ts=start_ts, end_ts=end_ts)

    llm = ChatOpenAI(
        model="qwen-max-2025-01-25",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        openai_api_key=os.environ["OPENAI_API_KEY"],
        temperature=0.7
    )

    conversation = ConversationChain(llm=llm, memory=memory, verbose=True)

    print("🤖 chatbot started. Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break

        use_index = should_use_existing_index(user_input)
        if use_index:
            docs = retriever.get_relevant_documents(user_input)
            filtered_docs = filter_docs_by_time_window(docs, start_ts, end_ts)
            print("\n[Retrieved Documents]")
            for i, doc in enumerate(filtered_docs):
                ts = datetime.fromtimestamp(doc.metadata.get("timestamp")).isoformat() if doc.metadata.get("timestamp") else "N/A"
                print(f"  [{i+1}] {doc.page_content[:100]}... (timestamp={ts})")
        else:
            if should_create_new_index(user_input):
                new_doc = Document(
                    page_content=user_input,
                    metadata={"timestamp": datetime.now().timestamp(), "source": "user"}
                )
                vectorstore.add_documents([new_doc])
                print("📌 New document has been added to the vector store.")

        response = conversation.predict(input=user_input)
        print("Bot:", response)

        if should_store_to_index(response):
            doc = Document(
                page_content=response,
                metadata={"timestamp": datetime.now().timestamp(), "source": "bot"}
            )
            vectorstore.add_documents([doc])
            print("📥 Response saved to long-term memory.")
        print()


if __name__ == "__main__":
    main()