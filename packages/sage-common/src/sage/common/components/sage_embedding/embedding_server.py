#!/usr/bin/env python3
"""
轻量化 Embedding 服务器 - 使用 FastAPI 提供 OpenAI 兼容的 API

用法:
    python embedding_server.py --model BAAI/bge-m3 --port 8080

然后在代码中使用:
    from sage.common.components.sage_embedding.embedding_api import apply_embedding_model

    embedding_model = apply_embedding_model(
        name="openai",
        model="BAAI/bge-m3",  # 或任意名称
        base_url="http://localhost:8080/v1",
        api_key="dummy"  # 本地服务不需要真实的 API key  # pragma: allowlist secret
    )

    result = embedding_model.embed("Hello world")
"""

# ========== 关键：必须在导入任何 HuggingFace 库之前设置环境变量 ==========
import os
import sys

# ========== 清除代理变量，避免 SOCKS 代理问题 ==========
# 本地 embedding 服务器使用 HuggingFace 镜像，不需要代理
# 清除代理可以避免 "Missing dependencies for SOCKS support" 错误
for proxy_var in [
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "all_proxy",
    "ALL_PROXY",
]:
    os.environ.pop(proxy_var, None)

# 设置环境变量 - 自动检测网络并配置 HuggingFace 镜像
from sage.common.config import ensure_hf_mirror_configured

ensure_hf_mirror_configured()

# ========== 强制所有 HuggingFace 请求使用镜像站 ==========
# 方案1: 设置所有可能的离线和镜像相关环境变量
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = "1"


# 方案2: Patch requests 库，将 huggingface.co 重定向到镜像站
def patch_huggingface_requests():
    """将所有 huggingface.co 的请求重定向到镜像站"""
    from functools import wraps

    import requests

    original_request = requests.Session.request
    hf_endpoint = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")

    @wraps(original_request)
    def patched_request(self, method, url, *args, **kwargs):
        # 将 huggingface.co 替换为镜像站
        if isinstance(url, str):
            url = url.replace("https://huggingface.co", hf_endpoint)
            url = url.replace("http://huggingface.co", hf_endpoint)
        return original_request(self, method, url, *args, **kwargs)

    requests.Session.request = patched_request


# 执行 patch（在导入 transformers 之前）
try:
    patch_huggingface_requests()
except Exception as e:
    print(f"Warning: Failed to patch requests: {e}", file=sys.stderr)

# ========== 现在可以安全导入其他库了 ==========
import argparse
import logging
import time
from typing import Any

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from transformers import AutoModel, AutoTokenizer

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EmbeddingRequest(BaseModel):
    """OpenAI 兼容的 embedding 请求格式"""

    input: str | list[str]
    model: str = "default"
    encoding_format: str = "float"


class EmbeddingResponse(BaseModel):
    """OpenAI 兼容的 embedding 响应格式"""

    object: str = "list"
    data: list[dict[str, Any]]
    model: str
    usage: dict[str, int]


class EmbeddingServer:
    """Embedding 服务器类 - 长期持有模型实例"""

    def __init__(self, model_name: str, device: str = "auto"):
        """初始化 embedding 服务器

        Args:
            model_name: HuggingFace 模型名称
            device: 设备类型 ("cuda", "cpu", "auto")
        """
        self.model_name = model_name
        logger.info(f"Loading model: {model_name}")

        # 确定设备
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Using device: {self.device}")

        # 加载模型和 tokenizer
        try:
            logger.info("Loading model from local cache...")
            logger.info(f"HF_ENDPOINT: {os.environ.get('HF_ENDPOINT', 'not set')}")

            # 检查本地缓存是否存在
            cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            model_cache = os.path.join(cache_dir, f"models--{model_name.replace('/', '--')}")

            # 如果本地缓存存在，优先使用本地文件（避免限流）
            local_files_only = os.path.exists(model_cache)
            if local_files_only:
                logger.info(f"Found local cache at {model_cache}")
                logger.info("Loading from local cache only (avoiding network requests)")
            else:
                logger.info("Local cache not found, will download from mirror")

            # 直接加载（优先使用本地已有的格式，避免下载 safetensors）
            # use_safetensors=False 会强制使用 pytorch_model.bin
            # local_files_only=True 时完全离线加载（避免 HuggingFace 限流）
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, trust_remote_code=True, local_files_only=local_files_only
            )
            self.model = AutoModel.from_pretrained(
                model_name,
                trust_remote_code=True,
                use_safetensors=False,
                local_files_only=local_files_only,
            )
            logger.info("Model loaded successfully")

            # 移动模型到指定设备
            self.model = self.model.to(self.device)
            self.model.eval()  # 设置为评估模式

            logger.info(f"Model loaded successfully on {self.device}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """对文本列表进行 embedding

        Args:
            texts: 文本列表

        Returns:
            embedding 向量列表
        """
        try:
            # Tokenize
            encoded = self.tokenizer(
                texts, return_tensors="pt", padding=True, truncation=True, max_length=512
            )

            # 移动到模型所在设备
            encoded = {k: v.to(self.device) for k, v in encoded.items()}

            # 推理
            with torch.no_grad():
                outputs = self.model(**encoded)
                # 使用 mean pooling
                embeddings = outputs.last_hidden_state.mean(dim=1)

            # 转换为 float32 并移回 CPU
            if embeddings.dtype == torch.bfloat16:
                embeddings = embeddings.to(torch.float32)

            embeddings = embeddings.cpu().numpy().tolist()

            return embeddings

        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise


# 全局变量存储服务器实例
embedding_server: EmbeddingServer | None = None

# 创建 FastAPI 应用
app = FastAPI(
    title="Embedding Server", description="OpenAI-compatible Embedding API", version="1.0"
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "status": "ok",
        "model": embedding_server.model_name if embedding_server else "not loaded",
        "device": embedding_server.device if embedding_server else "unknown",
    }


@app.get("/health")
async def health():
    """健康检查端点（标准路径）- Control Plane 使用此路径"""
    return {
        "status": "ok",
        "model": embedding_server.model_name if embedding_server else "not loaded",
        "device": embedding_server.device if embedding_server else "unknown",
    }


@app.get("/v1/models")
async def list_models():
    """列出可用模型（OpenAI 兼容）"""
    if not embedding_server:
        raise HTTPException(status_code=500, detail="Model not loaded")

    return {
        "object": "list",
        "data": [
            {
                "id": embedding_server.model_name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local",
            }
        ],
    }


@app.post("/v1/embeddings")
async def create_embeddings(request: EmbeddingRequest):
    """创建 embeddings（OpenAI 兼容）"""
    if not embedding_server:
        raise HTTPException(status_code=500, detail="Model not loaded")

    try:
        # 处理输入（单个字符串或列表）
        if isinstance(request.input, str):
            texts = [request.input]
        else:
            texts = request.input

        # 生成 embeddings
        start_time = time.time()
        embeddings = embedding_server.embed_texts(texts)
        elapsed_time = time.time() - start_time

        # 构建响应（OpenAI 兼容格式）
        data = [
            {"object": "embedding", "embedding": emb, "index": idx}
            for idx, emb in enumerate(embeddings)
        ]

        response = {
            "object": "list",
            "data": data,
            "model": embedding_server.model_name,
            "usage": {
                "prompt_tokens": sum(len(t.split()) for t in texts),
                "total_tokens": sum(len(t.split()) for t in texts),
            },
        }

        logger.info(
            f"Generated {len(embeddings)} embeddings in {elapsed_time:.3f}s "
            f"({len(embeddings) / elapsed_time:.2f} emb/s)"
        )

        return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Embedding Server - OpenAI Compatible API")
    parser.add_argument(
        "--model",
        type=str,
        default="BAAI/bge-m3",
        help="HuggingFace model name (default: BAAI/bge-m3)",
    )
    parser.add_argument("--port", type=int, default=8091, help="Server port (default: 8090)")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--device", type=str, default="auto", help="Device (cuda/cpu/auto, default: auto)"
    )
    parser.add_argument(
        "--gpu", type=int, default=None, help="Specific GPU ID to use (e.g., 0, 1, 2)"
    )
    parser.add_argument("--workers", type=int, default=1, help="Number of workers (default: 1)")

    args = parser.parse_args()

    # 如果指定了 GPU，设置 CUDA_VISIBLE_DEVICES
    if args.gpu is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
        logger.info(f"Setting CUDA_VISIBLE_DEVICES={args.gpu}")

    # 初始化全局 embedding 服务器
    global embedding_server
    try:
        embedding_server = EmbeddingServer(model_name=args.model, device=args.device)
    except Exception as e:
        logger.error(f"Failed to initialize embedding server: {e}")
        return

    # 启动 FastAPI 服务器
    logger.info(f"Starting server on {args.host}:{args.port}")
    logger.info(f"API endpoint: http://{args.host}:{args.port}/v1/embeddings")
    logger.info("Usage example:")
    logger.info(f"  curl -X POST http://localhost:{args.port}/v1/embeddings \\")
    logger.info('    -H "Content-Type: application/json" \\')
    logger.info(f'    -d \'{{"input": "Hello world", "model": "{args.model}"}}\'')

    uvicorn.run(app, host=args.host, port=args.port, workers=args.workers, log_level="info")


if __name__ == "__main__":
    main()
