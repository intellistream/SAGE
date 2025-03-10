import sys
import os
import numpy as np
from collections import Counter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.utils.query import Query
from src.utils.file_path import QUERY_FILE

from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
import torch
from rouge import Rouge
from tqdm import tqdm

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def plot_separate_scores(results_by_dialogue, output_image_prefix):
    """
    绘制每轮对话的平均分数变化趋势（分成 4 张图）：
    - X 轴：对话轮次 dialogue_index（减少刻度标注）
    - Y 轴：单个评分指标（BERT Recall、ROUGE-L、BRS、F1）
    """
    sns.set(style="whitegrid")  # 使用 Seaborn 主题

    dialogue_indices = sorted(results_by_dialogue.keys())  # 对话轮次索引

    # 计算每轮对话的平均分数
    avg_bert_rec = [np.mean([r["bert_rec"] for r in results_by_dialogue[idx]]) for idx in dialogue_indices]
    avg_rouge_l = [np.mean([r["rouge_l_score"] for r in results_by_dialogue[idx]]) for idx in dialogue_indices]
    avg_brs = [np.mean([r["brs_score"] for r in results_by_dialogue[idx]]) for idx in dialogue_indices]
    avg_f1 = [np.mean([r["f1_score"] for r in results_by_dialogue[idx]]) for idx in dialogue_indices]

    # 颜色和标题设置
    scores = {
        "BERT Recall": (avg_bert_rec, "#1f77b4"),
        "ROUGE-L": (avg_rouge_l, "#2ca02c"),
        "BRS": (avg_brs, "#d62728"),
        "F1 Score": (avg_f1, "#9467bd")
    }

    for metric_name, (score_values, color) in scores.items():
        plt.figure(figsize=(10, 5))  # 单张图大小
        plt.plot(dialogue_indices, score_values, linestyle='-', color=color, linewidth=2)

        # 设置标题、坐标轴
        plt.xlabel("Dialogue", fontsize=12)
        plt.ylabel(f"{metric_name}", fontsize=12)

        # 调整 x 轴刻度，减少标注密度
        plt.xticks(dialogue_indices[::10], fontsize=10)  # 每 10 个轮次标一个
        plt.yticks(fontsize=10)

        # 添加网格线
        plt.grid(True, linestyle='--', alpha=0.7)

        # 保存图片
        output_image = f"{output_image_prefix}_{metric_name.replace(' ', '_').lower()}.png"
        plt.savefig(output_image, dpi=300, bbox_inches='tight')
        plt.close()  # 关闭当前图，避免重叠

        print(f"Saved: {output_image}")  # 打印保存路径



# 初始化 BERT 模型和分词器
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
model = AutoModel.from_pretrained("bert-base-uncased")

# 初始化 Rouge
rouge = Rouge()


class F1:
    """计算 F1 评分，基于 token 级别的匹配。"""

    def __call__(self, predictions, references):
        scores = [self._f1_score(prediction, reference)
                  for prediction, reference in zip(predictions, references)]
        return {"f1": np.mean(scores)}

    def _f1_score(self, prediction, reference):
        """计算单个预测与参考文本的 F1 分数"""
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

    def _get_tokens(self, text):
        """简单分词，按空格拆分"""
        return text.lower().split()


# 实例化 F1 计算对象
f1_metric = F1()


def load_data(groundtruth_file, generated_file):
    """加载参考文本（groundtruth）和生成的文本"""
    query = Query(groundtruth_file)
    groundtruth = query.get_all_response()

    with open(generated_file, 'r') as file:
        responses = file.readlines()
    responses = [line.strip() for line in responses]

    return groundtruth, responses


def bert_recall(reference, generated):
    """计算 BERT Recall"""
    if not generated.strip():
        return 0.0

    inputs_ref = tokenizer(reference, return_tensors="pt", padding=True, truncation=True)
    inputs_gen = tokenizer(generated, return_tensors="pt", padding=True, truncation=True)

    with torch.no_grad():
        outputs_ref = model(**inputs_ref).last_hidden_state.mean(dim=1)
        outputs_gen = model(**inputs_gen).last_hidden_state.mean(dim=1)

    similarity = cosine_similarity(outputs_ref.numpy(), outputs_gen.numpy())
    return similarity[0][0]


def rouge_l(reference, generated):
    """计算 ROUGE-L"""
    if not generated.strip():
        return 0.0
    scores = rouge.get_scores(generated, reference)
    return scores[0]['rouge-l']['f']


def BRS(reference, generated):
    """计算 BRS (BERT Recall 和 ROUGE-L 的调和平均)"""
    bert_rec = bert_recall(reference, generated)
    rouge_l_score = rouge_l(reference, generated)

    if bert_rec == 0 or rouge_l_score == 0:
        brs_score = 0
    else:
        brs_score = (2 * bert_rec * rouge_l_score) / (bert_rec + rouge_l_score)

    return bert_rec, rouge_l_score, brs_score


def evaluate_all(query, generated_texts):
    """
    评估所有样本，按照 `dialogue_index` 进行分组计算每轮的平均指标，同时保留 `tqdm` 进度条。
    """
    results_by_dialogue = {}  # 按 dialogue_index 分组存储结果
    total_turns = sum(1 for _ in query.iter_all_dialogues())  # 计算总对话轮数
    gen_index = 0  # 追踪生成文本索引

    with tqdm(total=total_turns, desc="Evaluating", unit="turn") as pbar:
        for dialogue_index, turn, q, r in query.iter_all_dialogues():
            if dialogue_index not in results_by_dialogue:
                results_by_dialogue[dialogue_index] = []

            # 避免索引越界
            if gen_index >= len(generated_texts):
                break

            generated = generated_texts[gen_index]
            gen_index += 1  # 更新索引

            # 计算指标
            bert_rec, rouge_l_score, brs_score = BRS(r, generated)
            f1_score = f1_metric._f1_score(generated, r)

            results_by_dialogue[dialogue_index].append({
                "turn": turn,
                "reference": r,
                "generated": generated,
                "bert_rec": bert_rec,
                "rouge_l_score": rouge_l_score,
                "brs_score": brs_score,
                "f1_score": f1_score
            })

            pbar.update(1)  # 更新进度条

    return results_by_dialogue


def save_results(results_by_dialogue, output_file):
    """
    保存评估结果到文件：
    1. 先写入整体平均分
    2. 再写入每轮对话的平均分和详细结果
    """
    all_bert_rec = []
    all_rouge_l = []
    all_brs = []
    all_f1 = []

    with open(output_file, "w") as file:
        # 计算所有对话的总体平均分
        for results in results_by_dialogue.values():
            all_bert_rec.extend([r["bert_rec"] for r in results])
            all_rouge_l.extend([r["rouge_l_score"] for r in results])
            all_brs.extend([r["brs_score"] for r in results])
            all_f1.extend([r["f1_score"] for r in results])

        overall_avg_bert_rec = np.mean(all_bert_rec)
        overall_avg_rouge_l = np.mean(all_rouge_l)
        overall_avg_brs = np.mean(all_brs)
        overall_avg_f1 = np.mean(all_f1)

        # 先写入整体平均分
        file.write("\n===== Overall Average Scores =====\n")
        file.write(f"Overall BERT Recall: {overall_avg_bert_rec:.4f}\n")
        file.write(f"Overall ROUGE-L Score: {overall_avg_rouge_l:.4f}\n")
        file.write(f"Overall BRS Score: {overall_avg_brs:.4f}\n")
        file.write(f"Overall F1 Score: {overall_avg_f1:.4f}\n")
        file.write("=" * 60 + "\n")

        # 逐轮写入对话评分
        for dialogue_index, results in results_by_dialogue.items():
            avg_bert_rec = np.mean([r["bert_rec"] for r in results])
            avg_rouge_l = np.mean([r["rouge_l_score"] for r in results])
            avg_brs_score = np.mean([r["brs_score"] for r in results])
            avg_f1 = np.mean([r["f1_score"] for r in results])

            # 先写入该轮对话的平均指标
            file.write(f"Dialogue {dialogue_index} - Average Scores:\n")
            file.write(f"  Average BERT Recall: {avg_bert_rec:.4f}\n")
            file.write(f"  Average ROUGE-L Score: {avg_rouge_l:.4f}\n")
            file.write(f"  Average BRS Score: {avg_brs_score:.4f}\n")
            file.write(f"  Average F1 Score: {avg_f1:.4f}\n")
            file.write("=" * 60 + "\n")

            # 再写入该轮的详细结果
            for r in results:
                file.write(f"  Turn {r['turn']}:\n")
                file.write(f"    Reference: {r['reference']}\n")
                file.write(f"    Generated: {r['generated']}\n")
                file.write(f"    BERT Recall: {r['bert_rec']:.4f}\n")
                file.write(f"    ROUGE-L Score: {r['rouge_l_score']:.4f}\n")
                file.write(f"    BRS Score: {r['brs_score']:.4f}\n")
                file.write(f"    F1 Score: {r['f1_score']:.4f}\n")
                file.write("-" * 50 + "\n")

    print(f"\nEvaluation results saved to {output_file}")
    print("\n===== Overall Average Scores =====")
    print(f"Overall BERT Recall: {overall_avg_bert_rec:.4f}")
    print(f"Overall ROUGE-L Score: {overall_avg_rouge_l:.4f}")
    print(f"Overall BRS Score: {overall_avg_brs:.4f}")
    print(f"Overall F1 Score: {overall_avg_f1:.4f}")
    print("=" * 60)



def main():
    # 加载数据
    groundtruth_file = QUERY_FILE
    generated_file = '/workspace/experiment/memorag/output.txt'
    query = Query(groundtruth_file)

    with open(generated_file, 'r') as file:
        generated_texts = [line.strip() for line in file.readlines()]

    # 评估所有对话
    results_by_dialogue = evaluate_all(query, generated_texts)

    # 保存结果
    output_file = "/workspace/experiment/memorag/evaluation_results.txt"
    output_image = "/workspace/experiment/memorag/score_plot.png"

    save_results(results_by_dialogue, output_file)
    plot_separate_scores(results_by_dialogue, output_image)

if __name__ == "__main__":
    main()

