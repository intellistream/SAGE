from collections import Counter
from typing import Any, Dict, List, Tuple, Union

from rouge import Rouge
from sage.core.api.function.map_function import MapFunction
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoModel, AutoTokenizer


def _normalize_data(data: Union[Dict[str, Any], Tuple[Any, Any], str, Any]) -> Dict[str, Any]:
    """将上游数据标准化为评测期望的字典结构。

    兼容多种入参形态：
    - tuple: (user_query, generated_text) - 兼容旧格式
    - dict: 完整数据字典 - 新格式，包含所有字段
    - str/其他: 作为 generated 文本

    返回的字典至少包含：
    - 'generated': str
    - 'references': list[str]
    - 'question': str | None
    - 其余键原样保留
    """
    if isinstance(data, tuple):
        # 兼容旧的tuple格式: (question_data, generated_text)
        question_data = data[0] if len(data) > 0 else {}
        generated = data[1] if len(data) > 1 else ""
        
        # 如果question_data是字典且包含references，提取它们
        if isinstance(question_data, dict) and "references" in question_data:
            return {
                "question": question_data,
                "generated": generated if isinstance(generated, str) else str(generated),
                "references": question_data.get("references", []),
            }
        else:
            return {
                "question": question_data,
                "generated": generated if isinstance(generated, str) else str(generated),
                "references": [],
            }

    if isinstance(data, dict):
        out = dict(data)
        # 确保generated字段存在
        out.setdefault("generated", out.get("pred", ""))
        
        # 从多个可能的位置提取references，优先级：
        # 1. 顶级references字段
        # 2. golds字段  
        # 3. question.references字段
        references = out.get("references", [])
        if not references:
            references = out.get("golds", [])
        if not references and "question" in out and isinstance(out["question"], dict):
            references = out["question"].get("references", [])
        
        out["references"] = references if isinstance(references, list) else [str(references)]
        return out

    # 其他类型，统一作为 generated 文本
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
        nd["f1"] = best  # 将F1分数添加到结果中
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
        nd["recall"] = best  # 将Recall分数添加到结果中
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
        nd["bert_recall"] = best  # 将BertRecall分数添加到结果中
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
        nd["rouge_l"] = best  # 将ROUGE-L分数添加到结果中
        return nd


class BRSEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        scores = [(len(set(pred) & set(g)) / len(set(g))) if g else 0.0 for g in golds]
        best = max(scores) if scores else 0.0
        print(f"\033[93m[BRS] : {best:.4f}\033[0m")
        nd["brs"] = best  # 将BRS分数添加到结果中
        return nd


class AccuracyEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        golds = nd.get("references", [])
        pred = nd.get("generated", "")
        correct = any(pred.strip() == g.strip() for g in golds)
        accuracy = float(correct)
        print(f"\033[93m[Acc] : {accuracy:.4f}\033[0m")
        nd["accuracy"] = accuracy  # 将Accuracy分数添加到结果中
        return nd


class TokenCountEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        # 统计refined_docs的token数量，而不是generated的
        refined_docs = nd.get("refined_docs", [])
        total_tokens = 0
        for doc in refined_docs:
            if isinstance(doc, str):
                total_tokens += len(doc.split())
            elif isinstance(doc, dict) and "text" in doc:
                total_tokens += len(doc["text"].split())
            else:
                total_tokens += len(str(doc).split())
        print(f"\033[93m[Token Count] : {total_tokens}\033[0m")
        nd["token_count"] = total_tokens  # 将Token数量添加到结果中
        return nd


class LatencyEvaluate(MapFunction):
    def execute(self, data: dict):
        nd = _normalize_data(data)
        lat = nd.get("refine_time", 0.0) + nd.get("generate_time", 0.0)
        print(f"\033[93m[Latency] : {lat:.2f}s\033[0m")
        nd["latency"] = lat  # 将延迟添加到结果中
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
        nd["context_recall"] = rec  # 将Context Recall添加到结果中
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
        nd["compression_rate"] = rate  # 将压缩率添加到结果中
        return nd
