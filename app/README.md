# 测试内容

## 0 安装依赖
pip install bm25s
pip install pystemmer

## 1 创建索引

### BM25 模型

```bash
python -m app.index_constructor.create_index --model_name bm25 --corpus_path data/corpus/clapnq.jsonl --save_dir app/index_constructor/test/index
```

### E5 模型

```bash
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
```

## 2 检索测试

### Faiss 测试

```bash
python -m app.retriever.retrieval_test -test faiss
```

### BM25 测试

```bash
python -m app.retriever.retrieval_test -test bm25
```
