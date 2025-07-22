from collections import Counter
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
from rouge import Rouge

from sage_core.function.map_function import MapFunction



class F1Evaluate(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)

    def _get_tokens(self, text: str):
        return text.lower().split()

    def _f1_score(self, prediction: str, reference: str):
        ref_toks  = self._get_tokens(reference)
        pred_toks = self._get_tokens(prediction)
        common    = Counter(ref_toks) & Counter(pred_toks)
        num_common = sum(common.values())
        if not ref_toks or not pred_toks:
            return float(ref_toks == pred_toks)
        if num_common == 0:
            return 0.0
        p = num_common / len(pred_toks)
        r = num_common / len(ref_toks)
        return 2 * p * r / (p + r)

    def execute(self, data: dict):
        score = self._f1_score(data["generated"], data["reference"])
        print(f"\033[93m[F1 Score] : {score:.4f}\033[0m")
        return data


class RecallEvaluate(MapFunction):
    """纯召回率 Recall = #common / |reference_tokens|"""
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
    def _get_tokens(self, text: str):
        return text.lower().split()
    def _recall(self, prediction: str, reference: str):
        ref_toks = self._get_tokens(reference)
        pred_toks= self._get_tokens(prediction)
        if not ref_toks:
            return 0.0
        common = Counter(ref_toks) & Counter(pred_toks)
        return float(sum(common.values()) / len(ref_toks))
    def execute(self, data: dict):
        score = self._recall(data["generated"], data["reference"])
        print(f"\033[96m[Recall] : {score:.4f}\033[0m")
        return data


class BertRecallEvaluate(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.model     = AutoModel.from_pretrained("bert-base-uncased")
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    def _bert_recall(self, reference: str, generated: str):
        if not generated.strip():
            return 0.0
        inp_ref = self.tokenizer(reference, return_tensors="pt", padding=True, truncation=True)
        inp_gen = self.tokenizer(generated, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            out_ref = self.model(**inp_ref).last_hidden_state.mean(dim=1)
            out_gen = self.model(**inp_gen).last_hidden_state.mean(dim=1)
        sim = cosine_similarity(out_ref.numpy(), out_gen.numpy())
        return float(sim[0][0])
    def execute(self, data: dict):
        score = self._bert_recall(data["reference"], data["generated"])
        print(f"\033[95m[BERT Recall] : {score:.4f}\033[0m")
        return data


class RougeLEvaluate(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.rouge = Rouge()
    def _rouge_l(self, reference: str, generated: str):
        if not generated.strip():
            return 0.0
        scores = self.rouge.get_scores(generated, reference)
        return float(scores[0]['rouge-l']['f'])
    def execute(self, data: dict):
        score = self._rouge_l(data["reference"], data["generated"])
        print(f"\033[94m[ROUGE-L] : {score:.4f}\033[0m")
        return data


class BRSEvaluate(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.bert = BertRecallEvaluate(config)
        self.rouge = RougeLEvaluate(config)
    def _brs(self, ref: str, gen: str):
        b = self.bert._bert_recall(ref, gen)
        r = self.rouge._rouge_l(ref, gen)
        if b == 0 or r == 0:
            return 0.0
        return 2 * b * r / (b + r)
    def execute(self, data: dict):
        score = self._brs(data["reference"], data["generated"])
        print(f"\033[92m[BRS Score] : {score:.4f}\033[0m")
        return data


class AccuracyEvaluate(MapFunction):
    """严格匹配准确率 ACC"""
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
    def execute(self, data: dict):
        acc = float(data["reference"].strip() == data["generated"].strip())
        print(f"\033[96m[ACC] : {acc:.4f}\033[0m")
        return data


class TokenCountEvaluate(MapFunction):
    """原始/压缩 token 数及比例"""
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
    def _count(self, docs):
        return sum(len(d.lower().split()) for d in docs)
    def execute(self, data: dict):
        o = self._count(data["retrieved_docs"])
        r = self._count(data["refined_docs"]) or 1
        print(f"\033[96m[Tokens] Orig: {o}, Ref: {r}, Ratio: {o/r:.2f}\033[0m")
        return data


class LatencyEvaluate(MapFunction):
    """检索+压缩+生成 总延迟"""
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
    def execute(self, data: dict):
        total = data["retrieval_time"] + data["refine_time"] + data["generation_time"]
        print(f"\033[96m[Latency] Total: {total:.3f}s\033[0m")
        return data


class ContextRecallEvaluate(MapFunction):
    """上下文召回率 = |gold ∩ ctx| / |gold|"""
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
    def _toks(self, t): return t.lower().split()
    def execute(self, data: dict):
        gold = set(self._toks(data["reference"]))
        ctx  = set(self._toks(" ".join(data["refined_docs"])))
        rec  = float(len(gold & ctx) / len(gold)) if gold else 0.0
        print(f"\033[96m[Context Recall] : {rec:.4f}\033[0m")
        return data


class CompressionRateEvaluate(MapFunction):
    """压缩率 = orig_tokens / refined_tokens"""
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
    def _count(self, docs): return sum(len(d.lower().split()) for d in docs) or 1
    def execute(self, data: dict):
        o = self._count(data["retrieved_docs"])
        r = self._count(data["refined_docs"])
        print(f"\033[96m[Compression Rate] : {o/r:.2f}×\033[0m")
        return data