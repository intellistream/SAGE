from sage.api.operator import EvaluateFunction, Data
from collections import Counter
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
from rouge import Rouge




class F1Evaluate(EvaluateFunction):
    def __init__(self, config):
        super().__init__()
    
    def _get_tokens(self, text):
        return text.lower().split()
    
    def _f1_score(self, prediction, reference):
        reference_tokens = self._get_tokens(reference)
        prediction_tokens = self._get_tokens(prediction)

        common_tokens = Counter(reference_tokens) & Counter(prediction_tokens)
        num_common = sum(common_tokens.values())

        if len(reference_tokens) == 0 or len(prediction_tokens) == 0:
            return int(reference_tokens == prediction_tokens)

        if num_common == 0:
            return 0

        precision = num_common / len(prediction_tokens)
        recall = num_common / len(reference_tokens)
        f1 = (2 * precision * recall) / (precision + recall)
        return f1

    def execute(self, data: Data[tuple[str, str]]):
        reference, prediction = data.data
        score = self._f1_score(prediction, reference)

        print(f"\033[93m[F1 Score] : {score:.4f}\033[0m")


class BertRecallEvaluate(EvaluateFunction):
    def __init__(self, config):
        super().__init__()
        self.model = AutoModel.from_pretrained("bert-base-uncased")
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        
    def bert_recall(self, reference, generated):
        if not generated.strip():
            return 0.0
        inputs_ref = self.tokenizer(reference, return_tensors="pt", padding=True, truncation=True)
        inputs_gen = self.tokenizer(generated, return_tensors="pt", padding=True, truncation=True)

        with torch.no_grad():
            outputs_ref = self.model(**inputs_ref).last_hidden_state.mean(dim=1)
            outputs_gen = self.model(**inputs_gen).last_hidden_state.mean(dim=1)

        similarity = cosine_similarity(outputs_ref.numpy(), outputs_gen.numpy())
        return similarity[0][0]

    def execute(self, data: Data[tuple[str, str]]):
        reference, generated = data.data
        score = self.bert_recall(reference, generated)

        print(f"\033[95m[BERT Recall] : {score:.4f}\033[0m")


class RougeLEvaluate(EvaluateFunction):
    def __init__(self, config):
        self.rouge = Rouge()
        super().__init__()

    def rouge_l(self, reference, generated):
        if not generated.strip():
            return 0.0
        scores = self.rouge.get_scores(generated, reference)
        return scores[0]['rouge-l']['f']

    def execute(self, data: Data[tuple[str, str]]):
        reference, generated = data.data
        score = self.rouge_l(reference, generated)

        print(f"\033[94m[ROUGE-L] : {score:.4f}\033[0m")


class BRSEvaluate(EvaluateFunction):
    def __init__(self, config):
        super().__init__()
        self.bert_recall_evaluate = BertRecallEvaluate(config)
        self.rouge_l_evaluate = RougeLEvaluate(config)

    def BRS(self, reference, generated):
        bert_rec = self.bert_recall_evaluate.bert_recall(reference, generated)
        rouge_l_score = self.rouge_l_evaluate.rouge_l(reference, generated)

        if bert_rec == 0 or rouge_l_score == 0:
            return 0
        return (2 * bert_rec * rouge_l_score) / (bert_rec + rouge_l_score)

    def execute(self, data: Data[tuple[str, str]]):
        reference, generated = data.data
        score = self.BRS(reference, generated)

        print(f"\033[92m[BRS Score] : {score:.4f}\033[0m")



def test_evaluate_functions():
    # 模拟一条数据：reference 和 generated
    reference = "The cat sits on the mat."
    generated = "A cat is sitting on a mat."

    data = Data((reference, generated))

    config = {}  # 测试时config可以是空的

    # 初始化所有评估器
    f1_eval = F1Evaluate(config)
    bert_recall_eval = BertRecallEvaluate(config)
    rouge_l_eval = RougeLEvaluate(config)
    brs_eval = BRSEvaluate(config)

    # 分别执行
    print("\n=== F1 Evaluate ===")
    f1_eval.execute(data)

    print("\n=== BERT Recall Evaluate ===")
    bert_recall_eval.execute(data)

    print("\n=== ROUGE-L Evaluate ===")
    rouge_l_eval.execute(data)

    print("\n=== BRS Evaluate ===")
    brs_eval.execute(data)

test_evaluate_functions()