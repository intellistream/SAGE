from collections import Counter
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
from rouge import Rouge

from sage.core.api.function.map_function import MapFunction



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
        rec  = num_common / sum(r.values())
        return 2 * prec * rec / (prec + rec)

    def execute(self, data: dict):
        golds = data["references"]        # 始终是列表
        pred  = data.get("generated", "")
        best  = max(self._f1_score(pred, g) for g in golds) if golds else 0.0
        print(f"\033[93m[F1] : {best:.4f}\033[0m")
        return data


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
        golds = data["references"]
        pred  = data.get("generated", "")
        best  = max(self._recall(pred, g) for g in golds) if golds else 0.0
        print(f"\033[93m[Recall] : {best:.4f}\033[0m")
        return data


class BertRecallEvaluate(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        self.model     = AutoModel.from_pretrained("bert-base-uncased")

    def execute(self, data: dict):
        golds = data["references"]
        pred  = data.get("generated", "")
        scores = []
        for g in golds:
            encs   = self.tokenizer([pred, g], return_tensors="pt", padding=True)
            embs   = self.model(**encs).last_hidden_state.mean(dim=1).detach().numpy()
            scores.append(float(cosine_similarity([embs[0]], [embs[1]])[0][0]))
        best = max(scores) if scores else 0.0
        print(f"\033[93m[BertRecall] : {best:.4f}\033[0m")
        return data


class RougeLEvaluate(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.rouge = Rouge()

    def execute(self, data: dict):
        golds = data["references"]
        pred  = data.get("generated", "")
        scores = [self.rouge.get_scores(pred, g)[0]["rouge-l"]["f"] for g in golds]
        best   = max(scores) if scores else 0.0
        print(f"\033[93m[ROUGE-L] : {best:.4f}\033[0m")
        return data


class BRSEvaluate(MapFunction):
    def execute(self, data: dict):
        golds = data["references"]
        pred  = data.get("generated", "")
        scores = [(len(set(pred) & set(g)) / len(set(g))) if g else 0.0 for g in golds]
        best   = max(scores) if scores else 0.0
        print(f"\033[93m[BRS] : {best:.4f}\033[0m")
        return data


class AccuracyEvaluate(MapFunction):
    def execute(self, data: dict):
        golds   = data["references"]
        pred    = data.get("generated", "")
        correct = any(pred.strip() == g.strip() for g in golds)
        print(f"\033[93m[Acc] : {float(correct):.4f}\033[0m")
        return data


class TokenCountEvaluate(MapFunction):
    def execute(self, data: dict):
        tokens = data.get("pred", "").split()
        print(f"\033[93m[Token Count] : {len(tokens)}\033[0m")
        return data


class LatencyEvaluate(MapFunction):
    def execute(self, data: dict):
        lat = data.get("refine_time", 0.0) + data.get("generate_time", 0.0)
        print(f"\033[93m[Latency] : {lat:.2f}s\033[0m")
        return data


class ContextRecallEvaluate(MapFunction):
    def execute(self, data: dict):
        gold_ids = set(data["metadata"]["supporting_facts"]["sent_id"])
        ret_ids  = set(data.get("retrieved_sent_ids", []))
        rec = float(len(gold_ids & ret_ids) / len(gold_ids)) if gold_ids else 0.0
        print(f"\033[93m[Context Recall] : {rec:.4f}\033[0m")
        return data


class CompressionRateEvaluate(MapFunction):
    def _count(self, docs):
        return sum(len(d.split()) for d in docs) or 1

    def execute(self, data: dict):
        o = self._count(data.get("retrieved_docs", []))
        r = self._count(data.get("refined_docs", []))
        rate = o / r
        print(f"\033[93m[Compression Rate] : {rate:.2f}×\033[0m")
        return data