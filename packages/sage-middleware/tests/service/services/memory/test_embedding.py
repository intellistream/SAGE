import os
import sys
import unittest
from urllib import response

# 添加正确的项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sage_middleware_src = os.path.join(current_dir, "../../../../src")
sys.path.insert(0, os.path.abspath(sage_middleware_src))

from httpx import stream
from sage.middleware.utils.embedding.embedding_api import apply_embedding_model


class EmbeddingTestCase(unittest.TestCase):

    # def test_something(self):
    #     self.assertEqual(True, False)  # add assertion here

    def test_default(self):
        embedding_model = apply_embedding_model("default")
        e = embedding_model.embed("hello world")
        self.assertIsInstance(e, list)
        self.assertTrue(len(e) > 0)
        self.assertTrue(all(isinstance(x, float) for x in e))
        self.assertIsInstance(embedding_model.get_dim(), int)

    def test_hf(self):
        model = apply_embedding_model(
            "hf", model="sentence-transformers/all-MiniLM-L6-v2"
        )
        e = model.embed("This is huggingface.")
        self.assertIsInstance(e, list)
        self.assertTrue(all(isinstance(x, float) for x in e))
        self.assertTrue(len(e) > 0)
        self.assertIsInstance(model.get_dim(), int)

    # def test_openai_api(self):
    #     from dotenv import load_dotenv

    #     load_dotenv(override=False)
    #     api_key = os.environ.get("SILICONCLOUD_API_KEY")
    #     model = apply_embedding_model("openai",model="BAAI/bge-m3", base_url="https://api.siliconflow.cn/v1",
    #                                   api_key=api_key)
    #     e = model.embed("this is openai")
    #     self.assertIsInstance(e, list)
    #     self.assertTrue(all(isinstance(x, float) for x in e))
    #     self.assertTrue(len(e) > 0)
    #     self.assertIsInstance(model.get_dim(), int )

    # def test_jina(self):
    #     from dotenv import load_dotenv
    #     load_dotenv(override=False)
    #     api_key = os.environ.get("JINA_API_KEY")
    #     model = apply_embedding_model("jina",model="jina-embeddings-v3",api_key=api_key)
    #     e = model.embed("this is jina")
    #     self.assertIsInstance(e, list)
    #     self.assertTrue(all(isinstance(x, float) for x in e))
    #     self.assertTrue(len(e) > 0)
    #     self.assertIsInstance(model.get_dim(), int)


if __name__ == "__main__":
    unittest.main()
