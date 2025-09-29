#!/usr/bin/env python3
"""向后兼容的包装脚本，转发到 ``sage.tools`` 包实现。"""

from __future__ import annotations

import argparse
import sys

from sage.tools.dev.models.cache import (
    DEFAULT_MODEL_NAME,
    cache_embedding_model,
    check_embedding_model,
    clear_embedding_model_cache,
    configure_hf_environment,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CICD embedding模型管理")
    parser.add_argument(
        "--model", default=DEFAULT_MODEL_NAME, help="需要操作的模型标识"
    )
    parser.add_argument("--check", action="store_true", help="检查模型可用性")
    parser.add_argument("--cache", action="store_true", help="缓存模型")
    parser.add_argument("--clear-cache", action="store_true", help="清除模型缓存")
    parser.add_argument(
        "--configure", action="store_true", help="仅配置Hugging Face相关环境变量"
    )
    parser.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="缓存完成后不执行推理验证",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="下载失败时的最大重试次数",
    )

    args = parser.parse_args(argv)

    if args.configure:
        configure_hf_environment()
        return 0

    if args.clear_cache:
        return 0 if clear_embedding_model_cache(args.model) else 1

    if args.check:
        return 0 if check_embedding_model(args.model) else 1

    if args.cache:
        return (
            0
            if cache_embedding_model(
                args.model, verify=args.verify, retries=args.retries
            )
            else 1
        )

    # 默认行为与历史脚本保持一致：先检查，不通过则执行缓存
    if check_embedding_model(args.model):
        print("模型已可用，无需缓存")
        return 0

    print("模型不可用，开始缓存...")
    return (
        0
        if cache_embedding_model(args.model, verify=args.verify, retries=args.retries)
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
