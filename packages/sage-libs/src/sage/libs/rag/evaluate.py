from collections import Counter
from typing import Any, Dict, List, Tuple, Union

from rouge import Rouge
from sage.core.api.function.map_function import MapFunction
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoModel, AutoTokenizer


def _normalize_data(data: Union[Dict[str, Any], Tuple[Any, Any], str, Any]) -> Dict[str, Any]:
    """将上游数据标准化为评测期望的字典结构。

    兼容多种入参形态：
    - tuple: (user_query, generated_text)
    - dict: 直接透传（但保证必要键存在）
    - str/其他: 作为 generated 文本

    返回的字典至少包含：
    - 'generated': str
    - 'references': list[str]
    - 'question': str | None
    - 其余键原样保留
    """
    if isinstance(data, tuple):
        # 典型来自 OpenAIGenerator 的输出
        question = data[0] if len(data) > 0 else None
        generated = data[1] if len(data) > 1 else ""
        return {
            "question": question,
            "generated": generated if isinstance(generated, str) else str(generated),
            "references": [],
        }

    if isinstance(data, dict):
        out = dict(data)
        out.setdefault("generated", out.get("pred", ""))
        out.setdefault("references", out.get("golds", []))
        if not isinstance(out.get("references", []), list):
            out["references"] = [str(out["references"])]
        return out

    # 其他类型，统一本为 generated 文本
    return {
        "question": None,
        "generated": data if isinstance(data, str) else str(data),
        "references": [],
    }


class F1Evaluate(MapFunction):
    def _get_tokens(self, text: str):
        return text.lower().split()

    def _f1_score(self, pred: str, ref: str):
        r = Counter(self._get_tokens(ref))
        p = Counter(self._get_tokens(pred))
        common = r & p
        if not r or not p:
            return float(r == p)
        num_common = sum(common.values())
        if num_common == 0:
            return 0.0
        prec = num_common / sum(p.values())
        rec = num_common / sum(r.values())
        return 2 * prec * rec / (prec + rec)

    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        best = max(self._f1_score(pred, g) for g in golds) if golds else 0.0
        print(f"\033[93m[F1] : {best:.4f}\033[0m")
        return nd


class RecallEvaluate(MapFunction):
    def _get_tokens(self, text: str):
        return text.lower().split()

    def _recall(self, pred: str, ref: str):
        r = Counter(self._get_tokens(ref))
        p = Counter(self._get_tokens(pred))
        if not r:
            return 0.0
        common = r & p
        return float(sum(common.values()) / sum(r.values()))

    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        best = max(self._recall(pred, g) for g in golds) if golds else 0.0
        print(f"\033[93m[Recall] : {best:.4f}\033[0m")
        return nd


class BertRecallEvaluate(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        self.model = AutoModel.from_pretrained("bert-base-uncased")

    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        scores = []
        for g in golds:
            encs = self.tokenizer([pred, g], return_tensors="pt", padding=True)
            embs = self.model(**encs).last_hidden_state.mean(dim=1).detach().numpy()
            scores.append(float(cosine_similarity([embs[0]], [embs[1]])[0][0]))
        best = max(scores) if scores else 0.0
        print(f"\033[93m[BertRecall] : {best:.4f}\033[0m")
        return nd


class RougeLEvaluate(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.rouge = Rouge()

    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        scores = [self.rouge.get_scores(pred, g)[0]["rouge-l"]["f"] for g in golds]
        best = max(scores) if scores else 0.0
        print(f"\033[93m[ROUGE-L] : {best:.4f}\033[0m")
        return nd


class BRSEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        scores = [(len(set(pred) & set(g)) / len(set(g))) if g else 0.0 for g in golds]
        best = max(scores) if scores else 0.0
        print(f"\033[93m[BRS] : {best:.4f}\033[0m")
        return nd


class AccuracyEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        correct = any(pred.strip() == g.strip() for g in golds)
        print(f"\033[93m[Acc] : {float(correct):.4f}\033[0m")
        return nd


class TokenCountEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        tokens = nd.get("generated", "").split()
        print(f"\033[93m[Token Count] : {len(tokens)}\033[0m")
        return nd


class LatencyEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        lat = nd.get("refine_time", 0.0) + nd.get("generate_time", 0.0)
        print(f"\033[93m[Latency] : {lat:.2f}s\033[0m")
        return nd


class ContextRecallEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        meta = nd.get("metadata", {}) or {}
        sp = (meta.get("supporting_facts", {}) or {}).get("sent_id", [])
        gold_ids = set(sp)
        ret_ids = set(nd.get("retrieved_sent_ids", []))
        rec = float(len(gold_ids & ret_ids) / len(gold_ids)) if gold_ids else 0.0
        print(f"\033[93m[Context Recall] : {rec:.4f}\033[0m")
        return nd


class CompressionRateEvaluate(MapFunction):
    def _count(self, docs):
        return sum(len(d.split()) for d in docs) or 1

    def execute(self, data: dict):
        nd = _normalize_data(data)
        o = self._count(nd.get("retrieved_docs", []))
        r = self._count(nd.get("refined_docs", []))
        rate = o / r
        print(f"\033[93m[Compression Rate] : {rate:.2f}×\033[0m")
        return nd
