import os
import sys
import time

from dotenv import load_dotenv

# 延迟导入：这些模块在需要时才导入，避免在模块加载时就加载重量级依赖
load_dotenv()

# Ensure project root is on sys.path for imports that rely on package layout
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))


# Lazy HF mirror configuration: only configure when actually downloading models
# This avoids blocking imports with network checks
def _ensure_hf_configured():
    """Lazy initialization of HF mirror configuration"""
    from sage.common.config import ensure_hf_mirror_configured

    ensure_hf_mirror_configured()


class EmbeddingModel:
    # def __init__(self, method: str = "openai", model: str = "mistral-embed",
    #              base_url: str | None = None, api_key: str | None = None):
    def __init__(self, method: str = "openai", **kwargs):
        """
        初始化 embedding table
        :param method: 指定使用的 embedding 方法名称，例如 "openai" 或 "cohere" 或“hf"等
        """
        self.init_method = method
        self.dim = None
        if method == "default":
            method = "hf"
            kwargs["model"] = "sentence-transformers/all-MiniLM-L6-v2"

        if method == "mockembedder":
            kwargs["model"] = "mockembedder"  # 确保 model 参数存在
            if "fixed_dim" not in kwargs:
                kwargs["fixed_dim"] = 128  # 默认维度

        self.set_dim(kwargs["model"])
        self.method = method

        # self.kwargs = {}
        self.kwargs = kwargs
        if method == "hf":
            if "model" not in kwargs:
                raise ValueError("hf method need model")
            model_name = kwargs["model"]
            # Load HF models - fail explicitly if unavailable
            try:
                # Configure HF mirror before downloading (lazy init)
                _ensure_hf_configured()

                # 延迟导入 transformers
                from transformers import AutoModel, AutoTokenizer

                # 尝试使用本地缓存,如果失败则从网络下载
                try:
                    self.kwargs["tokenizer"] = AutoTokenizer.from_pretrained(
                        model_name, local_files_only=True
                    )
                    self.kwargs["embed_model"] = AutoModel.from_pretrained(
                        model_name, trust_remote_code=True, local_files_only=True
                    )
                except Exception:
                    # 如果本地加载失败,尝试从网络下载
                    self.kwargs["tokenizer"] = AutoTokenizer.from_pretrained(model_name)
                    self.kwargs["embed_model"] = AutoModel.from_pretrained(
                        model_name, trust_remote_code=True
                    )
                self.kwargs.pop("model")
            except Exception as e:
                # 明确失败，不静默回退到mockembedder
                raise RuntimeError(
                    f"Failed to load embedding model '{model_name}': {e}. "
                    f"Please ensure the model is available or use a different embedding method. "
                    f"For testing with mock embedder, explicitly set method='mockembedder'."
                ) from e
        elif method == "mockembedder":
            # 初始化 mockembedder
            from .wrappers.mock_wrapper import MockEmbedding

            self.kwargs["embed_model"] = MockEmbedding(fixed_dim=kwargs.get("fixed_dim", 128))
        self.embed_fn = self._get_embed_function(method)

    def set_dim(self, model_name):
        """
        :param model_name:
        :return:
        """
        dimension_mapping = {
            "mistral_embed": 1024,
            "embed-multilingual-v3.0": 1024,
            "embed-english-v3.0": 1024,
            "embed-english-light-v3.0": 384,
            "embed-multilingual-light-v3.0": 384,
            "embed-english-v2.0": 4096,
            "embed-english-light-v2.0": 1024,
            "embed-multilingual-v2.0": 768,
            "jina-embeddings-v3": 1024,
            "BAAI/bge-m3": 1024,
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "mockembedder": 128,
        }
        if model_name in dimension_mapping:
            self.dim = dimension_mapping[model_name]
        else:
            raise ValueError(f"<UNK> embedding <UNK>{model_name}")

    def get_dim(self):
        return self.dim

    def _get_embed_function(self, method: str):
        """根据方法名返回对应的 embedding 函数（延迟导入相关模块）"""
        # 延迟导入：只在实际使用时才导入对应的模块
        from sage.common.components.sage_embedding import (
            _cohere,
            bedrock,
            hf,
            jina,
            lollms,
            nvidia_openai,
            ollama,
            openai_wrapper,
            siliconcloud,
            zhipu,
        )

        mapping = {
            "openai": openai_wrapper.openai_embed_sync,
            "zhipu": zhipu.zhipu_embedding_sync,
            "bedrock": bedrock.bedrock_embed_sync,
            "hf": hf.hf_embed_sync,
            "jina": jina.jina_embed_sync,
            # "llama_index_impl": llama_index_impl.llama_index_embed,
            "lollms": lollms.lollms_embed_sync,
            "nvidia_openai": nvidia_openai.nvidia_openai_embed_sync,
            "ollama": ollama.ollama_embed_sync,
            "siliconcloud": siliconcloud.siliconcloud_embedding_sync,
            "cohere": _cohere.cohere_embed_sync,
            "mockembedder": lambda text, **kwargs: kwargs["embed_model"].embed(text),
            # "instructor": instructor.instructor_embed
        }
        if method not in mapping:
            raise ValueError(f"不支持的 embedding 方法：{method}")

        embed_fn = mapping[method]

        return embed_fn

    def _embed(self, text: str) -> list[float]:
        """
        异步执行 embedding 操作
        :param text: 要 embedding 的文本
        :param kwargs: embedding 方法可能需要的额外参数
        :return: embedding 后的结果
        """
        return self.embed_fn(text, **self.kwargs)

    def embed(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成 embedding（严格批量接口）

        只支持原生批量接口的方法。不支持的方法将抛出异常。

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表

        Raises:
            NotImplementedError: 如果方法不支持批量接口
        """
        if not texts:
            return []

        # 对于 openai 方法，使用原生批量接口
        if self.method == "openai":
            from sage.common.components.sage_embedding import openai_wrapper

            return openai_wrapper.openai_embed_batch_sync(texts, **self.kwargs)

        # 不支持批量的方法直接抛出异常
        raise NotImplementedError(
            f"Batch embedding not supported for method '{self.method}'. Supported methods: openai"
        )

        # 其他方法回退到逐个调用
        return [self.embed(text) for text in texts]

    def encode(self, text: str) -> list[float]:
        return self._embed(text)

    @property
    def method_name(self) -> str:
        """当前embedding方法名"""
        return self.init_method


def apply_embedding_model(name: str = "default", **kwargs) -> EmbeddingModel:
    """
    usage  参见sage/api/model/operator_test.py
    while name(method) = "hf", please set the param:model;
    while name(method) = "openai",if you need call other APIs which are compatible with openai,set the params:base_url,api_key,model;
    while name(method) = "jina/siliconcloud/cohere",please set the params:api_key,model;
    Example:operator_test.py
    """
    return EmbeddingModel(method=name, **kwargs)


def main():
    embedding_model = EmbeddingModel(method="hf", model="sentence-transformers/all-MiniLM-L6-v2")
    for i in range(10):
        start = time.time()
        v = embedding_model.embed(f"{i} times ")
        print(v)
        end = time.time()
        print(f"embedding time :{end - start}")


if __name__ == "__main__":
    main()
