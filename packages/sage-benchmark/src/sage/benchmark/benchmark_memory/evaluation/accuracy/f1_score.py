"""
F1 Score 指标 - 精确率和召回率的调和平均数
"""

from typing import Any, Dict

from sage.benchmark.benchmark_memory.evaluation.core.metric_interface import BaseMetric


class F1Score(BaseMetric):
    """F1 Score 指标
    
    F1 = 2 * (Precision * Recall) / (Precision + Recall)
    
    使用简单的 token-level 匹配来计算精确率和召回率。
    """
    
    def __init__(self):
        super().__init__(
            name="F1",
            description="F1 Score - 精确率和召回率的调和平均数"
        )
    
    def compute_single_question(
        self, 
        predicted_answer: str, 
        reference_answer: str,
        metadata: Dict[str, Any] | None = None
    ) -> float:
        """计算单个问题的 F1 分数
        
        使用 token-level 匹配：
        1. 将答案分词（按空格分割）
        2. 计算 Precision = 预测中正确的 token 数 / 预测的总 token 数
        3. 计算 Recall = 预测中正确的 token 数 / 参考答案的总 token 数
        4. 计算 F1 = 2 * P * R / (P + R)
        
        Args:
            predicted_answer: 预测答案
            reference_answer: 参考答案
            metadata: 额外元数据（暂未使用）
        
        Returns:
            float: F1 分数 (0-1)
        """
        if not predicted_answer or not reference_answer:
            return 0.0
        
        # 确保答案是字符串类型（处理数字等非字符串答案）
        pred_str = str(predicted_answer) if not isinstance(predicted_answer, str) else predicted_answer
        ref_str = str(reference_answer) if not isinstance(reference_answer, str) else reference_answer
        
        # 转为小写并分词
        pred_tokens = set(pred_str.lower().split())
        ref_tokens = set(ref_str.lower().split())
        
        if not pred_tokens or not ref_tokens:
            return 0.0
        
        # 计算交集
        common_tokens = pred_tokens & ref_tokens
        
        if not common_tokens:
            return 0.0
        
        # 计算 Precision 和 Recall
        precision = len(common_tokens) / len(pred_tokens)
        recall = len(common_tokens) / len(ref_tokens)
        
        # 计算 F1
        if precision + recall == 0:
            return 0.0
        
        f1 = 2 * (precision * recall) / (precision + recall)
        return f1


if __name__ == "__main__":
    # 测试示例
    metric = F1Score()
    
    # 测试用例 1: 完全匹配
    pred1 = "The answer is 42"
    ref1 = "The answer is 42"
    print(f"测试 1 - 完全匹配:")
    print(f"  预测: {pred1}")
    print(f"  参考: {ref1}")
    print(f"  F1: {metric.compute_single_question(pred1, ref1):.4f}\n")
    
    # 测试用例 2: 部分匹配
    pred2 = "The answer is 42"
    ref2 = "The correct answer is 42"
    print(f"测试 2 - 部分匹配:")
    print(f"  预测: {pred2}")
    print(f"  参考: {ref2}")
    print(f"  F1: {metric.compute_single_question(pred2, ref2):.4f}\n")
    
    # 测试用例 3: 完全不匹配
    pred3 = "The answer is 42"
    ref3 = "Wrong response"
    print(f"测试 3 - 完全不匹配:")
    print(f"  预测: {pred3}")
    print(f"  参考: {ref3}")
    print(f"  F1: {metric.compute_single_question(pred3, ref3):.4f}\n")
