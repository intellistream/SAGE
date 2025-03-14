import argparse
from app.index_constructor.base_index_constructor.index_factory import IndexFactory

def main():
    parser = argparse.ArgumentParser(description="Build an index for retrieval.")
    parser.add_argument("--model_name", type=str, required=True, help="Retrieval method (e.g., bm25, e5).")
    parser.add_argument("--corpus_path", type=str, required=True, help="Path to the corpus file.")
    parser.add_argument("--save_dir", type=str, default="indexes/", help="Directory to save the index.")

    # 解析不同索引方法的特定参数
    parser.add_argument("--bm25_backend", type=str, default="pyserini", choices=["pyserini", "bm25s"],
                        help="Backend for BM25 index construction.")
    parser.add_argument("--model_path", type=str, help="Path to the dense model (for e5).")
    parser.add_argument("--use_fp16", action="store_true", help="Use fp16 for faster inference (for e5).")
    parser.add_argument("--model_type", type=str, default="bert", help="Model type (e.g., bert, roberta) for e5.")
    parser.add_argument("--pooling_method", type=str, default="mean", help="Pooling method (e5).")
    parser.add_argument("--faiss_type", type=str, default="Flat", help="Faiss index type (e.g., Flat, IVF).")
    parser.add_argument("--faiss_gpu", action="store_true", help="Use GPU for Faiss index (for e5).")
    parser.add_argument("--max_length", type=int, default=512, help="Max input length for tokenization.")
    parser.add_argument("--batch_size", type=int, default=256, help="Batch size for indexing.")

    args = parser.parse_args()

    # 根据 retrieval_method 构造参数
    index_kwargs = {
        "corpus_path": args.corpus_path,
        "save_dir": args.save_dir,
    }

    if args.model_name == "bm25":
        index_kwargs.update({
            "backend": args.bm25_backend,
            "dir_name": "clapnq_test",
        })
    elif args.model_name == "e5":
        index_kwargs.update({
            "max_length": args.max_length,
            "batch_size": args.batch_size,
            "model_path": args.model_path,
            "use_fp16": args.use_fp16,
            "model_type": args.model_type,
            "pooling_method": args.pooling_method,
            "faiss_type": args.faiss_type,
            "faiss_gpu": args.faiss_gpu,
        })
    else:
        raise ValueError(f"Unsupported retrieval method: {args.retrieval_method}")

    # 使用工厂模式创建索引构造器
    index_builder = IndexFactory.create_index_constructor(
        model_name=args.model_name,
        **index_kwargs
    )

    # 构建索引
    index_builder.build_index()

if __name__ == "__main__":
    main()

'''
python -m app.index_constructor.create_index --model_name bm25 --corpus_path data/corpus/clapnq.jsonl --save_dir app/index_constructor/test/index

python -m app.index_constructor.create_index \
    --model_name e5 \
    --corpus_path data/corpus/clapnq.jsonl \
    --save_dir app/index_constructor/test/index \
    --model_path intfloat/e5-base-v2 \
    --model_type bert \
    --pooling_method mean \
    --max_length 512 \
    --batch_size 256 \
    --faiss_type Flat
'''