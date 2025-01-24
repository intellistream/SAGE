import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.utils.query import Query
from src.utils.file_path import QUERY_FILE

from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
import torch
from rouge import Rouge
from tqdm import tqdm

# 初始化 BERT 模型和分词器
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
model = AutoModel.from_pretrained("bert-base-uncased")

# 初始化 Rouge
rouge = Rouge()

def load_data(groundtruth_file, generated_file):
    """
    加载参考文本（groundtruth）和生成的文本
    """
    # 加载参考文本
    query = Query(groundtruth_file)
    groundtruth = query.get_all_response()

    # 加载生成的文本
    with open(generated_file, 'r') as file:
        responses = file.readlines()
    responses = [line.strip() for line in responses]

    return groundtruth, responses

def bert_recall(reference, generated):
    """
    计算 BERT Recall 分数
    """
    if not generated.strip():  # 检查生成的文本是否为空
        print(f"Error: Generated text is empty for reference: '{reference}'")
        return 0.0  # 如果为空，返回 0 分

    inputs_ref = tokenizer(reference, return_tensors="pt", padding=True, truncation=True)
    inputs_gen = tokenizer(generated, return_tensors="pt", padding=True, truncation=True)

    with torch.no_grad():
        outputs_ref = model(**inputs_ref).last_hidden_state.mean(dim=1)
        outputs_gen = model(**inputs_gen).last_hidden_state.mean(dim=1)

    similarity = cosine_similarity(outputs_ref.numpy(), outputs_gen.numpy())
    return similarity[0][0]

def rouge_l(reference, generated):
    """
    计算 ROUGE-L 分数
    """
    if not generated.strip():  # 检查生成的文本是否为空
        return 0.0  # 如果为空，返回 0 分
    scores = rouge.get_scores(generated, reference)
    return scores[0]['rouge-l']['f']

def rbalg(reference, generated):
    """
    计算 RBalg 分数
    """
    bert_rec = bert_recall(reference, generated)
    rouge_l_score = rouge_l(reference, generated)

    # 计算 RBalg 分数
    if bert_rec == 0 or rouge_l_score == 0:
        rbalg_score = 0  # 如果任一分数为 0，RBalg 分数为 0
    else:
        rbalg_score = (2 * bert_rec * rouge_l_score) / (bert_rec + rouge_l_score)

    return bert_rec, rouge_l_score, rbalg_score

def evaluate_all(groundtruth, generated_texts):
    """
    评估所有样本
    """
    results = []
    for ref, gen in tqdm(zip(groundtruth, generated_texts), total=len(groundtruth), desc="Evaluating"):
        bert_rec, rouge_l_score, rbalg_score = rbalg(ref, gen)
        results.append({
            "reference": ref,
            "generated": gen,
            "bert_rec": bert_rec,
            "rouge_l_score": rouge_l_score,
            "rbalg_score": rbalg_score
        })
    return results

def save_results(results, output_file):
    """
    保存评估结果到文件
    """
    average_rbalg_score = sum(result["rbalg_score"] for result in results) / len(results)
    average_bert_rec = sum(result["bert_rec"] for result in results) / len(results)
    average_rouge_l = sum(result["rouge_l_score"] for result in results) / len(results)

    print(f"Average RBalg Score: {average_rbalg_score:.4f}")
    print(f"Average BERT Recall: {average_bert_rec:.4f}")
    print(f"Average ROUGE-L Score: {average_rouge_l:.4f}")

    with open(output_file, "w") as file:
        file.write(f"Average RBalg Score: {average_rbalg_score:.4f}\n")
        file.write(f"Average BERT Recall: {average_bert_rec:.4f}\n")
        file.write(f"Average ROUGE-L Score: {average_rouge_l:.4f}\n")
        file.write("Detailed Results:\n")
        for i, result in enumerate(results):
            file.write(f"Sample {i + 1}:\n")
            file.write(f"  Reference: {result['reference']}\n")
            file.write(f"  Generated: {result['generated']}\n")
            file.write(f"  BERT Recall: {result['bert_rec']:.4f}\n")
            file.write(f"  ROUGE-L Score: {result['rouge_l_score']:.4f}\n")
            file.write(f"  RBalg Score: {result['rbalg_score']:.4f}\n")
            file.write("-" * 50 + "\n")

    print(f"\nDetailed results have been saved to {output_file}")

def main():
    # 加载数据
    groundtruth_file = QUERY_FILE
    generated_file = '/workspace/experiment/memorag/output.txt'
    groundtruth, generated_texts = load_data(groundtruth_file, generated_file)

    print(f"generateNum: {len(generated_texts)}")
    print(f"groundtruthNum: {len(groundtruth)}")

    results = evaluate_all(groundtruth[:len(generated_texts)], generated_texts)

    # 保存结果
    output_file = "/workspace/experiment/memorag/evaluation_results.txt"
    save_results(results, output_file)

if __name__ == "__main__":
    main()