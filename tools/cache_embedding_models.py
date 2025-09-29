#!/usr/bin/env python3
"""
CICD环境中的embedding模型预缓存脚本
"""

import os
import sys
from pathlib import Path


# 设置网络和缓存相关的环境变量
def setup_environment():
    """设置优化的环境变量"""
    # 使用HuggingFace镜像（如果在中国）
    if not os.environ.get("HF_ENDPOINT"):
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    # 禁用进度条以减少输出噪音
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

    # 设置合理的超时时间
    os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "60"

    # 启用离线模式检查
    os.environ["TRANSFORMERS_OFFLINE"] = "0"

    print("🔧 环境变量已配置:")
    print(f"  - HF_ENDPOINT: {os.environ.get('HF_ENDPOINT', 'default')}")
    print(
        f"  - HF_HUB_DOWNLOAD_TIMEOUT: {os.environ.get('HF_HUB_DOWNLOAD_TIMEOUT', 'default')}"
    )


# 在导入transformers之前设置环境
setup_environment()


def clear_model_cache():
    """清除模型缓存"""
    import shutil

    from transformers import TRANSFORMERS_CACHE

    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"🗑️  清除模型缓存: {model_name}")

    try:
        cache_dir = Path(TRANSFORMERS_CACHE)
        if cache_dir.exists():
            # 查找该模型的缓存目录
            model_dirs = list(cache_dir.glob("**/models--sentence-transformers--*"))

            for model_dir in model_dirs:
                if "all-MiniLM-L6-v2" in str(model_dir):
                    print(f"  删除: {model_dir}")
                    shutil.rmtree(model_dir, ignore_errors=True)

            print("✅ 缓存清除完成!")
            return True
        else:
            print("ℹ️  缓存目录不存在")
            return True

    except Exception as e:
        print(f"❌ 缓存清除失败: {e}")
        return False


def cache_embedding_models():
    """缓存CICD环境需要的embedding模型"""
    import time

    from transformers import AutoModel, AutoTokenizer

    print("🔄 开始缓存embedding模型...")

    # 默认使用的模型
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"📥 下载并缓存模型: {model_name}")

    # 设置环境变量以提高下载稳定性
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault(
        "TRANSFORMERS_CACHE", os.path.expanduser("~/.cache/huggingface/transformers")
    )

    # 配置网络重试参数
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        # 设置全局的requests session with retry
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 应用到huggingface_hub
        try:
            import huggingface_hub

            huggingface_hub.constants.DEFAULT_REQUEST_TIMEOUT = 60
        except Exception:
            pass

    except ImportError:
        print("ℹ️  requests未安装，跳过网络重试配置")

    max_retries = 3

    # 下载tokenizer（带重试）
    tokenizer = None
    for attempt in range(max_retries):
        try:
            print(f"  - 下载tokenizer (尝试 {attempt + 1}/{max_retries})...")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            print("  ✅ Tokenizer下载成功!")
            break
        except Exception as e:
            print(f"  ❌ Tokenizer下载失败: {type(e).__name__}: {str(e)[:100]}...")
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                print(f"  ⏳ 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print("❌ Tokenizer下载最终失败")
                return False

    # 下载模型（带重试）
    model = None
    for attempt in range(max_retries):
        try:
            print(f"  - 下载模型 (尝试 {attempt + 1}/{max_retries})...")
            model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
            print("  ✅ 模型下载成功!")
            break
        except Exception as e:
            print(f"  ❌ 模型下载失败: {type(e).__name__}: {str(e)[:100]}...")
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                print(f"  ⏳ 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print("❌ 模型下载最终失败")
                return False

    print("✅ 模型缓存完成!")

    # 验证模型可用性
    try:
        print("🧪 验证模型可用性...")
        test_text = "测试文本"
        inputs = tokenizer(
            test_text, return_tensors="pt", padding=True, truncation=True
        )
        outputs = model(**inputs)

        print(f"  - 模型输出维度: {outputs.last_hidden_state.shape}")
        print("✅ 模型验证通过!")

        # 显示缓存位置
        cache_dir = os.environ.get(
            "TRANSFORMERS_CACHE", "~/.cache/huggingface/transformers"
        )
        print(f"  - 缓存位置: {cache_dir}")

        return True

    except Exception as e:
        print(f"❌ 模型验证失败: {e}")
        return False


def check_model_availability():
    """检查模型是否已经可用"""
    import time

    from transformers import AutoModel, AutoTokenizer

    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"🔍 检查模型可用性: {model_name}")

    # 首先检查本地缓存
    try:
        # 尝试使用local_files_only参数检查本地缓存
        tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
        model = AutoModel.from_pretrained(
            model_name, local_files_only=True, trust_remote_code=True
        )
        print("✅ 模型已在本地缓存中可用!")
        return True
    except Exception:
        print("ℹ️  本地缓存中未找到模型，尝试从远程下载...")

    # 如果本地没有，尝试从远程下载（带重试）
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"  尝试 {attempt + 1}/{max_retries}...")

            # 设置较短的超时时间
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name, trust_remote_code=True)

            print("✅ 模型下载并可用!")
            return True

        except Exception as e:
            print(
                f"  ❌ 尝试 {attempt + 1} 失败: {type(e).__name__}: {str(e)[:100]}..."
            )
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # 指数退避
                print(f"  ⏳ 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

    print(f"❌ 经过 {max_retries} 次尝试后，模型仍不可用")
    return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CICD embedding模型管理")
    parser.add_argument("--check", action="store_true", help="检查模型可用性")
    parser.add_argument("--cache", action="store_true", help="缓存模型")
    parser.add_argument("--clear-cache", action="store_true", help="清除模型缓存")

    args = parser.parse_args()

    if args.clear_cache:
        success = clear_model_cache()
        sys.exit(0 if success else 1)
    elif args.check:
        available = check_model_availability()
        sys.exit(0 if available else 1)
    elif args.cache:
        success = cache_embedding_models()
        sys.exit(0 if success else 1)
    else:
        # 默认先检查，如果不可用则缓存
        if not check_model_availability():
            print("模型不可用，开始缓存...")
            success = cache_embedding_models()
            sys.exit(0 if success else 1)
        else:
            print("模型已可用，无需缓存")
            sys.exit(0)
