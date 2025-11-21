"""
Metrics computation for benchmark evaluation

This module provides functions to compute recall and other metrics
by comparing algorithm results with groundtruth.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
import os


def compute_recall(predictions: np.ndarray, 
                   groundtruth: np.ndarray, 
                   k: Optional[int] = None) -> float:
    """
    Compute recall@k for a set of predictions against groundtruth.
    
    Args:
        predictions: Predicted neighbor IDs, shape (nq, k_pred)
        groundtruth: Groundtruth neighbor IDs, shape (nq, k_gt)
        k: Number of neighbors to consider (default: use all predictions)
    
    Returns:
        Recall@k as a float between 0 and 1
    """
    if k is None:
        k = predictions.shape[1]
    
    # Truncate to k
    pred_k = predictions[:, :k]
    gt_k = groundtruth[:, :k]
    
    # For each query, count how many predicted neighbors are in groundtruth
    recalls = []
    for i in range(len(pred_k)):
        # Convert to sets for intersection
        pred_set = set(pred_k[i])
        gt_set = set(gt_k[i])
        
        # Recall = |intersection| / k
        intersection = len(pred_set & gt_set)
        recall = intersection / k
        recalls.append(recall)
    
    return float(np.mean(recalls))


def compute_recall_at_k(predictions: np.ndarray,
                       groundtruth: np.ndarray,
                       k_values: List[int]) -> Dict[int, float]:
    """
    Compute recall@k for multiple k values.
    
    Args:
        predictions: Predicted neighbor IDs, shape (nq, k_pred)
        groundtruth: Groundtruth neighbor IDs, shape (nq, k_gt)
        k_values: List of k values to compute
    
    Returns:
        Dictionary mapping k to recall@k
    """
    results = {}
    for k in k_values:
        if k <= predictions.shape[1] and k <= groundtruth.shape[1]:
            results[k] = compute_recall(predictions, groundtruth, k)
    return results


def compute_recall_per_query(predictions: np.ndarray,
                             groundtruth: np.ndarray,
                             k: Optional[int] = None) -> np.ndarray:
    """
    Compute recall@k for each query individually.
    
    Args:
        predictions: Predicted neighbor IDs, shape (nq, k_pred)
        groundtruth: Groundtruth neighbor IDs, shape (nq, k_gt)
        k: Number of neighbors to consider
    
    Returns:
        Array of recall values, shape (nq,)
    """
    if k is None:
        k = predictions.shape[1]
    
    pred_k = predictions[:, :k]
    gt_k = groundtruth[:, :k]
    
    recalls = []
    for i in range(len(pred_k)):
        pred_set = set(pred_k[i])
        gt_set = set(gt_k[i])
        intersection = len(pred_set & gt_set)
        recalls.append(intersection / k)
    
    return np.array(recalls)


def load_groundtruth_for_step(groundtruth_dir: str, step: int) -> Optional[np.ndarray]:
    """
    Load groundtruth tags for a specific step.
    
    Args:
        groundtruth_dir: Directory containing groundtruth files
        step: Step number
    
    Returns:
        Groundtruth tags array or None if not found
    """
    gt_file = os.path.join(groundtruth_dir, f"step{step}_tags.npy")
    if os.path.exists(gt_file):
        return np.load(gt_file)
    return None


def load_groundtruth_continuous(groundtruth_dir: str, 
                               step: int, 
                               continuous_id: int) -> Optional[np.ndarray]:
    """
    Load groundtruth for a continuous query.
    
    Args:
        groundtruth_dir: Directory containing groundtruth files
        step: Step number
        continuous_id: Continuous query ID
    
    Returns:
        Groundtruth tags array or None if not found
    """
    gt_file = os.path.join(groundtruth_dir, f"step{step}_continuous_{continuous_id}_tags.npy")
    if os.path.exists(gt_file):
        return np.load(gt_file)
    return None


def compute_metrics_with_groundtruth(results: Dict,
                                    groundtruth_dir: str,
                                    k_values: List[int] = None) -> Dict:
    """
    Compute recall metrics by comparing results with groundtruth.
    
    Args:
        results: Results dictionary from CongestionRunner
        groundtruth_dir: Directory containing groundtruth files
        k_values: List of k values to compute recall for (default: [1, 10, 100])
    
    Returns:
        Dictionary with recall metrics added
    """
    if k_values is None:
        k_values = [1, 10, 100]
    
    metrics = {
        'recall_at_k': {},
        'continuous_query_recalls': [],
        'search_step_recalls': {}
    }
    
    # Process continuous query results
    continuous_results = results.get('continuous_query_results', [])
    if continuous_results:
        for idx, pred_results in enumerate(continuous_results):
            # Try to load corresponding groundtruth
            # Assume continuous queries are from step 2 (batch_insert)
            gt = load_groundtruth_continuous(groundtruth_dir, step=2, continuous_id=idx)
            
            if gt is not None and pred_results is not None:
                pred_array = np.array(pred_results) if not isinstance(pred_results, np.ndarray) else pred_results
                
                # Compute recall for each k
                recalls = {}
                for k in k_values:
                    if k <= pred_array.shape[1] and k <= gt.shape[1]:
                        recalls[f'recall@{k}'] = compute_recall(pred_array, gt, k)
                
                metrics['continuous_query_recalls'].append({
                    'query_id': idx,
                    'recalls': recalls
                })
    
    # Aggregate continuous query recalls
    if metrics['continuous_query_recalls']:
        for k in k_values:
            key = f'recall@{k}'
            recalls_at_k = [r['recalls'].get(key, 0) for r in metrics['continuous_query_recalls'] if key in r['recalls']]
            if recalls_at_k:
                metrics['recall_at_k'][k] = {
                    'mean': float(np.mean(recalls_at_k)),
                    'std': float(np.std(recalls_at_k)),
                    'min': float(np.min(recalls_at_k)),
                    'max': float(np.max(recalls_at_k)),
                }
    
    return metrics


def format_recall_results(metrics: Dict) -> str:
    """
    Format recall metrics as a readable string.
    
    Args:
        metrics: Metrics dictionary with recall data
    
    Returns:
        Formatted string
    """
    lines = []
    lines.append("=== Recall Metrics ===")
    
    if 'recall_at_k' in metrics and metrics['recall_at_k']:
        lines.append("\nRecall@K (aggregated):")
        for k, stats in sorted(metrics['recall_at_k'].items()):
            lines.append(f"  Recall@{k}: {stats['mean']:.4f} "
                        f"(std={stats['std']:.4f}, min={stats['min']:.4f}, max={stats['max']:.4f})")
    
    if 'continuous_query_recalls' in metrics and metrics['continuous_query_recalls']:
        lines.append(f"\nContinuous queries evaluated: {len(metrics['continuous_query_recalls'])}")
    
    return "\n".join(lines)
